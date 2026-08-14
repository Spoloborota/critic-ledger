"""Characterization tests for rollup.py — the stage-9 round summary.

The script turns a round's `trace.jsonl` plus its `fix-ledger.md` into
`round-summary.json` and a human table. What the cases below pin: the
summary's shape field for field, the five metrics with their
`n/a: <reason>` propagation (the EMPTY DENOMINATOR rule), the
multi-verifier and re-fix aggregation rules, the `wallclock_s`
disagreement report, the identifier patterns rollup.py owns
(`object_slug`, `mode`), the T2 projection, and the privacy property
those rest on: no free text from either input ever reaches an output.

`rollup.py` is deliberately NOT added to conftest's `run` fixture (that
whitelist belongs to the six 0.1.x scripts); this module drives the script
through its own subprocess helper, with the same hardened environment.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

from conftest import hardened_env

SCRIPT = "rollup.py"
ROUND = "2026-08-11-101502-auth-plan"
SLUG = "auth-plan"

# The form a diagnostic line may take, verbatim, and the whole of what it
# may carry.
DIAGNOSTIC_RE = re.compile(
    r"^(unreadable|unparseable-line|no-usage|id-not-found|schema-refused"
    r"|write-failed): [\w./-]+(:\d+)?$"
)
# The bounded defect form, reused: a closed class plus one bounded locator.
DEFECT_RE = re.compile(r"^defect: [a-z-]+ (line|pass|lens) [A-Za-z0-9]+$")

# The summary's shape, field for field. Every assertion below compares against
# these sets with `==`, so an added key fails as loudly as a missing one.
SUMMARY_KEYS = {
    "round",
    "object_slug",
    "mode",
    "started",
    "ended",
    "wallclock_s",
    "lenses",
    "batches",
    "passes",
    "findings",
    "totals",
    "metrics",
}
LENS_KEYS = {
    "prefix",
    "model_assigned",
    "model_actual",
    "raised",
    "upheld",
    "wallclock_s",
    "tokens",
}
BATCH_KEYS = {"id", "ids_n", "fixed", "unworkable", "commit", "wallclock_s", "tokens"}
PASS_KEYS = {
    "ordinal",
    "prefix",
    "spans_n",
    "ids_n",
    "landed",
    "partial",
    "not_landed",
    "new",
    "bundled",
    "wallclock_s",
    "tokens",
}
FINDINGS_KEYS = {"by_severity", "by_terminal", "fix_application_n"}
TOTALS_KEYS = {"tokens", "coverage"}
METRIC_KEYS = {"CFR", "FPL", "VP", "TVR", "FADS"}
TVR_KEYS = {"in", "out", "cache_write", "cache_read", "fresh", "reuse", "seconds"}
PROJECTION_KEYS = {
    "v",
    "round_key",
    "date",
    "mode",
    "wallclock_s",
    "lenses",
    "batches",
    "passes",
    "findings",
    "totals",
    "metrics",
}
SEVERITY_KEYS = {"blocker", "major", "minor", "blank", "other"}
TERMINAL_KEYS = {
    "verified-landed",
    "refuted-with-reason",
    "accepted-residue",
    "refused-user-signed",
    "open",
}

# The four canonical example records, copied verbatim — the same
# acceptance fixture `test_trace.py` uses, fed here as rollup input.
EXAMPLE_OPEN = '{"v":1,"kind":"open","round":"2026-08-11-101502-auth-plan","span":"s3.01","parent":"s1.00","stage":3,"actor":"critic","unit":"HA","id_prefix":"HA","agent_id":"0a1b2c3d4e5f60718","model_assigned":"sonnet","started":"2026-08-11T10:16:04Z"}'  # noqa: E501
EXAMPLE_CRITIC = '{"v":1,"kind":"span","round":"2026-08-11-101502-auth-plan","span":"s3.01","parent":"s1.00","stage":3,"actor":"critic","unit":"HA","id_prefix":"HA","agent_id":"0a1b2c3d4e5f60718","ids":[],"id_tags":{},"flags":[],"model_assigned":"sonnet","model_actual":"claude-sonnet-4-6","model_source":"resolvedModel","tokens":{"in":118,"out":14203,"cache_write":96411,"cache_read":1204880},"tokens_source":"agent-tool-result","commit":null,"started":"2026-08-11T10:16:04Z","ended":"2026-08-11T10:33:47Z","wallclock_s":1063,"outcome":"findings:11"}'  # noqa: E501
EXAMPLE_FIXER = '{"v":1,"kind":"span","round":"2026-08-11-101502-auth-plan","span":"s7.02","parent":"s1.00","stage":7,"actor":"fixer","unit":"B2","id_prefix":null,"agent_id":null,"ids":["HA-2","HA-5","HB-1","HB-4"],"id_tags":{},"flags":["criterion-unworkable"],"model_assigned":"opus","model_actual":"unknown","model_source":"n/a","tokens":null,"tokens_source":"absent","commit":"9f31c02","started":"2026-08-11T11:02:10Z","ended":"2026-08-11T11:12:52Z","wallclock_s":642,"outcome":"fixed:3,unworkable:1"}'  # noqa: E501
EXAMPLE_ORCHESTRATOR = '{"v":1,"kind":"span","round":"2026-08-11-101502-auth-plan","span":"s6.03","parent":"s1.00","stage":6,"actor":"orchestrator","unit":"adjudication-batch-3","id_prefix":null,"agent_id":null,"ids":["HV-1","HV-2","HV-3","HV-4"],"id_tags":{"HV-2":["fix-application"],"HV-3":["fix-application","security-pii"],"HV-4":["refuted"]},"flags":[],"model_assigned":"n/a","model_actual":"n/a","model_source":"n/a","tokens":null,"tokens_source":"absent","commit":null,"started":"2026-08-11T11:40:00Z","ended":"2026-08-11T11:46:28Z","wallclock_s":388,"outcome":"upheld:3,refuted:1"}'  # noqa: E501
EXAMPLES = (EXAMPLE_OPEN, EXAMPLE_CRITIC, EXAMPLE_FIXER, EXAMPLE_ORCHESTRATOR)

# The string a leak would have to carry to be detectable. It is shaped
# like the things neither input may launder into a summary: a path, a
# quote, a shell substitution, a token.
POISON = 'SECRET-9f31/etc/passwd "leaked" $(whoami)'
POISON_MARK = "SECRET-9f31"

HEADER_8 = (
    "| id | sev | claim | verdict | criterion | fix | verified | terminal |\n"
    "|---|---|---|---|---|---|---|---|\n"
)
HEADER_7 = (
    "| id | sev | claim | verdict | fix | verified | terminal |\n"
    "|---|---|---|---|---|---|---|\n"
)
PASSES_HEADER = (
    "\n## Verification passes\n\n"
    "| # | pass (scope) | verdicts (L/P/NOT) | new findings | bundled | notes |\n"
    "|---|---|---|---|---|---|\n"
)


# --- helpers ---------------------------------------------------------------


@pytest.fixture
def rollup(scripts_dir, sandbox_home, tmp_path):
    """Invoke rollup.py and return the CompletedProcess."""
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


def span(**over: object) -> dict[str, object]:
    """Build a complete `span` record, overridden field by field."""
    record: dict[str, object] = {
        "v": 1,
        "kind": "span",
        "round": ROUND,
        "span": "s3.01",
        "parent": "s1.00",
        "stage": 3,
        "actor": "critic",
        "unit": "HA",
        "id_prefix": "HA",
        "agent_id": "a1",
        "ids": [],
        "id_tags": {},
        "flags": [],
        "model_assigned": "sonnet",
        "model_actual": "claude-sonnet-4-6",
        "model_source": "resolvedModel",
        "tokens": {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4},
        "tokens_source": "agent-tool-result",
        "commit": None,
        "started": "2026-08-11T10:16:04Z",
        "ended": "2026-08-11T10:16:14Z",
        "wallclock_s": 10,
        "outcome": "findings:0",
    }
    record.update(over)
    return record


def round_open(**over: object) -> dict[str, object]:
    """Build the round span's `open` record — stage 1, `parent: null`."""
    record: dict[str, object] = {
        "v": 1,
        "kind": "open",
        "round": ROUND,
        "span": "s1.00",
        "parent": None,
        "stage": 1,
        "actor": "orchestrator",
        "unit": "round",
        "id_prefix": None,
        "model_assigned": "n/a",
        "started": "2026-08-11T10:00:00Z",
    }
    record.update(over)
    return record


def round_close(**over: object) -> dict[str, object]:
    """Build the round span's close record — stage 9 writes it last."""
    return span(
        span="s1.00",
        parent=None,
        stage=1,
        actor="orchestrator",
        unit="round",
        id_prefix=None,
        agent_id=None,
        model_assigned="n/a",
        model_actual="n/a",
        model_source="n/a",
        tokens=None,
        tokens_source="absent",
        started="2026-08-11T10:00:00Z",
        ended="2026-08-11T12:00:00Z",
        wallclock_s=7200,
        outcome="closed",
        **over,
    )


@pytest.fixture
def make_round(tmp_path):
    """Write a run folder holding a ledger and (optionally) a trace."""
    counter = {"n": 0}

    def _make(
        rows: str = "",
        *,
        records: list[dict[str, object]] | None = None,
        raw_trace: str | None = None,
        header: str = HEADER_8,
        preamble: str = "- Mode: plan.\n\n",
        passes: str = "",
        name: str = ROUND,
    ):
        counter["n"] += 1
        folder = tmp_path / f"run{counter['n']}" / name
        folder.mkdir(parents=True)
        ledger = folder / "fix-ledger.md"
        ledger.write_text(preamble + header + rows + passes, encoding="utf-8")
        if raw_trace is not None:
            (folder / "trace.jsonl").write_text(raw_trace, encoding="utf-8")
        elif records is not None:
            (folder / "trace.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
            )
        return ledger

    return _make


def summary_of(ledger):
    """Read the `round-summary.json` written beside a ledger."""
    return json.loads(
        (ledger.parent / "round-summary.json").read_text(encoding="utf-8")
    )


def full_round(records: list[dict[str, object]] | None = None) -> list[dict[str, object]]:
    """A closed round: the round span's open record, spans, then its close."""
    return [round_open(), *(records or []), round_close()]


ROWS_8 = (
    "| HA-1 | major | c | FIX | L1 — x | B1 | LANDED | verified-landed |\n"
    "| HA-2 | minor | c | FIX | L1 — x | B1 | LANDED | verified-landed |\n"
    "| HA-3 | minor | c | REFUTED | — | — | — | refuted-with-reason |\n"
)


# --- the summary shape, field for field ------------------------------------


def test_summary_carries_exactly_the_specified_fields(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    result = rollup(ledger)
    assert result.returncode == 0
    data = summary_of(ledger)
    assert set(data) == SUMMARY_KEYS
    assert set(data["findings"]) == FINDINGS_KEYS
    assert set(data["totals"]) == TOTALS_KEYS
    assert set(data["metrics"]) == METRIC_KEYS
    assert set(data["metrics"]["TVR"]) == TVR_KEYS
    assert set(data["findings"]["by_severity"]) == SEVERITY_KEYS
    assert set(data["findings"]["by_terminal"]) == TERMINAL_KEYS


def test_group_entries_carry_exactly_their_specified_fields(rollup, make_round):
    records = full_round(
        [
            span(),
            span(
                span="s7.02",
                stage=7,
                actor="fixer",
                unit="B1",
                id_prefix=None,
                agent_id=None,
                ids=["HA-1", "HA-2"],
                model_assigned="opus",
                model_actual="unknown",
                model_source="n/a",
                commit="9f31c02",
                outcome="fixed:2,unworkable:0",
            ),
            span(
                span="s8.03",
                stage=8,
                actor="verifier",
                unit="P1",
                id_prefix="V1",
                ids=["HA-1", "HA-2"],
                outcome="L:2,P:0,NOT:0,new:0",
            ),
        ]
    )
    ledger = make_round(ROWS_8, records=records)
    assert rollup(ledger).returncode == 0
    data = summary_of(ledger)
    assert set(data["lenses"][0]) == LENS_KEYS
    assert set(data["batches"][0]) == BATCH_KEYS
    assert set(data["passes"][0]) == PASS_KEYS


def test_the_summary_is_written_beside_the_ledger(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    assert (ledger.parent / "round-summary.json").is_file()


def test_out_redirects_the_summary(rollup, make_round, tmp_path):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    target = tmp_path / "elsewhere.json"
    assert rollup(ledger, "--out", target).returncode == 0
    assert target.is_file()
    assert not (ledger.parent / "round-summary.json").exists()


def test_round_and_object_slug_are_derived_and_bounded(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    data = summary_of(ledger)
    assert data["round"] == ROUND
    assert data["object_slug"] == SLUG
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", data["object_slug"])


def test_object_slug_stays_inside_its_pattern_for_a_hostile_folder_name(
    rollup, make_round
):
    ledger = make_round(ROWS_8, name="Not A Round Folder $(whoami)")
    result = rollup(ledger)
    assert result.returncode == 0
    data = summary_of(ledger)
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", data["object_slug"])
    # A `round` that fails its anchored pattern is REFUSED rather than
    # written — the field is null and one diagnostic says so, exactly as
    # `mode` is ruled. A slug of the bad name is NOT written into it.
    assert data["round"] is None
    assert "schema-refused: fix-ledger.md" in result.stdout


def test_a_refused_round_id_leaves_the_summary_written_and_t2_skipped(
    rollup, make_round, tmp_path
):
    ledger = make_round(ROWS_8, name="Not A Round Folder")
    rounds = tmp_path / "rounds.jsonl"
    result = rollup(ledger, "--rounds", rounds)
    assert result.returncode == 0
    assert summary_of(ledger)["round"] is None
    assert "rounds: skipped (no round key)" in result.stdout
    assert not rounds.exists()


# --- `mode` has one producer and a two-value vocabulary ---------------------


@pytest.mark.parametrize(("line", "expected"), [("plan", "plan"), ("impl", "impl")])
def test_mode_is_read_from_the_mode_line(rollup, make_round, line, expected):
    ledger = make_round(ROWS_8, preamble=f"- Mode: {line}.\n\n")
    rollup(ledger)
    assert summary_of(ledger)["mode"] == expected


def test_a_mode_holding_neither_value_is_refused_not_written(rollup, make_round):
    ledger = make_round(ROWS_8, preamble="- Mode: whatever it wants.\n\n")
    result = rollup(ledger)
    assert result.returncode == 0
    assert summary_of(ledger)["mode"] is None
    assert "schema-refused: fix-ledger.md" in result.stdout


def test_a_missing_mode_line_is_null_without_a_refusal(rollup, make_round):
    ledger = make_round(ROWS_8, preamble="")
    result = rollup(ledger)
    assert summary_of(ledger)["mode"] is None
    assert "schema-refused" not in result.stdout


def test_mode_is_not_read_off_the_prerequisite_line(rollup, make_round):
    preamble = "- Prerequisite (stage 0): git = yes; normal mode.\n\n"
    ledger = make_round(ROWS_8, preamble=preamble)
    result = rollup(ledger)
    assert summary_of(ledger)["mode"] is None
    assert "schema-refused" not in result.stdout


# --- M1 (CFR) ---------------------------------------------------------------


def test_m1_is_computed_per_lens_from_the_critic_spans(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    data = summary_of(ledger)
    assert data["metrics"]["CFR"] == {"HA": 0.6667}
    assert data["lenses"][0]["raised"] == 3
    assert data["lenses"][0]["upheld"] == 2


def test_m1_is_na_when_no_lens_was_spawned(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round())
    rollup(ledger)
    data = summary_of(ledger)
    assert data["metrics"]["CFR"] == "n/a: no lenses spawned"
    assert data["lenses"] == []


def test_m1_never_groups_by_a_ledger_prefix_no_lens_produced(rollup, make_round):
    rows = "| KI-1 | major | c | FIX | L1 — x | B1 | LANDED | verified-landed |\n"
    ledger = make_round(rows, records=full_round())
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["CFR"] == "n/a: no lenses spawned"


def test_prefix_matching_is_anchored_never_startswith(rollup, make_round):
    rows = (
        "| K-1 | major | c | FIX | L1 — x | B1 | LANDED | verified-landed |\n"
        "| KI-1 | major | c | REFUTED | — | — | — | refuted-with-reason |\n"
        "| KI-2 | major | c | REFUTED | — | — | — | refuted-with-reason |\n"
    )
    ledger = make_round(rows, records=full_round([span(unit="K", id_prefix="K")]))
    rollup(ledger)
    data = summary_of(ledger)
    assert data["lenses"][0]["raised"] == 1
    assert data["metrics"]["CFR"] == {"K": 1.0}


def test_m1_is_na_for_a_lens_that_raised_nothing(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span(unit="ZZ", id_prefix="ZZ")]))
    rollup(ledger)
    # The empty denominator names the LENS, never borrowing the pass's own
    # reason string: the three closed reasons name three different units.
    assert summary_of(ledger)["metrics"]["CFR"]["ZZ"] == "n/a: lens raised no findings"


# --- M2 (FPL) and RE-FIX ATTRIBUTION ----------------------------------------


def fixer_span(unit: str, ids: list[str], **over: object) -> dict[str, object]:
    """A stage-7 fixer span for one batch."""
    fields: dict[str, object] = {
        "span": f"s7.0{unit[-1]}",
        "stage": 7,
        "actor": "fixer",
        "unit": unit,
        "id_prefix": None,
        "agent_id": None,
        "ids": ids,
        "model_assigned": "opus",
        "model_actual": "unknown",
        "model_source": "n/a",
        "tokens": None,
        "tokens_source": "absent",
        "commit": "9f31c02",
        "outcome": f"fixed:{len(ids)},unworkable:0",
    }
    fields.update(over)
    return span(**fields)


def verifier_span(unit: str, ids: list[str], **over: object) -> dict[str, object]:
    """A stage-8 verifier span for one pass."""
    fields: dict[str, object] = {
        "span": f"s8.0{unit[-1]}",
        "stage": 8,
        "actor": "verifier",
        "unit": unit,
        "id_prefix": f"V{unit[-1]}",
        "ids": ids,
        "outcome": f"L:{len(ids)},P:0,NOT:0,new:0",
    }
    fields.update(over)
    return span(**fields)


def test_m2_is_the_first_pass_landed_rate_per_batch(rollup, make_round):
    records = full_round(
        [fixer_span("B1", ["HA-1", "HA-2", "HA-3"]), verifier_span("P1", ["HA-1"])]
    )
    ledger = make_round(ROWS_8, records=records)
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["FPL"] == {"B1": 0.6667}


def test_m2_is_na_when_a_batch_has_no_ids(rollup, make_round):
    records = full_round([fixer_span("B1", []), verifier_span("P1", ["HA-1"])])
    ledger = make_round(ROWS_8, records=records)
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["FPL"] == {"B1": "n/a: batch has no ids"}


def test_m2_is_na_when_no_pass_covers_the_batch(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([fixer_span("B1", ["HA-1"])]))
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["FPL"] == {
        "B1": "n/a: no verification pass covers this batch"
    }


def test_m2_is_na_when_no_batch_ran(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["FPL"] == "n/a: no fix batches"


def test_a_refixed_id_credits_the_last_batch_only(rollup, make_round):
    records = full_round(
        [
            fixer_span("B1", ["HA-1"]),
            fixer_span("B2", ["HA-1"]),
            verifier_span("P1", ["HA-1"]),
        ]
    )
    ledger = make_round(ROWS_8, records=records)
    rollup(ledger)
    fpl = summary_of(ledger)["metrics"]["FPL"]
    # The id stays in BOTH denominators; the credit is the last batch's.
    assert fpl == {"B1": 0.0, "B2": 1.0}


# --- M3 (VP) and the multi-verifier rule ------------------------------------


def test_m3_is_verifier_precision_per_pass(rollup, make_round):
    rows = ROWS_8 + (
        "| V1-1 | minor | c | FIX | L1 — y | B2 | LANDED | verified-landed |\n"
        "| V1-2 | minor | c | REFUTED | — | — | — | refuted-with-reason |\n"
    )
    records = full_round([verifier_span("P1", ["HA-1"])])
    ledger = make_round(rows, records=records)
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["VP"] == {"P1": 0.5}


def test_m3_is_na_for_a_pass_that_raised_nothing(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([verifier_span("P1", ["HA-1"])]))
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["VP"] == {"P1": "n/a: pass raised no findings"}


def test_m3_is_na_when_no_pass_ran(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["VP"] == "n/a: no verification passes"


def test_a_pass_is_a_set_of_spans_not_one_span(rollup, make_round):
    records = full_round(
        [
            verifier_span(
                "P1",
                ["HA-1"],
                span="s8.01",
                agent_id="v1",
                started="2026-08-11T10:00:00Z",
                ended="2026-08-11T10:10:00Z",
                wallclock_s=600,
            ),
            verifier_span(
                "P1",
                ["HA-2"],
                span="s8.02",
                agent_id="v2",
                started="2026-08-11T10:05:00Z",
                ended="2026-08-11T10:30:00Z",
                wallclock_s=1500,
            ),
        ]
    )
    ledger = make_round(ROWS_8, records=records)
    rollup(ledger)
    entry = summary_of(ledger)["passes"][0]
    assert entry["spans_n"] == 2
    assert entry["ids_n"] == 2
    # Earliest open to latest close — NOT the sum of the spans' own values.
    assert entry["wallclock_s"] == 1800
    assert entry["tokens"] == {"in": 2, "out": 4, "cache_write": 6, "cache_read": 8}


def test_one_null_span_makes_the_whole_pass_token_figure_null(rollup, make_round):
    records = full_round(
        [
            verifier_span("P1", ["HA-1"], span="s8.01", agent_id="v1"),
            verifier_span(
                "P1",
                ["HA-2"],
                span="s8.02",
                agent_id="v2",
                tokens=None,
                tokens_source="absent",
            ),
        ]
    )
    ledger = make_round(ROWS_8, records=records)
    rollup(ledger)
    assert summary_of(ledger)["passes"][0]["tokens"] is None


def test_pass_verdicts_come_from_the_ledger_not_from_a_span(rollup, make_round):
    rows = (
        "| HA-1 | major | c | FIX | L1 — x | B1 | LANDED | verified-landed |\n"
        "| HA-2 | minor | c | FIX | L1 — x | B1 | NOT LANDED | open |\n"
        "| HA-3 | minor | c | FIX | L1 — x | B1 | PARTIAL | open |\n"
    )
    records = full_round([verifier_span("P1", ["HA-1", "HA-2", "HA-3"])])
    ledger = make_round(rows, records=records)
    rollup(ledger)
    entry = summary_of(ledger)["passes"][0]
    assert (entry["landed"], entry["partial"], entry["not_landed"]) == (1, 1, 1)


def test_a_pass_row_without_a_verifier_span_is_refused_not_written(
    rollup, make_round
):
    passes = PASSES_HEADER + "| 1 | B1 | 3/0/0 | 0 | no | ok |\n"
    ledger = make_round(ROWS_8, records=full_round(), passes=passes)
    result = rollup(ledger)
    assert result.returncode == 0
    assert summary_of(ledger)["passes"] == []
    assert "defect: pass-floor-refused pass 1" in result.stdout


# --- M4 (TVR) — a vector, never one number ----------------------------------


def test_m4_is_a_vector_over_the_terminal_rows(rollup, make_round):
    counters = {"in": 10, "out": 20, "cache_write": 30, "cache_read": 40}
    ledger = make_round(ROWS_8, records=full_round([span(tokens=counters)]))
    rollup(ledger)
    tvr = summary_of(ledger)["metrics"]["TVR"]
    assert tvr["in"] == pytest.approx(10 / 3, abs=0.01)
    assert tvr["fresh"] == pytest.approx(60 / 3, abs=0.01)
    assert tvr["reuse"] == pytest.approx(40 / 3, abs=0.01)
    assert isinstance(tvr["seconds"], float)


def test_m4_token_half_is_na_with_its_coverage_and_seconds_still_print(
    rollup, make_round
):
    records = full_round(
        [span(), span(span="s3.02", agent_id="a2", tokens=None, tokens_source="absent")]
    )
    ledger = make_round(ROWS_8, records=records)
    result = rollup(ledger)
    tvr = summary_of(ledger)["metrics"]["TVR"]
    assert tvr["in"] == "n/a: 1 of 2 spans without usage"
    assert isinstance(tvr["seconds"], float)
    assert "TVR: tokens n/a (1 of 2 spans without usage)" in result.stdout


def test_m4_is_na_when_the_round_has_no_terminal_row(rollup, make_round):
    rows = "| HA-1 | major | c | FIX | L1 — x | B1 | — | open |\n"
    ledger = make_round(rows, records=full_round([span()]))
    rollup(ledger)
    tvr = summary_of(ledger)["metrics"]["TVR"]
    assert set(tvr.values()) == {"n/a: round has no terminal rows"}


def test_totals_never_present_a_partial_sum_as_a_total(rollup, make_round):
    records = full_round(
        [span(), span(span="s3.02", agent_id="a2", tokens=None, tokens_source="absent")]
    )
    ledger = make_round(ROWS_8, records=records)
    rollup(ledger)
    totals = summary_of(ledger)["totals"]
    assert totals["tokens"] is None
    assert totals["coverage"] == "1/2 spans"


def test_an_orchestrator_span_is_not_counted_as_a_measurement_gap(
    rollup, make_round
):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    result = rollup(ledger)
    totals = summary_of(ledger)["totals"]
    assert totals["tokens"] == {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4}
    assert totals["coverage"] == "1/1 spans"
    assert "orchestrator: n/a (not separable)" in result.stdout


# --- M5 (FADS) and the summary's single join --------------------------------


def test_m5_counts_fix_application_tags_of_verification_raised_rows(
    rollup, make_round
):
    rows = ROWS_8 + (
        "| V1-1 | minor | c | FIX | L1 — y | B2 | LANDED | verified-landed |\n"
        "| V1-2 | minor | c | FIX | L1 — y | B2 | LANDED | verified-landed |\n"
    )
    tags = span(
        span="s6.04",
        stage=6,
        actor="orchestrator",
        unit="adjudication-batch-1",
        id_prefix=None,
        agent_id=None,
        ids=["V1-1", "V1-2", "HA-1"],
        id_tags={"V1-1": ["fix-application"], "HA-1": ["fix-application"]},
        model_assigned="n/a",
        model_actual="n/a",
        model_source="n/a",
        tokens=None,
        tokens_source="absent",
        outcome="upheld:2,refuted:0",
    )
    records = full_round([verifier_span("P1", ["HA-1"]), tags])
    ledger = make_round(rows, records=records)
    rollup(ledger)
    data = summary_of(ledger)
    # HA-1 carries the tag too, but its prefix is a LENS prefix — M5's
    # denominator is the verification-raised rows only.
    assert data["findings"]["fix_application_n"] == 1
    assert data["metrics"]["FADS"] == 0.5


def test_m5_numerator_and_metric_cannot_disagree(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([verifier_span("P1", ["HA-1"])]))
    rollup(ledger)
    data = summary_of(ledger)
    assert data["findings"]["fix_application_n"] == 0
    assert data["metrics"]["FADS"] == "n/a: no verification-raised findings"


def test_m5_is_na_without_a_verification_raised_row(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    assert summary_of(ledger)["metrics"]["FADS"] == "n/a: no verification-raised findings"


# --- legacy 7-cell rows are excluded from the rates, and say so -------------


def test_a_v1_ledger_reports_na_rather_than_guessing_upheld(rollup, make_round):
    rows = (
        "| HA-1 | major | c | FIX | B1 | LANDED | verified-landed |\n"
        "| HA-2 | minor | c | REFUTED | — | — | refuted-with-reason |\n"
    )
    ledger = make_round(rows, header=HEADER_7, records=full_round([span()]))
    result = rollup(ledger)
    assert result.returncode == 0
    data = summary_of(ledger)
    assert data["lenses"][0]["upheld"] is None
    assert data["metrics"]["CFR"] == {"HA": "n/a: v1 ledger (no criterion column)"}
    # Everything that does not need the criterion column still computes.
    assert data["findings"]["by_severity"]["major"] == 1


# --- terminality is the recount's own predicate, never the cell's first word -


def test_a_named_status_the_row_does_not_satisfy_counts_as_open(rollup, make_round):
    """The metrics reuse the recount's predicates so a metric cannot disagree
    with closure; terminality is bucketed under the same rule.
    """  # noqa: D205  # two sentences, one rule
    rows = (
        "| HA-1 | major | c | FIX | L1 — x | B1 | — | verified-landed |\n"
        "| HA-2 | minor | c | FIX | L1 — x | B1 | LANDED OTHERWISE () "
        "| verified-landed |\n"
        "| HA-3 | minor | c | FIX | L1 — x | B1 | ok | accepted-residue |\n"
        "| HA-4 | minor | c | FIX | L1 — x | B1 | ok "
        "| accepted-residue user-signed 9999-99-99 |\n"
        "| HA-5 | minor | c | FIX | L1 — x | B1 | ok | refused |\n"
    )
    ledger = make_round(rows, records=full_round([span()]))
    rollup(ledger)
    data = summary_of(ledger)
    assert data["findings"]["by_terminal"]["open"] == 5
    assert data["findings"]["by_terminal"]["verified-landed"] == 0
    assert data["findings"]["by_terminal"]["accepted-residue"] == 0
    # No terminal row means M4 has no denominator, and says so.
    assert data["metrics"]["TVR"]["seconds"] == "n/a: round has no terminal rows"


def test_a_signed_residue_and_a_signed_refusal_are_terminal(rollup, make_round):
    rows = (
        "| HA-1 | minor | c | FIX | L1 — x | B1 | ok "
        "| accepted-residue user-signed 2026-08-11 |\n"
        "| HA-2 | minor | c | CONFIRMED | — | — | ok "
        "| refused-user-signed 2026-08-11 |\n"
    )
    ledger = make_round(rows, records=full_round([span()]))
    rollup(ledger)
    by_terminal = summary_of(ledger)["findings"]["by_terminal"]
    assert by_terminal["accepted-residue"] == 1
    assert by_terminal["refused-user-signed"] == 1
    assert by_terminal["open"] == 0


def test_a_pass_never_infers_a_partial_from_an_id_with_no_row(rollup, make_round):
    """PARTIAL is READ from a cell, never taken as the residue of the two
    other verdicts: an id whose row is absent has no verdict to report.
    """  # noqa: D205  # two sentences, one rule
    records = full_round([verifier_span("P1", ["HA-1", "ZZ-9"])])
    ledger = make_round(ROWS_8, records=records)
    rollup(ledger)
    entry = summary_of(ledger)["passes"][0]
    assert entry["ids_n"] == 2
    assert (entry["landed"], entry["partial"], entry["not_landed"]) == (1, 0, 0)


# --- `tokens.total` is optional, and reaches no output ----------------------


def test_the_optional_total_key_is_accepted_and_never_summed(rollup, make_round):
    counters = {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4, "total": 10}
    ledger = make_round(ROWS_8, records=full_round([span(tokens=counters)]))
    result = rollup(ledger)
    assert result.returncode == 0
    assert "schema-refused" not in result.stdout
    totals = summary_of(ledger)["totals"]
    assert totals["tokens"] == {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4}
    assert "total" not in totals["tokens"]


def test_an_unknown_token_key_is_refused_rather_than_carried(rollup, make_round):
    counters = {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4, "note": POISON}
    ledger = make_round(ROWS_8, records=[round_open(), span(tokens=counters)])
    result = rollup(ledger)
    assert result.returncode == 0
    assert "schema-refused: trace.jsonl:2" in result.stdout
    assert POISON_MARK not in result.stdout
    assert POISON_MARK not in (ledger.parent / "round-summary.json").read_text(
        encoding="utf-8"
    )


def test_the_round_span_is_not_added_to_the_sum_of_the_spans_it_contains(
    rollup, make_round
):
    """The root span's `wallclock_s` is the envelope of every other span,
    so M4's seconds must not count the round twice — and must not change
    depending on whether the rollup ran before or after the close record.
    """  # noqa: D205  # two sentences, one rule
    open_round = make_round(ROWS_8, records=[round_open(), span()])
    closed_round = make_round(ROWS_8, records=full_round([span()]))
    rollup(open_round)
    rollup(closed_round)
    before = summary_of(open_round)["metrics"]["TVR"]["seconds"]
    after = summary_of(closed_round)["metrics"]["TVR"]["seconds"]
    assert before == after == pytest.approx(10 / 3, abs=0.01)


# --- a trace that is missing, empty or corrupt fails nothing ----------------


def test_a_missing_trace_still_produces_a_summary(rollup, make_round):
    ledger = make_round(ROWS_8)
    result = rollup(ledger)
    assert result.returncode == 0
    assert "trace: none" in result.stdout
    data = summary_of(ledger)
    assert data["started"] is None
    assert data["metrics"]["CFR"] == "n/a: no lenses spawned"
    assert data["metrics"]["FPL"] == "n/a: no fix batches"
    assert data["metrics"]["VP"] == "n/a: no verification passes"
    assert data["metrics"]["FADS"] == "n/a: no verification-raised findings"
    assert data["totals"]["tokens"] is None


def test_a_trace_pointed_at_a_directory_is_not_fatal(rollup, make_round):
    ledger = make_round(ROWS_8)
    result = rollup(ledger, "--trace", ledger.parent)
    assert result.returncode == 0
    assert "trace: none" in result.stdout
    assert "Traceback" not in result.stderr


def test_a_trace_that_exists_but_cannot_be_read_says_so(rollup, make_round):
    """The negative-claim rule: absence is not claimed without evidence.

    A trace that is not there is the flag-off case and prints `trace: none`
    alone; one that IS there and could not be read carries the `unreadable`
    diagnostic from the closed vocabulary beside it, so the two are
    distinguishable.
    """
    ledger = make_round(ROWS_8)
    unreadable = ledger.parent / "trace.jsonl"
    unreadable.mkdir()
    result = rollup(ledger)
    assert result.returncode == 0
    assert "unreadable: trace.jsonl" in result.stdout
    assert "trace: none" in result.stdout


def test_a_missing_trace_claims_no_more_than_absence(rollup, make_round):
    ledger = make_round(ROWS_8)
    result = rollup(ledger)
    assert "unreadable" not in result.stdout
    assert "trace: none" in result.stdout


def test_corrupt_trace_lines_are_counted_never_fatal(rollup, make_round):
    good = json.dumps(round_open())
    raw = f"{good}\nnot json at all\n{{}}\n"
    ledger = make_round(ROWS_8, raw_trace=raw)
    result = rollup(ledger)
    assert result.returncode == 0
    assert "2 refused lines" in result.stdout
    assert "unparseable-line: trace.jsonl:2" in result.stdout
    assert "schema-refused: trace.jsonl:3" in result.stdout


def test_the_trace_option_redirects_the_read(rollup, make_round, tmp_path):
    ledger = make_round(ROWS_8)
    elsewhere = tmp_path / "other.jsonl"
    elsewhere.write_text(json.dumps(round_open()) + "\n", encoding="utf-8")
    result = rollup(ledger, "--trace", elsewhere)
    assert result.returncode == 0
    assert summary_of(ledger)["started"] == "2026-08-11T10:00:00Z"


# --- reduction, unclosed spans, and no invented end -------------------------


def test_a_span_record_supersedes_its_open_and_the_pair_counts_once(
    rollup, make_round
):
    records = [round_open(), *[], span(kind="open"), span()]
    ledger = make_round(ROWS_8, records=records)
    result = rollup(ledger)
    assert "trace: 1 spans, 1 unclosed" in result.stdout


def test_an_unclosed_round_span_leaves_ended_null_and_says_so(rollup, make_round):
    ledger = make_round(ROWS_8, records=[round_open(), span()])
    result = rollup(ledger)
    data = summary_of(ledger)
    assert data["started"] == "2026-08-11T10:00:00Z"
    assert data["ended"] is None
    assert data["wallclock_s"] is None
    assert "1 unclosed" in result.stdout


def test_a_second_span_record_for_one_id_is_a_report_only_defect(rollup, make_round):
    ledger = make_round(ROWS_8, records=[round_open(), span(), span()])
    result = rollup(ledger)
    assert result.returncode == 0
    assert "defect: duplicate-span line 3" in result.stdout


# --- the `wallclock_s` disagreement -----------------------------------------


def test_a_wallclock_disagreement_is_reported_as_a_defect(rollup, make_round):
    ledger = make_round(ROWS_8, records=[round_open(), span(wallclock_s=999)])
    result = rollup(ledger)
    assert result.returncode == 0
    assert "defect: wallclock-mismatch line 2" in result.stdout


def test_an_agreeing_wallclock_raises_no_defect(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    result = rollup(ledger)
    assert "wallclock-mismatch" not in result.stdout
    assert "0 defects" in result.stdout


def test_every_defect_line_matches_the_bounded_form(rollup, make_round):
    rows = ROWS_8 + (
        "| V1-1 | minor | c | FIX | L1 — y | B2 | LANDED | verified-landed |\n"
    )
    passes = PASSES_HEADER + "| 1 | B1 | 1/0/0 | 7 | no | ok |\n"
    records = [
        round_open(),
        span(wallclock_s=999),
        span(),
        verifier_span("P1", ["HA-1"], flags=["bundled"]),
    ]
    ledger = make_round(rows, records=records, passes=passes)
    result = rollup(ledger)
    printed = [line for line in result.stdout.splitlines() if line.startswith("defect:")]
    assert printed
    for line in printed:
        assert DEFECT_RE.match(line), line
    assert any("new-findings-disagreement" in line for line in printed)
    assert any("bundled-disagreement" in line for line in printed)


def test_verifier_spans_of_one_pass_disagreeing_on_bundled_take_their_or(
    rollup, make_round
):
    """A pass whose spans disagree is reported, and the value is OR."""
    records = full_round(
        [
            verifier_span("P1", ["HA-1"], span="s8.01", agent_id="v1"),
            verifier_span(
                "P1", ["HA-2"], span="s8.02", agent_id="v2", flags=["bundled"]
            ),
        ]
    )
    ledger = make_round(ROWS_8, records=records)
    result = rollup(ledger)
    assert "defect: bundled-disagreement pass 1" in result.stdout
    assert summary_of(ledger)["passes"][0]["bundled"] is True


def test_an_outcome_disagreeing_with_the_ledger_is_a_defect_and_the_ledger_wins(
    rollup, make_round
):
    ledger = make_round(ROWS_8, records=full_round([span(outcome="findings:99")]))
    result = rollup(ledger)
    assert "defect: outcome-ledger-disagreement lens HA" in result.stdout
    assert summary_of(ledger)["lenses"][0]["raised"] == 3


# --- the T2 projection ------------------------------------------------------


def test_no_rounds_line_is_written_unless_the_path_is_given(rollup, make_round, tmp_path):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    assert not (tmp_path / "rounds.jsonl").exists()


def test_the_projection_drops_the_three_identity_fields(rollup, make_round, tmp_path):
    records = full_round([span(), fixer_span("B1", ["HA-1"])])
    ledger = make_round(ROWS_8, records=records)
    rounds = tmp_path / "rounds.jsonl"
    result = rollup(ledger, "--rounds", rounds)
    assert result.returncode == 0
    line = json.loads(rounds.read_text(encoding="utf-8").strip())
    assert set(line) == PROJECTION_KEYS
    assert "object_slug" not in line
    assert "round" not in line
    assert "started" not in line and "ended" not in line
    assert set(line["batches"][0]) == BATCH_KEYS - {"commit"}
    assert line["v"] == 1
    assert re.fullmatch(r"[0-9a-f]{12}", line["round_key"])
    assert line["date"] == "2026-08-11"


def test_the_projection_carries_every_duration_and_metric_untouched(
    rollup, make_round, tmp_path
):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rounds = tmp_path / "rounds.jsonl"
    rollup(ledger, "--rounds", rounds)
    line = json.loads(rounds.read_text(encoding="utf-8").strip())
    data = summary_of(ledger)
    assert line["wallclock_s"] == data["wallclock_s"] == 7200
    assert line["metrics"] == data["metrics"]
    assert line["totals"] == data["totals"]
    assert line["findings"] == data["findings"]
    assert line["lenses"] == data["lenses"]


def test_the_projection_copies_a_refused_mode_through_as_null(
    rollup, make_round, tmp_path
):
    ledger = make_round(
        ROWS_8, records=full_round([span()]), preamble="- Mode: neither.\n\n"
    )
    rounds = tmp_path / "rounds.jsonl"
    rollup(ledger, "--rounds", rounds)
    assert json.loads(rounds.read_text(encoding="utf-8").strip())["mode"] is None


def test_an_open_round_span_still_appends_its_t2_line(rollup, make_round, tmp_path):
    """Stage 9 appends T2 BEFORE it closes the round span.

    Gating the append on a close record that stage 9 writes afterwards
    would leave the T2 line unreachable on every ordinary round, so the
    day falls back to this script's own clock while the local summary
    keeps the honest `ended: null`.
    """
    ledger = make_round(ROWS_8, records=[round_open(), span()])
    rounds = tmp_path / "rounds.jsonl"
    result = rollup(ledger, "--rounds", rounds)
    assert result.returncode == 0
    assert summary_of(ledger)["ended"] is None
    line = json.loads(rounds.read_text(encoding="utf-8").strip())
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", line["date"])
    assert line["wallclock_s"] is None
    assert "rounds: appended 1 line" in result.stdout


def test_the_t2_file_is_appended_to_never_rewritten(rollup, make_round, tmp_path):
    rounds = tmp_path / "rounds.jsonl"
    rounds.write_text('{"v":1,"round_key":"aaaaaaaaaaaa"}\n', encoding="utf-8")
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger, "--rounds", rounds)
    lines = rounds.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["round_key"] == "aaaaaaaaaaaa"


def test_a_t2_write_failure_is_one_diagnostic_and_no_crash(
    rollup, make_round, tmp_path
):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    result = rollup(ledger, "--rounds", tmp_path / "missing-dir" / "rounds.jsonl")
    assert result.returncode == 0
    assert "write-failed: rounds.jsonl" in result.stdout


# --- the canonical example records as input ---------------------------------


def test_the_canonical_examples_roll_up(rollup, make_round):
    rows = (
        "| HA-2 | major | c | FIX | L1 — x | B2 | LANDED | verified-landed |\n"
        "| HA-5 | minor | c | FIX | L1 — x | B2 | LANDED | verified-landed |\n"
        "| HB-1 | minor | c | REFUTED | — | — | — | refuted-with-reason |\n"
        "| HB-4 | minor | c | FIX | L1 — x | B2 | NOT LANDED | open |\n"
        "| HV-1 | minor | c | REFUTED | — | — | — | refuted-with-reason |\n"
        "| HV-2 | minor | c | FIX | L1 — y | B3 | LANDED | verified-landed |\n"
        "| HV-3 | minor | c | FIX | L1 — y | B3 | LANDED | verified-landed |\n"
        "| HV-4 | minor | c | REFUTED | — | — | — | refuted-with-reason |\n"
    )
    raw = "".join(line + "\n" for line in EXAMPLES)
    ledger = make_round(rows, raw_trace=raw)
    result = rollup(ledger)
    assert result.returncode == 0
    assert "0 refused lines" in result.stdout
    data = summary_of(ledger)
    assert data["round"] == ROUND
    assert [lens["prefix"] for lens in data["lenses"]] == ["HA"]
    assert [batch["id"] for batch in data["batches"]] == ["B2"]
    assert data["batches"][0]["commit"] == "9f31c02"
    assert data["batches"][0]["ids_n"] == 4


def test_each_example_record_is_accepted_on_its_own(rollup, make_round):
    for example in EXAMPLES:
        ledger = make_round(ROWS_8, raw_trace=example + "\n")
        result = rollup(ledger)
        assert result.returncode == 0
        assert "refused lines" not in result.stdout or "0 refused lines" in result.stdout


# --- no free text, in either output -----------------------------------------


def test_ledger_prose_never_reaches_the_summary_or_the_table(rollup, make_round):
    rows = (
        f"| HA-1 | {POISON} | {POISON} | {POISON} | {POISON} | {POISON} "
        f"| {POISON} | {POISON} |\n"
    )
    preamble = f"- Mode: {POISON}\n- Object: {POISON}\n\n"
    passes = PASSES_HEADER + f"| 1 | {POISON} | {POISON} | 1 | {POISON} | {POISON} |\n"
    ledger = make_round(
        rows, records=full_round([span()]), preamble=preamble, passes=passes
    )
    result = rollup(ledger)
    assert result.returncode == 0
    assert POISON_MARK not in result.stdout
    assert POISON_MARK not in result.stderr
    written = (ledger.parent / "round-summary.json").read_text(encoding="utf-8")
    assert POISON_MARK not in written
    data = json.loads(written)
    assert data["findings"]["by_severity"]["other"] == 1
    assert data["findings"]["by_terminal"]["open"] == 1


def test_a_poisoned_trace_value_is_refused_without_an_echo(rollup, make_round):
    record = span(unit=POISON, id_prefix=POISON, outcome=POISON)
    ledger = make_round(ROWS_8, records=[round_open(), record])
    result = rollup(ledger)
    assert result.returncode == 0
    assert POISON_MARK not in result.stdout
    assert "schema-refused: trace.jsonl:2" in result.stdout
    assert POISON_MARK not in (ledger.parent / "round-summary.json").read_text(
        encoding="utf-8"
    )


def test_a_poisoned_unparseable_line_is_never_echoed(rollup, make_round):
    ledger = make_round(ROWS_8, raw_trace=f'{{"v":1,"kind":"open" {POISON}\n')
    result = rollup(ledger)
    assert result.returncode == 0
    assert POISON_MARK not in result.stdout
    assert "unparseable-line: trace.jsonl:1" in result.stdout


def test_a_poisoned_path_cannot_widen_the_diagnostic(rollup, make_round, tmp_path):
    """A file NAME is all a diagnostic may carry — and no more than that.

    The name here comes from the caller's own argv, not from the bytes of
    either input, so it is not content the diagnostic laundered; what the
    rule forbids is a line that carries anything beyond its closed class, a
    name and a line number. The quotes, spaces, shell substitution and
    directory components of the hostile path must all be gone, and the
    line must still match the closed form.
    """
    ledger = make_round(ROWS_8, records=full_round([span()]))
    hostile = tmp_path / "missing" / f'{POISON.replace("/", "")}.jsonl'
    result = rollup(ledger, "--rounds", hostile)
    assert result.returncode == 0
    diagnostics = [
        line for line in result.stdout.splitlines() if line.startswith("write-failed")
    ]
    assert diagnostics
    for line in diagnostics:
        assert DIAGNOSTIC_RE.match(line), line
        assert str(tmp_path) not in line
        for forbidden in ('"', "$", "(", ")", " ", "\\"):
            assert forbidden not in line.split(": ", 1)[1], forbidden


def test_every_diagnostic_the_script_prints_matches_the_closed_form(
    rollup, make_round, tmp_path
):
    cases = [
        make_round(ROWS_8, preamble="- Mode: nonsense.\n\n"),
        make_round(ROWS_8, raw_trace="{oops\n"),
        make_round(ROWS_8, raw_trace='{"v":9}\n'),
    ]
    printed: list[str] = []
    for ledger in cases:
        printed += rollup(ledger).stdout.splitlines()
    printed += rollup(tmp_path / "nope.md").stdout.splitlines()
    candidates = [
        line for line in printed if line.split(":")[0] in {
            "unreadable",
            "unparseable-line",
            "no-usage",
            "id-not-found",
            "schema-refused",
            "write-failed",
        }
    ]
    assert candidates
    for line in candidates:
        assert DIAGNOSTIC_RE.match(line), line


def test_the_script_contains_no_network_primitive_and_no_subprocess(scripts_dir):
    """No network and no child process, as a gate rather than a review."""
    source = (scripts_dir / SCRIPT).read_text(encoding="utf-8")
    for forbidden in ("urllib", "requests", "socket", "ftplib", "smtplib",
                      "http.client", "subprocess"):
        assert forbidden not in source, forbidden


def test_the_only_new_import_is_hashlib_and_it_is_standard_library(scripts_dir):
    """The one named import delta: `hashlib` for the T2 digest, nothing else."""
    source = (scripts_dir / SCRIPT).read_text(encoding="utf-8")
    imports = set(re.findall(r"^(?:import|from) (\w+)", source, re.MULTILINE))
    assert imports == {"hashlib", "json", "re", "sys", "unicodedata", "datetime",
                       "pathlib", "typing"}


# --- exit codes: fail-soft on data, exit 2 only on a missing input -----------


def test_help_prints_the_contract_and_exits_zero(rollup):
    result = rollup("--help")
    assert result.returncode == 0
    assert "round-summary.json" in result.stdout


def test_short_help_prints_the_usage_and_exits_zero(rollup):
    """`-h` is the same uniform-help contract as `--help` (KI-61)."""
    result = rollup("-h")
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_no_arguments_prints_the_usage_and_exits_two(rollup):
    """A bare invocation is a USAGE ERROR, not help — the sibling convention.

    `recount.py` with zero arguments exits 2, and this script's own exit-code
    contract reserves 2 for "the script was not given its input". Only an
    explicit `-h`/`--help` is the help request that exits 0.
    """
    result = rollup()
    assert result.returncode == 2
    assert "Usage:" in result.stdout


def test_an_unreadable_ledger_is_exit_two_with_one_diagnostic(rollup, tmp_path):
    result = rollup(tmp_path / "absent.md")
    assert result.returncode == 2
    assert result.stdout.strip() == "unreadable: absent.md"
    assert result.stderr == ""


def test_a_ledger_without_a_findings_table_is_exit_two(rollup, tmp_path):
    ledger = tmp_path / "prose.md"
    ledger.write_text("no table here at all\n", encoding="utf-8")
    result = rollup(ledger)
    assert result.returncode == 2
    assert "schema-refused: prose.md" in result.stdout


def test_an_unknown_option_is_a_usage_error(rollup, make_round):
    ledger = make_round(ROWS_8)
    result = rollup(ledger, "--nope", "x")
    assert result.returncode == 2


def test_an_option_without_a_value_is_a_usage_error(rollup, make_round):
    ledger = make_round(ROWS_8)
    result = rollup(ledger, "--trace")
    assert result.returncode == 2


def test_a_degenerate_findings_header_is_exit_two_without_a_traceback(
    rollup, make_round
):
    ledger = make_round("", header="| id |\n|---|\n")
    result = rollup(ledger)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_only_the_first_findings_table_is_read(rollup, make_round):
    """The recount reads the FIRST table up to the next heading; so does
    this, so an appendix table cannot inflate the round's counts.
    """  # noqa: D205  # two sentences, one rule
    rows = ROWS_8 + (
        "\n## Appendix\n\n"
        "| id | sev | claim | verdict | criterion | fix | verified | terminal |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| HA-9 | blocker | c | FIX | L1 — x | B1 | LANDED | verified-landed |\n"
    )
    ledger = make_round(rows, records=full_round([span()]))
    rollup(ledger)
    data = summary_of(ledger)
    assert data["lenses"][0]["raised"] == 3
    assert data["findings"]["by_severity"]["blocker"] == 0


def test_a_blank_severity_cell_is_bucketed_never_copied(rollup, make_round):
    rows = "| HA-1 | | c | FIX | L1 — x | B1 | LANDED | verified-landed |\n"
    ledger = make_round(rows, records=full_round([span()]))
    rollup(ledger)
    assert summary_of(ledger)["findings"]["by_severity"]["blank"] == 1


def test_a_malformed_row_is_skipped_never_fatal(rollup, make_round):
    rows = ROWS_8 + "| HA-4 | minor | broken row |\n"
    ledger = make_round(rows, records=full_round([span()]))
    result = rollup(ledger)
    assert result.returncode == 0
    assert summary_of(ledger)["lenses"][0]["raised"] == 3


def test_a_non_utf8_ledger_is_exit_two_not_a_traceback(rollup, tmp_path):
    ledger = tmp_path / "binary.md"
    ledger.write_bytes(b"\xff\xfe| id |\n")
    result = rollup(ledger)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_a_summary_write_failure_is_one_diagnostic_and_still_exit_zero(
    rollup, make_round, tmp_path
):
    ledger = make_round(ROWS_8, records=full_round([span()]))
    result = rollup(ledger, "--out", tmp_path / "no-such-dir" / "s.json")
    assert result.returncode == 0
    assert "write-failed: s.json" in result.stdout


# --- the human table --------------------------------------------------------


def test_the_table_names_every_group_and_the_trace_summary(rollup, make_round):
    records = full_round(
        [span(), fixer_span("B1", ["HA-1"]), verifier_span("P1", ["HA-1"])]
    )
    ledger = make_round(ROWS_8, records=records)
    result = rollup(ledger)
    out = result.stdout
    assert "lens HA:" in out
    assert "batch B1:" in out
    assert "pass P1:" in out
    assert "findings: rows 3" in out
    assert "wrote: round-summary.json" in out
    assert re.search(r"trace: \d+ spans, \d+ unclosed, \d+ refused lines", out)


def test_the_table_says_none_rather_than_printing_an_empty_section(
    rollup, make_round
):
    ledger = make_round(ROWS_8, records=full_round())
    out = rollup(ledger).stdout
    assert "lenses: none | CFR n/a: no lenses spawned" in out
    assert "batches: none | FPL n/a: no fix batches" in out
    assert "passes: none | VP n/a: no verification passes" in out
