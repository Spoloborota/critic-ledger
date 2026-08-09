"""Characterization tests for recount.py.

`tests/run-regression.sh` already pins 28 end-to-end ledger fixtures (row
schemas, terminal literals, the readiness-criterion rules, the frozen
marker, one delta case). The tests here are deliberately COMPLEMENTARY:
argument handling, IO failure modes, the printed line formats, the curve,
the four delta buckets and a few literal-matching edges the shell suite
does not exercise.

Exit codes: 0 = closable, 1 = open rows remain, 2 = structural/usage error,
3 = the ledger is frozen.
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


def test_missing_ledger_file_raises_instead_of_exiting_two(run, tmp_path):
    """Current behavior: an unreadable ledger path is an uncaught exception.

    The traceback exits 1 — the same code the script uses for "open rows
    remain" — rather than the documented 2 for an unusable input.
    """
    res = run(SCRIPT, tmp_path / "absent.md")
    assert res.returncode == 1
    assert "FileNotFoundError" in res.stderr


def test_prev_without_a_value_raises(run, ledger):
    """Current behavior: `--prev` as the last token is an uncaught IndexError."""
    res = run(SCRIPT, ledger(CLOSED), "--prev")
    assert res.returncode == 1
    assert "IndexError" in res.stderr


def test_missing_prev_file_raises(run, ledger, tmp_path):
    res = run(SCRIPT, ledger(CLOSED), "--prev", tmp_path / "absent.md")
    assert res.returncode == 1
    assert "FileNotFoundError" in res.stderr


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


def test_signature_date_is_not_calendar_checked(run, ledger):
    """Current behavior: the date is a shape (\\d{4}-\\d{2}-\\d{2}), not a date."""
    row = ("| DA-1 | minor | c | v | keep as is | f | x | accepted-residue "
           "user-signed 9999-99-99 |")
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
