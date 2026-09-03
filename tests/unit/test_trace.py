"""Characterization tests for trace.py — the T1 trace writer/validator.

The script is the ONE script in this repository that must never fail
closed: its exit code is always 0, and a failure produces one
diagnostic line drawn from the closed error-class vocabulary, which never
echoes the content it failed to read. Those two properties, the schema's
closed vocabularies and the `tokens`/`totalTokens` cross-check are what
the cases below pin.

`trace.py` is deliberately NOT added to conftest's `run` fixture (that
whitelist belongs to the six 0.1.x scripts); this module drives the
script through its own subprocess helper, with the same hardened
environment.

"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

from conftest import hardened_env

SCRIPT = "trace.py"
ROUND = "2026-08-11-101502-auth-plan"

# The form the diagnostic line may take, verbatim, and the whole of what
# it may carry.
DIAGNOSTIC_RE = re.compile(
    r"^(unreadable|unparseable-line|no-usage|id-not-found|schema-refused"
    r"|write-failed): [\w./-]+(:\d+)?$"
)
ERROR_CLASSES = (
    "unreadable",
    "unparseable-line",
    "no-usage",
    "id-not-found",
    "schema-refused",
    "write-failed",
)

# The four canonical example records, copied verbatim. They are the
# acceptance fixture: the validator must take all four unchanged.
EXAMPLE_OPEN = '{"v":1,"kind":"open","round":"2026-08-11-101502-auth-plan","span":"s3.01","parent":"s1.00","stage":3,"actor":"critic","unit":"HA","id_prefix":"HA","agent_id":"0a1b2c3d4e5f60718","model_assigned":"sonnet","started":"2026-08-11T10:16:04Z"}'  # noqa: E501
EXAMPLE_CRITIC = '{"v":1,"kind":"span","round":"2026-08-11-101502-auth-plan","span":"s3.01","parent":"s1.00","stage":3,"actor":"critic","unit":"HA","id_prefix":"HA","agent_id":"0a1b2c3d4e5f60718","ids":[],"id_tags":{},"flags":[],"model_assigned":"sonnet","model_actual":"claude-sonnet-4-6","model_source":"resolvedModel","tokens":{"in":118,"out":14203,"cache_write":96411,"cache_read":1204880},"tokens_source":"agent-tool-result","commit":null,"started":"2026-08-11T10:16:04Z","ended":"2026-08-11T10:33:47Z","wallclock_s":1063,"outcome":"findings:11"}'  # noqa: E501
EXAMPLE_FIXER = '{"v":1,"kind":"span","round":"2026-08-11-101502-auth-plan","span":"s7.02","parent":"s1.00","stage":7,"actor":"fixer","unit":"B2","id_prefix":null,"agent_id":null,"ids":["HA-2","HA-5","HB-1","HB-4"],"id_tags":{},"flags":["criterion-unworkable"],"model_assigned":"opus","model_actual":"unknown","model_source":"n/a","tokens":null,"tokens_source":"absent","commit":"9f31c02","started":"2026-08-11T11:02:10Z","ended":"2026-08-11T11:12:52Z","wallclock_s":642,"outcome":"fixed:3,unworkable:1"}'  # noqa: E501
EXAMPLE_ORCHESTRATOR = '{"v":1,"kind":"span","round":"2026-08-11-101502-auth-plan","span":"s6.03","parent":"s1.00","stage":6,"actor":"orchestrator","unit":"adjudication-batch-3","id_prefix":null,"agent_id":null,"ids":["HV-1","HV-2","HV-3","HV-4"],"id_tags":{"HV-2":["fix-application"],"HV-3":["fix-application","security-pii"],"HV-4":["refuted"]},"flags":[],"model_assigned":"n/a","model_actual":"n/a","model_source":"n/a","tokens":null,"tokens_source":"absent","commit":null,"started":"2026-08-11T11:40:00Z","ended":"2026-08-11T11:46:28Z","wallclock_s":388,"outcome":"upheld:3,refuted:1"}'  # noqa: E501
EXAMPLES = (EXAMPLE_OPEN, EXAMPLE_CRITIC, EXAMPLE_FIXER, EXAMPLE_ORCHESTRATOR)

# The string a leak would have to carry to be detectable. It is shaped
# like the things a trace must never launder: a path, a quote, a token.
POISON = 'SECRET-9f31/etc/passwd "leaked" $(whoami)'
POISON_MARK = "SECRET-9f31"


# --- helpers ---------------------------------------------------------------

@pytest.fixture
def trace(scripts_dir, sandbox_home, tmp_path):
    """Invoke trace.py and return the CompletedProcess."""
    env = hardened_env(sandbox_home)
    cwd = tmp_path / "cwd"
    cwd.mkdir(exist_ok=True)

    def _run(*args: object) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(scripts_dir / SCRIPT), *map(str, args)]
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )

    return _run


@pytest.fixture
def trace_file(tmp_path):
    """Write a trace file from raw lines and return its path."""
    def _write(*lines: str, name: str = "trace.jsonl"):
        path = tmp_path / name
        body = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
        path.write_text(body, encoding="utf-8")
        return path

    return _write


def to_args(path, opts: dict[str, str | None]) -> list[str]:
    """Flatten an option mapping into an `append` argv."""
    args: list[str] = ["append", str(path)]
    for key, value in opts.items():
        if value is None:
            continue
        args += [f"--{key}", value]
    return args


def open_args(path, **over: str | None) -> list[str]:
    """argv for the canonical critic OPEN record, with overrides."""
    opts: dict[str, str | None] = {
        "kind": "open",
        "round": ROUND,
        "span": "s3.01",
        "actor": "critic",
        "unit": "HA",
        "id-prefix": "HA",
        "agent-id": "0a1b2c3d4e5f60718",
        "model-assigned": "sonnet",
        "started": "2026-08-11T10:16:04Z",
    }
    opts.update(over)
    return to_args(path, opts)


def span_args(path, **over: str | None) -> list[str]:
    """argv for the canonical critic CLOSE record, with overrides."""
    opts: dict[str, str | None] = {
        "kind": "span",
        "round": ROUND,
        "span": "s3.01",
        "actor": "critic",
        "unit": "HA",
        "id-prefix": "HA",
        "agent-id": "0a1b2c3d4e5f60718",
        "model-assigned": "sonnet",
        "model-actual": "claude-sonnet-4-6",
        "tokens-in": "118",
        "tokens-out": "14203",
        "cache-write": "96411",
        "cache-read": "1204880",
        "outcome": "findings:11",
        "started": "2026-08-11T10:16:04Z",
        "ended": "2026-08-11T10:33:47Z",
    }
    opts.update(over)
    return to_args(path, opts)


def diagnostics(res) -> list[str]:
    """The lines of the output that are error-class diagnostics."""
    return [
        line
        for line in res.stdout.splitlines()
        if line.split(":", 1)[0] in ERROR_CLASSES
    ]


def defects(res) -> list[str]:
    """The report-only defect lines of the output."""
    return [line for line in res.stdout.splitlines() if line.startswith("defect: ")]


def records(path) -> list[dict]:
    """Decode the trace file into records."""
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# --- usage and the never-fail-closed property ------------------------------

@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_prints_usage_and_exits_zero(trace, flag):
    res = trace(flag)
    assert res.returncode == 0, res.stdout
    assert "Usage:  trace.py append <trace.jsonl>" in res.stdout
    assert "trace.py validate <trace.jsonl>" in res.stdout


def test_docstring_states_the_never_fail_closed_contract(trace):
    """The contract is required to be stated in the docstring itself."""
    res = trace("--help")
    assert "NEVER FAILS CLOSED" in res.stdout
    assert "Exit code: ALWAYS 0" in res.stdout


def test_no_enrich_subcommand_exists(trace, tmp_path):
    """The transcript fallback does not ship in 0.2.0."""
    res = trace("enrich", tmp_path / "trace.jsonl")
    assert res.returncode == 0, res.stdout
    assert "Usage:  trace.py append" in res.stdout
    assert not (tmp_path / "trace.jsonl").exists()


@pytest.mark.parametrize(
    "argv",
    [
        (),
        ("append",),
        ("append", "--kind"),
        ("append", "a.jsonl", "b.jsonl"),
        ("append", "a.jsonl", "--unknown", "x"),
        ("validate",),
        ("validate", "a.jsonl", "b.jsonl"),
        ("nonsense",),
    ],
    ids=[
        "no-args",
        "append-no-path",
        "dangling-option",
        "two-paths",
        "unknown-option",
        "validate-no-path",
        "validate-two-paths",
        "unknown-subcommand",
    ],
)
def test_every_malformed_invocation_exits_zero(trace, argv):
    """The inverse of every other gate here: observability never stops a round."""
    res = trace(*argv)
    assert res.returncode == 0, res.stdout
    assert res.stderr == ""


# --- append: the two records per span --------------------------------------

def test_append_open_creates_the_file_with_the_smaller_field_set(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    res = trace(*open_args(path))
    assert res.returncode == 0, res.stdout
    assert res.stdout == ""
    written = records(path)
    assert len(written) == 1
    assert written[0] == json.loads(EXAMPLE_OPEN)


def test_append_open_without_an_agent_id_omits_the_key(trace, tmp_path):
    """An `open` record carries `agent_id` only where the spawn returned one."""
    path = tmp_path / "trace.jsonl"
    trace(*open_args(path, **{"agent-id": None}))
    assert "agent_id" not in records(path)[0]


def test_append_span_copies_started_from_the_open_record(trace, tmp_path):
    """`started` is copied from disk, never re-read from a clock."""
    path = tmp_path / "trace.jsonl"
    trace(*open_args(path))
    res = trace(*span_args(path, started=None, ended="2026-08-11T10:33:47Z"))
    assert res.returncode == 0, res.stdout
    written = records(path)
    assert len(written) == 2
    assert written[1] == json.loads(EXAMPLE_CRITIC)


def test_append_span_computes_wallclock_from_the_two_timestamps(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    trace(*span_args(path))
    assert records(path)[0]["wallclock_s"] == 1063


def test_append_span_without_an_open_record_is_id_not_found(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text("", encoding="utf-8")
    res = trace(*span_args(path, started=None))
    assert res.returncode == 0
    assert diagnostics(res) == ["id-not-found: trace.jsonl"]
    assert path.read_text(encoding="utf-8") == ""


def test_append_span_on_a_missing_file_is_id_not_found(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, started=None))
    assert diagnostics(res) == ["id-not-found: trace.jsonl"]
    assert not path.exists()


def test_append_span_over_an_unreadable_file_says_unreadable(trace, tmp_path):
    directory = tmp_path / "trace.jsonl"
    directory.mkdir()
    res = trace(*span_args(directory, started=None))
    assert res.returncode == 0
    assert diagnostics(res) == ["unreadable: trace.jsonl"]


def test_append_is_append_only(trace, tmp_path):
    """Nothing already written is ever rewritten in place."""
    path = tmp_path / "trace.jsonl"
    trace(*open_args(path))
    trace(*span_args(path, started=None))
    trace(*open_args(path, span="s3.02"))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert json.loads(lines[0])["kind"] == "open"
    assert json.loads(lines[1])["kind"] == "span"
    assert json.loads(lines[2])["span"] == "s3.02"


def test_write_failure_is_reported_and_still_exits_zero(trace, tmp_path):
    path = tmp_path / "absent-dir" / "trace.jsonl"
    res = trace(*open_args(path))
    assert res.returncode == 0
    assert diagnostics(res) == ["write-failed: trace.jsonl"]


def test_round_span_defaults_to_a_null_parent(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    res = trace(
        *open_args(
            path,
            span="s1.00",
            actor="orchestrator",
            unit="scoping",
            **{"id-prefix": None, "agent-id": None, "model-assigned": None},
        )
    )
    assert res.returncode == 0, res.stdout
    written = records(path)[0]
    assert written["parent"] is None
    assert written["stage"] == 1
    assert written["model_assigned"] == "n/a"


# --- the closed vocabularies -----------------------------------------------

@pytest.mark.parametrize(
    "over",
    [
        {"kind": "close"},
        {"kind": "OPEN"},
        {"actor": "reviewer"},
        {"actor": "Critic"},
        {"round": "not-a-round-folder"},
        {"round": "2026-08-11-101502-Auth_Plan"},
        {"span": "3.01"},
        {"span": "s3.1"},
        {"unit": "lens-with-a-dash"},
        {"unit": "TooLongAPrefix"},
        {"model-assigned": "sonnet 4.6"},
        {"started": "2026-08-11 10:16:04"},
        {"started": "2026-02-30T10:16:04Z"},
        {"id-prefix": None},
    ],
    ids=[
        "kind-close",
        "kind-wrong-case",
        "actor-unknown",
        "actor-wrong-case",
        "round-shape",
        "round-uppercase",
        "span-no-s",
        "span-one-digit-seq",
        "unit-critic-dash",
        "unit-critic-too-long",
        "model-with-space",
        "timestamp-no-t",
        "timestamp-not-a-calendar-day",
        "critic-without-id-prefix",
    ],
)
def test_append_refuses_out_of_vocabulary_values(trace, tmp_path, over):
    path = tmp_path / "trace.jsonl"
    res = trace(*open_args(path, **over))
    assert res.returncode == 0
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]
    assert not path.exists()


def test_stage_zero_never_appears_in_a_valid_trace(trace, tmp_path):
    """The id names the stage that WROTE the span; `s0.00` is refused."""
    path = tmp_path / "trace.jsonl"
    res = trace(*open_args(path, span="s0.00", stage="0"))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]
    assert not path.exists()


def test_span_id_and_stage_must_agree(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    res = trace(*open_args(path, span="s3.01", stage="4"))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]


@pytest.mark.parametrize(
    ("actor", "unit", "accepted"),
    [
        ("verifier", "P1", True),
        ("verifier", "HA", False),
        ("fixer", "B2", True),
        ("fixer", "b2", False),
        ("script", "transcribe.py", True),
        ("script", "rollup.py", True),
        ("script", "make.py", False),
        ("orchestrator", "salvage", True),
        ("orchestrator", "adjudication-batch-3", True),
        ("orchestrator", "adjudication", False),
        # `round` joined the closed orchestrator list; the list is
        # still closed, and a near-miss is still refused.
        ("orchestrator", "round", True),
        ("orchestrator", "rounds", False),
        ("subagent-observed", "general-purpose", True),
        ("subagent-observed", "type with spaces", False),
    ],
)
def test_unit_is_closed_per_actor(trace, tmp_path, actor, unit, accepted):
    path = tmp_path / "trace.jsonl"
    prefix = "HA" if actor in ("critic", "verifier") else None
    model = "n/a" if actor in ("orchestrator", "script") else "sonnet"
    res = trace(
        *open_args(
            path,
            actor=actor,
            unit=unit,
            **{
                "id-prefix": prefix,
                "agent-id": None,
                "model-assigned": model,
            },
        )
    )
    assert res.returncode == 0
    assert (diagnostics(res) == []) is accepted, res.stdout


@pytest.mark.parametrize(
    ("actor", "outcome", "accepted"),
    [
        ("critic", "findings:11", True),
        ("critic", "dropped", True),
        ("critic", "findings:eleven", False),
        ("critic", "findings:11 plus a note", False),
        ("verifier", "L:9,P:1,NOT:0,new:2", True),
        ("verifier", "L:9", False),
        ("fixer", "fixed:3,unworkable:1", True),
        ("fixer", "fixed:3,unworkable:1,notfound:2", True),
        ("fixer", "fixed:3", False),
        ("fixer", "fixed:3,notfound:2", False),
        ("fixer", "fixed:3,unworkable:1,notfound:2,dropped:1", False),
        ("script", "ok", True),
        ("script", "error:unparseable-line", True),
        ("script", "error:whatever", False),
        ("orchestrator", "upheld:3,refuted:1", True),
        ("orchestrator", "salvaged", True),
        ("orchestrator", "adjudicated", False),
    ],
)
def test_outcome_is_closed_per_actor(trace, tmp_path, actor, outcome, accepted):
    path = tmp_path / "trace.jsonl"
    units = {
        "critic": "HA",
        "verifier": "P1",
        "fixer": "B2",
        "script": "recount.py",
        "orchestrator": "salvage",
    }
    prefix = "HA" if actor in ("critic", "verifier") else None
    model = "n/a" if actor in ("orchestrator", "script") else "sonnet"
    actual = "n/a" if actor in ("orchestrator", "script") else "unknown"
    res = trace(
        *span_args(
            path,
            actor=actor,
            unit=units[actor],
            outcome=outcome,
            **{
                "id-prefix": prefix,
                "agent-id": None,
                "model-assigned": model,
                "model-actual": actual,
                "tokens-in": None,
                "tokens-out": None,
                "cache-write": None,
                "cache-read": None,
            },
        )
    )
    assert (diagnostics(res) == []) is accepted, res.stdout


# The fixer bound BEFORE `notfound:` joined the outcome. Named here because
# the case below asserts both sides of the raise, and one of the two sides
# is a statement about the bound that no longer exists in the script.
PREVIOUS_FIXER_MAX_LEN = 32
# The realistic two-digit batch: ten fixed, ten unworkable, ten with no
# premise. Thirty-four characters, so the pattern alone never decided it.
TWO_DIGIT_FIXER_OUTCOME = "fixed:10,unworkable:10,notfound:10"


def test_a_two_digit_three_part_fixer_outcome_is_accepted(trace, tmp_path):
    """Both sides of the raise: too long for the old bound, taken by the new.

    `bounded` cuts by LENGTH independently of the pattern, so a three-part
    outcome that matches perfectly would still have been refused at 32. The
    fixture is the realistic case, not the worst one: a batch of ten is
    ordinary, and it is already two characters over the old bound.
    """
    assert len(TWO_DIGIT_FIXER_OUTCOME) == 34
    assert len(TWO_DIGIT_FIXER_OUTCOME) > PREVIOUS_FIXER_MAX_LEN
    path = tmp_path / "trace.jsonl"
    res = trace(
        *span_args(
            path,
            actor="fixer",
            unit="B2",
            outcome=TWO_DIGIT_FIXER_OUTCOME,
            **{
                "id-prefix": None,
                "agent-id": None,
                "model-assigned": "opus",
                "model-actual": "unknown",
                "tokens-in": None,
                "tokens-out": None,
                "cache-write": None,
                "cache-read": None,
            },
        )
    )
    assert diagnostics(res) == [], res.stdout
    written = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert written["outcome"] == TWO_DIGIT_FIXER_OUTCOME


def test_the_worst_case_three_part_outcome_still_fits_the_bound(trace, tmp_path):
    """Four digits in every counter — 40 characters, under the bound of 48."""
    worst = "fixed:9999,unworkable:9999,notfound:9999"
    assert len(worst) == 40
    path = tmp_path / "trace.jsonl"
    res = trace(
        *span_args(
            path,
            actor="fixer",
            unit="B2",
            outcome=worst,
            **{
                "id-prefix": None,
                "agent-id": None,
                "model-assigned": "opus",
                "model-actual": "unknown",
                "tokens-in": None,
                "tokens-out": None,
                "cache-write": None,
                "cache-read": None,
            },
        )
    )
    assert diagnostics(res) == [], res.stdout


@pytest.mark.parametrize(
    ("flags", "accepted"),
    [("respawn", True), ("bundled,degraded", True), ("rerun", False)],
)
def test_flags_are_a_closed_vocabulary(trace, tmp_path, flags, accepted):
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, flags=flags))
    assert (diagnostics(res) == []) is accepted, res.stdout


@pytest.mark.parametrize(
    ("tags", "accepted"),
    [
        ('{"HV-2":["fix-application"]}', True),
        ('{"HV-2":["security-pii","duplicate","refuted"]}', True),
        ('{"HV-2":["blocker"]}', False),
        ('{"HV2":["refuted"]}', False),
        ("not json", False),
    ],
)
def test_id_tags_are_a_closed_vocabulary(trace, tmp_path, tags, accepted):
    path = tmp_path / "trace.jsonl"
    res = trace(
        *span_args(
            path,
            span="s6.03",
            actor="orchestrator",
            unit="adjudication-batch-3",
            ids="HV-2",
            outcome="upheld:1,refuted:0",
            **{
                "id-tags": tags,
                "id-prefix": None,
                "agent-id": None,
                "model-assigned": "n/a",
                "model-actual": "n/a",
                "tokens-in": None,
                "tokens-out": None,
                "cache-write": None,
                "cache-read": None,
            },
        )
    )
    assert (diagnostics(res) == []) is accepted, res.stdout


def test_id_tags_are_written_at_stage_six_only(trace, tmp_path):
    """`id_tags` is written at stage 6 and nowhere else."""
    path = tmp_path / "trace.jsonl"
    res = trace(
        *span_args(
            path,
            span="s7.02",
            actor="fixer",
            unit="B2",
            ids="HA-2",
            outcome="fixed:1,unworkable:0",
            **{
                "id-tags": '{"HA-2":["fix-application"]}',
                "id-prefix": None,
                "model-actual": "unknown",
            },
        )
    )
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]


def test_commit_belongs_to_stage_seven_spans(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    accepted = trace(
        *span_args(
            path,
            span="s7.02",
            actor="fixer",
            unit="B2",
            commit="9f31c02",
            outcome="fixed:1,unworkable:0",
            **{"id-prefix": None, "model-actual": "unknown"},
        )
    )
    assert diagnostics(accepted) == [], accepted.stdout
    refused = trace(*span_args(path, commit="9f31c02"))
    assert diagnostics(refused) == ["schema-refused: trace.jsonl"]


# --- tokens: the tool-result capture and its rules -------------------------

def test_primary_capture_defaults_to_the_tool_result_sources(trace, tmp_path):
    """Counters plus the resolved model, recorded verbatim."""
    path = tmp_path / "trace.jsonl"
    trace(*span_args(path))
    written = records(path)[0]
    assert written["tokens"] == {
        "in": 118,
        "out": 14203,
        "cache_write": 96411,
        "cache_read": 1204880,
    }
    assert written["tokens_source"] == "agent-tool-result"
    assert written["model_source"] == "resolvedModel"
    assert written["agent_id"] == "0a1b2c3d4e5f60718"


def test_missing_usage_is_null_and_absent_never_zero(trace, tmp_path):
    """A missing token number is `null`, never `0`, never omitted."""
    path = tmp_path / "trace.jsonl"
    trace(
        *span_args(
            path,
            **{
                "tokens-in": None,
                "tokens-out": None,
                "cache-write": None,
                "cache-read": None,
                "model-actual": "unknown",
            },
        )
    )
    written = records(path)[0]
    assert written["tokens"] is None
    assert written["tokens_source"] == "absent"
    assert written["model_source"] == "n/a"


def test_a_partial_counter_set_is_refused(trace, tmp_path):
    """Three of four counters would need a zero stand-in, which is banned."""
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, **{"cache-read": None}))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]


def test_a_bare_total_tokens_is_written_under_its_own_source(trace, tmp_path):
    """`append` writes the aggregate-alone record `validate` accepts — and
    only where `--tokens-source` names that delivery.
    """  # noqa: D205  # two sentences, one rule
    path = tmp_path / "trace.jsonl"
    bare: dict[str, str | None] = {
        "total-tokens": "1315612",
        "tokens-in": None,
        "tokens-out": None,
        "cache-write": None,
        "cache-read": None,
    }
    accepted = trace(
        *span_args(path, **bare, **{"tokens-source": "agent-tool-result-total"})
    )
    assert diagnostics(accepted) == [], accepted.stdout
    written = records(path)
    assert len(written) == 1
    assert written[0]["tokens"] == {"total": 1315612}
    assert written[0]["tokens_source"] == "agent-tool-result-total"
    # PRESERVED: the same bare aggregate is refused where the source does not
    # name the total-only delivery — defaulted, or given as another source.
    for over in ({}, {"tokens-source": "agent-tool-result"}):
        refused = trace(*span_args(path, **bare, **over))
        assert diagnostics(refused) == ["schema-refused: trace.jsonl"]
    assert len(records(path)) == 1


def test_non_integer_counters_are_refused(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, **{"tokens-in": "many"}))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]


def test_tokens_null_with_a_source_other_than_absent_is_refused(trace, trace_file):
    line = json.loads(EXAMPLE_FIXER)
    line["tokens_source"] = "agent-tool-result"
    path = trace_file(json.dumps(line))
    res = trace("validate", path)
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_orchestrator_spans_carry_no_tokens(trace, trace_file):
    """The main loop's spend is never attributed."""
    line = json.loads(EXAMPLE_ORCHESTRATOR)
    line["tokens"] = {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4}
    line["tokens_source"] = "agent-tool-result"
    path = trace_file(json.dumps(line))
    res = trace("validate", path)
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_total_tokens_cross_check_passes_when_the_sum_agrees(trace, tmp_path):
    """The four counters are checked against `totalTokens`."""
    path = tmp_path / "trace.jsonl"
    total = 118 + 14203 + 96411 + 1204880
    trace(*span_args(path, **{"total-tokens": str(total)}))
    res = trace("validate", path)
    assert records(path)[0]["tokens"]["total"] == total
    assert defects(res) == []
    assert diagnostics(res) == []


def test_total_tokens_cross_check_reports_a_mismatch(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    trace(*span_args(path, **{"total-tokens": "42"}))
    res = trace("validate", path)
    assert res.returncode == 0
    assert defects(res) == ["defect: total-tokens-mismatch line 1"]


# --- tokens: the total-only delivery ---------------------------------------

def total_only(**over: object) -> str:
    """A closing record measured as ONE aggregate — no four counters."""
    line = json.loads(EXAMPLE_CRITIC)
    line["tokens"] = {"total": 1315612}
    line["tokens_source"] = "agent-tool-result-total"
    line.update(over)
    return json.dumps(line)


def test_a_single_total_key_is_valid_for_the_total_only_source(trace, trace_file):
    """`{"total": n}` is the shape `agent-tool-result-total` delivers."""
    res = trace("validate", trace_file(total_only()))
    assert diagnostics(res) == []
    assert defects(res) == []


def test_the_four_counter_form_stays_valid_beside_the_new_branch(trace, trace_file):
    """PRESERVED: the branch was ADDED, it did not replace the old form."""
    res = trace("validate", trace_file(EXAMPLE_CRITIC))
    assert diagnostics(res) == []
    assert defects(res) == []


def test_a_total_only_object_is_refused_for_the_four_counter_source(
    trace, trace_file
):
    """The one-key form is admitted for its own source and no other."""
    line = total_only(tokens_source="agent-tool-result")
    res = trace("validate", trace_file(line))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_the_four_counter_form_is_refused_for_the_total_only_source(
    trace, trace_file
):
    """The source names what was measured: an aggregate, and nothing else."""
    line = json.loads(EXAMPLE_CRITIC)
    line["tokens_source"] = "agent-tool-result-total"
    res = trace("validate", trace_file(json.dumps(line)))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_a_negative_total_is_refused_in_the_total_only_form(trace, trace_file):
    res = trace("validate", trace_file(total_only(tokens={"total": -1})))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_a_counter_riding_beside_the_total_is_refused(trace, trace_file):
    """`total` and nothing else: an aggregate carrying a PARTIAL breakdown
    is not the shape the source names, and exact equality is what says so.
    """  # noqa: D205  # two sentences, one rule
    line = total_only(tokens={"total": 1315612, "in": 118})
    res = trace("validate", trace_file(line))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_all_five_token_keys_are_refused_in_the_total_only_form(trace, trace_file):
    """Nor may the FULL four-counter breakdown ride along with the aggregate."""
    line = total_only(
        tokens={
            "in": 118,
            "out": 14203,
            "cache_write": 96411,
            "cache_read": 1204880,
            "total": 1315612,
        }
    )
    res = trace("validate", trace_file(line))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_validate_on_a_total_only_trace_prints_the_normal_summary(
    trace, trace_file
):
    """The RUN, not the predicate: the reader of the four counters used to
    raise on this record, and `main()` printed `write-failed` in its place.
    """  # noqa: D205  # two sentences, one rule
    res = trace("validate", trace_file(total_only()))
    assert res.returncode == 0
    assert res.stderr == ""
    assert "write-failed" not in res.stdout
    assert "trace: 1 spans, 0 unclosed, 0 refused lines, 0 defects" in res.stdout


# --- models ----------------------------------------------------------------

def test_model_actual_is_never_silently_equal_to_model_assigned(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, **{"model-actual": "sonnet"}))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]


def test_model_actual_na_is_refused_for_a_spawn_actor(trace, tmp_path):
    """For critic/fixer/verifier, absence of an observation is `unknown`."""
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, **{"model-actual": "n/a"}))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]


def test_orchestrator_spans_read_na_in_both_model_cells(trace, trace_file):
    """The one permitted equality: none assigned, none observed."""
    res = trace("validate", trace_file(EXAMPLE_ORCHESTRATOR))
    assert diagnostics(res) == []
    line = json.loads(EXAMPLE_ORCHESTRATOR)
    line["model_actual"] = "unknown"
    res = trace("validate", trace_file(json.dumps(line), name="second.jsonl"))
    assert diagnostics(res) == ["schema-refused: second.jsonl:1"]


@pytest.mark.parametrize(
    ("source", "accepted"),
    [("resolvedModel", True), ("self-report", True), ("n/a", True),
     ("agent-tool-result", False)],
)
def test_model_source_is_a_closed_enum(trace, tmp_path, source, accepted):
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, **{"model-source": source}))
    assert (diagnostics(res) == []) is accepted, res.stdout


def test_self_report_is_removed_from_the_token_source_enum(trace, trace_file):
    """`tokens_source: self-report` has no producer and is refused."""
    line = json.loads(EXAMPLE_CRITIC)
    line["tokens_source"] = "self-report"
    res = trace("validate", trace_file(json.dumps(line)))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


# --- subagent-observed pairing ---------------------------------------------

def observed(**over):
    """A `subagent-observed` span, the only single-line span class."""
    line = {
        "v": 1,
        "kind": "span",
        "round": ROUND,
        "span": "s3.04",
        "parent": "s1.00",
        "stage": 3,
        "actor": "subagent-observed",
        "unit": "general-purpose",
        "id_prefix": None,
        "agent_id": "0a1b2c3d4e5f60718",
        "ids": [],
        "id_tags": {},
        "flags": [],
        "model_assigned": "sonnet",
        "model_actual": "claude-sonnet-4-6",
        "model_source": "resolvedModel",
        "tokens": {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4},
        "tokens_source": "subagent-transcript",
        "commit": None,
        "started": "2026-08-11T10:16:04Z",
        "ended": "2026-08-11T10:17:04Z",
        "wallclock_s": 60,
        "outcome": "observed:tokens",
    }
    line.update(over)
    return json.dumps(line)


def test_observed_tokens_pairs_with_a_recovered_usage(trace, trace_file):
    res = trace("validate", trace_file(observed()))
    assert diagnostics(res) == []
    assert defects(res) == []


def test_observed_no_tokens_pairs_with_a_null_usage(trace, trace_file):
    line = observed(
        outcome="observed:no-tokens", tokens=None, tokens_source="absent"
    )
    res = trace("validate", trace_file(line))
    assert diagnostics(res) == []


def test_observed_tokens_with_the_other_token_state_is_refused(trace, trace_file):
    line = observed(tokens=None, tokens_source="absent")
    res = trace("validate", trace_file(line))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_observed_no_tokens_with_a_usage_is_refused(trace, trace_file):
    line = observed(outcome="observed:no-tokens")
    res = trace("validate", trace_file(line))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


# --- validate: the examples, the record shapes, the defects ----------------

def test_validate_accepts_the_four_canonical_examples(trace, trace_file):
    """The acceptance fixture: all four canonical examples, verbatim."""
    res = trace("validate", trace_file(*EXAMPLES))
    assert res.returncode == 0, res.stdout
    assert diagnostics(res) == []
    assert defects(res) == []
    # The critic `span` supersedes its `open` record: the pair counts once.
    assert res.stdout.strip().splitlines()[-1] == (
        "trace: 3 spans, 0 unclosed, 0 refused lines, 0 defects"
    )


@pytest.mark.parametrize("example", EXAMPLES, ids=["open", "critic", "fixer", "orch"])
def test_each_example_validates_on_its_own(trace, trace_file, example):
    res = trace("validate", trace_file(example))
    assert diagnostics(res) == []


def test_an_open_record_with_an_extra_key_is_refused(trace, trace_file):
    """An `open` carries the smaller field set and no other key."""
    line = json.loads(EXAMPLE_OPEN)
    line["ended"] = "2026-08-11T10:33:47Z"
    res = trace("validate", trace_file(json.dumps(line)))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_a_span_record_missing_a_mandatory_field_is_refused(trace, trace_file):
    line = json.loads(EXAMPLE_CRITIC)
    del line["wallclock_s"]
    res = trace("validate", trace_file(json.dumps(line)))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_an_unknown_schema_version_is_skipped_and_said_so(trace, trace_file):
    """A reader that does not know `v` skips the line and says so."""
    line = json.loads(EXAMPLE_CRITIC)
    line["v"] = 2
    res = trace("validate", trace_file(json.dumps(line)))
    assert res.returncode == 0
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_unclosed_spans_are_reported_and_change_no_exit_code(trace, trace_file):
    """An interrupted round leaves the prefix already written."""
    path = trace_file(EXAMPLE_OPEN, EXAMPLE_FIXER)
    res = trace("validate", path)
    assert res.returncode == 0
    assert "trace: 1 unclosed spans (round interrupted)" in res.stdout


def test_a_second_span_record_for_one_id_is_a_defect(trace, trace_file):
    res = trace("validate", trace_file(EXAMPLE_CRITIC, EXAMPLE_CRITIC))
    assert res.returncode == 0
    assert defects(res) == ["defect: duplicate-span line 2"]


def test_a_critic_unit_id_prefix_disagreement_is_a_defect(trace, trace_file):
    line = json.loads(EXAMPLE_CRITIC)
    line["id_prefix"] = "HB"
    res = trace("validate", trace_file(json.dumps(line)))
    assert defects(res) == ["defect: unit-id-prefix-disagreement line 1"]


def test_a_wallclock_disagreement_is_a_defect(trace, trace_file):
    line = json.loads(EXAMPLE_CRITIC)
    line["wallclock_s"] = 7
    res = trace("validate", trace_file(json.dumps(line)))
    assert defects(res) == ["defect: wallclock-mismatch line 1"]


def test_an_id_tag_naming_an_id_outside_ids_is_a_defect(trace, trace_file):
    line = json.loads(EXAMPLE_ORCHESTRATOR)
    line["id_tags"]["HV-9"] = ["refuted"]
    res = trace("validate", trace_file(json.dumps(line)))
    assert defects(res) == ["defect: id-tags-orphan line 1"]


def test_blank_lines_are_ignored(trace, trace_file):
    res = trace("validate", trace_file(EXAMPLE_CRITIC, "", "   ", EXAMPLE_FIXER))
    assert diagnostics(res) == []
    assert "trace: 2 spans" in res.stdout


def test_validate_on_a_missing_file_says_unreadable(trace, tmp_path):
    res = trace("validate", tmp_path / "absent.jsonl")
    assert res.returncode == 0
    assert diagnostics(res) == ["unreadable: absent.jsonl"]
    assert res.stderr == ""


def test_validate_on_an_unreadable_path_says_unreadable(trace, tmp_path):
    directory = tmp_path / "trace.jsonl"
    directory.mkdir()
    res = trace("validate", directory)
    assert diagnostics(res) == ["unreadable: trace.jsonl"]


def test_validate_on_an_empty_file_reports_nothing_found(trace, trace_file):
    res = trace("validate", trace_file())
    assert res.returncode == 0
    assert res.stdout.strip() == (
        "trace: 0 spans, 0 unclosed, 0 refused lines, 0 defects"
    )


# --- privacy: the content rule and the failure output ----------------------

def test_poisoned_content_never_reaches_the_trace_or_the_output(trace, tmp_path):
    """Poisoned fields through the token-capture path."""
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, unit=POISON))
    assert res.returncode == 0
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]
    assert POISON_MARK not in res.stdout
    assert POISON_MARK not in res.stderr
    assert not path.exists()


@pytest.mark.parametrize(
    "field",
    ["round", "unit", "id-prefix", "agent-id", "model-assigned", "model-actual",
     "outcome", "commit", "started"],
)
def test_no_field_launders_content_through_append(trace, tmp_path, field):
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, **{field: POISON}))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]
    assert POISON_MARK not in res.stdout + res.stderr
    assert not path.exists()


def test_a_poisoned_path_cannot_widen_the_diagnostic(trace, tmp_path):
    """The diagnostic prints a sanitized file NAME, never a path."""
    poisoned = tmp_path / ('bad name; echo ' + POISON_MARK + '.jsonl')
    res = trace("validate", poisoned)
    assert res.returncode == 0
    assert len(diagnostics(res)) == 1
    assert DIAGNOSTIC_RE.match(diagnostics(res)[0]), diagnostics(res)[0]
    assert "/" not in diagnostics(res)[0].split(": ", 1)[1]


@pytest.mark.parametrize(
    "line",
    [
        '{"v":1,"kind":"span","round":"' + ROUND + '","note":"' + POISON_MARK + '"',
        '{"v":1,"kind":"span","unit":"' + POISON_MARK + '"} trailing ' + POISON_MARK,
        "not json at all: " + POISON_MARK,
    ],
    ids=["truncated", "trailing-garbage", "not-json"],
)
def test_the_failure_path_never_echoes_the_bytes_it_could_not_parse(
    trace, trace_file, line
):
    """The failure half of the poisoned fixture."""
    res = trace("validate", trace_file(line))
    assert res.returncode == 0
    printed = diagnostics(res)
    assert len(printed) == 1
    assert printed[0] == "unparseable-line: trace.jsonl:1"
    assert DIAGNOSTIC_RE.match(printed[0])
    assert POISON_MARK not in res.stdout + res.stderr


def test_a_wrong_shape_with_poisoned_content_is_refused_without_an_echo(
    trace, trace_file
):
    line = json.loads(EXAMPLE_CRITIC)
    line["note"] = POISON
    line["outcome"] = POISON
    res = trace("validate", trace_file(json.dumps(line)))
    printed = diagnostics(res)
    assert printed == ["schema-refused: trace.jsonl:1"]
    assert DIAGNOSTIC_RE.match(printed[0])
    assert POISON_MARK not in res.stdout + res.stderr


def test_every_diagnostic_the_script_can_print_matches_the_closed_form(
    trace, tmp_path, trace_file
):
    """One assertion over all reachable classes, so none can widen quietly."""
    produced: list[str] = []
    produced += diagnostics(trace("validate", tmp_path / "absent.jsonl"))
    produced += diagnostics(trace("validate", trace_file("{oops")))
    produced += diagnostics(trace("validate", trace_file('{"v":1}', name="b.jsonl")))
    produced += diagnostics(trace(*span_args(tmp_path / "c.jsonl", started=None)))
    produced += diagnostics(trace(*open_args(tmp_path / "no-dir" / "d.jsonl")))
    assert len(produced) == 5
    classes = {line.split(":", 1)[0] for line in produced}
    assert classes == {
        "unreadable",
        "unparseable-line",
        "schema-refused",
        "id-not-found",
        "write-failed",
    }
    for line in produced:
        assert DIAGNOSTIC_RE.match(line), line


def test_the_script_contains_no_network_primitive_and_no_subprocess(scripts_dir):
    """No network and no child process, asserted on the shipped file itself."""
    text = (scripts_dir / SCRIPT).read_text(encoding="utf-8")
    for forbidden in ("urllib", "requests", "socket", "ftplib", "smtplib",
                      "http.client", "subprocess"):
        assert forbidden not in text, forbidden


# --- validate refuses type confusion, not only bad vocabulary --------------

def mutate(example: str, **patch) -> str:
    """A canonical example with fields replaced."""
    line = json.loads(example)
    line.update(patch)
    return json.dumps(line)


def round_span(**over) -> str:
    """The round span `s1.00` — the one span with a null parent."""
    line = {
        "v": 1,
        "kind": "span",
        "round": ROUND,
        "span": "s1.00",
        "parent": None,
        "stage": 1,
        "actor": "orchestrator",
        "unit": "closure",
        "id_prefix": None,
        "agent_id": None,
        "ids": [],
        "id_tags": {},
        "flags": [],
        "model_assigned": "n/a",
        "model_actual": "n/a",
        "model_source": "n/a",
        "tokens": None,
        "tokens_source": "absent",
        "commit": None,
        "started": "2026-08-11T10:00:00Z",
        "ended": "2026-08-11T12:00:00Z",
        "wallclock_s": 7200,
        "outcome": "closed",
    }
    line.update(over)
    return json.dumps(line)


def test_the_round_span_validates_with_a_null_parent(trace, trace_file):
    res = trace("validate", trace_file(round_span()))
    assert diagnostics(res) == []
    assert defects(res) == []


def test_the_round_span_pair_carries_unit_round(trace, tmp_path):
    """`s1.00` has its own orchestrator unit, `round`.

    Stage 1 writes the `open` record and stage 9 the close; `stage` stays
    1 on both, because the id names the stage that WROTE the span, and the
    close carries the existing step outcome `closed`.
    """
    path = tmp_path / "trace.jsonl"
    common: dict[str, str | None] = {
        "round": ROUND,
        "span": "s1.00",
        "actor": "orchestrator",
        "unit": "round",
        "id-prefix": None,
        "agent-id": None,
        "model-assigned": None,
    }
    opened = trace(
        *to_args(path, {"kind": "open", **common, "started": "2026-08-11T10:00:00Z"})
    )
    assert opened.returncode == 0
    assert diagnostics(opened) == [], opened.stdout
    closed = trace(
        *to_args(
            path,
            {
                "kind": "span",
                **common,
                "outcome": "closed",
                "ended": "2026-08-11T12:00:00Z",
            },
        )
    )
    assert closed.returncode == 0
    assert diagnostics(closed) == [], closed.stdout

    written = records(path)
    assert [r["kind"] for r in written] == ["open", "span"]
    assert [r["unit"] for r in written] == ["round", "round"]
    assert [r["stage"] for r in written] == [1, 1]
    assert [r["parent"] for r in written] == [None, None]
    assert written[1]["started"] == "2026-08-11T10:00:00Z"
    assert written[1]["outcome"] == "closed"

    res = trace("validate", path)
    assert res.returncode == 0
    assert diagnostics(res) == []
    assert defects(res) == []
    assert res.stdout.splitlines()[-1] == (
        "trace: 1 spans, 0 unclosed, 0 refused lines, 0 defects"
    )


@pytest.mark.parametrize(
    "line",
    [
        "[1, 2]",
        '"a bare string"',
        mutate(EXAMPLE_CRITIC, ids="HA-1"),
        mutate(EXAMPLE_CRITIC, ids=[1]),
        mutate(EXAMPLE_CRITIC, ids=["HA1"]),
        mutate(EXAMPLE_CRITIC, stage="3"),
        mutate(EXAMPLE_CRITIC, stage=True),
        mutate(EXAMPLE_CRITIC, parent=17),
        mutate(EXAMPLE_CRITIC, unit=17),
        mutate(EXAMPLE_CRITIC, model_assigned=17),
        mutate(EXAMPLE_CRITIC, model_actual=17),
        mutate(EXAMPLE_CRITIC, id_tags=["HA-1"]),
        mutate(EXAMPLE_CRITIC, tokens=5),
        mutate(EXAMPLE_CRITIC, tokens_source="absent"),
        mutate(
            EXAMPLE_CRITIC,
            tokens={"in": 1, "out": 2, "cache_write": 3, "cache_read": 4, "x": 5},
        ),
        mutate(
            EXAMPLE_CRITIC,
            tokens={"in": -1, "out": 2, "cache_write": 3, "cache_read": 4},
        ),
        mutate(EXAMPLE_CRITIC, ended="2026-08-11T10:00:00Z"),
        mutate(EXAMPLE_CRITIC, wallclock_s="1063"),
        mutate(EXAMPLE_CRITIC, wallclock_s=-1),
        mutate(EXAMPLE_FIXER, id_prefix="HA"),
        mutate(EXAMPLE_ORCHESTRATOR, agent_id="0a1b2c3d"),
        mutate(EXAMPLE_ORCHESTRATOR, model_assigned="opus"),
        mutate(EXAMPLE_ORCHESTRATOR, unit="adjudication-batch-" + "9" * 20),
        round_span(parent="s1.00"),
        '{"1": 2, "kind": "span"}',
    ],
    ids=[
        "top-level-list",
        "top-level-string",
        "ids-not-a-list",
        "ids-item-not-a-string",
        "ids-item-not-an-id",
        "stage-as-string",
        "stage-as-bool",
        "parent-not-a-string",
        "unit-not-a-string",
        "model-assigned-not-a-string",
        "model-actual-not-a-string",
        "id-tags-not-an-object",
        "tokens-not-an-object",
        "tokens-present-but-source-absent",
        "tokens-extra-key",
        "tokens-negative-counter",
        "ended-before-started",
        "wallclock-as-string",
        "wallclock-negative",
        "id-prefix-on-a-fixer",
        "agent-id-on-an-orchestrator",
        "model-assigned-on-an-orchestrator",
        "orchestrator-unit-too-long",
        "round-span-with-a-parent",
        "missing-required-keys",
    ],
)
def test_validate_refuses_a_wrong_type_as_firmly_as_a_wrong_word(
    trace, trace_file, line
):
    res = trace("validate", trace_file(line))
    assert res.returncode == 0
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_a_non_utf8_trace_is_unreadable_not_a_traceback(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_bytes(b'{"v":1,\xff\xfe}\n')
    res = trace("validate", path)
    assert res.returncode == 0
    assert diagnostics(res) == ["unreadable: trace.jsonl"]
    assert res.stderr == ""


# --- append: option parsing edges -----------------------------------------

@pytest.mark.parametrize(
    "over",
    [{"stage": "three"}, {"total-tokens": "lots"}],
    ids=["stage-not-an-integer", "total-tokens-not-an-integer"],
)
def test_non_integer_options_are_refused(trace, tmp_path, over):
    path = tmp_path / "trace.jsonl"
    res = trace(*span_args(path, **over))
    assert diagnostics(res) == ["schema-refused: trace.jsonl"]
    assert not path.exists()


def test_an_explicit_parent_is_honoured(trace, tmp_path):
    path = tmp_path / "trace.jsonl"
    res = trace(*open_args(path, parent="s2.01"))
    assert diagnostics(res) == [], res.stdout
    assert records(path)[0]["parent"] == "s2.01"


def test_the_open_lookup_walks_past_noise_lines(trace, trace_file):
    """A close finds its own open record even beside blanks and junk."""
    path = trace_file(
        "",
        "not json",
        '"a bare string"',
        mutate(EXAMPLE_OPEN, span="s3.09"),
        EXAMPLE_OPEN,
    )
    res = trace(*span_args(path, started=None, ended="2026-08-11T10:33:47Z"))
    assert diagnostics(res) == [], res.stdout
    written = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(written[-1])["started"] == "2026-08-11T10:16:04Z"


# --- the composite finding id -----------------------------------------------
#
# The finding-id shape here is `recount.py`'s id contract, which accepts a
# dash-joined composite prefix (`V-CIT-1`) — the form a verifier uses to keep
# the lens it re-checked inside the id. A narrower shape would make a span
# naming such a finding `schema-refused`, which is a trace hole exactly where
# the round did the most work.

def test_a_span_naming_a_composite_finding_id_is_written_and_validates(
    trace, tmp_path
):
    """`V-CIT-1` is the id contract's composite form, not a malformed id."""
    path = tmp_path / "trace.jsonl"
    appended = trace(
        *span_args(
            path,
            span="s7.02",
            actor="fixer",
            unit="B2",
            ids="V-CIT-1,HA-2",
            outcome="fixed:2,unworkable:0",
            **{"id-prefix": None, "model-actual": "unknown"},
        )
    )
    assert diagnostics(appended) == [], appended.stdout
    assert records(path)[0]["ids"] == ["V-CIT-1", "HA-2"]
    validated = trace("validate", path)
    assert validated.returncode == 0
    assert diagnostics(validated) == [], validated.stdout


# --- the owner-wait span: an orchestrator unit, not a new actor -------------
#
# Waiting for the owner is recorded as an orchestrator UNIT with two closed
# vocabularies of its own — a reason inside the unit name and an outcome
# (`answered | refused | abandoned`). The outcome check is UNIT-aware for
# exactly one reason: a single merged pattern would pass `scoped` on an
# owner-wait span and `answered` on `scoping`, and the schema would stop
# telling the two units apart. The cases below pin that discrimination in
# both directions, and the length bound the longest reason sits on.

OWNER_WAIT_REASONS = (
    "signature",
    "authorization",
    "fork",
    "amendment",
    "ratification",
    "z3-closure",
)
# The bound as the script itself states it — read out of the source text,
# never re-typed here, so a change to the constant fails this test rather
# than passing under a stale copy.
ORCHESTRATOR_UNIT_LEN_RE = re.compile(
    r"^MAX_ORCHESTRATOR_UNIT_LEN = (\d+)$", re.MULTILINE
)


def owner_wait(**over) -> str:
    """An owner-wait span: the orchestrator's own record of a wait."""
    line = {
        "v": 1,
        "kind": "span",
        "round": ROUND,
        "span": "s9.01",
        "parent": "s1.00",
        "stage": 9,
        "actor": "orchestrator",
        "unit": "owner-wait-signature",
        "id_prefix": None,
        "agent_id": None,
        "ids": [],
        "id_tags": {},
        "flags": [],
        "model_assigned": "n/a",
        "model_actual": "n/a",
        "model_source": "n/a",
        "tokens": None,
        "tokens_source": "absent",
        "commit": None,
        "started": "2026-08-11T11:50:00Z",
        "ended": "2026-08-11T12:05:00Z",
        "wallclock_s": 900,
        "outcome": "answered",
    }
    line.update(over)
    return json.dumps(line)


def test_an_owner_wait_span_validates(trace, trace_file):
    """The fixture the unmodified code refused: the unit was not in the list."""
    res = trace("validate", trace_file(owner_wait()))
    assert res.returncode == 0, res.stdout
    assert diagnostics(res) == [], res.stdout
    assert defects(res) == []
    assert res.stdout.strip().splitlines()[-1] == (
        "trace: 1 spans, 0 unclosed, 0 refused lines, 0 defects"
    )


@pytest.mark.parametrize("reason", OWNER_WAIT_REASONS)
def test_every_reason_of_the_closed_vocabulary_is_accepted(trace, trace_file, reason):
    res = trace("validate", trace_file(owner_wait(unit=f"owner-wait-{reason}")))
    assert diagnostics(res) == [], res.stdout


@pytest.mark.parametrize("outcome", ["answered", "refused", "abandoned"])
def test_every_owner_wait_outcome_is_accepted(trace, trace_file, outcome):
    res = trace("validate", trace_file(owner_wait(outcome=outcome)))
    assert diagnostics(res) == [], res.stdout


@pytest.mark.parametrize(
    ("unit", "outcome", "accepted"),
    [
        ("owner-wait-signature", "answered", True),
        # The discrimination itself: neither word crosses to the other unit.
        ("owner-wait-signature", "scoped", False),
        ("scoping", "answered", False),
        # A reason outside the closed vocabulary is not an owner-wait unit.
        ("owner-wait-lunch", "answered", False),
        ("owner-wait-lunch", "scoped", False),
        # And the orchestrator's own units keep their own outcomes.
        ("scoping", "scoped", True),
        ("closure", "closed", True),
        ("adjudication-batch-3", "upheld:1,refuted:0", True),
    ],
)
def test_the_outcome_check_tells_the_orchestrator_units_apart(
    trace, trace_file, unit, outcome, accepted
):
    res = trace("validate", trace_file(owner_wait(unit=unit, outcome=outcome)))
    assert res.returncode == 0
    assert (diagnostics(res) == []) is accepted, res.stdout


def test_an_owner_wait_span_carrying_tokens_is_refused(trace, trace_file):
    """A PRESERVED property, not evidence of this change.

    `valid_tokens` already refuses any `tokens` on an orchestrator span,
    and did so before the owner-wait unit existed — this case reads the
    same before and after. It is pinned so the new unit cannot acquire a
    token cell through a later widening.
    """
    line = owner_wait(
        tokens={"in": 1, "out": 2, "cache_write": 3, "cache_read": 4},
        tokens_source="agent-tool-result",
    )
    res = trace("validate", trace_file(line))
    assert diagnostics(res) == ["schema-refused: trace.jsonl:1"]


def test_the_longest_reason_sits_exactly_on_the_unit_length_bound(
    trace, trace_file, scripts_dir
):
    """`owner-wait-authorization` is the bound, checked and not eyeballed."""
    found = ORCHESTRATOR_UNIT_LEN_RE.findall(
        (scripts_dir / SCRIPT).read_text(encoding="utf-8")
    )
    assert len(found) == 1, found
    longest = "owner-wait-authorization"
    assert len(longest) == int(found[0])
    accepted = trace("validate", trace_file(owner_wait(unit=longest)))
    assert diagnostics(accepted) == [], accepted.stdout
    # One character past the bound is refused, and so is a padded reason.
    refused = trace(
        "validate",
        trace_file(owner_wait(unit=longest + "x"), name="second.jsonl"),
    )
    assert diagnostics(refused) == ["schema-refused: second.jsonl:1"]


def test_the_owner_wait_pair_is_written_through_append(trace, tmp_path):
    """The orchestrator opens at the question and closes on the owner's word."""
    path = tmp_path / "trace.jsonl"
    common: dict[str, str | None] = {
        "round": ROUND,
        "span": "s6.04",
        "actor": "orchestrator",
        "unit": "owner-wait-fork",
        "id-prefix": None,
        "agent-id": None,
        "model-assigned": None,
    }
    opened = trace(
        *to_args(path, {"kind": "open", **common, "started": "2026-08-11T11:50:00Z"})
    )
    assert diagnostics(opened) == [], opened.stdout
    closed = trace(
        *to_args(
            path,
            {
                "kind": "span",
                **common,
                "outcome": "refused",
                "ended": "2026-08-11T12:05:00Z",
            },
        )
    )
    assert diagnostics(closed) == [], closed.stdout

    written = records(path)
    assert [r["kind"] for r in written] == ["open", "span"]
    assert [r["unit"] for r in written] == ["owner-wait-fork", "owner-wait-fork"]
    # `started` is copied from the open record, so a wait that spanned a
    # compaction keeps its true length.
    assert written[1]["started"] == "2026-08-11T11:50:00Z"
    assert written[1]["wallclock_s"] == 900
    assert written[1]["model_assigned"] == "n/a"
    assert written[1]["tokens"] is None

    res = trace("validate", path)
    assert diagnostics(res) == []
    assert defects(res) == []


def test_an_owner_wait_open_without_its_close_is_an_unclosed_span(trace, tmp_path):
    """An unfinished wait reads as one unclosed span, never as a zero."""
    path = tmp_path / "trace.jsonl"
    trace(
        *to_args(
            path,
            {
                "kind": "open",
                "round": ROUND,
                "span": "s9.01",
                "actor": "orchestrator",
                "unit": "owner-wait-signature",
                "id-prefix": None,
                "agent-id": None,
                "model-assigned": None,
                "started": "2026-08-11T11:50:00Z",
            },
        )
    )
    res = trace("validate", path)
    assert res.returncode == 0
    assert diagnostics(res) == [], res.stdout
    assert "trace: 1 unclosed spans (round interrupted)" in res.stdout
