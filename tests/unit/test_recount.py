"""Characterization tests for recount.py.

`tests/run-regression.sh` already pins 28 end-to-end ledger fixtures (row
schemas, terminal literals, the readiness-criterion rules, the frozen
marker, one delta case). The tests here are deliberately COMPLEMENTARY:
argument handling, IO failure modes, the printed line formats, the curve,
the four delta buckets and a few literal-matching edges the shell suite
does not exercise.

Exit codes: 0 = closable (help is 0 too), 1 = open rows remain,
2 = structural/usage error, 3 = the ledger is frozen.

"""

from __future__ import annotations

import pytest

from conftest import HEADER_7, HEADER_8

SCRIPT = "recount.py"

CLOSED = "| DA-1 | major | claim | verdict | crit | fix | LANDED | verified-landed |"
OPEN = "| DA-2 | major | claim | verdict |  | fix | x | open |"


# --- usage and IO ----------------------------------------------------------

@pytest.mark.parametrize("argv", [(), ("a.md", "b.md")])
def test_wrong_argument_count_prints_usage(run, argv):
    res = run(SCRIPT, *argv)
    assert res.returncode == 2, res.stdout
    assert "Usage:  recount.py <ledger.md> [--prev <old-ledger.md>]" in res.stdout


def test_missing_ledger_file_is_a_structural_error(run, tmp_path):
    """An unreadable ledger path is an unusable input: exit 2, no traceback.

    Exit 1 would be indistinguishable from "open rows remain", so the
    absence of a traceback on stderr is part of the assertion.
    """
    res = run(SCRIPT, tmp_path / "absent.md")
    assert res.returncode == 2, res.stdout
    assert "cannot read" in res.stdout
    assert res.stderr == ""


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_flags_print_usage_and_exit_zero(run, flag):
    res = run(SCRIPT, flag)
    assert res.returncode == 0, res.stdout
    assert "Usage:  recount.py <ledger.md> [--prev <old-ledger.md>]" in res.stdout


def test_help_wins_over_a_ledger_path(run, ledger):
    """`-h` after a real ledger prints usage instead of recounting it.

    Before the uniform-help change `-h` was consumed as a second path and
    tripped the arity check (exit 2); the ledger is closable, so a run that
    still counted would print "rows:" and exit 0 for the wrong reason.
    """
    res = run(SCRIPT, ledger(CLOSED), "-h")
    assert res.returncode == 0, res.stdout
    assert "Usage:  recount.py <ledger.md> [--prev <old-ledger.md>]" in res.stdout
    assert "rows:" not in res.stdout


def test_prev_without_a_value_is_a_usage_error(run, ledger):
    """`--prev` as the last token is a usage error: exit 2, no traceback."""
    res = run(SCRIPT, ledger(CLOSED), "--prev")
    assert res.returncode == 2, res.stdout
    assert "--prev needs a path" in res.stdout
    assert res.stderr == ""


def test_missing_prev_file_is_a_structural_error(run, ledger, tmp_path):
    absent = tmp_path / "absent.md"
    res = run(SCRIPT, ledger(CLOSED), "--prev", absent)
    assert res.returncode == 2, res.stdout
    assert f"cannot read {absent}" in res.stdout
    assert res.stderr == ""


def test_file_without_a_findings_table(run, tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("# Notes\n\nNo table here.\n", encoding="utf-8")
    res = run(SCRIPT, path)
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("no ledger rows found — wrong file or broken table?")


def test_empty_file(run, tmp_path):
    path = tmp_path / "empty.md"
    path.write_text("", encoding="utf-8")
    res = run(SCRIPT, path)
    assert res.returncode == 2, res.stdout
    assert "no ledger rows found" in res.stdout


# --- counting and printed shape --------------------------------------------

def test_closable_ledger_prints_counts_and_verdict(run, ledger):
    res = run(SCRIPT, ledger(CLOSED))
    assert res.returncode == 0, res.stdout
    assert res.stdout.splitlines()[0] == "rows: 1 | terminal: 1 | non-terminal: 0"
    assert res.stdout.rstrip().endswith("ROUND CLOSABLE: zero non-terminal rows.")


def test_open_row_is_listed_by_id(run, ledger):
    res = run(SCRIPT, ledger(CLOSED + "\n" + OPEN))
    assert res.returncode == 1, res.stdout
    assert "rows: 2 | terminal: 1 | non-terminal: 1" in res.stdout
    assert "non-terminal ids: DA-2" in res.stdout


def test_prose_and_blank_lines_inside_the_table_are_skipped(run, ledger):
    rows = CLOSED + "\n\nsome prose between rows\n\n" + OPEN
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 1, res.stdout
    assert "rows: 2 | terminal: 1 | non-terminal: 1" in res.stdout


def test_legacy_seven_cell_schema_still_counts(run, ledger):
    row = "| DA-1 | major | claim | verdict | fix | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row, header=HEADER_7))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout


def test_header_of_an_unsupported_width_is_structural(run, ledger):
    header = "| id | sev | claim | verdict | verified | terminal |\n|---|---|---|---|---|---|\n"
    row = "| DA-1 | major | claim | verdict | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row, header=header))
    assert res.returncode == 2, res.stdout
    assert ("line 1: findings header has 6 cells; the table must be 7-cell "
            "(legacy) or 8-cell (with criterion)" in res.stdout)


def test_degenerate_one_cell_header_is_structural(run, ledger):
    """A `| id |` header is named by width and exits 2, never a traceback.

    Such a header cannot address a row's severity/verified/terminal cells;
    reading its rows used to raise an uncaught IndexError, which the shell
    reports as exit 1 — indistinguishable from "open rows remain". The
    empty stderr is part of the assertion.
    """
    res = run(SCRIPT, ledger("| DA-1 |", header="| id |\n|---|\n"))
    assert res.returncode == 2, res.stdout
    assert ("line 1: findings header has 1 cells; the table must be 7-cell "
            "(legacy) or 8-cell (with criterion)" in res.stdout)
    assert res.stderr == ""
    assert "rows:" not in res.stdout


@pytest.mark.parametrize(
    ("header", "rows", "cells"),
    [
        ("| id | terminal |\n|---|---|\n", "| DA-1 | verified-landed |", 2),
        ("| id | sev | terminal |\n|---|---|---|\n",
         "| DA-1 | major | verified-landed |", 3),
    ],
)
def test_too_narrow_headers_are_structural_without_a_traceback(
    run, ledger, header, rows, cells,
):
    """Any header too narrow for id+sev+verified+terminal takes exit 2.

    Widths 2 and 3 do not raise today, but they alias two row cells onto
    one; they take the same named-width path as the degenerate `| id |`,
    and no count is printed from them.
    """
    res = run(SCRIPT, ledger(rows, header=header))
    assert res.returncode == 2, res.stdout
    assert f"line 1: findings header has {cells} cells" in res.stdout
    assert res.stderr == ""
    assert "rows:" not in res.stdout


def test_malformed_id_is_structural(run, ledger):
    res = run(SCRIPT, ledger("| 1A-3 | major | c | v | crit | f | LANDED | verified-landed |"))
    assert res.returncode == 2, res.stdout
    assert ("first cell is not a valid id (<Prefix>-<n>, letter-led): '1A-3'"
            in res.stdout)


# --- terminal literals -----------------------------------------------------

def test_terminal_literal_is_matched_case_insensitively(run, ledger):
    row = "| DA-1 | major | c | v | crit | f | landed | Verified-Landed |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout


def test_lowercase_not_landed_still_blocks_the_row(run, ledger):
    row = "| DA-1 | major | c | v | crit | f | not landed | verified-landed |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 1, res.stdout
    assert ("CONSISTENCY: DA-1: terminal says verified-landed but verified "
            "cell is 'not landed'" in res.stdout)


def test_verified_cell_without_a_landed_verdict(run, ledger):
    row = "| DA-1 | major | c | v | crit | f | checked twice | verified-landed |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 1, res.stdout
    assert ("CONSISTENCY: DA-1: terminal says verified-landed but verified "
            "cell carries no LANDED verdict" in res.stdout)


def test_landed_otherwise_with_a_whitespace_only_description(run, ledger):
    row = ("| DA-1 | major | c | v | crit | f | LANDED OTHERWISE (   ) | "
           "verified-landed |")
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 1, res.stdout
    assert ("'LANDED OTHERWISE' without a non-empty description in parentheses"
            in res.stdout)


def test_refuted_with_reason_needs_the_em_dash_criterion(run, ledger):
    row = "| DA-1 | major | c | v | — | f | x | refuted-with-reason |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout


def test_empty_terminal_cell_is_open_without_a_diagnostic(run, ledger):
    row = "| DA-1 | major | c | v |  | f | x |  |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 1, res.stdout
    assert "CONSISTENCY" not in res.stdout
    assert "non-terminal ids: DA-1" in res.stdout


@pytest.mark.parametrize("bad", ["9999-99-99", "2026-02-30"])
def test_signature_date_must_be_a_calendar_date(run, ledger, bad):
    """The signature date is checked for CALENDAR validity, not just shape."""
    row = ("| DA-1 | minor | c | v | keep as is | f | x | accepted-residue "
           f"user-signed {bad} |")
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 1, res.stdout
    assert "rows: 1 | terminal: 0 | non-terminal: 1" in res.stdout
    assert (f"CONSISTENCY: DA-1: signature date '{bad}' is not a calendar "
            f"date (YYYY-MM-DD)" in res.stdout)


def test_calendar_valid_signature_date_still_closes(run, ledger):
    """The positive case: a real date stays terminal (calendar check only)."""
    row = ("| DA-1 | minor | c | v | keep as is | f | x | accepted-residue "
           "user-signed 2026-08-09 |")
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout


# --- frozen ledgers --------------------------------------------------------

@pytest.mark.parametrize("marker", [
    "Ledger state: FROZEN (superseded by a rewrite)\n",
    "- ledger state: frozen\n",
    "   - Ledger State: Frozen — superseded\n",
])
def test_frozen_marker_variants(run, ledger, marker):
    res = run(SCRIPT, ledger(CLOSED, preamble=marker))
    assert res.returncode == 3, res.stdout
    assert res.stdout.startswith(
        "LEDGER IS FROZEN (superseded by a rewrite) — not closable:")
    assert marker.strip() in res.stdout


def test_frozen_wins_over_structural_errors(run, ledger):
    broken = "| DA-1 | major | too | few | cells |"
    res = run(SCRIPT, ledger(broken, preamble="Ledger state: FROZEN\n"))
    assert res.returncode == 3, res.stdout


# --- the new-findings curve ------------------------------------------------

PASSES_HEADER = ("\n## Verification passes\n\n"
                 "| # | pass | verdicts | new findings | notes |\n"
                 "|---|---|---|---|---|\n")


def passes(values):
    rows = "".join(f"| {i} | p{i} | L | {v} | - |\n"
                   for i, v in enumerate(values, 1))
    return PASSES_HEADER + rows


def test_curve_is_printed_in_order(run, ledger):
    res = run(SCRIPT, ledger(CLOSED, suffix=passes([5, 3, 1])))
    assert res.returncode == 0, res.stdout
    assert "new-findings curve: 5 -> 3 -> 1" in res.stdout
    assert "KILL-CRITERION" not in res.stdout


def test_flat_non_zero_curve_triggers_the_kill_criterion(run, ledger):
    res = run(SCRIPT, ledger(CLOSED, suffix=passes([3, 3, 3])))
    assert res.returncode == 0, res.stdout
    assert ("KILL-CRITERION WARNING: curve has not decayed for three "
            "consecutive passes — stop and fork to the user." in res.stdout)


def test_flat_zero_curve_does_not_trigger_the_kill_criterion(run, ledger):
    res = run(SCRIPT, ledger(CLOSED, suffix=passes([0, 0, 0])))
    assert res.returncode == 0, res.stdout
    assert "new-findings curve: 0 -> 0 -> 0" in res.stdout
    assert "KILL-CRITERION" not in res.stdout


def test_two_passes_never_trigger_the_kill_criterion(run, ledger):
    res = run(SCRIPT, ledger(CLOSED, suffix=passes([7, 9])))
    assert res.returncode == 0, res.stdout
    assert "KILL-CRITERION" not in res.stdout


def test_no_passes_table_prints_no_curve(run, ledger):
    res = run(SCRIPT, ledger(CLOSED))
    assert "new-findings curve" not in res.stdout


# --- severity distribution and the upheld/refuted split --------------------
#
# Severity is cell index 1 in BOTH schemas, so the distribution is printed
# for 7-cell and 8-cell ledgers alike. The upheld/refuted
# split needs the criterion cell and is 8-cell only.

def test_severity_distribution_names_the_three_canonical_classes(run, ledger):
    """A class with no rows is printed as 0/0 — an absence is a fact too."""
    res = run(SCRIPT, ledger(CLOSED))
    assert res.returncode == 0, res.stdout
    assert ("severity distribution (terminal/rows): blocker 0/0 | major 1/1 | "
            "minor 0/0" in res.stdout)


def test_severity_distribution_separates_terminal_from_open_rows(run, ledger):
    res = run(SCRIPT, ledger(CLOSED + "\n" + OPEN))
    assert res.returncode == 1, res.stdout
    assert "major 1/2" in res.stdout


def test_severity_distribution_is_printed_for_a_seven_cell_ledger(run, ledger):
    row = "| DA-1 | minor | claim | verdict | fix | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row, header=HEADER_7))
    assert res.returncode == 0, res.stdout
    assert ("severity distribution (terminal/rows): blocker 0/0 | major 0/0 | "
            "minor 1/1" in res.stdout)


def test_severity_value_is_matched_case_insensitively(run, ledger):
    row = "| DA-1 | BLOCKER | c | v | crit | f | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row))
    assert "blocker 1/1" in res.stdout


def test_unknown_severity_is_reported_under_its_own_name(run, ledger):
    """An unexpected class is named, never folded into a known one."""
    row = "| DA-1 | cosmetic | c | v | crit | f | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 0, res.stdout
    assert ("severity distribution (terminal/rows): blocker 0/0 | major 0/0 | "
            "minor 0/0 | cosmetic 1/1" in res.stdout)


def test_blank_severity_cell_is_reported_as_blank(run, ledger):
    row = "| DA-1 |  | c | v | crit | f | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row))
    assert "(blank) 1/1" in res.stdout


def test_upheld_split_is_na_on_a_seven_cell_ledger(run, ledger):
    row = "| DA-1 | major | claim | verdict | fix | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row, header=HEADER_7))
    assert "upheld/refuted: n/a (v1 ledger — no criterion column)" in res.stdout


def test_upheld_split_counts_a_criterion_bearing_row_as_upheld(run, ledger):
    res = run(SCRIPT, ledger(CLOSED))
    assert "upheld/refuted: 1 upheld, 0 refuted" in res.stdout


def test_refuted_row_carrying_the_em_dash_is_counted_as_refuted(run, ledger):
    row = "| DA-1 | major | c | v | — | f | x | refuted-with-reason |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 0, res.stdout
    assert "upheld/refuted: 0 upheld, 1 refuted" in res.stdout


def test_refused_row_is_upheld_despite_the_em_dash(run, ledger):
    """A signed refusal means the claim STOOD and the owner declined to act."""
    row = ("| SE-1 | major | pii | refused | — | f | x | refused-user-signed "
           "2026-08-09 |")
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 0, res.stdout
    assert "upheld/refuted: 1 upheld, 0 refuted" in res.stdout


# --- the passes table: column lookup and the time axis ---------------------

V2_HEADER = ("\n## Verification passes\n\n"
             "| # | pass | verdicts | new findings | notes | started | ended |\n"
             "|---|---|---|---|---|---|---|\n")


def v2_passes(rows):
    """`rows` are (new-findings, started, ended) triples, in pass order."""
    body = "".join(f"| {i} | p{i} | L | {n} | - | {s} | {e} |\n"
                   for i, (n, s, e) in enumerate(rows, 1))
    return V2_HEADER + body


CLEAN_V2 = [
    (5, "2026-08-10T10:00:00Z", "2026-08-10T10:30:00Z"),
    (3, "2026-08-10T11:00:00Z", "2026-08-10T11:15:00Z"),
    (1, "2026-08-10T12:00:00Z", "2026-08-10T12:10:00Z"),
]


def test_new_findings_column_is_found_by_name_off_index_three(run, ledger):
    """Named lookup adds tolerance the positional reader never had."""
    table = ("\n## Verification passes\n\n"
             "| # | pass | verdicts | notes | new findings |\n"
             "|---|---|---|---|---|\n"
             "| 1 | p1 | L | 99 | 5 |\n"
             "| 2 | p2 | L | 98 | 2 |\n")
    res = run(SCRIPT, ledger(CLOSED, suffix=table))
    assert res.returncode == 0, res.stdout
    assert "new-findings curve: 5 -> 2" in res.stdout


def test_unnamed_passes_header_still_reads_index_three(run, ledger):
    """The positional fallback is the pre-0.2.0 behaviour, unchanged."""
    table = ("\n## Verification passes\n\n"
             "| # | a | b | c | d |\n|---|---|---|---|---|\n"
             "| 1 | x | y | 7 | 99 |\n| 2 | x | y | 4 | 98 |\n")
    res = run(SCRIPT, ledger(CLOSED, suffix=table))
    assert res.returncode == 0, res.stdout
    assert "new-findings curve: 7 -> 4" in res.stdout


def test_v1_passes_table_says_why_there_is_no_time_axis(run, ledger):
    res = run(SCRIPT, ledger(CLOSED, suffix=passes([5, 3, 1])))
    assert res.returncode == 0, res.stdout
    assert ("time axis: n/a (no started/ended columns — v1 passes table)"
            in res.stdout)
    assert "time-indexed curve" not in res.stdout


def test_v2_passes_table_prints_the_time_indexed_curve(run, ledger):
    res = run(SCRIPT, ledger(CLOSED, suffix=v2_passes(CLEAN_V2)))
    assert res.returncode == 0, res.stdout
    assert "new-findings curve: 5 -> 3 -> 1" in res.stdout
    assert ("time-indexed curve (from 2026-08-10T10:00:00Z): +0s -> 5 | "
            "+3600s -> 3 | +7200s -> 1" in res.stdout)
    assert "pass wall-clock: 1: 1800s | 2: 900s | 3: 600s" in res.stdout
    assert "time axis: n/a" not in res.stdout


def test_malformed_ended_is_named_and_the_axis_suppressed(run, ledger):
    """Amendment 13 (user-signed 2026-08-10): named, suppressed, exit AS-IS.

    The two columns exist only because observability is on, so a defect in
    them may not create a failure path the flag alone would introduce.
    """
    rows = list(CLEAN_V2)
    rows[1] = (3, "2026-08-10T11:00:00Z", "yesterday")
    res = run(SCRIPT, ledger(CLOSED, suffix=v2_passes(rows)))
    assert res.returncode == 0, res.stdout
    assert ("passes: row 2 'ended' unparseable — time axis suppressed"
            in res.stdout)
    assert "new-findings curve: 5 -> 3 -> 1" in res.stdout
    assert "time-indexed curve" not in res.stdout
    assert "pass wall-clock" not in res.stdout


def test_malformed_timestamp_does_not_promote_an_open_ledger(run, ledger):
    """The other half of "exit code unchanged": 1 stays 1, not 2."""
    rows = list(CLEAN_V2)
    rows[0] = (5, "not-a-time", "2026-08-10T10:30:00Z")
    res = run(SCRIPT, ledger(CLOSED + "\n" + OPEN, suffix=v2_passes(rows)))
    assert res.returncode == 1, res.stdout
    assert ("passes: row 1 'started' unparseable — time axis suppressed"
            in res.stdout)
    assert "non-terminal ids: DA-2" in res.stdout


def test_empty_timestamp_cell_is_reported_rather_than_skipped(run, ledger):
    rows = list(CLEAN_V2)
    rows[2] = (1, "2026-08-10T12:00:00Z", "")
    res = run(SCRIPT, ledger(CLOSED, suffix=v2_passes(rows)))
    assert res.returncode == 0, res.stdout
    assert "passes: row 3 'ended' unparseable" in res.stdout


def test_a_row_too_short_for_the_time_columns_is_reported(run, ledger):
    table = (V2_HEADER
             + "| 1 | p1 | L | 5 | - | 2026-08-10T10:00:00Z | "
               "2026-08-10T10:30:00Z |\n"
             + "| 2 | p2 | L | 3 | - |\n")
    res = run(SCRIPT, ledger(CLOSED, suffix=table))
    assert res.returncode == 0, res.stdout
    assert "passes: row 2 'started' unparseable" in res.stdout
    assert "passes: row 2 'ended' unparseable" in res.stdout


def test_only_one_time_column_is_treated_as_a_v1_table(run, ledger):
    """Half a v2 table is not a v2 table: no axis, no error, one line why."""
    table = ("\n## Verification passes\n\n"
             "| # | pass | verdicts | new findings | notes | started |\n"
             "|---|---|---|---|---|---|\n"
             "| 1 | p1 | L | 5 | - | 2026-08-10T10:00:00Z |\n")
    res = run(SCRIPT, ledger(CLOSED, suffix=table))
    assert res.returncode == 0, res.stdout
    assert "time axis: n/a (no started/ended columns" in res.stdout


def test_a_passes_table_without_numbers_prints_no_curve_and_no_axis(run, ledger):
    table = (V2_HEADER + "| a | p1 | L | none | - | bad | bad |\n")
    res = run(SCRIPT, ledger(CLOSED, suffix=table))
    assert res.returncode == 0, res.stdout
    assert "new-findings curve" not in res.stdout
    assert "time axis" not in res.stdout
    assert "unparseable" not in res.stdout


def test_a_calendar_impossible_timestamp_is_unparseable(run, ledger):
    """Right shape, no such day: `2026-02-30T10:00:00Z` names no instant."""
    rows = list(CLEAN_V2)
    rows[0] = (5, "2026-02-30T10:00:00Z", "2026-08-10T10:30:00Z")
    res = run(SCRIPT, ledger(CLOSED, suffix=v2_passes(rows)))
    assert res.returncode == 0, res.stdout
    assert "passes: row 1 'started' unparseable" in res.stdout
    assert "time-indexed curve" not in res.stdout


def test_non_integer_pass_ordinal_falls_back_to_the_row_position(run, ledger):
    table = (V2_HEADER
             + "| one | p1 | L | 5 | - | 2026-08-10T10:00:00Z | broken |\n")
    res = run(SCRIPT, ledger(CLOSED, suffix=table))
    assert res.returncode == 0, res.stdout
    assert "passes: row 1 'ended' unparseable" in res.stdout


# --- the optional --trace line ---------------------------------------------
#
# The trace is not the ledger: nothing about it may reach an exit code.

SPAN = '{"v": 1, "kind": "span", "round": "r", "span": "s1.00"}'


def test_trace_without_a_value_is_a_usage_error(run, ledger):
    res = run(SCRIPT, ledger(CLOSED), "--trace")
    assert res.returncode == 2, res.stdout
    assert "--trace needs a path" in res.stdout
    assert res.stderr == ""


def test_absent_trace_is_reported_as_none(run, ledger, tmp_path):
    res = run(SCRIPT, ledger(CLOSED), "--trace", tmp_path / "absent.jsonl")
    assert res.returncode == 0, res.stdout
    assert "trace: none" in res.stdout


def test_trace_records_are_counted(run, ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(SPAN + "\n" + SPAN + "\n\n", encoding="utf-8")
    res = run(SCRIPT, ledger(CLOSED), "--trace", trace)
    assert res.returncode == 0, res.stdout
    assert "trace: 2 records" in res.stdout
    assert "unreadable" not in res.stdout


def test_corrupt_trace_lines_are_counted_and_never_fatal(run, ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(SPAN + "\nnot json\n{\"v\": 1,\n[]\n", encoding="utf-8")
    res = run(SCRIPT, ledger(CLOSED), "--trace", trace)
    assert res.returncode == 0, res.stdout
    assert "trace: 1 records, 3 unreadable lines skipped" in res.stdout


def test_a_corrupt_trace_does_not_change_an_open_ledgers_exit_code(
        run, ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text("not json\n", encoding="utf-8")
    res = run(SCRIPT, ledger(CLOSED + "\n" + OPEN), "--trace", trace)
    assert res.returncode == 1, res.stdout
    assert "trace: 0 records, 1 unreadable lines skipped" in res.stdout


def test_trace_pointed_at_a_directory_is_handled(run, ledger, tmp_path):
    """No traceback, no exit-code change — only the file NAME is echoed."""
    directory = tmp_path / "trace.jsonl"
    directory.mkdir()
    res = run(SCRIPT, ledger(CLOSED), "--trace", directory)
    assert res.returncode == 0, res.stdout
    assert "trace: unreadable (trace.jsonl)" in res.stdout
    assert res.stderr == ""


def test_undecodable_trace_is_reported_without_a_traceback(
        run, ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_bytes(b'{"v": 1}\n\xff\xfe\n')
    res = run(SCRIPT, ledger(CLOSED), "--trace", trace)
    assert res.returncode == 0, res.stdout
    assert "trace: unreadable (trace.jsonl)" in res.stdout
    assert res.stderr == ""


def test_empty_trace_file_is_zero_records(run, ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text("", encoding="utf-8")
    res = run(SCRIPT, ledger(CLOSED), "--trace", trace)
    assert res.returncode == 0, res.stdout
    assert "trace: 0 records" in res.stdout


def test_trace_flag_may_precede_the_ledger_argument(run, ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(SPAN + "\n", encoding="utf-8")
    res = run(SCRIPT, "--trace", trace, ledger(CLOSED))
    assert res.returncode == 0, res.stdout
    assert "trace: 1 records" in res.stdout


def test_trace_and_prev_combine(run, ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(SPAN + "\n", encoding="utf-8")
    prev = ledger(CLOSED, name="prev.md")
    res = run(SCRIPT, ledger(CLOSED, name="cur.md"), "--prev", prev,
              "--trace", trace)
    assert res.returncode == 0, res.stdout
    assert "trace: 1 records" in res.stdout
    assert f"DELTA vs {prev}:" in res.stdout


# --- inter-round delta -----------------------------------------------------

def test_delta_fills_all_four_buckets(run, ledger):
    prev = ledger(
        "| DA-1 | major | c | v |  | f | x | open |\n"
        "| DA-2 | major | c | v | crit | f | LANDED | verified-landed |\n"
        "| DA-3 | major | c | v |  | f | x | open |",
        name="prev.md")
    cur = ledger(
        "| DA-1 | major | c | v | crit | f | LANDED | verified-landed |\n"
        "| DA-2 | major | c | v |  | f | x | open |\n"
        "| DA-3 | major | c | v |  | f | x | open |\n"
        "| DA-4 | major | c | v |  | f | x | open |",
        name="cur.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 1, res.stdout
    assert (f"DELTA vs {prev}: newly-terminal ['DA-1'] | regressed ['DA-2'] | "
            f"still-open ['DA-3'] | new-open ['DA-4']" in res.stdout)


def test_delta_prints_empty_buckets_as_brackets(run, ledger):
    prev = ledger(CLOSED, name="prev.md")
    cur = ledger(CLOSED, name="cur.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert ("newly-terminal [] | regressed [] | still-open [] | new-open []"
            in res.stdout)


def test_delta_is_skipped_when_the_previous_ledger_is_broken(run, ledger):
    prev = ledger("| DA-1 | major | too | few |", name="prev.md")
    cur = ledger(CLOSED, name="cur.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert "--prev ledger has structural errors; delta skipped." in res.stdout
    assert "DELTA vs" not in res.stdout


def test_prev_flag_may_precede_the_ledger_argument(run, ledger):
    prev = ledger(CLOSED, name="prev.md")
    cur = ledger(CLOSED, name="cur.md")
    res = run(SCRIPT, "--prev", prev, cur)
    assert res.returncode == 0, res.stdout
    assert f"DELTA vs {prev}:" in res.stdout


def test_eight_cell_current_against_seven_cell_previous(run, ledger):
    prev = ledger("| DA-1 | major | c | v | f | x | open |", header=HEADER_7,
                  name="prev.md")
    cur = ledger(CLOSED, name="cur.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert "newly-terminal ['DA-1']" in res.stdout
