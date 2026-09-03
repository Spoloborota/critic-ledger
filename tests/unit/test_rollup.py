"""Characterization tests for rollup.py — the stage-9 round summary.

The script turns a round's `trace.jsonl` plus its `fix-ledger.md` into
`round-summary.json` and a human table. What the cases below pin: the
summary's shape field for field, M1-M11 (the eleven metrics) with their
`n/a: <reason>` propagation (the EMPTY DENOMINATOR rule), the
multi-verifier and re-fix aggregation rules, the `wallclock_s`
disagreement report, the identifier patterns rollup.py owns
(`object_slug`, `mode`), the T2 projection, and the privacy property
those rest on: no free text from either input ever reaches an output.

`rollup.py` is deliberately NOT added to conftest's `run` fixture (that
whitelist is the seven scripts of `SCRIPT_NAMES`); this module drives the
script through its own subprocess helper, with the same hardened
environment.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime

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
    # R-T9: the object's scale — three counts the closing stage measured
    # and passed in, never anything this script went out and read.
    "object",
    "started",
    "ended",
    "wallclock_s",
    "lenses",
    "batches",
    "passes",
    "stages",
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
STAGE_KEYS = {"stage", "started", "ended", "wallclock_s", "spans_n"}
FINDINGS_KEYS = {"by_severity", "by_terminal", "fix_application_n"}
TOTALS_KEYS = {"tokens", "coverage"}
METRIC_KEYS = {
    "CFR",
    "FPL",
    "VP",
    "TVR",
    "FADS",
    "RDE",
    "SWP",
    # The four classes of round time: parallelism, the per-stage
    # orchestrator remainder, the round's idle, and the owner's wait.
    "PAR",
    "ORE",
    "IDLE",
    "OWN",
}
TVR_KEYS = {"in", "out", "cache_write", "cache_read", "fresh", "reuse", "seconds"}
PAR_KEYS = {"union_s", "sum_s", "ratio", "idle_share"}
IDLE_KEYS = {"idle_s", "intervals_s", "gaps_n"}
# EXACTLY these two, and this is asserted by name: no reason key, no
# outcome key, no per-wait row. The breakdown stays local to the trace.
OWN_KEYS = {"wait_s", "share"}
# The object's scale: exactly three keys, and every value an integer or
# `null`. A string anywhere under here would be a name of something.
OBJECT_KEYS = {"lines_at_pin", "changed_lines", "files_touched"}
PROJECTION_KEYS = {
    "v",
    "round_key",
    "date",
    "mode",
    # `object{}` DOES cross, by the explicit disposition R-T6(b) demands:
    # three counts, the denominator a cross-project line needs.
    "object",
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
    # The round contract's two, terminal in the recount and therefore
    # terminal here: a status closure counts as closed and this histogram
    # counted as `open` would put M4's denominator at odds with closure.
    "out-of-scope-by-contract",
    "frozen-carried",
    # The Z3 closing act's own status, terminal in the recount for the same
    # reason and under the same zone condition the script re-checks here.
    "logged-no-action",
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
# The v3 schema: `zone` third, so the criterion stays the fourth cell from
# the END of the row — this script reads it exactly as the recount does.
HEADER_9 = (
    "| id | sev | zone | claim | verdict | criterion | fix | verified | "
    "terminal |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
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
    assert set(data["stages"][0]) == STAGE_KEYS


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


@pytest.mark.parametrize(
    "outcome",
    [
        # The form every trace of a closed round carries, still summed.
        "fixed:10,unworkable:10",
        # The three-part form. The regex reading it here is a DUPLICATE of
        # the validator's in `trace.py`: left anchored on the two-part form
        # it would match nothing on this line, sum nothing, and report the
        # batch as `fixed: 0` — a silent zero, which is what this case
        # exists to catch.
        "fixed:10,unworkable:10,notfound:10",
    ],
)
def test_a_batch_counts_both_written_forms_of_the_fixer_outcome(
    rollup, make_round, outcome
):
    records = full_round([fixer_span("B1", ["HA-1", "HA-2"], outcome=outcome)])
    ledger = make_round(ROWS_8, records=records)
    assert rollup(ledger).returncode == 0
    data = summary_of(ledger)
    batch = data["batches"][0]
    assert (batch["fixed"], batch["unworkable"]) == (10, 10)
    # `notfound` is READ and deliberately NOT projected: the batch entry
    # gains no third counter, so the summary keeps its specified shape.
    assert set(batch) == BATCH_KEYS
    assert "notfound" not in json.dumps(data)


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


def test_the_contracts_two_statuses_are_terminal_buckets_of_their_own(
    rollup, make_round
):
    """The recount's terminal set IS this histogram's terminal set.

    Both statuses close a row there, so a summary that counted them as
    `open` would put M4's denominator (`count(terminal rows)`) at odds with
    closure — the one disagreement these buckets exist to prevent.
    """
    rows = (
        "| HA-1 | minor | c | FIX | L1 — x | B1 | ok "
        "| out-of-scope-by-contract (NG-2, signed 2026-08-29) |\n"
        "| HA-2 | major | c | FIX | L1 — x | B1 | ok "
        "| frozen-carried (stop-rule, 2026-08-29) |\n"
    )
    ledger = make_round(rows, records=full_round([span()]))
    rollup(ledger)
    by_terminal = summary_of(ledger)["findings"]["by_terminal"]
    assert by_terminal["out-of-scope-by-contract"] == 1
    assert by_terminal["frozen-carried"] == 1
    assert by_terminal["open"] == 0


def test_an_incomplete_contract_literal_counts_as_open(rollup, make_round):
    """Recognized only in full, exactly as at closure.

    The bare status, a freeze with no date, an uncalendar date and a
    lower-cased `ng-2` all fail the recount's own patterns, so none of them
    is a terminal bucket here either.
    """
    rows = (
        "| HA-1 | minor | c | FIX | L1 — x | B1 | ok "
        "| out-of-scope-by-contract |\n"
        "| HA-2 | major | c | FIX | L1 — x | B1 | ok "
        "| frozen-carried (stop-rule) |\n"
        "| HA-3 | major | c | FIX | L1 — x | B1 | ok "
        "| out-of-scope-by-contract (NG-2, signed 2026-02-30) |\n"
        "| HA-4 | major | c | FIX | L1 — x | B1 | ok "
        "| out-of-scope-by-contract (ng-2, signed 2026-08-29) |\n"
    )
    ledger = make_round(rows, records=full_round([span()]))
    rollup(ledger)
    by_terminal = summary_of(ledger)["findings"]["by_terminal"]
    assert by_terminal["open"] == 4
    assert by_terminal["out-of-scope-by-contract"] == 0
    assert by_terminal["frozen-carried"] == 0


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


# --- the total-only token form ---------------------------------------------


def total_only_span(**over: object) -> dict[str, object]:
    """A span measured as ONE aggregate — no four-counter breakdown."""
    return span(
        tokens={"total": 1000},
        tokens_source="agent-tool-result-total",
        **over,
    )


def test_a_total_only_span_is_read_rather_than_refused(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([total_only_span()]))
    result = rollup(ledger)
    assert result.returncode == 0
    assert "schema-refused" not in result.stdout


def test_a_total_only_round_is_covered_beside_a_null_four_counter_total(
    rollup, make_round
):
    """Both halves of the one line: full coverage, and no counter sum."""
    records = full_round(
        [total_only_span(), total_only_span(span="s3.02", agent_id="a2")]
    )
    ledger = make_round(ROWS_8, records=records)
    result = rollup(ledger)
    assert "totals: tokens n/a | coverage 2/2 spans" in result.stdout
    totals = summary_of(ledger)["totals"]
    assert totals["tokens"] is None
    assert totals["coverage"] == "2/2 spans"


def test_a_total_only_span_never_mixes_into_the_four_counter_sum(rollup, make_round):
    records = full_round([span(), total_only_span(span="s3.02", agent_id="a2")])
    ledger = make_round(ROWS_8, records=records)
    result = rollup(ledger)
    assert result.returncode == 0
    summary = summary_of(ledger)
    assert summary["totals"]["tokens"] is None
    assert summary["totals"]["coverage"] == "2/2 spans"
    assert summary["lenses"][0]["tokens"] is None


def test_the_four_counter_sum_stands_where_no_total_only_span_is_present(
    rollup, make_round
):
    """PRESERVED: the four-counter path still sums, and still prints."""
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rollup(ledger)
    totals = summary_of(ledger)["totals"]
    assert totals["tokens"] == {"in": 1, "out": 2, "cache_write": 3, "cache_read": 4}
    assert totals["coverage"] == "1/1 spans"


def test_m4_names_the_missing_breakdown_rather_than_a_zero_gap(rollup, make_round):
    ledger = make_round(ROWS_8, records=full_round([total_only_span()]))
    result = rollup(ledger)
    tvr = summary_of(ledger)["metrics"]["TVR"]
    assert tvr["in"] == "n/a: usage measured without a counter breakdown"
    assert isinstance(tvr["seconds"], float)
    assert (
        "TVR: tokens n/a (usage measured without a counter breakdown)"
        in result.stdout
    )
    assert "0 of 1 spans without usage" not in result.stdout


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


# --- M6 (RDE) and M7 (SWP): the two stopping metrics ------------------------
#
# Both reach `round-summary.json` through the mechanism every other metric
# uses, and both are measurements only: a number or one of the fixed
# `n/a: <reason>` strings, never prose. `k` has the same single source here
# as in `recount.py` — the header's machine-form `Lenses:` lines — so the two
# scripts cannot report different lens counts for one round. M7's window is
# ordered by each ledger's own `Round-started`, never by argument position,
# and a `--prev` that cannot be read costs the metric its value and nothing
# else: no observability condition reaches this script's exit code.

LENS_HEADER = (
    "- Mode: plan.\n"
    "- Round-started: 2026-08-29\n"
    "- Lenses:\n"
    "  - AA | a | sonnet\n"
    "  - BB | b | sonnet\n"
    "  - CC | c | sonnet\n"
    "  - DD | d | sonnet\n"
    "  - EE | e | sonnet\n"
    "  timebox 15 min each; prose below the run is not counted.\n\n"
)
# The same window `recount.py`'s cases use: 7 -> 4 -> 2 major rows, so the
# deltas are -3 and -2 and the moving average is -2.5.
JACKKNIFE_ROWS = (
    "| AA-1 | major | c | FIX | crit | B1 | LANDED | verified-landed |\n"
    "| BB-1 | major | c | FIX | crit | B1 | LANDED | verified-landed |\n"
    "| CC-1 | major | c | FIX | crit | B1 | LANDED | verified-landed |\n"
    "| DD-1 | minor | c | FIX | =CC-1 | B1 | LANDED | verified-landed |\n"
    "| EE-1 | minor | c | FIX | crit | B1 | LANDED | verified-landed |\n"
    "| V1-1 | minor | c | FIX | crit | B1 | LANDED | verified-landed |\n"
)


def window(make_round, day: str, majors: int):
    """A ledger dated `day` with `majors` major rows — one plateau member."""
    rows = "".join(
        f"| PA-{i} | major | c | FIX | crit | B1 | LANDED | verified-landed |\n"
        for i in range(1, majors + 1)
    )
    return make_round(rows, preamble=f"- Mode: plan.\n- Round-started: {day}\n\n")


def test_rde_matches_the_hand_computed_value(rollup, make_round):
    """k=5, D=4, f1=3 -> 4 + (4/5)*3 = 6.4; the verifier row is no lens."""
    ledger = make_round(JACKKNIFE_ROWS, preamble=LENS_HEADER)
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["RDE"] == 6.4


def test_rde_is_na_below_the_applicability_floor(rollup, make_round):
    preamble = (
        "- Mode: plan.\n- Lenses:\n  - AA | a | sonnet\n  - BB | b | sonnet\n\n"
    )
    ledger = make_round(ROWS_8, preamble=preamble)
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["RDE"] == "n/a: k<4"


def test_rde_is_na_when_the_header_declares_no_lenses(rollup, make_round):
    """The compat shape: `k` is never guessed off the id prefixes."""
    ledger = make_round(ROWS_8)
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["RDE"] == "n/a: k not derived from the header"


def test_swp_is_na_without_a_window(rollup, make_round):
    ledger = make_round(ROWS_8)
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["SWP"] == "n/a: fewer than two previous ledgers"


def test_swp_is_the_moving_average_over_the_window(rollup, make_round):
    cur = window(make_round, "2026-08-29", 2)
    prev1 = window(make_round, "2026-08-20", 4)
    prev2 = window(make_round, "2026-08-10", 7)
    assert rollup(cur, "--prev", prev1, "--prev", prev2).returncode == 0
    assert summary_of(cur)["metrics"]["SWP"] == -2.5


def test_swp_ignores_the_order_of_its_arguments(rollup, make_round):
    """The chronology is the ledgers'; the argument order carries nothing."""
    cur = window(make_round, "2026-08-29", 2)
    prev1 = window(make_round, "2026-08-20", 4)
    prev2 = window(make_round, "2026-08-10", 7)
    assert rollup(cur, "--prev", prev2, "--prev", prev1).returncode == 0
    assert summary_of(cur)["metrics"]["SWP"] == -2.5


def test_swp_refuses_a_window_it_cannot_order(rollup, make_round):
    cur = window(make_round, "2026-08-29", 2)
    prev1 = window(make_round, "2026-08-20", 4)
    prev2 = make_round(ROWS_8)
    assert rollup(cur, "--prev", prev1, "--prev", prev2).returncode == 0
    assert summary_of(cur)["metrics"]["SWP"] == (
        "n/a: previous-ledger order not derived (Round-started)"
    )


def test_an_unreadable_prev_costs_the_metric_and_nothing_else(
    rollup, make_round, tmp_path
):
    cur = window(make_round, "2026-08-29", 2)
    prev1 = window(make_round, "2026-08-20", 4)
    result = rollup(cur, "--prev", prev1, "--prev", tmp_path / "absent.md")
    assert result.returncode == 0, result.stdout
    assert "unreadable: absent.md" in result.stdout
    assert summary_of(cur)["metrics"]["SWP"] == "n/a: a previous ledger could not be read"


def test_a_third_prev_is_a_usage_error(rollup, make_round):
    cur = window(make_round, "2026-08-29", 2)
    prev1 = window(make_round, "2026-08-20", 4)
    result = rollup(cur, "--prev", prev1, "--prev", prev1, "--prev", prev1)
    assert result.returncode == 2
    assert "Usage:  rollup.py" in result.stdout


def test_the_table_prints_both_stopping_metrics(rollup, make_round):
    ledger = make_round(JACKKNIFE_ROWS, preamble=LENS_HEADER)
    out = rollup(ledger).stdout
    assert "RDE: 6.4 (ESTIMATE — advisory, in no stop rule)" in out
    assert "SWP: n/a: fewer than two previous ledgers" in out


def test_the_projection_carries_the_two_metrics_and_no_prose(
    rollup, make_round, tmp_path
):
    """T2 gets the numbers, never the caveat: the summary holds no prose."""
    ledger = make_round(
        JACKKNIFE_ROWS, preamble=LENS_HEADER, records=full_round([span()])
    )
    rounds = tmp_path / "rounds.jsonl"
    assert rollup(ledger, "--rounds", rounds).returncode == 0
    line = json.loads(rounds.read_text(encoding="utf-8").splitlines()[0])
    assert line["metrics"]["RDE"] == 6.4
    assert line["metrics"]["SWP"] == "n/a: fewer than two previous ledgers"
    assert "ADVISORY" not in rounds.read_text(encoding="utf-8")


def test_a_prev_with_a_refused_schema_costs_the_metric_only(rollup, make_round):
    """A window member whose table is not 7, 8 or 9 cells is refused, not fatal."""
    cur = window(make_round, "2026-08-29", 2)
    prev1 = window(make_round, "2026-08-20", 4)
    prev2 = make_round("", header="| id |\n|---|\n")
    result = rollup(cur, "--prev", prev1, "--prev", prev2)
    assert result.returncode == 0, result.stdout
    assert "schema-refused: fix-ledger.md" in result.stdout
    assert summary_of(cur)["metrics"]["SWP"] == "n/a: a previous ledger could not be read"


# --- 0.3.0 zones: the v3 nine-cell ledger ----------------------------------
# The rollup is an instrument, never a gate — but its terminal histogram is
# M4's denominator, so a status the recount closes on and this script counts
# as `open` would put the two at odds. `logged-no-action` is that status, and
# it carries the recount's own zone condition here.

V3_ROWS = (
    "| DA-1 | major | Z2 | claim | verdict | crit | b1 | LANDED | "
    "verified-landed |\n"
    "| DA-2 | minor | Z3 | claim | logged | crit | b1 | x | "
    "logged-no-action |\n"
)


def test_a_v3_ledger_is_read_rather_than_refused(rollup, make_round):
    ledger = make_round(V3_ROWS, header=HEADER_9)
    result = rollup(ledger)
    assert result.returncode == 0, result.stdout
    assert "schema-refused" not in result.stdout
    assert "findings: rows 2 | terminal 2" in result.stdout


def test_logged_no_action_at_z3_is_bucketed_terminal(rollup, make_round):
    ledger = make_round(V3_ROWS, header=HEADER_9)
    assert rollup(ledger).returncode == 0
    by_terminal = summary_of(ledger)["findings"]["by_terminal"]
    assert by_terminal["logged-no-action"] == 1
    assert by_terminal["open"] == 0


def test_logged_no_action_outside_z3_is_bucketed_open(rollup, make_round):
    """The recount calls that row a structural error; `open` is what agrees.

    Counting it as terminal here would make M4's denominator wider than
    closure's — the one thing these buckets exist not to do.
    """
    ledger = make_round(V3_ROWS.replace("| Z3 |", "| Z1 |"), header=HEADER_9)
    assert rollup(ledger).returncode == 0
    by_terminal = summary_of(ledger)["findings"]["by_terminal"]
    assert by_terminal["logged-no-action"] == 0
    assert by_terminal["open"] == 1


def test_the_criterion_of_a_v3_row_is_read_from_the_end(rollup, make_round):
    """A hard `cells[4]` would read the VERDICT prose of a nine-cell row.

    The RDE's cross-lens duplicate collapse is what makes that visible: it
    reads the `=<primary-id>` convention out of the criterion cell. This is
    the v3 form of the hand-computed case above, so the value must be the
    SAME 6.4; a `cells[4]` read would see the verdict `FIX` everywhere, find
    no duplicate, and give D=5, f1=4 -> 8.2.
    """
    rows = JACKKNIFE_ROWS.replace("| c | FIX |", "| Z2 | c | FIX |")
    ledger = make_round(rows, header=HEADER_9, preamble=LENS_HEADER)
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["RDE"] == 6.4


# --- the composite id contract: `V-CIT-1` and its `=V-CIT-1` pointer --------
#
# The id contract read here is `recount.py`'s, and that contract accepts a
# dash-joined composite prefix — the form a verifier uses to keep the lens it
# re-checked inside the id. A narrower shape in this script would drop such a
# row from every histogram and read its `=<primary-id>` pointer as prose, so
# both halves are pinned: the row is counted, and the two rows pointing at it
# collapse into ONE distinct finding.

COMPOSITE_ROWS = (
    "| V-CIT-1 | minor | c | FIX | crit | B1 | LANDED | verified-landed |\n"
    "| AA-1 | major | c | FIX | =V-CIT-1 | B1 | LANDED | verified-landed |\n"
    "| BB-1 | major | c | FIX | =V-CIT-1 | B1 | LANDED | verified-landed |\n"
    "| CC-1 | major | c | FIX | crit | B1 | LANDED | verified-landed |\n"
    "| DD-1 | minor | c | FIX | crit | B1 | LANDED | verified-landed |\n"
    "| EE-1 | minor | c | FIX | crit | B1 | LANDED | verified-landed |\n"
)


def test_a_composite_id_row_is_read_and_bucketed(rollup, make_round):
    """`V-CIT-1` is a row of the table, not a line the parser walks past."""
    ledger = make_round(COMPOSITE_ROWS, preamble=LENS_HEADER)
    result = rollup(ledger)
    assert result.returncode == 0, result.stdout
    assert "findings: rows 6 | terminal 6" in result.stdout
    findings = summary_of(ledger)["findings"]
    assert findings["by_severity"]["minor"] == 3
    assert findings["by_severity"]["major"] == 3
    assert findings["by_terminal"]["verified-landed"] == 6


def test_a_duplicate_pointer_at_a_composite_id_collapses_its_group(
    rollup, make_round
):
    """k=5, D=4, f1=3 -> 4 + (4/5)*3 = 6.4: the AA and BB rows are ONE group.

    A pointer shape that refused the composite id would key each of them on
    its own id instead, give D=5, f1=5 and 9.0, and so report a round as
    holding more distinct findings than it has.
    """
    ledger = make_round(COMPOSITE_ROWS, preamble=LENS_HEADER)
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["RDE"] == 6.4


# --- stages[] and M8-M11: the four classes of round time --------------------
#
# The round already writes every span these read; nothing below asks it to
# write one more. `stages[]` is the per-stage ENVELOPE derived from the
# `stage` FIELD of the spans that exist, and the four metrics are the four
# quantities that envelope makes answerable: how much of the round ran at
# once (PAR), how much of a stage no span covered (ORE), how much of the
# round nothing covered (IDLE), and how much of it was the owner's wait
# (OWN). Three numbers are deliberately kept apart throughout — the SUM of
# the spans' own `wallclock_s`, their ENVELOPE, and the UNION of their
# intervals — and every fixture below is built so the three differ.

CLOCK_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DAY = "2026-08-11T"
# The floor an idle stretch must reach to be listed, mirrored from the
# script: a gap AT the floor is listed, one below it is only counted.
FLOOR_S = 240
# The two forms no value inside `metrics` may take, in the projected line or
# in the local summary — `trace.py`'s own timestamp pattern and the day it
# coarsens to.
TIMESTAMP_FORM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DATE_FORM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def at(clock: str) -> str:
    """Return a round-day timestamp for a wall-clock time."""
    return f"{DAY}{clock}Z"


def seconds_between(start: str, end: str) -> int:
    """Return the seconds between two timestamps — the fixtures' own arithmetic."""
    first = datetime.strptime(start, CLOCK_FORMAT).replace(tzinfo=UTC)
    last = datetime.strptime(end, CLOCK_FORMAT).replace(tzinfo=UTC)
    return int((last - first).total_seconds())


def timed(span_id: str, stage: int, start: str, end: str, **over: object):
    """A closed span covering a known stretch, its `wallclock_s` derived.

    Deriving rather than declaring it keeps the fixture from raising a
    `wallclock-mismatch` defect it never meant to test.
    """
    started, ended = at(start), at(end)
    return span(
        span=span_id,
        stage=stage,
        started=started,
        ended=ended,
        wallclock_s=seconds_between(started, ended),
        **over,
    )


def opened(span_id: str, stage: int, start: str, **over: object):
    """An `open` record with no close — an UNCLOSED span."""
    record: dict[str, object] = {
        "v": 1,
        "kind": "open",
        "round": ROUND,
        "span": span_id,
        "parent": "s1.00",
        "stage": stage,
        "actor": "critic",
        "unit": "HZ",
        "id_prefix": "HZ",
        "model_assigned": "sonnet",
        "started": at(start),
    }
    record.update(over)
    return record


def owner_wait(span_id: str, start: str, end: str, unit: str = "owner-wait-signature"):
    """A closed owner-wait span: an ORCHESTRATOR unit from the closed six."""
    return timed(
        span_id,
        6,
        start,
        end,
        actor="orchestrator",
        unit=unit,
        id_prefix=None,
        agent_id=None,
        model_assigned="n/a",
        model_actual="n/a",
        model_source="n/a",
        tokens=None,
        tokens_source="absent",
        outcome="answered",
    )


def windowed(records: list[dict[str, object]], start: str, end: str):
    """A closed round whose own window is stated rather than defaulted."""
    close = round_close()
    close.update(
        {
            "started": at(start),
            "ended": at(end),
            "wallclock_s": seconds_between(at(start), at(end)),
        }
    )
    return [round_open(started=at(start)), *records, close]


# The worked fixture, hand-computed once and reused. Window 10:00:00 ->
# 12:00:00 = 7200 s. Stage 3 holds two OVERLAPPING spans and a third apart
# from them; stages 5 and 7 hold one each; stages 1, 2, 4, 6, 8 and 9 hold
# none.
#   sum of the spans' own wallclock  1200+1200+660+180+720 = 3960
#   union of their intervals         1800 + 660 + 180 + 720 = 3360
#   stage-3 envelope                 10:10:00 -> 10:56:00   = 2760
#   stage-3 sum                      1200 + 1200 + 660      = 3060
#   stage-3 union                    1800 + 660             = 2460
#   gaps in the window   600, 300, 240, 120, 2580  (five; one below FLOOR_S)
WORKED = [
    timed("s3.01", 3, "10:10:00", "10:30:00"),
    timed("s3.02", 3, "10:20:00", "10:40:00"),
    timed("s3.03", 3, "10:45:00", "10:56:00"),
    timed("s5.01", 5, "11:00:00", "11:03:00"),
    timed("s7.01", 7, "11:05:00", "11:17:00"),
]


def strings_under(value: object):
    """Yield every string VALUE in a nested JSON structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_under(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_under(item)


# --- R-T2: stages[] ---------------------------------------------------------


def test_stages_carry_the_envelope_of_the_spans_that_name_them(rollup, make_round):
    """One row per stage, `min(started)`/`max(ended)` over its own spans."""
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["stages"] == [
        {
            "stage": 3,
            "started": at("10:10:00"),
            "ended": at("10:56:00"),
            "wallclock_s": 2760,
            "spans_n": 3,
        },
        {
            "stage": 5,
            "started": at("11:00:00"),
            "ended": at("11:03:00"),
            "wallclock_s": 180,
            "spans_n": 1,
        },
        {
            "stage": 7,
            "started": at("11:05:00"),
            "ended": at("11:17:00"),
            "wallclock_s": 720,
            "spans_n": 1,
        },
    ]


def test_a_stage_envelope_is_not_the_sum_of_its_overlapping_spans(
    rollup, make_round
):
    """Stage 3's two spans overlap, so the envelope and the sum differ.

    `passes[]` already names the envelope `wallclock_s`; this field carries
    the same quantity under the same name. A sum would report 3060 s for a
    stage that took 2760.
    """
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    assert rollup(ledger).returncode == 0
    stage3 = summary_of(ledger)["stages"][0]
    assert stage3["wallclock_s"] == 2760
    assert stage3["wallclock_s"] != 1200 + 1200 + 660


def test_a_stage_with_no_span_gets_no_row_at_all(rollup, make_round):
    """Not a `0`, not a `null` — no row: nothing was measured there."""
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    assert rollup(ledger).returncode == 0
    assert [row["stage"] for row in summary_of(ledger)["stages"]] == [3, 5, 7]


def test_the_round_span_is_not_a_stage_of_its_own(rollup, make_round):
    """`s1.00` carries `stage: 1`, and it is still not stage 1's envelope.

    Its interval is the whole round — the reason `work_spans` keeps it out
    of every sum — so a stage-1 row built from it would report the round as
    the stage and make M9's remainder for stage 1 identically zero.
    """
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    assert rollup(ledger).returncode == 0
    data = summary_of(ledger)
    assert 1 not in [row["stage"] for row in data["stages"]]
    assert 7200 not in [row["wallclock_s"] for row in data["stages"]]


def test_stages_do_not_enter_the_rounds_projection(rollup, make_round, tmp_path):
    """The absence of `stages` from the projection is a PRESERVED property.

    The field carries an absolute `started`/`ended` per stage while the
    projection coarsens only the top-level pair to a day, so the disposition
    is that it does not cross. It is achieved by INACTION — the allowlist
    simply does not name the key — and the absence assertion alone would
    hold before this batch too, when there was no key to omit. The last
    line is what pairs it with a differentiating one: the local summary DOES
    carry the stages the projection leaves behind.
    """
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    rounds = tmp_path / "rounds.jsonl"
    assert rollup(ledger, "--rounds", rounds).returncode == 0
    line = json.loads(rounds.read_text(encoding="utf-8").strip())
    assert set(line) == PROJECTION_KEYS
    assert "stages" not in line
    assert summary_of(ledger)["stages"], "the local summary DOES carry them"


# --- R-T3(d): the union primitive -------------------------------------------


def test_the_union_is_neither_the_envelope_nor_the_sum(rollup, make_round):
    """Overlapping, nested and disjoint spans, where all three numbers differ.

    Four stage-4 spans: 10:00-10:10 and 10:05-10:15 overlap, 10:06-10:08 is
    nested inside both, 10:30-10:40 is disjoint.
        sum       600 + 600 + 120 + 600 = 1920
        union     (10:00-10:15) 900 + 600 = 1500
        envelope  10:00 -> 10:40         = 2400
    """
    records = [
        timed("s4.01", 4, "10:00:00", "10:10:00"),
        timed("s4.02", 4, "10:05:00", "10:15:00"),
        timed("s4.03", 4, "10:06:00", "10:08:00"),
        timed("s4.04", 4, "10:30:00", "10:40:00"),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    assert rollup(ledger).returncode == 0
    data = summary_of(ledger)
    assert data["metrics"]["PAR"]["sum_s"] == 1920
    assert data["metrics"]["PAR"]["union_s"] == 1500
    assert data["stages"][0]["wallclock_s"] == 2400


def test_an_unclosed_span_refuses_the_union_rather_than_shortening_it(
    rollup, make_round
):
    """No `ended` is invented, and no confident smaller number is reported."""
    records = [
        timed("s4.01", 4, "10:00:00", "10:10:00"),
        opened("s4.02", 4, "10:20:00"),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    assert rollup(ledger).returncode == 0
    data = summary_of(ledger)
    assert data["metrics"]["PAR"]["union_s"] == "n/a: 1 unclosed spans"
    assert data["metrics"]["PAR"]["ratio"] == "n/a: 1 unclosed spans"
    assert data["metrics"]["IDLE"] == "n/a: 1 unclosed spans"


# --- R-T3(a): M8 PAR --------------------------------------------------------


def test_m8_is_the_union_against_the_sum_with_the_idle_share(rollup, make_round):
    """The worked fixture: union 3360 s, sum 3960 s, idle 3840 s of 7200 s."""
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    result = rollup(ledger)
    assert result.returncode == 0
    par = summary_of(ledger)["metrics"]["PAR"]
    assert set(par) == PAR_KEYS
    assert par["union_s"] == 3360
    assert par["sum_s"] == 3960
    assert par["ratio"] == 0.8485
    assert par["idle_share"] == 0.5333
    assert (
        "PAR: union 3360s / sum 3960s = 0.8485 | idle_share 0.5333" in result.stdout
    )


def test_m8_idle_share_is_m10_over_the_window_and_not_one_minus_the_ratio(
    rollup, make_round
):
    """The two shares of M8 have different denominators and do not sum to 1.

    `ratio` is the union over the SUM; `idle_share` is M10's own idle over
    the round WINDOW — the same denominator M11's `share` uses. Reporting
    `1 - ratio` here would give 0.1515 for a round that idled 53 % of its
    length.
    """
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    assert rollup(ledger).returncode == 0
    metrics = summary_of(ledger)["metrics"]
    assert metrics["PAR"]["idle_share"] == round(metrics["IDLE"]["idle_s"] / 7200, 4)
    assert metrics["PAR"]["idle_share"] != round(1 - metrics["PAR"]["ratio"], 4)


# --- R-T3(b): M9 ORE --------------------------------------------------------


def test_m9_is_the_stage_envelope_minus_the_union_of_its_own_spans(
    rollup, make_round
):
    """Stage 3: envelope 2760 minus union 2460 = 300 s no span covered.

    The 10:40:00 -> 10:45:00 stretch is the whole of it. Stages 5 and 7 hold
    one span each, so their remainder is 0 — a measured zero, printed.
    """
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    result = rollup(ledger)
    assert result.returncode == 0
    assert summary_of(ledger)["metrics"]["ORE"] == {"3": 300, "5": 0, "7": 0}
    assert "ORE: s3 300s s5 0s s7 0s" in result.stdout


def test_m9_is_na_when_no_span_names_a_stage(rollup, make_round):
    """A round whose only span is the root has no stage to take a remainder of."""
    ledger = make_round(ROWS_8, records=full_round())
    result = rollup(ledger)
    assert result.returncode == 0
    assert summary_of(ledger)["metrics"]["ORE"] == "n/a: no stage spans"
    assert "ORE: n/a: no stage spans" in result.stdout


def test_m9_refuses_one_stage_and_keeps_the_stages_it_could_measure(
    rollup, make_round
):
    """A stage holding a closed AND an unclosed span carries its OWN `n/a`.

    The remainder is per stage, so the refusal is per stage too. Stage 3's
    union is unmeasurable while `s3.02` has no close, and the entry is the
    reason string; stage 5, whose two spans are both closed, keeps its
    measured 1800 - 1200 = 600 s in the same object. Subtracting a union
    short of the unclosed span would report stage 3's whole envelope as
    orchestrator remainder — 1200 s nobody spent.
    """
    records = [
        timed("s3.01", 3, "10:10:00", "10:30:00"),
        opened("s3.02", 3, "10:40:00"),
        timed("s5.01", 5, "11:00:00", "11:10:00"),
        timed("s5.02", 5, "11:20:00", "11:30:00"),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    result = rollup(ledger)
    assert result.returncode == 0
    ore = summary_of(ledger)["metrics"]["ORE"]
    assert ore == {"3": "n/a: 1 unclosed spans", "5": 600}
    assert "ORE: s3 n/a: 1 unclosed spans s5 600s" in result.stdout


# --- R-T3(c): M10 IDLE ------------------------------------------------------


def test_m10_counts_every_gap_and_lists_only_the_long_ones(rollup, make_round):
    """Five gaps, four listed: `gaps_n` is the count the listing cannot give.

    The window's uncovered stretches are 600, 300, 240, 120 and 2580 s. The
    120 s one is below the printing floor and never reaches `intervals_s`,
    so a `gaps_n` derived from the listing would say four and lose it; the
    field is asserted here with its own known number for exactly that
    reason.
    """
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    result = rollup(ledger)
    assert result.returncode == 0
    idle = summary_of(ledger)["metrics"]["IDLE"]
    assert set(idle) == IDLE_KEYS
    assert idle["idle_s"] == 3840
    assert idle["intervals_s"] == [2580, 600, 300, 240]
    assert idle["gaps_n"] == 5
    assert idle["gaps_n"] > len(idle["intervals_s"])
    assert min(idle["intervals_s"]) == FLOOR_S, "a gap AT the floor is listed"
    assert "IDLE: 3840s | intervals 2580/600/300/240s (4 of 5)" in result.stdout


def test_m10_lists_nothing_when_every_gap_is_short(rollup, make_round):
    """The first pinned corner: `intervals none (0 of <m>)`, and not `n/a`.

    A 600 s window covered in three 120 s spans leaves two 120 s gaps. The
    idle is known — 240 s — and so is the number of gaps; only the listing
    is empty.
    """
    records = [
        timed("s3.01", 3, "10:00:00", "10:02:00"),
        timed("s3.02", 3, "10:04:00", "10:06:00"),
        timed("s3.03", 3, "10:08:00", "10:10:00"),
    ]
    ledger = make_round(
        ROWS_8, records=windowed(records, "10:00:00", "10:10:00")
    )
    result = rollup(ledger)
    assert result.returncode == 0
    idle = summary_of(ledger)["metrics"]["IDLE"]
    assert idle == {"idle_s": 240, "intervals_s": [], "gaps_n": 2}
    assert "IDLE: 240s | intervals none (0 of 2)" in result.stdout


def test_m10_is_a_measured_zero_on_a_round_covered_end_to_end(rollup, make_round):
    """The second pinned corner: `0s | intervals none (0 of 0)`, never `n/a`.

    `n/a` belongs to incomplete data — an unclosed span, an unmeasured
    window. A round nothing idled in is a measurement, and it is zero.
    """
    records = [timed("s3.01", 3, "10:00:00", "12:00:00")]
    ledger = make_round(ROWS_8, records=full_round(records))
    result = rollup(ledger)
    assert result.returncode == 0
    assert summary_of(ledger)["metrics"]["IDLE"] == {
        "idle_s": 0,
        "intervals_s": [],
        "gaps_n": 0,
    }
    assert "IDLE: 0s | intervals none (0 of 0)" in result.stdout


def test_m10_is_na_while_the_round_window_is_not_measured(rollup, make_round):
    """On the ordinary path `s1.00` is still open, and no window is invented."""
    ledger = make_round(ROWS_8, records=[round_open(), *WORKED])
    assert rollup(ledger).returncode == 0
    metrics = summary_of(ledger)["metrics"]
    assert metrics["IDLE"] == "n/a: no measured round window"
    assert metrics["PAR"]["idle_share"] == "n/a: no measured round window"
    assert metrics["PAR"]["union_s"] == 3360, "the union needs no window"


# --- R-T3(f): M11 OWN -------------------------------------------------------


def test_m11_sums_the_closed_owner_wait_spans_over_the_round(rollup, make_round):
    """Two waits of 900 s and 300 s in a 7200 s round: 1200 s, share 0.1667."""
    records = [
        owner_wait("s6.01", "10:20:00", "10:35:00"),
        owner_wait("s6.02", "11:00:00", "11:05:00", unit="owner-wait-fork"),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    result = rollup(ledger)
    assert result.returncode == 0
    own = summary_of(ledger)["metrics"]["OWN"]
    assert set(own) == OWN_KEYS
    assert own["wait_s"] == 1200
    assert own["share"] == 0.1667
    assert "OWN: wait 1200s / round 7200s = 0.1667" in result.stdout


def test_m11_is_a_sum_and_never_a_union(rollup, make_round):
    """Two waits that OVERLAP are two waits: 900 + 900, not the union 1200.

    The union primitive exists in this file and is deliberately not applied
    here — the second reading was available and is refused.
    """
    records = [
        owner_wait("s6.01", "10:00:00", "10:15:00"),
        owner_wait("s6.02", "10:10:00", "10:25:00", unit="owner-wait-fork"),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["OWN"]["wait_s"] == 1800


def test_m11_is_na_with_its_own_counter_on_an_unclosed_wait(rollup, make_round):
    """An unclosed wait is not an undercount, and its counter is M11's own."""
    records = [
        owner_wait("s6.01", "10:20:00", "10:35:00"),
        opened(
            "s6.02",
            6,
            "11:00:00",
            actor="orchestrator",
            unit="owner-wait-amendment",
            id_prefix=None,
            model_assigned="n/a",
        ),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    result = rollup(ledger)
    assert result.returncode == 0
    metrics = summary_of(ledger)["metrics"]
    assert metrics["OWN"] == "n/a: 1 unclosed owner-wait spans"
    assert metrics["OWN"] != 900
    assert "OWN: n/a: 1 unclosed owner-wait spans" in result.stdout


def test_the_unclosed_counters_of_m10_and_m11_are_separate(rollup, make_round):
    """A span unclosed outside the waits refuses M10 and leaves M11 measured.

    The two counters are different because the sets are: an unclosed span
    that is no owner wait does not enter M11, and an unclosed wait would
    make both `n/a` under two different reasons.
    """
    records = [owner_wait("s6.01", "10:20:00", "10:35:00"), opened("s3.09", 3, "11:00:00")]
    ledger = make_round(ROWS_8, records=full_round(records))
    assert rollup(ledger).returncode == 0
    metrics = summary_of(ledger)["metrics"]
    assert metrics["IDLE"] == "n/a: 1 unclosed spans"
    assert metrics["OWN"]["wait_s"] == 900


def test_m11_is_na_rather_than_zero_without_an_owner_wait_span(rollup, make_round):
    """Deliberately unlike M10's zero: every older trace looks like this one.

    A trace written before the metric existed is indistinguishable from a
    round in which the owner was never waited for, so `0s` would be an
    assertion rather than a measurement. The nearest precedent is M9's
    `n/a: no stage spans`.
    """
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    result = rollup(ledger)
    assert result.returncode == 0
    assert summary_of(ledger)["metrics"]["OWN"] == "n/a: no owner-wait spans"
    assert "OWN: n/a: no owner-wait spans" in result.stdout


def test_an_owner_wait_unit_on_another_actor_is_not_a_wait(rollup, make_round):
    """Waiting for the owner is an ORCHESTRATOR unit, not a free-floating one.

    `subagent-observed` accepts a free-form unit that an `owner-wait-…`
    string satisfies, so the unit alone would be wider than the schema and
    would count somebody else's work as the owner's wait.
    """
    records = [
        timed(
            "s3.09",
            3,
            "10:20:00",
            "10:35:00",
            actor="subagent-observed",
            unit="owner-wait-signature",
            id_prefix=None,
            outcome="observed:tokens",
        ),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    assert rollup(ledger).returncode == 0
    assert summary_of(ledger)["metrics"]["OWN"] == "n/a: no owner-wait spans"


# --- R-T3(e): the form that leaves the machine ------------------------------


def test_the_projected_own_carries_exactly_wait_s_and_share(
    rollup, make_round, tmp_path
):
    """Asserted on `metrics.OWN` BY NAME, not on the metrics subtree at large.

    The whole point of the field is what it does NOT carry: no reason, no
    outcome, no per-wait row, no absolute time mark. Those stay in the local
    trace, on the machine that wrote it.
    """
    records = [
        owner_wait("s6.01", "10:20:00", "10:35:00"),
        owner_wait("s6.02", "11:00:00", "11:05:00", unit="owner-wait-fork"),
    ]
    ledger = make_round(ROWS_8, records=full_round(records))
    rounds = tmp_path / "rounds.jsonl"
    assert rollup(ledger, "--rounds", rounds).returncode == 0
    own = json.loads(rounds.read_text(encoding="utf-8").strip())["metrics"]["OWN"]
    assert set(own) == OWN_KEYS
    assert own == {"wait_s": 1200, "share": 0.1667}
    for text in strings_under(own):
        assert not TIMESTAMP_FORM_RE.match(text)
        assert not DATE_FORM_RE.match(text)


def test_the_projected_idle_intervals_are_integers_and_nothing_else(
    rollup, make_round, tmp_path
):
    """Durations leave the machine; the moments they happened at do not."""
    ledger = make_round(ROWS_8, records=full_round(WORKED))
    rounds = tmp_path / "rounds.jsonl"
    assert rollup(ledger, "--rounds", rounds).returncode == 0
    idle = json.loads(rounds.read_text(encoding="utf-8").strip())["metrics"]["IDLE"]
    assert idle["intervals_s"] == [2580, 600, 300, 240]
    assert all(isinstance(v, int) and not isinstance(v, bool) for v in idle["intervals_s"])


def test_no_projected_metric_value_takes_a_timestamp_or_date_form(
    rollup, make_round, tmp_path
):
    """PRESERVED property of the R-T3(e) ban, true before this batch as well.

    `project()` passes the whole `metrics` object through UNFILTERED, so the
    day-level coarsening it applies to `started`/`ended` does not protect
    the metrics; the ban is kept by what the metrics are built from, and
    this case watches it. It does not by itself distinguish before from
    after — the assertions that do are the four fixtures above.
    """
    records = [*WORKED, owner_wait("s6.01", "10:20:00", "10:35:00")]
    ledger = make_round(ROWS_8, records=full_round(records))
    rounds = tmp_path / "rounds.jsonl"
    assert rollup(ledger, "--rounds", rounds).returncode == 0
    line = json.loads(rounds.read_text(encoding="utf-8").strip())
    values = list(strings_under(line["metrics"]))
    assert values, "the metrics do carry strings — the n/a reasons"
    for text in values:
        assert not TIMESTAMP_FORM_RE.match(text), text
        assert not DATE_FORM_RE.match(text), text
    assert DATE_FORM_RE.match(line["date"]), "the day IS carried, outside metrics"


def test_m8_refuses_a_ratio_with_no_span_to_divide_by(rollup, make_round):
    """An empty denominator is `n/a: <reason>` here as everywhere else.

    A round whose only span is the root has nothing to divide by, so
    `ratio` is refused rather than reported as `0` or `1.0`. The idle is
    still measured, and it is the whole round: nothing covered any of it.
    """
    ledger = make_round(ROWS_8, records=full_round())
    result = rollup(ledger)
    assert result.returncode == 0
    metrics = summary_of(ledger)["metrics"]
    assert metrics["PAR"] == {
        "union_s": 0,
        "sum_s": 0,
        "ratio": "n/a: round has no spans",
        "idle_share": 1.0,
    }
    assert metrics["IDLE"] == {"idle_s": 7200, "intervals_s": [7200], "gaps_n": 1}


# --- R-T9: `object{}` — the scale the closing stage measured ----------------
#
# The three counts come out of `git diff --numstat` at stage 9, and this
# script runs no command: they arrive as arguments and leave as numbers.
# So what these cases pin is exactly what the script is responsible for —
# that a given count reaches the summary and the T2 line UNMODIFIED, that
# an ungiven one is `null` rather than a plausible `0`, that a malformed
# one is refused the way every other value here is, and that no string can
# get into the field. Which diff ends and which paths were measured is the
# closing stage's own text (`references/stage-9-closure.md`), where the
# three commands stand verbatim with the `':(exclude).critic-ledger/<run>/'`
# pathspec that keeps the round from counting its own records as work on
# the object.


def test_a_plan_rounds_three_counts_reach_the_summary_unmodified(
    rollup, make_round
):
    """The plan-mode fixture: line count at the pin, then the round's work."""
    ledger = make_round(ROWS_8, records=full_round([span()]))
    result = rollup(
        ledger,
        "--lines-at-pin",
        4811,
        "--changed-lines",
        372,
        "--files-touched",
        9,
    )
    assert result.returncode == 0
    scale = summary_of(ledger)["object"]
    assert set(scale) == OBJECT_KEYS
    assert scale == {"lines_at_pin": 4811, "changed_lines": 372, "files_touched": 9}


def test_an_impl_rounds_three_counts_reach_the_summary_unmodified(
    rollup, make_round
):
    """The impl-mode fixture: `lines_at_pin` is the RANGE's own size.

    Nothing in the script distinguishes the modes — the difference lives
    in which `git diff --numstat` the closing stage runs — so the case
    that matters here is that an impl round's numbers pass through the
    same way, `mode` included.
    """
    ledger = make_round(
        ROWS_8, records=full_round([span()]), preamble="- Mode: impl.\n\n"
    )
    result = rollup(
        ledger,
        "--lines-at-pin",
        1204,
        "--changed-lines",
        88,
        "--files-touched",
        4,
    )
    assert result.returncode == 0
    data = summary_of(ledger)
    assert data["mode"] == "impl"
    assert data["object"] == {
        "lines_at_pin": 1204,
        "changed_lines": 88,
        "files_touched": 4,
    }


def test_the_round_folders_own_records_do_not_move_the_counts(
    rollup, make_round
):
    """A record inside `.critic-ledger/<run>/` never reaches the counts.

    The exclusion is in the commands the closing stage runs, not here —
    this script reads no repository at all. What that leaves it
    responsible for is the other half of the same property: a run folder
    filling up with the round's own files moves no count, because the
    numbers it was given are the only numbers it has.
    """
    ledger = make_round(ROWS_8, records=full_round([span()]))
    (ledger.parent / "critic-CIT-report.md").write_text(
        "\n".join(f"a line of the round's own record {n}" for n in range(200)),
        encoding="utf-8",
    )
    (ledger.parent / "gates").mkdir()
    (ledger.parent / "gates" / "K-1.sh").write_text(
        "#!/bin/sh\nexit 0\n", encoding="utf-8"
    )
    result = rollup(
        ledger,
        "--lines-at-pin",
        4811,
        "--changed-lines",
        372,
        "--files-touched",
        9,
    )
    assert result.returncode == 0
    assert summary_of(ledger)["object"] == {
        "lines_at_pin": 4811,
        "changed_lines": 372,
        "files_touched": 9,
    }


def test_a_count_that_was_not_given_is_null_and_never_zero(rollup, make_round):
    """Unmeasured and zero are different facts; only one is written."""
    ledger = make_round(ROWS_8, records=full_round([span()]))
    assert rollup(ledger, "--files-touched", 9).returncode == 0
    assert summary_of(ledger)["object"] == {
        "lines_at_pin": None,
        "changed_lines": None,
        "files_touched": 9,
    }


@pytest.mark.parametrize(
    "value", ["twelve", "-4", "3.5", "1000000000", "9 ; rm -rf /", ""]
)
def test_a_count_outside_its_form_is_refused_not_carried(
    rollup, make_round, value
):
    """One `schema-refused` diagnostic, `null` in its place, summary written."""
    ledger = make_round(ROWS_8, records=full_round([span()]))
    result = rollup(ledger, "--changed-lines", value)
    assert result.returncode == 0
    assert "schema-refused: round-summary.json" in result.stdout
    assert summary_of(ledger)["object"]["changed_lines"] is None


def test_the_projection_carries_the_object_scale_and_no_string_under_it(
    rollup, make_round, tmp_path
):
    """R-T9(a-2): `object{}` enters `--rounds`, as three numbers and nothing else."""
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rounds = tmp_path / "rounds.jsonl"
    assert rollup(
        ledger,
        "--rounds",
        rounds,
        "--lines-at-pin",
        4811,
        "--changed-lines",
        372,
        "--files-touched",
        9,
    ).returncode == 0
    line = json.loads(rounds.read_text(encoding="utf-8").strip())
    assert set(line) == PROJECTION_KEYS
    assert set(line["object"]) == OBJECT_KEYS
    assert line["object"] == summary_of(ledger)["object"]
    assert line["object"] == {
        "lines_at_pin": 4811,
        "changed_lines": 372,
        "files_touched": 9,
    }
    assert list(strings_under(line["object"])) == []
    for value in line["object"].values():
        assert isinstance(value, int) and not isinstance(value, bool)


def test_an_unmeasured_scale_still_projects_as_three_nulls(
    rollup, make_round, tmp_path
):
    """The key crosses measured or not — and carries no string either way."""
    ledger = make_round(ROWS_8, records=full_round([span()]))
    rounds = tmp_path / "rounds.jsonl"
    assert rollup(ledger, "--rounds", rounds).returncode == 0
    line = json.loads(rounds.read_text(encoding="utf-8").strip())
    assert line["object"] == {
        "lines_at_pin": None,
        "changed_lines": None,
        "files_touched": None,
    }
    assert list(strings_under(line["object"])) == []
