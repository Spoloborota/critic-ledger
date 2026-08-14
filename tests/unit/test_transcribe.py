"""Characterization tests for transcribe.py.

The script turns critic-report finding headers into eight-cell ledger rows,
either printed (`--stdout`) or inserted into a ledger right after the
separator of its first findings table. Exit codes: 0 = rows produced (help
is 0 too), 2 = structural or usage error and nothing was written.
"""

from __future__ import annotations

import pytest

from conftest import FENCE, HEADER_8

SCRIPT = "transcribe.py"

TWO_FINDINGS = ("# Findings report\n"
                "\n"
                "GA-1 | major | first claim\n"
                "GA-2 | minor | second claim\n")

LEDGER_ROW = "| EX-1 | minor | existing | v | c | f | LANDED | verified-landed |"


def read(path):
    return path.read_text(encoding="utf-8")


# --- printing mode ---------------------------------------------------------

def test_stdout_mode_prints_eight_cell_rows(run, report):
    path = report(TWO_FINDINGS)
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "| GA-1 | major | first claim |  |  |  |  |  |\n"
        "| GA-2 | minor | second claim |  |  |  |  |  |\n"
    )


def test_stdout_mode_sends_the_summary_to_stderr(run, report):
    path = report(TWO_FINDINGS)
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stderr == (f"transcribed 2 findings\n"
                          f"  {path}: 2 — GA-1, GA-2\n")


def test_severity_literal_is_copied_as_written(run, report):
    res = run(SCRIPT, report("GA-1 | BLOCKER | shouting claim\n"), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "| GA-1 | BLOCKER | shouting claim |  |  |  |  |  |\n"


def test_pipe_inside_a_claim_is_escaped(run, report):
    res = run(SCRIPT, report("GA-1 | major | a | b\n"), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "| GA-1 | major | a \\| b |  |  |  |  |  |\n"


@pytest.mark.parametrize("line", [
    "**GA-1 | major | wrapped claim**",
    "__GA-1 | major | wrapped claim__",
    "## GA-1 | major | wrapped claim",
    "> GA-1 | major | wrapped claim",
    "   GA-1 | major | wrapped claim",
    ">  **GA-1 | major | wrapped claim**",
])
def test_tolerated_wrappers_are_stripped(run, report, line):
    res = run(SCRIPT, report(line + "\n"), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "| GA-1 | major | wrapped claim |  |  |  |  |  |\n"


def test_dash_separated_header_is_accepted(run, report):
    res = run(SCRIPT, report("GB-1 — major — dash separated claim\n"), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "| GB-1 | major | dash separated claim |  |  |  |  |  |\n"


def test_reports_keep_argv_order_and_file_order(run, report):
    first = report("GA-1 | major | one\nGA-2 | major | two\n", name="a.md")
    second = report("GB-1 | minor | three\n", name="b.md")
    res = run(SCRIPT, second, first, "--stdout")
    assert res.returncode == 0, res.stderr
    assert [line.split("|")[1].strip() for line in res.stdout.splitlines()] == [
        "GB-1", "GA-1", "GA-2"]
    assert f"  {second}: 1 — GB-1\n" in res.stderr
    assert f"  {first}: 2 — GA-1, GA-2\n" in res.stderr


# --- fences ----------------------------------------------------------------

def test_quoted_rows_inside_a_fence_are_not_findings(run, report):
    text = (f"# Report\n\nGA-1 | major | real finding\n\n"
            f"{FENCE}\nGB-9 | major | quoted from another lens\n{FENCE}\n")
    res = run(SCRIPT, report(text), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "| GA-1 | major | real finding |  |  |  |  |  |\n"


def test_a_fence_wrapping_the_whole_report_is_unwrapped(run, report):
    text = (f"salvaged verbatim:\n\n{FENCE}\n"
            f"GA-1 | major | first\nGA-2 | major | second\n{FENCE}\n")
    res = run(SCRIPT, report(text), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "| GA-1 | major | first |  |  |  |  |  |\n"
        "| GA-2 | major | second |  |  |  |  |  |\n"
    )


def test_a_fence_holding_one_finding_stays_a_quote(run, report):
    text = (f"salvaged verbatim:\n\n{FENCE}\nGA-1 | major | only one\n{FENCE}\n")
    res = run(SCRIPT, report(text), "--stdout")
    assert res.returncode == 2, res.stdout
    assert "no findings recognized in:" in res.stdout


# --- prose that must not abort a run ---------------------------------------

@pytest.mark.parametrize("line", [
    "GB-1 — discussed above, high confidence.",
    "GB-1 – covered by the previous paragraph.",
])
def test_dash_cross_reference_is_prose_not_a_finding(run, report, line):
    res = run(SCRIPT, report(line + "\n"), "--stdout")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("no findings recognized in:")


def test_report_without_any_finding(run, report):
    res = run(SCRIPT, report("# Report\n\nNothing to raise.\n"), "--stdout")
    assert res.returncode == 2, res.stdout
    assert "no findings recognized in:" in res.stdout


# --- structural errors -----------------------------------------------------

def test_unknown_severity_on_a_pipe_line_is_structural(run, report):
    path = report("GA-1 | critical | claim\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("STRUCTURAL ERRORS — nothing was written:")
    assert (f"  {path}:1: looks like a finding header but does not parse "
            f"(severity not one of blocker/major/minor, mixed separators, or "
            f"empty claim): GA-1 | critical | claim" in res.stdout)


def test_mixed_separators_are_structural(run, report):
    path = report("GA-1 — major | claim\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert f"{path}:1: looks like a finding header but does not parse" in res.stdout


def test_empty_claim_is_structural(run, report):
    path = report("GA-1 | major |\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert f"{path}:1: looks like a finding header but does not parse" in res.stdout


def test_duplicate_id_across_reports_is_structural(run, report):
    first = report("GA-1 | major | one\n", name="a.md")
    second = report("GA-1 | minor | again\n", name="b.md")
    res = run(SCRIPT, first, second, "--stdout")
    assert res.returncode == 2, res.stdout
    assert (f"{second}:1: DUPLICATE FINDING ID GA-1 (first seen at {first}:1)"
            in res.stdout)


def test_unreadable_report(run, tmp_path):
    missing = tmp_path / "absent.md"
    res = run(SCRIPT, missing, "--stdout")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith(f"cannot read {missing}: ")


# --- ledger mode -----------------------------------------------------------

def test_rows_are_inserted_after_the_separator(run, report, ledger):
    target = ledger(LEDGER_ROW)
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", target)
    assert res.returncode == 0, res.stderr
    assert read(target).splitlines() == [
        "| id | sev | claim | verdict | criterion | fix | verified | terminal |",
        "|---|---|---|---|---|---|---|---|",
        "| GA-1 | major | first claim |  |  |  |  |  |",
        "| GA-2 | minor | second claim |  |  |  |  |  |",
        LEDGER_ROW,
    ]


def test_ledger_mode_reports_the_insertion_point_on_stdout(run, report, ledger):
    target = ledger(LEDGER_ROW)
    path = report(TWO_FINDINGS)
    res = run(SCRIPT, path, "--ledger", target)
    assert res.returncode == 0, res.stderr
    assert res.stdout == (f"transcribed 2 findings into {target} after line 2\n"
                          f"  {path}: 2 — GA-1, GA-2\n")
    assert res.stderr == ""


def test_the_first_findings_table_wins(run, report, ledger):
    target = ledger(LEDGER_ROW, suffix="\n## Appendix\n\n" + HEADER_8
                    + "| DX-9 | minor | inherited | v | c | f | x | open |\n")
    res = run(SCRIPT, report("GA-1 | major | claim\n"), "--ledger", target)
    assert res.returncode == 0, res.stderr
    body = read(target).splitlines()
    assert body[2] == "| GA-1 | major | claim |  |  |  |  |  |"
    assert body[3] == LEDGER_ROW


def test_no_temporary_file_is_left_behind(run, report, ledger, tmp_path):
    target = ledger(LEDGER_ROW)
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", target)
    assert res.returncode == 0, res.stderr
    assert not (tmp_path / (target.name + ".transcribe.tmp")).exists()


def test_id_already_present_in_the_ledger_is_refused(run, report, ledger):
    target = ledger("| GA-1 | minor | already there | v | c | f | x | open |")
    before = read(target)
    path = report("GA-1 | major | claim\n")
    res = run(SCRIPT, path, "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert (f"{path}:1: id GA-1 is ALREADY a row of {target} — refusing to "
            f"transcribe it twice" in res.stdout)
    assert read(target) == before


def test_ledger_without_a_findings_table_is_refused(run, report, tmp_path):
    target = tmp_path / "ledger.md"
    target.write_text("# Ledger\n\nNo table here.\n", encoding="utf-8")
    before = read(target)
    res = run(SCRIPT, report("GA-1 | major | claim\n"), "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert (f"{target}: no findings table found (no header row whose first "
            f"cell is `id`) — wrong file or broken table?" in res.stdout)
    assert read(target) == before


def test_header_without_a_separator_row_is_refused(run, report, tmp_path):
    target = tmp_path / "ledger.md"
    target.write_text(
        "| id | sev | claim | verdict | criterion | fix | verified | terminal |\n"
        "| DA-1 | major | c | v | crit | f | LANDED | verified-landed |\n",
        encoding="utf-8")
    res = run(SCRIPT, report("GA-1 | major | claim\n"), "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert (f"{target}: line 2: the findings header at line 1 is not followed "
            f"by a separator row — refusing to guess where rows go" in res.stdout)


def test_unreadable_ledger(run, report, tmp_path):
    missing = tmp_path / "absent-ledger.md"
    res = run(SCRIPT, report("GA-1 | major | claim\n"), "--ledger", missing)
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith(f"cannot read {missing}: ")


def test_ledger_is_untouched_when_a_report_is_broken(run, report, ledger):
    target = ledger(LEDGER_ROW)
    before = read(target)
    res = run(SCRIPT, report("GA-1 | critical | claim\n"), "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert read(target) == before


# --- usage -----------------------------------------------------------------

def test_no_output_mode_is_a_usage_error(run, report):
    res = run(SCRIPT, report(TWO_FINDINGS))
    assert res.returncode == 2, res.stdout
    assert "Usage:  transcribe.py" in res.stdout


def test_both_output_modes_is_a_usage_error(run, report, ledger):
    res = run(SCRIPT, report(TWO_FINDINGS), "--stdout", "--ledger",
              ledger(LEDGER_ROW))
    assert res.returncode == 2, res.stdout
    assert "Usage:  transcribe.py" in res.stdout


def test_no_reports_is_a_usage_error(run):
    res = run(SCRIPT, "--stdout")
    assert res.returncode == 2, res.stdout
    assert "Usage:  transcribe.py" in res.stdout


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_flags_print_usage_and_exit_zero(run, report, flag):
    """Help wins over the report argument and over the output-mode check."""
    res = run(SCRIPT, report(TWO_FINDINGS), flag)
    assert res.returncode == 0, res.stdout
    assert "Usage:  transcribe.py" in res.stdout
    assert "| GA-1 |" not in res.stdout


def test_ledger_flag_without_a_value(run, report):
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("--ledger needs a path")
