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

import importlib.util
import re
import sys

import pytest

from conftest import HEADER_7, HEADER_8, HEADER_9, write_ledger

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


def test_the_empty_table_message_carries_its_remedy(run, tmp_path):
    """The commonest cause of this exit is a stage, not a broken file.

    A ledger whose critics are salvaged but not yet transcribed has zero
    rows, so the exit is EXPECTED there; the message says what to run.
    """
    path = tmp_path / "fresh.md"
    path.write_text("# Fix ledger\n", encoding="utf-8")
    res = run(SCRIPT, path)
    assert res.returncode == 2, res.stdout
    assert "run transcribe.py first)" in res.stdout


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
            "(v1, legacy), 8-cell (v2, with criterion) or 9-cell (v3, with "
            "zone)" in res.stdout)


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
            "(v1, legacy), 8-cell (v2, with criterion) or 9-cell (v3, with "
            "zone)" in res.stdout)
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
    assert ("first cell is not a valid id (<Prefix>-<n>, every prefix segment "
            "letter-led, dash-joined segments allowed as in `V-CIT-1`): '1A-3'"
            in res.stdout)


# --- the id contract: composite prefixes ------------------------------------
#
# A verifier that carries the lens it re-checked inside its own ids
# (`V-CIT-1`) used to fail the recount on the second dash and cost the round
# a run plus a rename. The prefix is one or more dash-joined letter-led
# segments; the number is still the tail, and an empty segment is still an
# error.


@pytest.mark.parametrize("row_id", ["V-CIT-1", "DA-1", "L1-12", "V-CIT-DUP-3"])
def test_a_composite_prefix_is_a_valid_id(run, ledger, row_id):
    row = f"| {row_id} | major | c | v | crit | f | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout


@pytest.mark.parametrize("row_id", ["-1", "V--1", "1-V", "V-CIT-", "V-CIT",
                                    "V-1-2", "V-", "-V-1"])
def test_a_broken_composite_id_is_still_structural(run, ledger, row_id):
    row = f"| {row_id} | major | c | v | crit | f | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 2, res.stdout
    assert "first cell is not a valid id" in res.stdout
    assert repr(row_id) in res.stdout


def test_a_composite_id_belongs_to_its_whole_prefix(run, ledger):
    """`V-CIT-1`'s prefix is `V-CIT`, never the leading `V`.

    The security-lens backstop matches a row to a lens by everything before
    the final `-<n>`, so a composite verifier id is NOT charged to a lens
    that happens to share its first segment.
    """
    rows = ("| V-CIT-1 | major | c | v | crit | f | LANDED | verified-landed |\n"
            "| V-2 | major | c | class:security-pii | crit | f | LANDED |"
            " verified-landed |")
    res = run(SCRIPT, ledger(rows, preamble="- Security lens: V\n\n"))
    assert res.returncode == 0, res.stdout
    assert "rows: 2 | terminal: 2 | non-terminal: 0" in res.stdout


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


@pytest.mark.parametrize("marker", [
    "- Ledger state: closed 2026-01-15\n",
    "Ledger state: CLOSED 2026-01-15\n",
])
def test_a_closed_header_is_not_a_frozen_one(run, ledger, marker):
    """Stage 9's third header value passes the frozen branch untouched.

    The branch matches the substring `frozen`; `closed` does not contain
    it, which is why stage 9 can write `Ledger state: closed <ISO-date>`
    with no change to this script. A closed ledger must therefore recount
    exactly as an open one does — the shell suite's c73 pins the same fact
    end to end.
    """
    res = run(SCRIPT, ledger(CLOSED, preamble=marker))
    assert res.returncode == 0, res.stdout
    assert "ROUND CLOSABLE: zero non-terminal rows." in res.stdout
    assert "FROZEN" not in res.stdout


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


# --- the stop criterion, on its own line ------------------------------------
#
# The curve and the binary signal were ONE line, and a first-time reader took
# "the curve is falling" for "the criterion is met". They are different
# claims, so these tests hold them to being different lines — and hold the
# criterion to never claiming `met` off a cell it could not read.

VERDICTS_HEADER = ("\n## Verification passes\n\n"
                   "| # | pass | verdicts (L/P/NOT) | new findings | notes |\n"
                   "|---|---|---|---|---|\n")


def passes_v(pairs):
    """A passes table whose verdicts cells are machine-readable."""
    rows = "".join(f"| {i} | p{i} | {v} | {n} | - |\n"
                   for i, (v, n) in enumerate(pairs, 1))
    return VERDICTS_HEADER + rows


def test_the_curve_and_the_stop_criterion_are_two_lines(run, ledger):
    """The DoD case: both lines print, and the criterion prints once."""
    res = run(SCRIPT, ledger(CLOSED, suffix=passes([5, 3, 1])))
    assert res.returncode == 0, res.stdout
    assert "new-findings curve: 5 -> 3 -> 1" in res.stdout
    assert res.stdout.count("stop criterion (verdict streak): ") == 1


def test_two_clean_passes_meet_the_stop_criterion(run, ledger):
    res = run(SCRIPT, ledger(CLOSED,
                             suffix=passes_v([("9/0/2", 4), ("4/0/0", 0),
                                              ("3/0/0", 0)])))
    assert res.returncode == 0, res.stdout
    assert ("stop criterion (verdict streak): met — passes 2, 3 both clean "
            "(0 NOT LANDED, 0 new major/blocker findings)" in res.stdout)


def test_a_not_landed_verdict_breaks_the_streak(run, ledger):
    res = run(SCRIPT, ledger(CLOSED,
                             suffix=passes_v([("4/0/0", 0), ("3/0/1", 0)])))
    assert res.returncode == 0, res.stdout
    assert ("stop criterion (verdict streak): not met — pass 2: 1 NOT LANDED"
            in res.stdout)


def test_new_findings_of_unnamed_severity_break_the_streak(run, ledger):
    """A count whose severity nothing names is never read as minor."""
    res = run(SCRIPT, ledger(CLOSED,
                             suffix=passes_v([("4/0/0", 0), ("3/0/0", 2)])))
    assert res.returncode == 0, res.stdout
    assert ("stop criterion (verdict streak): not met — pass 2: 2 new findings "
            "of unnamed severity" in res.stdout)


def test_streak_ignores_new_minor_findings(run, ledger):
    """The signal is "zero major/blocker", and a minor is neither.

    The round of record printed `not met — pass 1: 1 new findings` beside
    its own `ROUND CLOSABLE`, off a cell reading `1 (V1-1, minor)`.
    """
    minor = run(SCRIPT, ledger(CLOSED, suffix=passes_v([
        ("17/0/0", "1 (V1-1, minor)"),
        ("1/0/0", 0),
    ])))
    assert minor.returncode == 0, minor.stdout
    assert "stop criterion (verdict streak): met — passes 1, 2 both clean" \
        in minor.stdout

    major = run(SCRIPT, ledger(CLOSED, suffix=passes_v([
        ("17/0/0", "1 (V1-1, major)"),
        ("1/0/0", 0),
    ])))
    assert major.returncode == 0, major.stdout
    assert ("stop criterion (verdict streak): not met — pass 1: 1 new major "
            "findings" in major.stdout)


def test_a_spelled_out_verdicts_cell_is_read(run, ledger):
    """`23 L (+1 LANDED OTHERWISE) / 0 P / 0 NOT` is the corpus's other
    shape, and it is read rather than reported unreadable."""
    res = run(SCRIPT, ledger(CLOSED, suffix=passes_v([
        ("5 L / 0 P / 0 NOT", 0),
        ("23 L (+1 LANDED OTHERWISE) / 0 P / 0 NOT", 0),
    ])))
    assert res.returncode == 0, res.stdout
    assert "stop criterion (verdict streak): met" in res.stdout


def test_an_unreadable_verdicts_cell_never_reads_as_clean(run, ledger):
    """The one error that would announce a convergence nobody measured."""
    res = run(SCRIPT, ledger(CLOSED,
                             suffix=passes_v([("all LANDED", 0), ("3/0/0", 0)])))
    assert res.returncode == 0, res.stdout
    assert ("stop criterion (verdict streak): not met — pass 1: verdicts cell "
            "not machine-readable (all LANDED)" in res.stdout)


def test_a_single_pass_cannot_meet_the_stop_criterion(run, ledger):
    res = run(SCRIPT, ledger(CLOSED, suffix=passes_v([("3/0/0", 0)])))
    assert res.returncode == 0, res.stdout
    assert ("stop criterion (verdict streak): not met — 1 verification "
            "pass(es) recorded, the signal needs 2 consecutive clean ones"
            in res.stdout)


def test_a_single_pass_line_says_it_is_report_only(run, ledger):
    """The not-met form for too few passes carries the report-only tail."""
    res = run(SCRIPT, ledger(CLOSED, suffix=passes_v([("3/0/0", 0)])))
    assert ("stop criterion (verdict streak): not met — 1 verification "
            "pass(es) recorded, the signal needs 2 consecutive clean ones; "
            "report-only, no exit code" in res.stdout)


def test_a_dirty_pass_line_says_it_is_report_only(run, ledger):
    """The not-met form with reasons carries the report-only tail."""
    res = run(SCRIPT, ledger(CLOSED,
                             suffix=passes_v([("4/0/0", 0), ("3/0/1", 0)])))
    assert ("stop criterion (verdict streak): not met — pass 2: 1 NOT LANDED"
            "; report-only, no exit code" in res.stdout)


def test_no_passes_table_prints_no_stop_criterion(run, ledger):
    res = run(SCRIPT, ledger(CLOSED))
    assert "stop criterion" not in res.stdout


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
    """Malformed 'ended': named in output, time axis suppressed, exit AS-IS.

    The two columns are optional, so a defect in them may not create a
    failure path their mere presence would introduce.
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


# --- verdict-cell tags: class recurrences and the injection rate ------------
#
# Two optional tags live inside the free-prose `verdict` cell, each with a
# fixed boundary so it can be lifted back out: `class:<slug>` (the defect
# class) and `origin:fix-application from:<batch>` (a finding that is itself
# a defect in applying an earlier fix, plus the batch whose fix it was). The
# compatibility claim these tests protect is the first one below: a ledger
# that carries neither tag prints neither report.

def tagged(rid: str, verdict: str, *, fix: str = "aa11", sev: str = "major",
           criterion: str = "L2 crit", verified: str = "LANDED",
           terminal: str = "verified-landed") -> str:
    """One findings row, addressed by the cells these tests vary."""
    return (f"| {rid} | {sev} | claim | {verdict} | {criterion} | {fix} | "
            f"{verified} | {terminal} |")


def test_an_untagged_ledger_prints_neither_new_report(run, ledger):
    """The compatibility claim: no tag, no new line, exactly as before."""
    res = run(SCRIPT, ledger(CLOSED + "\n" + OPEN))
    assert res.returncode == 1, res.stdout
    assert "class recurrences" not in res.stdout
    assert "injection rate" not in res.stdout
    assert "CLASS-KILL DUE" not in res.stdout


def test_two_upheld_rows_of_one_class_print_class_kill_due(run, ledger):
    rows = "\n".join([tagged("DA-1", "upheld, class:line-rot"),
                      tagged("DA-2", "upheld, class:line-rot")])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert ("class recurrences (upheld rows per class tag): line-rot 2"
            in res.stdout)
    assert "CLASS-KILL DUE: line-rot (2 upheld: DA-1, DA-2)" in res.stdout


def test_the_class_kill_warning_names_the_trigger_as_ours(run, ledger):
    """The "second recurrence" number is ours, and the output says so."""
    rows = "\n".join([tagged("DA-1", "upheld, class:line-rot"),
                      tagged("DA-2", "upheld, class:line-rot")])
    res = run(SCRIPT, ledger(rows))
    assert "The 2nd-recurrence trigger is OURS" in res.stdout
    assert "no standard supplies it" in res.stdout


def test_one_row_of_a_class_is_counted_but_raises_no_warning(run, ledger):
    rows = "\n".join([tagged("DA-1", "upheld, class:line-rot"),
                      tagged("DA-2", "upheld, class:pipe-in-cell")])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert ("class recurrences (upheld rows per class tag): line-rot 1 | "
            "pipe-in-cell 1" in res.stdout)
    assert "CLASS-KILL DUE" not in res.stdout


def test_a_refuted_row_does_not_count_toward_its_class(run, ledger):
    """A refuted claim is not a recurrence of anything."""
    rows = "\n".join([
        tagged("DA-1", "upheld, class:line-rot"),
        tagged("DA-2", "refuted, class:line-rot", criterion="—",
               verified="n/a", terminal="refuted-with-reason"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert ("class recurrences (upheld rows per class tag): line-rot 1"
            in res.stdout)
    assert "CLASS-KILL DUE" not in res.stdout


def test_one_row_naming_the_same_class_twice_is_one_row(run, ledger):
    rows = tagged("DA-1", "upheld, class:line-rot (again class:line-rot)")
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert ("class recurrences (upheld rows per class tag): line-rot 1"
            in res.stdout)


def test_class_grouping_is_by_exact_slug(run, ledger):
    """Nothing is normalized: two literals are two classes."""
    rows = "\n".join([tagged("DA-1", "upheld, class:line-rot"),
                      tagged("DA-2", "upheld, class:linerot")])
    res = run(SCRIPT, ledger(rows))
    assert "line-rot 1 | linerot 1" in res.stdout
    assert "CLASS-KILL DUE" not in res.stdout


@pytest.mark.parametrize("slug", ["Foo", "Line-Rot", ".x", "/x", "a" * 33])
def test_a_class_tag_outside_the_alphabet_is_a_structural_error(
        run, ledger, slug):
    """Fail-closed: the boundary is never guessed, exit 2 names the row.

    These are the cases in which a slug is ATTEMPTED and none is readable
    — the first character after the literal is outside the alphabet
    (without being whitespace), or the run of alphabet characters never
    ends within 32.
    """
    res = run(SCRIPT, ledger(tagged("DA-1", f"upheld, class:{slug}")))
    assert res.returncode == 2, res.stdout
    assert "STRUCTURAL ERRORS" in res.stdout
    assert "DA-1 carries a `class:` tag" in res.stdout


@pytest.mark.parametrize("verdict", [
    "upheld [class: count-citation-off]",          # the pre-tag hand convention
    "refuted; it never belonged to the security class:",  # end of the cell
    "upheld, marked class: and left at that",
    r"upheld (class:\| pipe next)",
])
def test_a_class_colon_written_as_prose_is_not_a_tag(run, ledger, verdict):
    """`class:` followed by whitespace, a `|` or the end of the cell is
    English prose, not a botched tag: no error, no group, nothing printed.

    Compatibility outranks the widest reading of the fail-closed rule
    here. Ledgers closed before this tag existed carry exactly these two
    shapes in their verdict cells, and an old ledger must recount as it
    did in 0.2.0. Nothing readable is lost: a tag never attaches its slug
    across whitespace.
    """
    res = run(SCRIPT, ledger(tagged("DA-1", verdict)))
    assert res.returncode == 0, res.stdout
    assert "STRUCTURAL ERRORS" not in res.stdout
    assert "class recurrences" not in res.stdout
    assert "CLASS-KILL DUE" not in res.stdout


def test_a_prose_class_colon_leaves_the_output_byte_identical(run, ledger):
    """The compatibility claim in its strongest form: adding the pre-tag
    hand convention to a verdict cell changes nothing that is printed.
    """
    plain = run(SCRIPT, ledger(tagged("DA-1", "upheld"), name="plain.md"))
    prose = run(SCRIPT, ledger(tagged("DA-1", "upheld [class: count-citation-off]"),
                               name="prose.md"))
    assert plain.returncode == prose.returncode == 0, prose.stdout
    assert plain.stdout == prose.stdout


@pytest.mark.parametrize("written", ["line_rot", "line.rot", "line/rot",
                                     "line rot"])
def test_a_class_slug_ends_at_the_first_character_outside_the_alphabet(
        run, ledger, written):
    """`class:line_rot` is the slug `line`: `_`, `.`, `/` and a space are
    TERMINATORS, not slug characters, so what follows one is prose. Pinned
    because the trailing text is dropped silently — the tag is readable, so
    nothing here is a structural error.
    """
    res = run(SCRIPT, ledger(tagged("DA-1", f"upheld, class:{written}")))
    assert res.returncode == 0, res.stdout
    assert ("class recurrences (upheld rows per class tag): line 1"
            in res.stdout)


def test_class_tags_are_read_on_a_seven_cell_legacy_ledger(run, ledger):
    """The verdict cell is index 3 in both schemas — no branch is needed."""
    rows = "\n".join([
        "| DA-1 | major | c | upheld, class:line-rot | f | LANDED | "
        "verified-landed |",
        "| DA-2 | major | c | upheld, class:line-rot | f | LANDED | "
        "verified-landed |",
    ])
    res = run(SCRIPT, ledger(rows, header=HEADER_7))
    assert res.returncode == 0, res.stdout
    assert "CLASS-KILL DUE: line-rot (2 upheld: DA-1, DA-2)" in res.stdout


def test_the_class_kill_warning_does_not_change_the_exit_code(run, ledger):
    rows = "\n".join([
        tagged("DA-1", "upheld, class:line-rot"),
        tagged("DA-2", "upheld, class:line-rot"),
        tagged("DA-3", "upheld", criterion="", verified="x", terminal="open"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 1, res.stdout
    assert "CLASS-KILL DUE: line-rot" in res.stdout
    assert "non-terminal ids: DA-3" in res.stdout


# --- the defect class / signature mode split -------------------------------
# The security-lens backstop obliges EVERY row of the declared lens to carry
# `class:security-pii`, so the slug on such a row says which lens raised the
# finding — a signature mode — and not that a defect class recurred. Two of
# them used to produce `CLASS-KILL DUE: security-pii` with no recurring class
# anywhere. The default counts toward no kill; the adjudicator who means the
# class writes it, and then it counts exactly as any other class does.

SECURITY_HEADER = "- Security lens: SE\n"


def test_the_lens_default_security_class_raises_no_class_kill(run, ledger):
    """Two rows carrying only the BACKSTOP's default: census, no kill.

    The census line still counts both tags — it is a tag census and says so
    — while the kill count is zero, and the gap is named on its own line
    rather than left for a reader to derive.
    """
    rows = "\n".join([tagged("SE-1", "upheld class:security-pii"),
                      tagged("SE-2", "upheld class:security-pii")])
    res = run(SCRIPT, ledger(rows, preamble=SECURITY_HEADER))
    assert res.returncode == 0, res.stdout
    assert ("class recurrences (upheld rows per class tag): security-pii 2"
            in res.stdout)
    assert "CLASS-KILL DUE" not in res.stdout
    assert "class-kill count for security-pii: 0 of 2 upheld rows" in res.stdout
    assert "signature mode and not a defect class" in res.stdout


def test_an_explicitly_adjudicated_security_class_still_kills(run, ledger):
    """The written origin restores the count, and nothing else does.

    `class-origin:adjudicator` in the same cell is the adjudicator saying
    the class is their own call rather than the lens's default, so the two
    rows are a recurrence and `CLASS-KILL DUE` prints exactly as it does
    for any other slug.
    """
    verdict = "upheld class:security-pii class-origin:adjudicator"
    rows = "\n".join([tagged("SE-1", verdict), tagged("SE-2", verdict)])
    res = run(SCRIPT, ledger(rows, preamble=SECURITY_HEADER))
    assert res.returncode == 0, res.stdout
    assert "CLASS-KILL DUE: security-pii (2 upheld: SE-1, SE-2)" in res.stdout
    assert "class-kill count for security-pii" not in res.stdout


def test_a_marked_defect_class_beside_the_default_leaves_it_a_default(
        run, ledger):
    """The marker qualifies the tag it stands BESIDE, not the whole cell.

    A security row carrying the backstop's default AND a coined class the
    adjudicator marked is the ordinary shape of such a row. Read over the
    whole cell, the marker made `security-pii` adjudicator-chosen too and
    fired the kill on the lens's own backstop.
    """
    verdict = ("upheld class:security-pii class:citation-drift "
               "class-origin:adjudicator")
    rows = "\n".join([tagged("SE-1", verdict), tagged("SE-2", verdict)])
    res = run(SCRIPT, ledger(rows, preamble=SECURITY_HEADER))
    assert res.returncode == 0, res.stdout
    assert ("CLASS-KILL DUE: citation-drift (2 upheld: SE-1, SE-2)"
            in res.stdout)
    assert "CLASS-KILL DUE: security-pii" not in res.stdout
    assert "class-kill count for security-pii: 0 of 2 upheld rows" in res.stdout


def test_the_marker_binds_to_its_neighbour_whichever_side_it_is_written(
        run, ledger):
    """Nearest tag wins, so either order of writing the pair reads alike."""
    verdict = ("upheld class-origin:adjudicator class:security-pii "
               "class:citation-drift")
    rows = "\n".join([tagged("SE-1", verdict), tagged("SE-2", verdict)])
    res = run(SCRIPT, ledger(rows, preamble=SECURITY_HEADER))
    assert res.returncode == 0, res.stdout
    assert ("CLASS-KILL DUE: security-pii (2 upheld: SE-1, SE-2)"
            in res.stdout)


def test_the_security_class_counts_where_no_lens_default_could_set_it(
        run, ledger):
    """No declared security lens, no backstop, so nothing set the class but
    the adjudicator: the slug counts as it always did.
    """
    rows = "\n".join([tagged("DA-1", "upheld class:security-pii"),
                      tagged("DA-2", "upheld class:security-pii")])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "CLASS-KILL DUE: security-pii (2 upheld: DA-1, DA-2)" in res.stdout


def test_another_lens_row_carrying_the_security_class_counts(run, ledger):
    """The exemption is the DECLARED lens's own rows and nothing wider.

    A row of another prefix was never obliged to carry the class, so its
    tag is a judgment and enters the kill count — one of the two rows here
    is the lens's default and the other is not, which leaves the count at
    one and the warning unprinted.
    """
    rows = "\n".join([tagged("SE-1", "upheld class:security-pii"),
                      tagged("DA-1", "upheld class:security-pii")])
    res = run(SCRIPT, ledger(rows, preamble=SECURITY_HEADER))
    assert res.returncode == 0, res.stdout
    assert "class-kill count for security-pii: 1 of 2 upheld rows" in res.stdout
    assert "CLASS-KILL DUE" not in res.stdout


# --- the open class-kill row -----------------------------------------------

def test_an_open_class_kill_row_prints_kill_in_flight(run, ledger):
    """The warning speaks of "no kill in flight"; the kill that IS in flight
    is now printed with its slug and its id, and the exit code is untouched.

    The comparison fixture is the same ledger with the tag removed: the
    literal appears in one and not the other, and both exit the same way.
    """
    base = [tagged("DA-1", "upheld, class:line-rot"),
            tagged("DA-2", "upheld, class:line-rot")]
    gate = tagged("K-1", "the gate for class-kill:line-rot",
                  criterion="grep -c raw-date = 0", verified="x",
                  terminal="open")
    plain = tagged("K-1", "the gate for this class",
                   criterion="grep -c raw-date = 0", verified="x",
                   terminal="open")
    res = run(SCRIPT, ledger("\n".join([*base, gate]), name="in-flight.md"))
    assert res.returncode == 1, res.stdout
    assert "kill in flight: line-rot (K-1)" in res.stdout
    assert re.search(r"kill in flight: [a-z0-9-]+ \(", res.stdout), res.stdout
    # The threshold line reads the SAME row: with a kill open, the kill is
    # in flight, not due. The comparison fixture — identical but for the
    # tag — is what carries `DUE`, and both exit the same way.
    assert "CLASS-KILL IN FLIGHT: line-rot (2 upheld: DA-1, DA-2)" in res.stdout
    assert "CLASS-KILL DUE" not in res.stdout
    before = run(SCRIPT, ledger("\n".join([*base, plain]), name="no-tag.md"))
    assert before.returncode == res.returncode, before.stdout
    assert "kill in flight:" not in before.stdout
    assert "CLASS-KILL DUE: line-rot" in before.stdout


def test_a_terminal_class_kill_row_is_not_in_flight(run, ledger):
    """The gate landed: the row is terminal and nothing is in flight."""
    rows = "\n".join([
        tagged("DA-1", "upheld, class:line-rot"),
        tagged("DA-2", "upheld, class:line-rot"),
        tagged("K-1", "the gate for class-kill:line-rot"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "kill in flight:" not in res.stdout


def test_a_terminal_class_kill_row_prints_done_not_due(run, ledger):
    """The third state: the kill LANDED, so nothing is due and nothing is
    in flight. The comparison fixture is the same ledger with the tag
    removed — it prints `DUE`, and both exit the same way.
    """
    base = [tagged("DA-1", "upheld, class:line-rot"),
            tagged("DA-2", "upheld, class:line-rot")]
    gate = tagged("K-1", "the gate for class-kill:line-rot")
    plain = tagged("K-1", "the gate for this class")
    res = run(SCRIPT, ledger("\n".join([*base, gate]), name="done.md"))
    assert res.returncode == 0, res.stdout
    assert "CLASS-KILL DONE: line-rot (2 upheld: DA-1, DA-2)" in res.stdout
    assert "CLASS-KILL DUE" not in res.stdout
    before = run(SCRIPT, ledger("\n".join([*base, plain]), name="no-tag2.md"))
    assert before.returncode == res.returncode, before.stdout
    assert "CLASS-KILL DUE: line-rot" in before.stdout
    assert "CLASS-KILL DONE" not in before.stdout


# --- injection rate --------------------------------------------------------

def test_the_injection_rate_is_printed_per_batch(run, ledger):
    """Denominator = rows carrying the batch id in `fix`; numerator =
    `from:<batch>` inside an `origin:fix-application` tag.
    """
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="aa11"),
        tagged("DA-2", "upheld", fix="aa11"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="bb22"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "  aa11: 1/2 = 50.0%" in res.stdout
    assert "  bb22: 0/1 = 0.0%" in res.stdout


def test_the_batch_key_is_the_first_hash_in_the_fix_cell(run, ledger):
    """The DoD case: `F3 c447822 (touch-up)` and a bare `c447822` are ONE
    batch. Before, each wording was its own batch with its own denominator.
    """
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="F3 c447822 (touch-up)"),
        tagged("DA-2", "upheld", fix="c447822"),
        tagged("V1-1", "upheld, origin:fix-application from:c447822",
               fix="F4 d93c088"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "  c447822: 1/2 = 50.0%" in res.stdout
    assert "  d93c088: 0/1 = 0.0%" in res.stdout
    assert "F3 c447822" not in res.stdout


def test_a_fix_cell_without_a_hash_keeps_its_whole_literal_as_the_key(
        run, ledger):
    """A snapshot-named batch groups exactly as it always did — and a bare
    date is not mistaken for a commit hash.
    """
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="snapshot B4"),
        tagged("DA-2", "upheld", fix="20260904"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11",
               fix="snapshot B4"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "  snapshot B4: 0/2 = 0.0%" in res.stdout
    assert "  20260904: 0/1 = 0.0%" in res.stdout


def test_the_reference_points_are_marked_as_literature(run, ledger):
    rows = tagged("V1-1", "upheld, origin:fix-application from:aa11")
    res = run(SCRIPT, ledger(rows))
    assert ("7% and 3.5% are LITERATURE reference points — undisciplined "
            "and disciplined floor — not our measurement" in res.stdout)


def test_two_consecutive_high_batches_recommend_stopping_the_batching(
        run, ledger):
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="aa11"),
        tagged("DA-2", "upheld", fix="aa11"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="bb22"),
        tagged("V1-2", "upheld", fix="bb22"),
        tagged("V2-1", "upheld, origin:fix-application from:bb22", fix="cc33"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "INJECTION RATE HIGH: bb22, 50.0%" in res.stdout
    assert "recommend stopping the batching and forking to the user" in res.stdout
    assert "this metric never stops the round by itself" in res.stdout


def test_the_injection_flag_needs_two_consecutive_batches(run, ledger):
    """One high batch followed by a clean one raises nothing."""
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="aa11"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="bb22"),
        tagged("V1-2", "upheld", fix="bb22"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "  aa11: 1/1 = 100.0%" in res.stdout
    assert "  bb22: 0/2 = 0.0%" in res.stdout
    assert "INJECTION RATE HIGH" not in res.stdout


def test_a_batch_below_seven_percent_raises_nothing(run, ledger):
    rows = "\n".join(
        [tagged(f"DA-{n}", "upheld", fix="aa11") for n in range(1, 21)]
        + [tagged("V1-1", "upheld, origin:fix-application from:aa11",
                  fix="bb22")],
    )
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "  aa11: 1/20 = 5.0%" in res.stdout
    assert "INJECTION RATE HIGH" not in res.stdout


def test_the_injection_flag_does_not_borrow_the_class_kill_literal(
        run, ledger):
    """One literal, one weight of compulsion: the injection threshold never
    prints CLASS-KILL DUE.
    """
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="aa11"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="bb22"),
        tagged("V2-1", "upheld, origin:fix-application from:bb22", fix="cc33"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert "INJECTION RATE HIGH" in res.stdout
    assert "CLASS-KILL DUE" not in res.stdout


def test_a_tagged_row_without_a_readable_from_is_unattributed(run, ledger):
    """It is listed, never charged to the latest batch by guess."""
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="aa11"),
        tagged("V1-1", "upheld, origin:fix-application", fix="aa11"),
        tagged("V1-2", "upheld, origin:fix-application from:UPPER", fix="aa11"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "INJECTION UNATTRIBUTED: V1-1, V1-2" in res.stdout
    assert "  aa11: 0/3 = 0.0%" in res.stdout


def test_a_row_fixed_by_no_identifiable_batch_gets_n_a(run, ledger):
    rows = "\n".join([
        tagged("DA-1", "upheld", fix=" "),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="aa11"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "injection rate: n/a (batch not identifiable) for DA-1" in res.stdout


def test_a_refuted_row_is_not_reported_as_an_unidentifiable_batch(
        run, ledger):
    """A refuted row was never fixed; it belongs to no batch at all."""
    rows = "\n".join([
        tagged("DA-1", "refuted", criterion="—", fix="—", verified="n/a",
               terminal="refuted-with-reason"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="aa11"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert "batch not identifiable" not in res.stdout


def test_a_from_reference_naming_no_batch_is_reported(run, ledger):
    """Attribution to a batch the fix column does not know is visible, not
    silently dropped from the metric.
    """
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="aa11"),
        tagged("V1-1", "upheld, origin:fix-application from:zz99", fix="aa11"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert ("injection: no batch in the fix column is named by from:zz99"
            in res.stdout)


def test_the_injection_report_does_not_change_the_exit_code(run, ledger):
    rows = "\n".join([
        tagged("DA-1", "upheld", fix="aa11"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="aa11"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert res.returncode == 0, res.stdout
    assert res.stdout.rstrip().endswith("ROUND CLOSABLE: zero non-terminal rows.")


# --- residue: the two named waits and the durable register ------------------
#
# A residue NOMINEE is not an open row and not a terminal one: it waits in a
# NAMED non-terminal state until the owner ratifies it. The exit contract
# therefore has four buckets and still two codes, and the register that holds
# what was accepted lives outside the run folder, so it outlives it. The
# compatibility claim these tests protect is the last one below: a ledger with
# neither a register nor a nomination prints not one new line.

NOMINEE = (
    "| DA-2 | minor | claim | verdict | crit | fix | x | "
    "awaiting-signature (nominated 2026-08-29) |"
)
RATIFIED = (
    "| DA-2 | minor | claim | verdict | crit | fix | x | "
    "accepted-residue user-signed 2026-08-29 |"
)
NO_ACTION = (
    "| DA-3 | minor | claim | verdict | crit | fix | x | "
    "awaiting-logged-no-action |"
)
# An open row whose id collides with neither of the two waiting rows above.
OPEN_TOO = "| DA-4 | major | claim | verdict |  | fix | x | open |"
REG_HEADER = (
    "| run-qualified id | severity | claim-hook | rationale | "
    "compensating-control | review-by | status | origin-run |\n"
    "|---|---|---|---|---|---|---|---|\n"
)


def reg_row(rid: str = "run1/DA-2", sev: str = "minor", hook: str = "hook",
            rationale: str = "argued when it was made",
            control: str = "a leak gate stays red",
            review_by: str = "2099-01-01",
            status: str = "nominated 2099-01-01",
            origin: str = "run1") -> str:
    """One register row, addressed by the cells these tests vary."""
    return (f"| {rid} | {sev} | {hook} | {rationale} | {control} | "
            f"{review_by} | {status} | {origin} |")


def register(tmp_path, *rows: str, header: str = REG_HEADER,
             name: str = "residue-register.md"):
    """Write a residue register into tmp_path and return its path."""
    path = tmp_path / name
    body = "\n".join(rows) + "\n" if rows else ""
    path.write_text("# Residue register\n\n" + header + body, encoding="utf-8")
    return path


def run_ledger(tmp_path, rows: str, *, run: str = "run1"):
    """Write a ledger at the layout address the register is derived from."""
    folder = tmp_path / ".critic-ledger" / run
    folder.mkdir(parents=True, exist_ok=True)
    return write_ledger(folder / "fix-ledger.md", rows)


# --- the named waits and the four exit buckets ------------------------------


def test_a_nomination_is_a_named_wait_not_an_open_row(run, ledger):
    """The DoD case: no open row, one nominee -> awaiting ratification, exit 1."""
    res = run(SCRIPT, ledger(CLOSED + "\n" + NOMINEE))
    assert res.returncode == 1, res.stdout
    assert "awaiting-signature ids: DA-2" in res.stdout
    assert ("ROUND AWAITING RATIFICATION: 1 rows await the owner's signature."
            in res.stdout)
    assert "non-terminal ids:" not in res.stdout
    assert "ROUND NOT CLOSABLE" not in res.stdout


def test_the_same_fixture_closes_once_the_nomination_is_ratified(run, ledger):
    """The second half of the DoD case: ratified -> ROUND CLOSABLE, exit 0."""
    res = run(SCRIPT, ledger(CLOSED + "\n" + RATIFIED))
    assert res.returncode == 0, res.stdout
    assert res.stdout.rstrip().endswith("ROUND CLOSABLE: zero non-terminal rows.")
    assert "AWAITING" not in res.stdout


def test_a_wait_still_counts_as_non_terminal_in_the_header_count(run, ledger):
    res = run(SCRIPT, ledger(CLOSED + "\n" + NOMINEE))
    assert res.stdout.splitlines()[0] == "rows: 2 | terminal: 1 | non-terminal: 1"


def test_a_blocker_may_not_be_nominated(run, ledger):
    """The DoD case: a blocker nominee is a structural error, exit 2."""
    row = NOMINEE.replace("DA-2 | minor", "DA-2 | blocker")
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 2, res.stdout
    assert "categorically non-nominable" in res.stdout
    assert "rows:" not in res.stdout


@pytest.mark.parametrize("terminal", [
    "awaiting-signature",
    "awaiting-signature (nominated)",
    "awaiting-signature (nominated 2026-02-30)",
])
def test_a_nomination_without_a_readable_date_is_an_open_row(
        run, ledger, terminal):
    """A nomination whose age cannot be read cannot be chased for a deadline."""
    row = f"| DA-2 | minor | claim | verdict | crit | fix | x | {terminal} |"
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 1, res.stdout
    assert "non-terminal ids: DA-2" in res.stdout
    assert "ROUND NOT CLOSABLE: 1 open rows." in res.stdout
    assert "AWAITING RATIFICATION" not in res.stdout
    assert "  CONSISTENCY: DA-2" in res.stdout


@pytest.mark.parametrize("criterion", ["", "-", "—"])
def test_a_nominee_keeps_the_criterion_written_at_adjudication(
        run, ledger, criterion):
    """A nominee is UPHELD, exactly as a ratified residue is."""
    row = NOMINEE.replace("| crit |", f"| {criterion} |")
    res = run(SCRIPT, ledger(row))
    assert res.returncode == 2, res.stdout
    assert "is awaiting-signature but its readiness-criterion cell" in res.stdout


def test_an_open_row_outranks_both_waits(run, ledger):
    """Bucket 1 wins, and the two queues are still listed under it."""
    res = run(SCRIPT, ledger("\n".join([OPEN_TOO, NOMINEE, NO_ACTION])))
    assert res.returncode == 1, res.stdout
    assert "non-terminal ids: DA-4" in res.stdout
    assert "awaiting-signature ids: DA-2" in res.stdout
    assert "awaiting-logged-no-action ids: DA-3" in res.stdout
    assert "ROUND NOT CLOSABLE: 1 open rows." in res.stdout


def test_ratification_outranks_the_logged_no_action_wait(run, ledger):
    """The MIXED state: one state line, and it is the ratification one."""
    res = run(SCRIPT, ledger("\n".join([NOMINEE, NO_ACTION])))
    assert res.returncode == 1, res.stdout
    assert "awaiting-logged-no-action ids: DA-3" in res.stdout
    assert "ROUND AWAITING RATIFICATION" in res.stdout
    assert "ROUND AWAITING Z3 CLOSURE" not in res.stdout


def test_the_logged_no_action_queue_has_a_state_line_of_its_own(run, ledger):
    res = run(SCRIPT, ledger(CLOSED + "\n" + NO_ACTION))
    assert res.returncode == 1, res.stdout
    assert ("ROUND AWAITING Z3 CLOSURE: 1 rows await the owner's act."
            in res.stdout)


@pytest.mark.parametrize("rows", [
    OPEN_TOO + "\n" + NOMINEE,
    NOMINEE + "\n" + NO_ACTION,
    CLOSED + "\n" + NO_ACTION,
    CLOSED,
])
def test_exactly_one_state_line_is_printed(run, ledger, rows):
    """Four buckets, one state line — that of the first bucket that matches."""
    res = run(SCRIPT, ledger(rows))
    states = sum(
        res.stdout.count(literal)
        for literal in ("ROUND NOT CLOSABLE", "ROUND AWAITING RATIFICATION",
                        "ROUND AWAITING Z3 CLOSURE", "ROUND CLOSABLE")
    )
    assert states == 1, res.stdout


def test_a_waiting_row_is_not_reported_as_an_unidentifiable_batch(run, ledger):
    """A nominee was never handed to a fixer; it belongs to no batch."""
    rows = "\n".join([
        NOMINEE.replace("| fix |", "|  |"),
        tagged("V1-1", "upheld, origin:fix-application from:aa11", fix="aa11"),
    ])
    res = run(SCRIPT, ledger(rows))
    assert "batch not identifiable" not in res.stdout


# --- the durable register ---------------------------------------------------


def test_a_ledger_with_no_register_and_no_nomination_prints_nothing_new(
        run, ledger):
    """The compatibility claim: no register in play, no register line."""
    res = run(SCRIPT, ledger(CLOSED + "\n" + OPEN))
    assert "residue register" not in res.stdout
    assert "rows: 2 | terminal: 1 | non-terminal: 1" in res.stdout


def test_a_legacy_seven_cell_ledger_prints_no_register_line(run, ledger):
    row = "| DA-1 | major | claim | verdict | fix | LANDED | verified-landed |"
    res = run(SCRIPT, ledger(row, header=HEADER_7))
    assert res.returncode == 0, res.stdout
    assert "residue register" not in res.stdout


def test_the_register_path_is_derived_from_the_ledger_layout(run, tmp_path):
    """`<root>/.critic-ledger/<run>/fix-ledger.md` gives the register beside it."""
    path = run_ledger(tmp_path, CLOSED + "\n" + NOMINEE)
    register(tmp_path / ".critic-ledger", reg_row())
    res = run(SCRIPT, path)
    assert res.returncode == 1, res.stdout
    assert "residue-register.md" in res.stdout
    assert "rows: 1 | nominated 1 | ratified 0 | expired-reopened 0" in res.stdout


def test_the_register_flag_overrides_the_convention(run, tmp_path):
    path = run_ledger(tmp_path, CLOSED + "\n" + NOMINEE)
    register(tmp_path / ".critic-ledger", reg_row())
    elsewhere = register(tmp_path, reg_row(), reg_row(rid="run1/DA-9"),
                         name="other-register.md")
    res = run(SCRIPT, path, "--register", elsewhere)
    assert "rows: 2 |" in res.stdout
    assert "other-register.md" in res.stdout


def test_a_ledger_outside_the_run_root_derives_no_register_path(run, ledger):
    res = run(SCRIPT, ledger(NOMINEE))
    assert "residue register: n/a (path not derived" in res.stdout
    assert res.returncode == 1, res.stdout


def test_a_derivable_register_that_does_not_exist_is_reported(run, tmp_path):
    path = run_ledger(tmp_path, CLOSED + "\n" + NOMINEE)
    res = run(SCRIPT, path)
    assert "residue register: n/a (not found at " in res.stdout
    assert "residue-register.md)" in res.stdout


def test_the_flag_puts_the_register_in_play_without_a_nomination(run, ledger,
                                                                 tmp_path):
    """A closable ledger still gets the aggregate when the flag names one."""
    reg = register(tmp_path, reg_row(status="ratified 2026-01-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | nominated 0 | ratified 1 | expired-reopened 0" in res.stdout
    assert res.stdout.rstrip().endswith("ROUND CLOSABLE: zero non-terminal rows.")


def test_the_flag_without_a_value_is_a_usage_error(run, ledger):
    res = run(SCRIPT, ledger(CLOSED), "--register")
    assert res.returncode == 2, res.stdout
    assert "--register needs a path" in res.stdout
    assert res.stderr == ""


def test_the_aggregate_counts_every_status_and_the_age_of_the_oldest(
        run, ledger, tmp_path):
    reg = register(
        tmp_path,
        reg_row(rid="r/A-1", status="nominated 2099-01-01"),
        reg_row(rid="r/A-2", status="ratified 2026-01-01"),
        reg_row(rid="r/A-3", status="expired-reopened 2020-01-01"),
    )
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "rows: 3 | nominated 1 | ratified 1 | expired-reopened 1" in res.stdout
    assert "oldest " in res.stdout
    assert "(2020-01-01, r/A-3)" in res.stdout


def test_an_empty_register_prints_a_zero_aggregate(run, ledger, tmp_path):
    reg = register(tmp_path)
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 0, res.stdout
    assert ("rows: 0 | nominated 0 | ratified 0 | expired-reopened 0 | withdrawn 0 | "
            "oldest n/a (empty register)" in res.stdout)


def test_a_withdrawn_row_is_parsed(run, ledger, tmp_path):
    """A withdrawn nomination is a status of its own, not a malformed row."""
    reg = register(tmp_path, reg_row(status="withdrawn 2026-09-15"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 0, res.stdout
    assert "RESIDUE REGISTER STRUCTURAL ERRORS:" not in res.stdout
    assert "NOMINATION OVERDUE" not in res.stdout


def test_the_aggregate_counts_a_withdrawn_row(run, ledger, tmp_path):
    reg = register(
        tmp_path,
        reg_row(rid="r/A-1", status="nominated 2099-01-01"),
        reg_row(rid="r/A-2", status="ratified 2026-01-01"),
        reg_row(rid="r/A-3", status="expired-reopened 2026-01-01"),
        reg_row(rid="r/DA-4", status="withdrawn 2020-01-01"),
    )
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert ("rows: 4 | nominated 1 | ratified 1 | expired-reopened 1 | "
            "withdrawn 1 | oldest " in res.stdout)


def test_an_overdue_nomination_is_printed(run, ledger, tmp_path):
    """The DoD case for the unratified nomination's own 30-day limit."""
    reg = register(tmp_path, reg_row(status="nominated 2020-01-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "NOMINATION OVERDUE: run1/DA-2 (nominated 2020-01-01," in res.stdout
    assert "the 30-day limit on an UNRATIFIED nomination is OURS" in res.stdout


def test_a_fresh_nomination_is_not_overdue(run, ledger, tmp_path):
    reg = register(tmp_path, reg_row(status="nominated 2099-01-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "NOMINATION OVERDUE" not in res.stdout


def test_an_expired_review_by_is_printed(run, ledger, tmp_path):
    """The DoD case: expiry RE-OPENS by default, never renews in silence."""
    reg = register(tmp_path, reg_row(status="ratified 2020-01-01",
                                     review_by="2020-06-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "REVIEW-BY EXPIRED: run1/DA-2 (review-by 2020-06-01," in res.stdout
    assert "expiry RE-OPENS by default" in res.stdout


def test_a_review_by_still_ahead_is_not_printed(run, ledger, tmp_path):
    reg = register(tmp_path, reg_row(status="ratified 2026-01-01",
                                     review_by="2099-01-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "REVIEW-BY EXPIRED" not in res.stdout


def test_an_unratified_row_is_not_charged_with_an_expired_review_by(
        run, ledger, tmp_path):
    """Only accepted risk is re-counted; a nominee has its own deadline."""
    reg = register(tmp_path, reg_row(status="nominated 2099-01-01",
                                     review_by="2020-01-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "REVIEW-BY EXPIRED" not in res.stdout


def test_a_withdrawn_row_is_never_counted_as_expiring(run, ledger, tmp_path):
    """A withdrawn nomination is neither overdue nor expiring, even once its
    review-by date has passed."""
    reg = register(tmp_path, reg_row(status="withdrawn 2020-01-01",
                                     review_by="2020-06-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 0, res.stdout
    assert "REVIEW-BY EXPIRED" not in res.stdout
    assert "NOMINATION OVERDUE" not in res.stdout


def test_a_second_cycle_row_demands_an_owner_fork(run, ledger, tmp_path):
    reg = register(tmp_path,
                   reg_row(status="expired-reopened 2026-01-01 (#2)"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "SECOND CYCLE — OWNER FORK REQUIRED: run1/DA-2" in res.stdout
    assert "cycle #2" in res.stdout


def test_a_first_reopen_raises_no_fork(run, ledger, tmp_path):
    reg = register(tmp_path, reg_row(status="expired-reopened 2026-01-01"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "SECOND CYCLE" not in res.stdout


def test_a_nomination_with_no_register_row_is_named(run, tmp_path):
    path = run_ledger(tmp_path, CLOSED + "\n" + NOMINEE)
    register(tmp_path / ".critic-ledger", reg_row(rid="run1/DA-9"))
    res = run(SCRIPT, path)
    assert "NOMINATION WITHOUT A REGISTER ROW: DA-2" in res.stdout


def test_a_run_qualified_id_accounts_for_the_bare_ledger_id(run, tmp_path):
    path = run_ledger(tmp_path, CLOSED + "\n" + NOMINEE)
    register(tmp_path / ".critic-ledger", reg_row(rid="run1/DA-2"))
    res = run(SCRIPT, path)
    assert "NOMINATION WITHOUT A REGISTER ROW" not in res.stdout


def test_a_withdrawn_register_row_accounts_for_no_nomination(run, tmp_path):
    """A withdrawal sends the finding back to adjudication, so a ledger row
    still awaiting signature behind it is named, not counted as a wait."""
    path = run_ledger(tmp_path, CLOSED + "\n" + NOMINEE)
    register(tmp_path / ".critic-ledger",
             reg_row(rid="run1/DA-2", status="withdrawn 2026-09-10"))
    res = run(SCRIPT, path)
    flagged = [line for line in res.stdout.splitlines()
               if "NOMINATION WITHOUT A REGISTER ROW: DA-2" in line]
    assert flagged, res.stdout


def test_the_honest_boundary_is_printed_with_the_aggregate(run, ledger,
                                                           tmp_path):
    reg = register(tmp_path, reg_row())
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "visibility, not traction" in res.stdout
    assert "append-only in this release" in res.stdout


def test_no_register_line_changes_the_exit_code(run, ledger, tmp_path):
    """Overdue, expired and second-cycle at once, on a closable ledger."""
    reg = register(
        tmp_path,
        reg_row(rid="r/A-1", status="nominated 2020-01-01"),
        reg_row(rid="r/A-2", status="ratified 2020-01-01",
                review_by="2020-06-01"),
        reg_row(rid="r/A-3", status="expired-reopened 2020-01-01 (#3)"),
    )
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 0, res.stdout
    assert "NOMINATION OVERDUE" in res.stdout
    assert "REVIEW-BY EXPIRED" in res.stdout
    assert "SECOND CYCLE" in res.stdout


# --- the register's fail-closed parsing -------------------------------------


@pytest.mark.parametrize(("row", "message"), [
    (reg_row(rationale=""), "blank `rationale`"),
    (reg_row(rationale="—"), "blank `rationale`"),
    (reg_row(control=""), "blank `compensating-control`"),
    (reg_row(control="-"), "blank `compensating-control`"),
    (reg_row(sev="blocker"), "categorically non-nominable"),
    (reg_row(review_by="soon"), "it must be a calendar-valid ISO date"),
    (reg_row(review_by="2026-02-30"), "it must be a calendar-valid ISO date"),
    (reg_row(status="accepted"), "it must be one of nominated"),
    (reg_row(status="nominated"), "it must be one of nominated"),
    (reg_row(status="nominated 2026-02-30"), "not a calendar date"),
])
def test_a_malformed_register_row_is_a_structural_error(
        run, ledger, tmp_path, row, message):
    reg = register(tmp_path, row)
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 2, res.stdout
    assert "RESIDUE REGISTER STRUCTURAL ERRORS:" in res.stdout
    assert message in res.stdout


def test_the_direct_risk_literal_is_a_legitimate_compensating_control(
        run, ledger, tmp_path):
    reg = register(tmp_path, reg_row(control="none — direct risk accepted"))
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 0, res.stdout
    assert "rows: 1 |" in res.stdout


def test_a_duplicate_register_id_is_a_structural_error(run, ledger, tmp_path):
    reg = register(tmp_path, reg_row(), reg_row())
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 2, res.stdout
    assert "DUPLICATE REGISTER ID run1/DA-2" in res.stdout


def test_a_short_register_row_is_a_structural_error(run, ledger, tmp_path):
    reg = register(tmp_path, "| run1/DA-2 | minor | hook | why | control |")
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 2, res.stdout
    assert "malformed register row (5 cells, need 8" in res.stdout


def test_a_register_header_of_the_wrong_width_is_a_structural_error(
        run, ledger, tmp_path):
    reg = register(tmp_path, reg_row(),
                   header="| run-qualified id | severity |\n|---|---|\n")
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert res.returncode == 2, res.stdout
    assert "register header has 2 cells" in res.stdout


def test_register_rows_stop_at_the_next_heading(run, ledger, tmp_path):
    reg = tmp_path / "reg.md"
    reg.write_text(
        REG_HEADER + reg_row() + "\n\n## Notes\n" + REG_HEADER
        + reg_row(rid="r/X-1") + "\n",
        encoding="utf-8",
    )
    res = run(SCRIPT, ledger(CLOSED), "--register", reg)
    assert "rows: 1 |" in res.stdout


def test_an_unreadable_register_is_reported_and_never_fatal(
        run, ledger, tmp_path):
    """A directory in the register's place is a report line, not a traceback."""
    (tmp_path / "reg-dir.md").mkdir()
    res = run(SCRIPT, ledger(CLOSED), "--register", tmp_path / "reg-dir.md")
    assert res.returncode == 0, res.stdout
    assert "residue register: n/a (" in res.stdout
    assert res.stderr == ""


# --- 0.3.0 stopping metrics: the residual-defect ESTIMATE and the plateau ---
#
# Both are REPORT-ONLY: nothing here may move an exit code. The estimate has
# exactly ONE source for `k` — the header's machine-form `Lenses:` lines —
# and the plateau derives the chronology of its window from each ledger's own
# `Round-started` field rather than from the order of the arguments. The
# tests below pin both refusals as hard as they pin the numbers: an estimate
# computed off a guessed `k`, or a plateau ordered by argument position,
# would be a wrong number printed with the same confidence as a right one.

ESTIMATE = "residual-defect ESTIMATE"
PLATEAU = "severity plateau"


def lens_field(*prefixes: str, tail: str = "") -> str:
    """A header preamble whose `Lenses:` field declares these prefixes."""
    body = "".join(f"  - {p} | lens {p.lower()} | sonnet\n" for p in prefixes)
    return "- Lenses:\n" + body + tail + "\n"


def raised(rid: str, sev: str = "major", criterion: str = "crit") -> str:
    """One terminal, upheld findings row — the shape a raised finding takes."""
    return (f"| {rid} | {sev} | claim | verdict | {criterion} | fix | "
            f"LANDED | verified-landed |")


def window_ledger(ledger, day: str, majors: int, *, name: str):
    """A ledger dated `day` carrying `majors` major rows — a plateau member."""
    rows = "\n".join(raised(f"PA-{i}") for i in range(1, majors + 1))
    return ledger(rows, preamble=f"- Round-started: {day}\n", name=name)


# --- the prefixes that belong to a process rather than to a lens -----------
#
# `Process prefixes:` declares what is NOT a lens: the `NOTICED OUTSIDE
# BATCH` prefix and a class-kill gate's own row take ids of exactly a lens's
# shape, so without the field nothing tells them apart machine-side. The
# field is read by its OWN anchored pattern, and the property these cases
# pin is that it stays out of `k`: a process prefix reaching `lens_prefixes`
# would inflate the residual-defect estimate's lens count.

FIVE_LENSES = ("AA", "BB", "CC", "DD", "EE")
# Five lenses, four raised findings, three of them single-lens: k=5, D=4,
# f1=3 -> 6.4, the hand-computed value the estimate case below reuses.
ESTIMATE_ROWS = "\n".join([
    raised("AA-1"), raised("BB-1"), raised("CC-1"),
    raised("DD-1", sev="minor", criterion="=CC-1"),
    raised("EE-1", sev="minor"),
])


def test_the_process_prefix_field_leaves_k_and_the_estimate_untouched(
    run, ledger
):
    """The same ledger with and without the field recounts identically.

    This is the preserved property, checked rather than assumed: the new
    field has its own pattern and feeds nothing the `Lenses:` run feeds, so
    `k` is 5 either way and the two prefixes it names appear in no lens
    list. Were the field read by a widened lens pattern, `k` would read 7.
    """
    without = run(SCRIPT, ledger(ESTIMATE_ROWS, preamble=lens_field(*FIVE_LENSES)))
    with_field = run(
        SCRIPT,
        ledger(
            ESTIMATE_ROWS,
            preamble="- Process prefixes: NB, CK\n" + lens_field(*FIVE_LENSES),
        ),
    )
    assert without.returncode == 0, without.stdout
    assert with_field.returncode == 0, with_field.stdout
    assert with_field.stdout == without.stdout
    assert "k 5 (AA, BB, CC, DD, EE)" in with_field.stdout
    assert "NB" not in with_field.stdout
    assert "CK" not in with_field.stdout


def test_the_literal_none_is_a_readable_process_prefix_field(run, ledger):
    """`none` and an ABSENT field say the same thing and recount the same."""
    declared = run(
        SCRIPT,
        ledger(
            ESTIMATE_ROWS,
            preamble="- Process prefixes: none\n" + lens_field(*FIVE_LENSES),
        ),
    )
    absent = run(SCRIPT, ledger(ESTIMATE_ROWS, preamble=lens_field(*FIVE_LENSES)))
    assert declared.returncode == 0, declared.stdout
    assert declared.stdout == absent.stdout


def test_an_unreadable_process_prefix_field_is_a_structural_error(run, ledger):
    """A field that arms nothing on a typo would be worse than no field."""
    res = run(
        SCRIPT,
        ledger(
            CLOSED,
            preamble="- Process prefixes: the noticed one\n",
        ),
    )
    assert res.returncode == 2, res.stdout
    assert "`Process prefixes:` reads 'the noticed one'" in res.stdout


def test_a_process_prefix_that_is_also_a_lens_is_a_structural_error(run, ledger):
    """A prefix written in both fields tells a process from a lens nowhere."""
    res = run(
        SCRIPT,
        ledger(
            ESTIMATE_ROWS,
            preamble="- Process prefixes: NB, CC\n" + lens_field(*FIVE_LENSES),
        ),
    )
    assert res.returncode == 2, res.stdout
    assert "`Process prefixes:` names CC" in res.stdout


@pytest.mark.parametrize(
    "field_line",
    ["- Process prefixes:\n", "- Process prefixes: \n"],
    ids=["colon-at-end-of-line", "one-trailing-space"],
)
def test_an_empty_process_prefix_field_is_present_and_unreadable(
    run, ledger, field_line
):
    """PRESENT-and-empty is not ABSENT, whatever the editor did to the space.

    A line ending AT THE COLON used to match the field's pattern nowhere and
    read exactly like an absent field — no error, no diagnostic, exit 0 —
    while the same line with one trailing space was caught. A fail-closed
    gate must not hang on a byte an editor is free to strip on save: both
    spellings are the same empty declaration and both are structural errors.
    """
    res = run(SCRIPT, ledger(CLOSED, preamble=field_line))
    assert res.returncode == 2, res.stdout
    assert "STRUCTURAL ERRORS" in res.stdout
    assert "`Process prefixes:` reads ''" in res.stdout


def test_two_process_prefix_fields_are_a_structural_error(run, ledger):
    """The field is ONE per ledger; a second line is an overwrite.

    Both values here are individually well-formed, which is the point: the
    parser used to return on the first match and discard the second with no
    trace, where `Row schema:` and `Stop-rule freeze:` both refuse a second
    declaration outright.
    """
    res = run(
        SCRIPT,
        ledger(
            CLOSED,
            preamble="- Process prefixes: NB\n- Process prefixes: CK\n",
        ),
    )
    assert res.returncode == 2, res.stdout
    assert "carries 2 `Process prefixes:` fields" in res.stdout
    assert "never a silent replacement" in res.stdout


# --- k, and the one place it comes from ------------------------------------


def test_a_ledger_declaring_no_lenses_gets_no_estimate(run, ledger):
    """The compat shape: an old ledger names no `k`, so none is invented."""
    res = run(SCRIPT, ledger(CLOSED))
    assert res.returncode == 0, res.stdout
    assert f"{ESTIMATE}: n/a: k not derived from the header" in res.stdout
    assert "N-hat" not in res.stdout


def test_three_lenses_are_below_the_applicability_floor(run, ledger):
    """The DoD case: k=3 prints `n/a: k<4` and no number at all."""
    res = run(SCRIPT, ledger(CLOSED, preamble=lens_field("AA", "BB", "CC")))
    assert res.returncode == 0, res.stdout
    assert f"{ESTIMATE}: n/a: k<4 (k=3;" in res.stdout
    assert "N-hat" not in res.stdout


def test_the_estimate_matches_the_hand_computed_value(run, ledger):
    """The DoD case: k=5, D=4, f1=3 -> 4 + (4/5)*3 = 6.4, computed by hand.

    `DD-1` is a cross-lens duplicate of `CC-1` by the `=id` convention, so
    that finding was raised by two lenses and is not a singleton; `V1-1` was
    raised by a verifier, which is no lens at all, so it is not counted.
    """
    rows = "\n".join([
        raised("AA-1"), raised("BB-1"), raised("CC-1"),
        raised("DD-1", sev="minor", criterion="=CC-1"),
        raised("EE-1", sev="minor"), raised("V1-1", sev="minor"),
    ])
    res = run(SCRIPT, ledger(
        rows, preamble=lens_field("AA", "BB", "CC", "DD", "EE")))
    assert res.returncode == 0, res.stdout
    assert ("N-hat 6.4 | D 4 raised | f1 3 single-lens | k 5 "
            "(AA, BB, CC, DD, EE)" in res.stdout)


def test_a_composite_primary_id_is_read_as_a_duplicate_pointer(run, ledger):
    """A criterion cell `=V-CIT-1` is a pointer, not prose.

    The `=id` convention takes ids under the WHOLE id contract, composite
    prefixes included, so `AA-1` and `BB-1` glossing the same verifier-pass
    primary are ONE group two lenses raised: k=4, D=3, f1=2 ->
    3 + (3/4)*2 = 4.5. Were the composite pointer read as prose, the same two
    rows would stay two single-lens groups and the estimate would be 7.0.
    """
    rows = "\n".join([
        raised("AA-1", criterion="=V-CIT-1"),
        raised("BB-1", criterion="=V-CIT-1"),
        raised("CC-1"), raised("DD-1"),
    ])
    res = run(SCRIPT, ledger(
        rows, preamble=lens_field("AA", "BB", "CC", "DD")))
    assert res.returncode == 0, res.stdout
    assert ("N-hat 4.5 | D 3 raised | f1 2 single-lens | k 4 "
            "(AA, BB, CC, DD)" in res.stdout)


def test_a_verifier_row_never_raises_k(run, ledger):
    """The whole reason `k` is not counted off the table: passes add prefixes.

    Four lenses are declared and three verification passes have written
    rows. A `k` counted from the id prefixes would be 7; the declared count
    is 4, and only the declared count may be used.
    """
    rows = "\n".join([
        raised("AA-1"), raised("BB-1"), raised("CC-1"), raised("DD-1"),
        raised("V1-1"), raised("V2-1"), raised("V3-1"),
    ])
    res = run(SCRIPT, ledger(
        rows, preamble=lens_field("AA", "BB", "CC", "DD")))
    assert "| k 4 (AA, BB, CC, DD)" in res.stdout
    assert "N-hat 7.0 | D 4 raised | f1 4 single-lens" in res.stdout


def test_reading_the_lens_run_stops_at_the_first_foreign_line(run, ledger):
    """Prose below the run is not counted, and neither is a later bullet."""
    preamble = (lens_field("AA", "BB", "CC", "DD",
                           tail="  timebox 15 min each.\n")
                + "- Verifier passes: V\n"
                + "  - ZZ | not a lens line, it is below the prose | sonnet\n")
    res = run(SCRIPT, ledger(raised("AA-1"), preamble=preamble))
    assert "| k 4 (AA, BB, CC, DD)" in res.stdout
    assert "ZZ" not in res.stdout


def test_a_prefix_written_twice_is_one_lens(run, ledger):
    res = run(SCRIPT, ledger(
        raised("AA-1"),
        preamble=lens_field("AA", "BB", "CC", "DD", "AA")))
    assert "| k 4 (AA, BB, CC, DD)" in res.stdout


def test_a_lens_line_of_the_wrong_shape_is_not_a_lens(run, ledger):
    """The old arrow form parses as nothing: `n/a`, never a partial count."""
    preamble = ("- Lenses:\n"
                "  - consistency -> AA -> sonnet -> 15 min\n"
                "  - correctness -> BB -> sonnet -> 15 min\n"
                "  - coverage -> CC -> sonnet -> 15 min\n"
                "  - cost -> DD -> sonnet -> 15 min\n")
    res = run(SCRIPT, ledger(raised("AA-1"), preamble=preamble))
    assert f"{ESTIMATE}: n/a: k not derived from the header" in res.stdout


def test_a_refuted_finding_was_still_raised(run, ledger):
    """D counts findings BEFORE adjudication: a refuted claim is in it."""
    refuted = "| BB-1 | minor | claim | verdict | — | fix | x | refuted-with-reason |"
    rows = "\n".join([raised("AA-1"), refuted, raised("CC-1"), raised("DD-1")])
    res = run(SCRIPT, ledger(
        rows, preamble=lens_field("AA", "BB", "CC", "DD")))
    assert "N-hat 7.0 | D 4 raised | f1 4 single-lens" in res.stdout


def test_the_estimate_carries_its_caveat_and_both_owners(run, ledger):
    """The number never travels without the caution, nor the caution's owner."""
    res = run(SCRIPT, ledger(
        "\n".join(raised(f"{p}-1") for p in ("AA", "BB", "CC", "DD")),
        preamble=lens_field("AA", "BB", "CC", "DD")))
    assert "ESTIMATE is ADVISORY" in res.stdout
    assert "Lens diversity does not invalidate it" in res.stdout
    assert "four field measurements" in res.stdout
    assert "75-94%" in res.stdout
    assert "comparability is not established" in res.stdout


def test_the_estimate_never_moves_the_exit_code(run, ledger):
    """An open row still exits 1 and a closable ledger still exits 0."""
    open_row = "| BB-1 | major | claim | verdict |  | fix | x | open |"
    preamble = lens_field("AA", "BB", "CC", "DD")
    assert run(SCRIPT, ledger(raised("AA-1"), preamble=preamble)).returncode == 0
    res = run(SCRIPT, ledger(raised("AA-1") + "\n" + open_row,
                             preamble=preamble))
    assert res.returncode == 1, res.stdout
    assert "N-hat" in res.stdout


# --- the severity-weighted plateau and its derived chronology --------------


def test_two_prev_ledgers_print_the_plateau(run, ledger, tmp_path):
    """The DoD case: 7 -> 4 -> 2 gives deltas -3 and -2, average -2.5."""
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    p2 = window_ledger(ledger, "2026-08-10", 7, name="p2.md")
    res = run(SCRIPT, cur, "--prev", p1, "--prev", p2)
    assert res.returncode == 0, res.stdout
    assert (f"{PLATEAU} (3-round moving average of major+blocker deltas): "
            "-2.5 | major+blocker per round (oldest first): 7 -> 4 -> 2 | "
            "deltas -3, -2" in res.stdout)
    assert "prev order: reordered" not in res.stdout
    # TWO lines: the numbers, then the advisory sentence in its own words.
    # The first no longer trails a clause about the binary streak, and the
    # second does not carry the `stop criterion` literal — that literal
    # belongs to ONE line of the output and to no other.
    assert "never instead of it" not in res.stdout.split("severity plateau (")[1] \
        .split("\n")[0]
    assert ("  severity plateau is ADVISORY: it is reported beside the binary "
            "verdict-streak signal, never instead of it, and it enters no "
            "stop rule, no gate and no exit code." in res.stdout)
    assert "stop criterion" not in res.stdout


def test_the_window_is_ordered_by_the_ledgers_not_by_the_arguments(
        run, ledger, tmp_path):
    """Arguments in the wrong order give the SAME plateau, plus the notice."""
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    p2 = window_ledger(ledger, "2026-08-10", 7, name="p2.md")
    res = run(SCRIPT, cur, "--prev", p2, "--prev", p1)
    assert res.returncode == 0, res.stdout
    assert "prev order: reordered by Round-started" in res.stdout
    assert "(oldest first): 7 -> 4 -> 2 | deltas -3, -2" in res.stdout


def test_the_delta_goes_to_the_nearer_previous_ledger(run, ledger):
    """Whichever order the two arrive in, the delta is against the nearer."""
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    p2 = window_ledger(ledger, "2026-08-10", 7, name="p2.md")
    for argv in ((p1, p2), (p2, p1)):
        res = run(SCRIPT, cur, "--prev", argv[0], "--prev", argv[1])
        assert f"DELTA vs {p1}:" in res.stdout


def test_a_plateau_rising_is_reported_with_its_sign(run, ledger):
    cur = window_ledger(ledger, "2026-08-29", 8, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    p2 = window_ledger(ledger, "2026-08-10", 2, name="p2.md")
    res = run(SCRIPT, cur, "--prev", p1, "--prev", p2)
    assert "deltas): +3.0 | major+blocker per round (oldest first): 2 -> 4 -> 8" \
        in res.stdout


@pytest.mark.parametrize("missing", ["cur", "p1", "p2"])
def test_a_ledger_without_round_started_stops_the_plateau(run, ledger, missing):
    """Any member of the window without a readable date refuses the metric."""
    days = {"cur": "2026-08-29", "p1": "2026-08-20", "p2": "2026-08-10"}
    paths = {
        name: (ledger("\n".join(raised(f"PA-{i}") for i in range(1, 3)),
                      name=f"{name}.md")
               if name == missing
               else window_ledger(ledger, days[name], 2, name=f"{name}.md"))
        for name in ("cur", "p1", "p2")
    }
    res = run(SCRIPT, paths["cur"], "--prev", paths["p1"],
              "--prev", paths["p2"])
    assert res.returncode == 0, res.stdout
    assert (f"{PLATEAU}: n/a: the order of the previous ledgers is not derived"
            in res.stdout)
    assert "DELTA vs" in res.stdout


@pytest.mark.parametrize("missing", ["cur", "p1", "p2"])
def test_the_stopped_plateau_names_the_undated_ledger(run, ledger, missing):
    """WHICH ledger cost the metric is named, not left to be re-derived."""
    days = {"cur": "2026-08-29", "p1": "2026-08-20", "p2": "2026-08-10"}
    paths = {
        name: (ledger("\n".join(raised(f"PA-{i}") for i in range(1, 3)),
                      name=f"{name}.md")
               if name == missing
               else window_ledger(ledger, days[name], 2, name=f"{name}.md"))
        for name in ("cur", "p1", "p2")
    }
    res = run(SCRIPT, paths["cur"], "--prev", paths["p1"],
              "--prev", paths["p2"])
    assert res.returncode == 0, res.stdout
    assert f"no readable Round-started in {paths[missing]})" in res.stdout


def test_the_stopped_plateau_names_both_undated_ledgers(run, ledger):
    """Two undated members are both named, in the order they were read."""
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    rows = "\n".join(raised(f"PA-{i}") for i in range(1, 3))
    p1 = ledger(rows, name="p1.md")
    p2 = ledger(rows, name="p2.md")
    res = run(SCRIPT, cur, "--prev", p1, "--prev", p2)
    assert res.returncode == 0, res.stdout
    assert f"no readable Round-started in {p1}, {p2})" in res.stdout


def test_two_previous_ledgers_of_the_same_date_have_no_order(run, ledger):
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    p2 = window_ledger(ledger, "2026-08-20", 7, name="p2.md")
    res = run(SCRIPT, cur, "--prev", p1, "--prev", p2)
    assert (f"{PLATEAU}: n/a: the order of the previous ledgers is not derived"
            in res.stdout)
    assert f"the same Round-started in {p1}, {p2})" in res.stdout


def test_an_uncalendared_round_started_is_not_a_date(run, ledger):
    """`2026-02-30` cannot exist, so it never orders a window."""
    cur = window_ledger(ledger, "2026-02-30", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    p2 = window_ledger(ledger, "2026-08-10", 7, name="p2.md")
    res = run(SCRIPT, cur, "--prev", p1, "--prev", p2)
    assert (f"{PLATEAU}: n/a: the order of the previous ledgers is not derived"
            in res.stdout)


def test_one_prev_still_behaves_as_it_did(run, ledger):
    """The DoD case: a single `--prev` keeps the 0.2.0 delta, unchanged."""
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    res = run(SCRIPT, cur, "--prev", p1)
    assert res.returncode == 0, res.stdout
    assert f"DELTA vs {p1}:" in res.stdout
    assert f"{PLATEAU}: n/a: 1 previous ledger given" in res.stdout
    assert "moving average" not in res.stdout


def test_a_third_prev_is_a_usage_error(run, ledger):
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    res = run(SCRIPT, cur, "--prev", p1, "--prev", p1, "--prev", p1)
    assert res.returncode == 2, res.stdout
    assert "--prev takes at most 2 paths" in res.stdout


def test_a_prev_with_a_broken_table_refuses_the_plateau(run, ledger):
    """A structurally broken window member costs the metric, not the round."""
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    p1 = window_ledger(ledger, "2026-08-20", 4, name="p1.md")
    broken = ledger("| DA-1 | major | a|b | v | crit | f | LANDED | "
                    "verified-landed |",
                    preamble="- Round-started: 2026-08-10\n", name="p2.md")
    res = run(SCRIPT, cur, "--prev", p1, "--prev", broken)
    assert res.returncode == 0, res.stdout
    assert f"{PLATEAU}: n/a: a --prev ledger has structural errors" in res.stdout
    assert f"DELTA vs {p1}:" in res.stdout


def test_a_missing_prev_path_is_still_a_structural_error(run, ledger, tmp_path):
    cur = window_ledger(ledger, "2026-08-29", 2, name="cur.md")
    res = run(SCRIPT, cur, "--prev", tmp_path / "absent.md")
    assert res.returncode == 2, res.stdout
    assert "cannot read" in res.stdout


def test_no_prev_prints_no_plateau_line_at_all(run, ledger):
    """Without `--prev` there is no delta block, so there is no plateau line."""
    res = run(SCRIPT, window_ledger(ledger, "2026-08-29", 2, name="cur.md"))
    assert PLATEAU not in res.stdout


# --- 0.3.0 the round contract: its two terminal statuses and its backstop ---
#
# Both statuses close a finding on a signature given BEFORE the round, which
# is exactly why neither may close one by its opening words: the tests below
# pin the COMPLETE-literal rule as hard as they pin terminality. Two more
# claims are load-bearing here. `frozen-carried` must NOT block closability —
# that is the whole difference from `superseded-by-rewrite`, and a round
# stopped by its own rule would otherwise have no legitimate exit. And the
# `Stop-rule freeze:` header field has TWO independent writers, so "written
# once, by the first occasion" is enforced rather than left to whoever writes
# second. The last group is the security-lens backstop: the default class of
# a declared security lens is removed in writing or not at all.

OUT_OF_SCOPE = "out-of-scope-by-contract"
FROZEN_CARRIED = "frozen-carried"
FREEZE_FIELD = (
    "- Stop-rule freeze: 2026-08-29 | carried-to: 2026-09-01-120000-object\n"
)


def contract_row(terminal: str, rid: str = "DA-1", verdict: str = "upheld",
                 sev: str = "major") -> str:
    """One 8-cell row whose terminal cell is the value under test."""
    return f"| {rid} | {sev} | claim | {verdict} | crit | fix | x | {terminal} |"


# --- out-of-scope-by-contract ----------------------------------------------


def test_the_complete_contract_literal_is_terminal(run, ledger):
    res = run(SCRIPT, ledger(contract_row(
        f"{OUT_OF_SCOPE} (NG-2, signed 2026-08-29)")))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout


@pytest.mark.parametrize("cell", [
    OUT_OF_SCOPE,
    f"{OUT_OF_SCOPE} (signed 2026-08-29)",
    f"{OUT_OF_SCOPE} (NG-2)",
    f"{OUT_OF_SCOPE} (NG-2, signed)",
    f"{OUT_OF_SCOPE} NG-2 signed 2026-08-29",
])
def test_a_partial_contract_literal_is_not_terminal(run, ledger, cell):
    """A pre-signed disposition closes a row only in full, never in part."""
    res = run(SCRIPT, ledger(contract_row(cell)))
    assert res.returncode == 1, res.stdout
    assert "expected the complete literal" in res.stdout
    assert "non-terminal ids: DA-1" in res.stdout


def test_an_impossible_contract_signature_date_is_not_terminal(run, ledger):
    """`2026-02-30` names no day, so it cannot be an auditable signature."""
    res = run(SCRIPT, ledger(contract_row(
        f"{OUT_OF_SCOPE} (NG-2, signed 2026-02-30)")))
    assert res.returncode == 1, res.stdout
    assert "is not a calendar date" in res.stdout


def test_a_security_pii_row_may_not_leave_on_the_pre_signature(run, ledger):
    """The one class whose BOTH outcomes need the owner's live word."""
    res = run(SCRIPT, ledger(contract_row(
        f"{OUT_OF_SCOPE} (NG-2, signed 2026-08-29)",
        rid="SE-1", verdict="upheld class:security-pii")))
    assert res.returncode == 2, res.stdout
    assert "no live `user-signed <date>`" in res.stdout


def test_a_security_pii_row_leaves_with_its_own_live_signature(run, ledger):
    res = run(SCRIPT, ledger(contract_row(
        f"{OUT_OF_SCOPE} (NG-2, signed 2026-08-29) user-signed 2026-08-30",
        rid="SE-1", verdict="upheld class:security-pii")))
    assert res.returncode == 0, res.stdout


@pytest.mark.parametrize("slug", ["security", "pii", "sec-pii"])
def test_a_synonym_of_the_class_slug_is_not_the_class_mark(run, ledger, slug):
    """ONE literal keys every check: `security-pii` and nothing near it."""
    res = run(SCRIPT, ledger(contract_row(
        f"{OUT_OF_SCOPE} (NG-2, signed 2026-08-29)",
        rid="SE-1", verdict=f"upheld class:{slug}")))
    assert res.returncode == 0, res.stdout


# --- frozen-carried and its single header field ----------------------------


def test_frozen_carried_is_terminal_and_prints_the_carry(run, ledger):
    """The DoD case: two frozen rows of DIFFERENT dates, one header field."""
    rows = "\n".join([
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)",
                     rid="DA-1", sev="blocker"),
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-30)", rid="DA-2"),
    ])
    res = run(SCRIPT, ledger(rows, preamble=FREEZE_FIELD))
    assert res.returncode == 0, res.stdout
    assert "FROZEN CARRIED: 2 rows → 2026-09-01-120000-object" in res.stdout
    assert "ROUND CLOSABLE: zero non-terminal rows." in res.stdout


def test_a_frozen_blocker_is_allowed_where_a_nominated_one_is_not(run, ledger):
    """A blocker's ONE contractual disposition is the freeze, never residue."""
    res = run(SCRIPT, ledger(
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)",
                     sev="blocker"),
        preamble=FREEZE_FIELD))
    assert res.returncode == 0, res.stdout
    assert "categorically non-nominable" not in res.stdout


def test_a_partial_freeze_literal_is_not_terminal(run, ledger):
    res = run(SCRIPT, ledger(contract_row(FROZEN_CARRIED),
                             preamble=FREEZE_FIELD))
    assert res.returncode == 1, res.stdout
    assert "expected the complete literal" in res.stdout


def test_a_frozen_row_without_the_header_field_is_a_structural_error(
        run, ledger):
    """A carry that names no destination is a transfer into nowhere."""
    res = run(SCRIPT, ledger(
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)")))
    assert res.returncode == 2, res.stdout
    assert "a transfer into nowhere" in res.stdout


def test_two_freeze_fields_are_a_structural_error(run, ledger):
    """The collision rule: two writers, one field, written ONCE."""
    res = run(SCRIPT, ledger(
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)"),
        preamble=FREEZE_FIELD
        + "- Stop-rule freeze: 2026-08-30 | carried-to: r-other\n"))
    assert res.returncode == 2, res.stdout
    assert "the header carries 2 `Stop-rule freeze:` fields" in res.stdout
    assert "FROZEN CARRIED" not in res.stdout


@pytest.mark.parametrize("field", [
    "- Stop-rule freeze: 2026-08-29\n",
    "- Stop-rule freeze: carried-to: r-next\n",
    "- Stop-rule freeze: yesterday | carried-to: r-next\n",
    "- Stop-rule freeze: 2026-08-29 | carried-to:\n",
])
def test_a_malformed_freeze_field_is_a_structural_error(run, ledger, field):
    res = run(SCRIPT, ledger(
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)"),
        preamble=field))
    assert res.returncode == 2, res.stdout
    assert "`Stop-rule freeze:`" in res.stdout


def test_an_impossible_freeze_date_in_the_header_is_a_structural_error(
        run, ledger):
    res = run(SCRIPT, ledger(
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)"),
        preamble="- Stop-rule freeze: 2026-02-30 | carried-to: r-next\n"))
    assert res.returncode == 2, res.stdout
    assert "not a calendar date" in res.stdout


def test_carried_to_pending_at_closure_is_a_structural_error(run, ledger):
    res = run(SCRIPT, ledger(
        contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)"),
        preamble="- Stop-rule freeze: 2026-08-29 | carried-to: pending\n"))
    assert res.returncode == 2, res.stdout
    assert "still reads `carried-to: pending`" in res.stdout


def test_carried_to_pending_while_the_round_is_open_is_not_an_error(
        run, ledger):
    """`pending` is refused AT CLOSURE only — mid-round it is the normal state."""
    rows = contract_row(f"{FROZEN_CARRIED} (stop-rule, 2026-08-29)") + "\n" + OPEN
    res = run(SCRIPT, ledger(
        rows, preamble="- Stop-rule freeze: 2026-08-29 | carried-to: pending\n"))
    assert res.returncode == 1, res.stdout
    assert "still reads" not in res.stdout
    assert "ROUND NOT CLOSABLE: 1 open rows." in res.stdout


# --- the security-lens backstop --------------------------------------------


def test_a_security_lens_row_without_the_class_is_a_structural_error(
        run, ledger):
    """The default is the point: silence stops being a way past the gates."""
    res = run(SCRIPT, ledger(
        "| SE-1 | major | claim | upheld | crit | fix | LANDED | "
        "verified-landed |",
        preamble="- Security lens: SE\n"))
    assert res.returncode == 2, res.stdout
    assert "raised by the declared security lens SE" in res.stdout


def test_a_security_lens_row_carrying_the_class_passes(run, ledger):
    res = run(SCRIPT, ledger(
        "| SE-1 | major | claim | upheld class:security-pii | crit | fix | "
        "LANDED | verified-landed |",
        preamble="- Security lens: SE\n"))
    assert res.returncode == 0, res.stdout


def test_the_default_is_removed_in_writing_with_a_reason(run, ledger):
    res = run(SCRIPT, ledger(
        "| SE-1 | major | claim | upheld; declassed:security-pii — the path "
        "is a fixture, no real data | crit | fix | LANDED | verified-landed |",
        preamble="- Security lens: SE\n"))
    assert res.returncode == 0, res.stdout


def test_a_declass_with_an_empty_reason_is_a_structural_error(run, ledger):
    res = run(SCRIPT, ledger(
        "| SE-1 | major | claim | upheld; declassed:security-pii — | crit | "
        "fix | LANDED | verified-landed |",
        preamble="- Security lens: SE\n"))
    assert res.returncode == 2, res.stdout
    assert "with an empty reason" in res.stdout


def test_the_backstop_touches_only_the_declared_lens_prefix(run, ledger):
    """A neighbouring lens's rows are not swept up by the security lens's rule."""
    rows = "\n".join([
        "| SE-1 | major | claim | upheld class:security-pii | crit | fix | "
        "LANDED | verified-landed |",
        CLOSED,
    ])
    res = run(SCRIPT, ledger(rows, preamble="- Security lens: SE\n"))
    assert res.returncode == 0, res.stdout


def test_security_lens_none_arms_no_backstop(run, ledger):
    res = run(SCRIPT, ledger(
        "| SE-1 | major | claim | upheld | crit | fix | LANDED | "
        "verified-landed |",
        preamble="- Security lens: none\n"))
    assert res.returncode == 0, res.stdout


def test_an_unreadable_security_lens_field_is_a_structural_error(run, ledger):
    """A field that arms a gate is never allowed to disarm itself on a typo."""
    res = run(SCRIPT, ledger(CLOSED, preamble="- Security lens: the sec one\n"))
    assert res.returncode == 2, res.stdout
    assert "`Security lens:`" in res.stdout


def test_two_security_lens_fields_are_a_structural_error(run, ledger):
    """The duplicate rule is the SAME rule for every header field.

    `Process prefixes:` refused a second declaration; its neighbour
    `Security lens:` returned the first match and discarded the second with
    no trace, because the two were parsed by two hand-written patterns. Both
    now go through `ledger_md.header_field`, whose rule is exactly one
    occurrence — and both values here are individually well-formed, which is
    the point: the defect was silent acceptance, not a bad value.
    """
    res = run(
        SCRIPT,
        ledger(
            CLOSED,
            preamble="- Security lens: SE\n- Security lens: SF\n",
        ),
    )
    assert res.returncode == 2, res.stdout
    assert "carries 2 `Security lens:` fields" in res.stdout
    assert "never a silent replacement" in res.stdout


def test_a_ledger_declaring_neither_field_prints_neither_report(run, ledger):
    """The compatibility promise of this batch, asserted rather than claimed."""
    res = run(SCRIPT, ledger(CLOSED))
    assert res.returncode == 0, res.stdout
    for absent in ("FROZEN CARRIED", "Stop-rule freeze", "Security lens",
                   "security lens"):
        assert absent not in res.stdout


# --- an empty verdict cell: the state "not adjudicated" --------------------
# A stage-5 layout carries transcribed findings whose verdict cells are still
# blank. The backstop used to refuse it as a structural error, which made the
# recount unusable exactly where it helps most — before adjudication. The
# empty cell is a STATE now; the filled cell that leaves the class out is the
# structural error it always was.

def test_an_empty_verdict_cell_is_a_state_and_not_a_structural_error(
        run, ledger):
    """The fresh skeleton: exit code of an unclosed round, no error, and the
    rows counted by their own line.
    """
    rows = "\n".join([
        "| SE-1 | major | claim |  |  | fix | x |  |",
        "| SE-2 | minor | claim |  |  | fix | x |  |",
    ])
    res = run(SCRIPT, ledger(rows, preamble=SECURITY_HEADER))
    assert res.returncode == 1, res.stdout
    assert "STRUCTURAL ERRORS" not in res.stdout
    assert "not adjudicated: 2 rows" in res.stdout
    assert "ROUND NOT CLOSABLE: 2 open rows." in res.stdout


def test_a_filled_verdict_cell_without_the_class_stays_a_structural_error(
        run, ledger):
    """The relaxation is EXACTLY the empty case.

    A verdict that was written and left the class out is a judgment made,
    not a judgment pending: same exit code and same diagnostic as before,
    and the row is not reported as unadjudicated.
    """
    row = ("| SE-1 | major | claim | upheld, the path is a fixture | crit | "
           "fix | LANDED | verified-landed |")
    res = run(SCRIPT, ledger(row, preamble=SECURITY_HEADER))
    assert res.returncode == 2, res.stdout
    assert "raised by the declared security lens SE" in res.stdout
    assert "not adjudicated" not in res.stdout


def test_a_ledger_with_every_verdict_filled_prints_no_such_line(run, ledger):
    """Compatibility: the new line appears only where an empty cell does."""
    res = run(SCRIPT, ledger(CLOSED))
    assert res.returncode == 0, res.stdout
    assert "not adjudicated" not in res.stdout


# --- the per-lens sustained rate and the shelf share beside it -------------
#
# The between-rounds sustained-rate metric, and the `shelf:` tag beside it.
# Three properties are pinned hard, because each is a way the metric could
# lie: it is printed ONLY with `--prev` (a single-ledger recount is byte for
# byte what it was); its lens prefixes come from the header's machine-form
# `Lenses:` lines and never from the id prefixes in the table; and a figure
# that cannot be computed is `n/a: <reason>`, never `0` — an absent `shelf:`
# tag means the tag was never set, which is not a share of zero. The rate
# never fires alone either: the printed warning says so in words, because
# the pairing is the rule itself, not a detail beside it.

SUSTAINED = "per-lens sustained rate"
SHELF_BASELINE = "BELOW THE 92% BASELINE"


def refuted(rid: str, verdict: str = "verdict") -> str:
    """One terminal, REFUTED row — the shelf tag's only legitimate home."""
    return (f"| {rid} | minor | claim | {verdict} | — | fix | x | "
            f"refuted-with-reason |")


def test_no_prev_prints_no_sustained_rate_at_all(run, ledger):
    """The compatibility promise: the block belongs to `--prev` and nowhere else."""
    res = run(SCRIPT, ledger(raised("AA-1"), preamble=lens_field("AA")))
    assert res.returncode == 0, res.stdout
    assert SUSTAINED not in res.stdout
    assert "shelf" not in res.stdout


def test_prev_prints_the_rate_with_the_shelf_share_beside_it(run, ledger):
    """The DoD case: two rows carry `shelf:`, and the share stands beside the rate."""
    rows = "\n".join([
        raised("AA-1"),
        refuted("AA-2", "refuted; shelf:ng-2"),
        refuted("AA-3", "refuted; shelf:ng-2"),
        refuted("AA-4"),
    ])
    cur = ledger(rows, preamble=lens_field("AA"), name="cur.md")
    prev = ledger(raised("AA-9"), preamble=lens_field("AA"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert "AA: sustained 2/5 = 40.0% | shelf 2/3 = 66.7%" in res.stdout


def test_a_window_with_no_shelf_tag_says_n_a_and_never_zero(run, ledger):
    """The rule of the missing number, asserted where it is easiest to break."""
    rows = "\n".join([raised("AA-1"), refuted("AA-2")])
    cur = ledger(rows, preamble=lens_field("AA"), name="cur.md")
    prev = ledger(raised("AA-9"), preamble=lens_field("AA"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert "shelf n/a: no `shelf:` tag anywhere in the window" in res.stdout
    assert "shelf 0/" not in res.stdout


def test_a_lens_with_no_refutation_has_no_shelf_denominator(run, ledger):
    rows = "\n".join([raised("AA-1"), refuted("BB-1", "refuted; shelf:ng-2")])
    cur = ledger(rows, preamble=lens_field("AA", "BB"), name="cur.md")
    prev = ledger(raised("AA-9"), preamble=lens_field("AA", "BB"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert "AA: sustained 2/2 = 100.0% | shelf n/a: no refutation" in res.stdout


def test_a_declared_lens_that_raised_nothing_is_n_a_not_zero(run, ledger):
    cur = ledger(raised("AA-1"), preamble=lens_field("AA", "ZZ"), name="cur.md")
    prev = ledger(raised("AA-9"), preamble=lens_field("AA", "ZZ"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert "ZZ: n/a: no rows raised under this prefix in the window" in res.stdout


def test_the_below_baseline_warning_names_the_paired_condition(run, ledger):
    """The tightening is never assigned on the sustained rate alone."""
    rows = "\n".join([raised("AA-1"), refuted("AA-2"), refuted("AA-3")])
    cur = ledger(rows, preamble=lens_field("AA"), name="cur.md")
    prev = ledger(refuted("AA-9"), preamble=lens_field("AA"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert SHELF_BASELINE in res.stdout
    assert "TIGHTENS this lens's framing rather than dropping the lens" in res.stdout
    assert "the rate alone is never the trigger" in res.stdout


def test_a_lens_at_or_above_the_baseline_gets_no_warning(run, ledger):
    cur = ledger(raised("AA-1"), preamble=lens_field("AA"), name="cur.md")
    prev = ledger(raised("AA-9"), preamble=lens_field("AA"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert "AA: sustained 2/2 = 100.0%" in res.stdout
    assert SHELF_BASELINE not in res.stdout


def test_a_header_declaring_no_lenses_refuses_to_guess_the_prefixes(run, ledger):
    """The same single source as `k`: never the id prefixes of the table."""
    cur = ledger(raised("AA-1"), name="cur.md")
    prev = ledger(raised("AA-9"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert f"{SUSTAINED}: n/a: no machine-form `Lenses:` lines" in res.stdout
    assert "AA: sustained" not in res.stdout


def test_a_seven_cell_ledger_in_the_window_stops_the_split(run, ledger):
    """Upheld/refuted needs the criterion column, exactly as the split line does."""
    cur = ledger(raised("AA-1"), preamble=lens_field("AA"), name="cur.md")
    prev = ledger("| AA-9 | major | claim | verdict | fix | LANDED | "
                  "verified-landed |",
                  header=HEADER_7, preamble=lens_field("AA"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 0, res.stdout
    assert f"{SUSTAINED}: n/a: a v1 (7-cell) ledger in the window" in res.stdout


def test_the_rate_never_reaches_an_exit_code(run, ledger):
    """Report-only, like the two metrics above it: an open row still rules."""
    rows = "\n".join([refuted("AA-1"), OPEN])
    cur = ledger(rows, preamble=lens_field("AA"), name="cur.md")
    prev = ledger(refuted("AA-9"), preamble=lens_field("AA"), name="prev.md")
    res = run(SCRIPT, cur, "--prev", prev)
    assert res.returncode == 1, res.stdout
    assert SHELF_BASELINE in res.stdout
    assert "ROUND NOT CLOSABLE: 1 open rows." in res.stdout


# --- the `shelf:` tag's own boundary ---------------------------------------


def test_a_malformed_shelf_slug_is_a_structural_error(run, ledger):
    """Fail-closed, exactly like `class:`: a guessed boundary is no boundary."""
    res = run(SCRIPT, ledger(refuted("AA-1", "refuted; shelf:NG2")))
    assert res.returncode == 2, res.stdout
    assert "carries a `shelf:` tag whose slug is not 1-32 characters" in res.stdout


@pytest.mark.parametrize("verdict", [
    "refuted; the shelf: it was pre-signed",
    "refuted; shelf:",
])
def test_shelf_followed_by_whitespace_or_the_cell_end_is_prose(run, ledger, verdict):
    """The compatibility exception the `class:` tag already carries."""
    res = run(SCRIPT, ledger(refuted("AA-1", verdict)))
    assert res.returncode == 0, res.stdout
    assert "shelf:" not in res.stdout


def test_an_over_long_shelf_slug_is_refused(run, ledger):
    res = run(SCRIPT, ledger(refuted("AA-1", "refuted; shelf:" + "a" * 33)))
    assert res.returncode == 2, res.stdout
    assert "carries a `shelf:` tag" in res.stdout


def test_the_shelf_tag_changes_no_count_on_a_single_ledger_recount(run, ledger):
    """The tag is read by ONE report, and that report lives under `--prev`."""
    plain = run(SCRIPT, ledger(refuted("AA-1"), name="plain.md"))
    tagged = run(SCRIPT, ledger(refuted("AA-1", "verdict; shelf:ng-2"),
                                name="tagged.md"))
    assert plain.returncode == tagged.returncode == 0
    assert plain.stdout == tagged.stdout


# --- 0.3.0 zones: the v3 row, its zone cell and the Z3 closing act ----------
# The zone column is inserted THIRD so that every cell the script addresses
# from the END of the row keeps its address. What these tests pin is that
# claim (`criterion` read as the fourth cell from the end at width 8 and 9
# alike), the one rule the zone cell feeds (`logged-no-action` at Z3 only),
# the third bucket's own overdue report, and the header's schema declaration.
# `tests/run-regression.sh` c63-c72 covers the same ground end to end; these
# add the line formats and the edges the shell suite does not reach.

V3_CLOSED = ("| DA-1 | major | Z2 | claim | verdict | crit | fix | LANDED | "
             "verified-landed |")
V3_LOGGED = ("| DA-2 | minor | Z3 | claim | logged, no action | crit | fix | "
             "x | logged-no-action |")


def test_a_nine_cell_ledger_recounts(run, ledger):
    res = run(SCRIPT, ledger(V3_CLOSED, header=HEADER_9))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout
    assert "ROUND CLOSABLE" in res.stdout


def test_the_criterion_is_the_fourth_cell_from_the_end_at_width_nine(
        run, ledger):
    """The whole point of inserting `zone` third.

    A hard `cells[4]` would read the VERDICT prose here — non-empty, so the
    consistency check would pass silently and never fire. Reading from the
    end finds the empty criterion and fails closed.
    """
    row = ("| DA-1 | major | Z2 | claim | upheld — the wording is ambiguous "
           "|  | fix | LANDED | verified-landed |")
    res = run(SCRIPT, ledger(row, header=HEADER_9))
    assert res.returncode == 2, res.stdout
    assert "readiness-criterion cell is ''" in res.stdout


def test_the_same_row_with_a_criterion_passes(run, ledger):
    """The pair of the test above: only the criterion cell differs."""
    row = ("| DA-1 | major | Z2 | claim | upheld — the wording is ambiguous "
           "| grep -c TODO = 0 | fix | LANDED | verified-landed |")
    res = run(SCRIPT, ledger(row, header=HEADER_9))
    assert res.returncode == 0, res.stdout


def test_the_upheld_split_is_computed_for_a_v3_ledger(run, ledger):
    """A v3 row HAS a criterion cell, so the split is not `n/a` for it."""
    res = run(SCRIPT, ledger(V3_CLOSED + "\n" + V3_LOGGED, header=HEADER_9))
    assert res.returncode == 0, res.stdout
    assert "upheld/refuted: 2 upheld, 0 refuted" in res.stdout


def test_logged_no_action_is_terminal_at_zone_z3(run, ledger):
    res = run(SCRIPT, ledger(V3_LOGGED, header=HEADER_9))
    assert res.returncode == 0, res.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in res.stdout


@pytest.mark.parametrize("zone", ["Z1", "Z2", "", "z3 (probably)"])
def test_logged_no_action_outside_z3_is_structural(run, ledger, zone):
    res = run(SCRIPT, ledger(V3_LOGGED.replace("| Z3 |", f"| {zone} |"),
                             header=HEADER_9))
    assert res.returncode == 2, res.stdout
    assert "the status is accepted at zone Z3 alone" in res.stdout


def test_a_lower_case_zone_still_names_the_zone(run, ledger):
    """The literal is matched case-insensitively; nothing else is normalized."""
    res = run(SCRIPT, ledger(V3_LOGGED.replace("| Z3 |", "| z3 |"),
                             header=HEADER_9))
    assert res.returncode == 0, res.stdout


@pytest.mark.parametrize(("header", "row"), [
    (HEADER_7, "| DA-1 | minor | c | v | f | x | logged-no-action |"),
    (HEADER_8, "| DA-1 | minor | c | v | crit | f | x | logged-no-action |"),
])
def test_logged_no_action_in_an_older_schema_is_structural(
        run, ledger, header, row):
    """No `zone` cell exists there, so the condition has nothing to read.

    Silence would be worse than an error: a mass closure route accepted on
    no condition at all is exactly what the zone was introduced to prevent.
    """
    res = run(SCRIPT, ledger(row, header=header))
    assert res.returncode == 2, res.stdout
    assert "the status exists only in the 9-cell (v3) schema" in res.stdout


def test_logged_no_action_on_a_security_row_needs_a_live_signature(
        run, ledger):
    """B5.3's exception, word for word, on the other pre-signed route."""
    row = ("| SE-1 | minor | Z3 | claim | upheld class:security-pii | crit | "
           "fix | x | logged-no-action |")
    res = run(SCRIPT, ledger(row, header=HEADER_9))
    assert res.returncode == 2, res.stdout
    assert "never closed inside a batch act" in res.stdout


def test_a_signed_security_row_may_be_logged(run, ledger):
    row = ("| SE-1 | minor | Z3 | claim | upheld class:security-pii | crit | "
           "fix | x | logged-no-action user-signed 2026-08-29 |")
    res = run(SCRIPT, ledger(row, header=HEADER_9))
    assert res.returncode == 0, res.stdout


def test_a_logged_row_is_not_reported_as_an_unidentifiable_batch(run, ledger):
    """It was never handed to a fixer, exactly like the waits before it."""
    res = run(SCRIPT, ledger(V3_LOGGED.replace("| fix |", "|  |"),
                             header=HEADER_9))
    assert res.returncode == 0, res.stdout
    assert "batch not identifiable" not in res.stdout


# --- the wait, its date and the 30-day limit -------------------------------

def wait_row(listed: str = "2026-08-29") -> str:
    return ("| DA-2 | minor | Z3 | claim | logged | crit | fix | x | "
            f"awaiting-logged-no-action (listed {listed}) |")


def test_the_wait_carries_its_listed_date(run, ledger):
    from datetime import UTC, datetime
    today = datetime.now(UTC).date().isoformat()
    res = run(SCRIPT, ledger(V3_CLOSED + "\n" + wait_row(today),
                             header=HEADER_9))
    assert res.returncode == 1, res.stdout
    assert "awaiting-logged-no-action ids: DA-2" in res.stdout
    assert "ROUND AWAITING Z3 CLOSURE: 1 rows await the owner's act." in res.stdout
    assert "Z3 CLOSURE OVERDUE" not in res.stdout


def test_a_wait_past_thirty_days_is_reported_overdue(run, ledger):
    res = run(SCRIPT, ledger(V3_CLOSED + "\n" + wait_row("2020-01-01"),
                             header=HEADER_9))
    assert res.returncode == 1, res.stdout
    assert "Z3 CLOSURE OVERDUE: DA-2 (listed 2020-01-01" in res.stdout
    assert "A permanent wait is banned." in res.stdout
    assert "ROUND AWAITING Z3 CLOSURE" in res.stdout


@pytest.mark.parametrize("cell", [
    "awaiting-logged-no-action",
    "awaiting-logged-no-action (listed 2026-02-30)",
])
def test_an_unageable_wait_is_still_the_wait_but_is_reported(run, ledger, cell):
    """The owner's act drains the queue whether or not the date reads.

    Demoting the row to an ordinary open one would change what the 0.3.0
    B1 batch shipped; saying nothing would hide a wait nobody can chase.
    """
    row = ("| DA-2 | minor | Z3 | claim | logged | crit | fix | x | "
           f"{cell} |")
    res = run(SCRIPT, ledger(V3_CLOSED + "\n" + row, header=HEADER_9))
    assert res.returncode == 1, res.stdout
    assert "awaiting-logged-no-action ids: DA-2" in res.stdout
    assert "ROUND AWAITING Z3 CLOSURE" in res.stdout
    assert "CONSISTENCY: DA-2" in res.stdout
    assert "Z3 CLOSURE OVERDUE" not in res.stdout


# --- the header's row-schema declaration -----------------------------------

V1_CLOSED = "| DA-1 | major | claim | verdict | fix | LANDED | verified-landed |"


@pytest.mark.parametrize(("declared", "header", "row"), [
    ("v1", HEADER_7, V1_CLOSED),
    ("v2", HEADER_8, CLOSED),
    ("v3", HEADER_9, V3_CLOSED),
    ("V3", HEADER_9, V3_CLOSED),
])
def test_a_declaration_that_matches_the_table_changes_nothing(
        run, ledger, declared, header, row):
    res = run(SCRIPT, ledger(row, header=header,
                             preamble=f"- Row schema: {declared}\n"))
    assert res.returncode == 0, res.stdout


def test_a_declaration_contradicting_the_table_is_structural(run, ledger):
    res = run(SCRIPT, ledger(V3_CLOSED, header=HEADER_9,
                             preamble="- Row schema: v2\n"))
    assert res.returncode == 2, res.stdout
    assert "declares 8 cells but the findings header has 9" in res.stdout


def test_an_unknown_schema_name_is_structural(run, ledger):
    res = run(SCRIPT, ledger(V3_CLOSED, header=HEADER_9,
                             preamble="- Row schema: latest\n"))
    assert res.returncode == 2, res.stdout
    assert "is not one of v1/v2/v3" in res.stdout


def test_two_schema_declarations_are_structural(run, ledger):
    res = run(SCRIPT, ledger(V3_CLOSED, header=HEADER_9,
                             preamble="- Row schema: v3\n- Row schema: v3\n"))
    assert res.returncode == 2, res.stdout
    assert "`Row schema:` header fields" in res.stdout


def test_a_ledger_without_the_field_recounts_as_before(run, ledger):
    """Absence is silence: the width still comes from the table's header."""
    without = run(SCRIPT, ledger(CLOSED, name="without.md"))
    withit = run(SCRIPT, ledger(CLOSED, preamble="- Row schema: v2\n",
                                name="with.md"))
    assert without.returncode == withit.returncode == 0
    assert without.stdout == withit.stdout

# --- the class-kill gate's verified cell (R-T9(b)) ---------------------------
#
# `gates/<K-id>.sh` is the file form of a class-kill row, and the outcome of
# running it is written into that row's `verified` cell. The literal is
# AGREED with this script's contract rather than invented, and the case
# below asserts the collision that decided it.

GATE_ROW = (
    "| K-1 | major | claim | upheld class-kill:stale-anchor | crit | B3 "
    "| {verified} | verified-landed |"
)


def test_the_gate_literal_fits_the_contract_and_a_bare_gate_ok_does_not(
        run, ledger):
    """`LANDED — gate K-1.sh OK` closes the gate's row; `GATE OK` does not.

    A `verified-landed` row wants the substring LANDED in its `verified`
    cell, so a bare `GATE OK` would leave the gate's own row non-terminal
    and the round unclosable on the very thing that killed the class. Both
    forms of the convention — the passing one and `NOT LANDED — gate
    K-1.sh FAIL` — are read by this contract as it stands, which is what
    the collision below shows.
    """
    ok = run(SCRIPT, ledger(GATE_ROW.format(verified="LANDED — gate K-1.sh OK")))
    assert ok.returncode == 0, ok.stdout
    assert "rows: 1 | terminal: 1 | non-terminal: 0" in ok.stdout

    bare = run(SCRIPT, ledger(GATE_ROW.format(verified="GATE OK")))
    assert bare.returncode == 1, bare.stdout
    assert "verified cell carries no LANDED verdict" in bare.stdout
    assert "non-terminal ids: K-1" in bare.stdout

    failed = run(
        SCRIPT, ledger(GATE_ROW.format(verified="NOT LANDED — gate K-1.sh FAIL")))
    assert failed.returncode == 1, failed.stdout
    assert "non-terminal ids: K-1" in failed.stdout


# --- the reading contract: `read_ledger` -----------------------------------
#
# The one place this file imports code instead of running the script: the
# container `read_ledger` returns is an internal contract that no subprocess
# run can see, so it is pinned in process. Everything else stays black-box.
# `read_ledger` lives in `ledger_model.py`, the module beside the script.


@pytest.fixture(scope="module")
def ledger_model(scripts_dir):
    """The reading module, imported from the scripts directory itself.

    Its own imports resolve beside it, as they do under the script's path
    insert, so the directory is on `sys.path` for the import only.
    """
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "ledger_model_under_test",
            scripts_dir / "ledger_model.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["ledger_model_under_test"] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(scripts_dir))
    return module


def read_lines(path) -> list[str]:
    """Hand back a file's lines the way the script reads them."""
    with path.open(encoding="utf-8") as fh:
        return fh.readlines()


def test_read_ledger_collects_the_header_in_one_pass(ledger_model, tmp_path):
    """One call yields the rows, the declared lenses and no errors."""
    path = write_ledger(tmp_path / "ledger.md",
                        "\n".join([raised("AA-1"), raised("BB-1")]),
                        preamble=lens_field("L", "T"))
    ledger, errors = ledger_model.read_ledger(
        read_lines(path), ledger_path=str(path), register_arg=None)
    assert len(ledger.rows) == 2
    assert ledger.lens_prefixes == ["L", "T"]
    assert errors == []


def test_read_ledger_reports_a_row_of_the_wrong_width(ledger_model, tmp_path):
    """An 8-cell row under a 9-cell header is an error, never silence."""
    path = write_ledger(tmp_path / "ledger.md", raised("AA-1"), header=HEADER_9,
                        preamble="- Row schema: v3\n" + lens_field("L", "T"))
    _, errors = ledger_model.read_ledger(
        read_lines(path), ledger_path=str(path), register_arg=None)
    assert errors
    assert "malformed row (8 cells, need 9" in errors[0]
