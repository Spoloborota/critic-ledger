"""Characterization tests for transcribe.py.

The script turns critic-report finding headers into ledger rows, either
printed (`--stdout`, as nine-cell rows) or inserted into a ledger right
after the separator of its first findings table (with that ledger's own
width). Exit codes: 0 = rows produced (help is 0 too), 2 = structural or
usage error and nothing was written.
"""

from __future__ import annotations

import re
import subprocess
import sys

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

def test_stdout_mode_prints_nine_cell_rows(run, report):
    path = report(TWO_FINDINGS)
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "| GA-1 | major | · | first claim |  |  |  |  |  |\n"
        "| GA-2 | minor | · | second claim |  |  |  |  |  |\n"
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
    assert res.stdout == "| GA-1 | BLOCKER | · | shouting claim |  |  |  |  |  |\n"


def test_pipe_inside_a_claim_is_escaped(run, report):
    res = run(SCRIPT, report("GA-1 | major | a | b\n"), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "| GA-1 | major | · | a \\| b |  |  |  |  |  |\n"


def test_a_pipe_in_a_non_claim_cell_is_escaped_too(scripts_dir):
    """Escaping is a property of the emitted ROW, not of one field.

    The claim was the only cell escaped, so a pipe reaching any other
    copied cell would split the row and shift every cell after it — a
    nine-cell row read as eleven, silently. `row()` is exercised directly
    because the parser cannot produce such a cell today: the invariant
    under test is that the EMITTER holds whatever the parser hands it,
    which is what stops a later parser change from re-opening the hole.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "transcribe_under_test", scripts_dir / SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    finding = {"id": "GA-1", "sev": "ma|jor", "claim": "a | b",
               "file": "r.md", "line": 1}
    emitted = mod.row(finding)
    assert emitted == "| GA-1 | ma\\|jor | · | a \\| b |  |  |  |  |  |"
    # The column count is what the escaping protects: unescaped, the two
    # pipes would make this row read as eleven cells instead of nine.
    assert len(re.findall(r"(?<!\\)\|", emitted)) - 1 == 9


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
    assert res.stdout == "| GA-1 | major | · | wrapped claim |  |  |  |  |  |\n"


def test_dash_separated_header_is_accepted(run, report):
    res = run(SCRIPT, report("GB-1 — major — dash separated claim\n"), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "| GB-1 | major | · | dash separated claim |  |  |  |  |  |\n"


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
    assert res.stdout == "| GA-1 | major | · | real finding |  |  |  |  |  |\n"


def test_a_fence_wrapping_the_whole_report_is_unwrapped(run, report):
    text = (f"salvaged verbatim:\n\n{FENCE}\n"
            f"GA-1 | major | first\nGA-2 | major | second\n{FENCE}\n")
    res = run(SCRIPT, report(text), "--stdout")
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "| GA-1 | major | · | first |  |  |  |  |  |\n"
        "| GA-2 | major | · | second |  |  |  |  |  |\n"
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

def test_unknown_severity_on_a_pipe_line_is_skipped_with_its_location(
    run, report
):
    """The line is named and passed over; nothing else in the file is lost."""
    path = report("GA-1 | critical | claim\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("no findings recognized in:")
    assert (f"  {path}:1: looks like a finding header but does not parse "
            f"(severity not one of blocker/major/minor, mixed separators, or "
            f"empty claim): GA-1 | critical | claim" in res.stdout)


def test_mixed_separators_are_skipped(run, report):
    path = report("GA-1 — major | claim\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert f"{path}:1: looks like a finding header but does not parse" in res.stdout


def test_empty_claim_is_skipped(run, report):
    path = report("GA-1 | major |\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert f"{path}:1: looks like a finding header but does not parse" in res.stdout


def test_partial_file_transcribes_valid_rows(run, report):
    """Three well-formed lines survive two that are not."""
    path = report("GA-1 | major | first claim\n"
                  "X-1 | fixed | not a severity\n"
                  "GA-2 | minor | second claim\n"
                  "XX-3 | done | not a severity either\n"
                  "GB-1 | blocker | third claim\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 0, res.stdout + res.stderr
    assert res.stdout.count("\n") == 3
    assert "transcribed 3 findings" in res.stderr
    assert "SKIPPED LINES — 2 line(s) considered and not transcribed:" in res.stderr
    assert f"{path}:2: looks like a finding header" in res.stderr
    assert f"{path}:4: looks like a finding header" in res.stderr


def test_three_header_forms(run, report):
    """The table row, the bullet and the section heading, one each."""
    table = report("GA-1 | major | table form\n", name="table.md")
    bullet = report("- **V1-1 | minor | bullet form**\n", name="bullet.md")
    section = report("## GB-2 — section form\n"
                     "\n"
                     "**Conclusion: HOLDS.** Severity: **major**.\n",
                     name="section.md")
    for path, expected_id in ((table, "GA-1"), (bullet, "V1-1"), (section, "GB-2")):
        res = run(SCRIPT, path, "--stdout")
        assert res.returncode == 0, res.stdout + res.stderr
        assert res.stdout.count("\n") >= 1, path
        assert res.stdout.startswith(f"| {expected_id} | "), res.stdout


def test_a_heading_naming_an_id_without_a_severity_is_prose(run, report):
    """The section form counts only where its own block declares a severity."""
    path = report("## GB-2 — a section about a finding\n"
                  "\n"
                  "Prose that names no severity at all.\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("no findings recognized in:")


def test_a_severity_below_the_next_heading_belongs_to_that_heading(run, report):
    """A block ends at the next heading; a severity is never read across it."""
    path = report("## GB-1 — first section\n"
                  "\n"
                  "## GB-2 — second section\n"
                  "\n"
                  "Severity: **minor**.\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 0, res.stdout
    assert res.stdout == "| GB-2 | minor | · | second section |  |  |  |  |  |\n"


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


def test_a_duplicate_does_not_cost_the_other_rows(run, report, ledger):
    """The DoD case: one duplicate + two new. Before this, the duplicate
    took the whole salvage down and the operator re-laid it by hand; now
    the two new rows are written, the duplicate is NAMED, and the exit code
    still reports the failure.
    """
    target = ledger("| GA-1 | minor | already there | v | c | f | x | open |")
    path = report("GA-1 | major | duplicate\n"
                  "GA-2 | major | new one\n"
                  "GB-1 | minor | new two\n")
    res = run(SCRIPT, path, "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert "REJECTED DUPLICATE IDS — 1 row(s) not transcribed:" in res.stdout
    assert (f"  {path}:1: id GA-1 is ALREADY a row of {target} — refusing to "
            f"transcribe it twice" in res.stdout)
    assert "transcribed 2 findings into" in res.stdout
    written = read(target).splitlines()
    assert "| GA-2 | major | new one |  |  |  |  |  |" in written
    assert "| GB-1 | minor | new two |  |  |  |  |  |" in written
    # The duplicate itself was NOT laid out a second time.
    assert len([ln for ln in written if ln.startswith("| GA-1 |")]) == 1


def test_a_salvage_that_is_all_duplicates_writes_nothing(run, report, ledger):
    """Nothing survived: the ledger is not rewritten with what it has."""
    target = ledger("| GA-1 | minor | already there | v | c | f | x | open |")
    before = read(target)
    res = run(SCRIPT, report("GA-1 | major | duplicate\n"), "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert "REJECTED DUPLICATE IDS — 1 row(s) not transcribed:" in res.stdout
    assert ("nothing was written: every recognized finding was a duplicate"
            in res.stdout)
    assert read(target) == before


def test_an_unparsable_line_beside_a_duplicate_costs_only_those_two_lines(
    run, report, ledger
):
    """Both are per-LINE now: the duplicate is rejected, the unparsable one
    skipped, and neither takes the rest of the salvage down with it.
    """
    target = ledger("| GA-1 | minor | already there | v | c | f | x | open |")
    path = report("GA-1 | major | duplicate\n"
                  "GA-2 | critical | unparsable severity\n"
                  "GB-1 | major | survivor\n")
    res = run(SCRIPT, path, "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert "REJECTED DUPLICATE IDS — 1 row(s) not transcribed:" in res.stdout
    assert f"{path}:2: looks like a finding header" in res.stdout
    assert "transcribed 1 findings into" in res.stdout
    assert "| GB-1 | major | survivor |" in read(target)


def test_stdout_mode_keeps_a_duplicate_all_or_nothing(run, report):
    """`--stdout` writes nothing and its stdout is documented as carrying
    ONLY rows, so a partial set there would be pasted into a ledger with
    the rejection notice on another stream. The mode keeps the old refusal.
    """
    path = report("GA-1 | major | one\nGA-1 | minor | again\n"
                  "GA-2 | major | survivor\n")
    res = run(SCRIPT, path, "--stdout")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("STRUCTURAL ERRORS — nothing was written:")
    assert "GA-2" not in res.stdout


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


# --- the closed round is frozen evidence -----------------------------------

CLOSED_PREAMBLE = "# Ledger\n\n- Ledger state: closed 2026-01-01\n\n"
OPEN_PREAMBLE = "# Ledger\n\n- Ledger state: open\n\n"


def test_a_closed_ledger_is_refused_in_one_line(run, report, ledger):
    """A finished round is evidence: no row is appended to it, by any path.

    This writer used to append into a closed ledger and exit 0 — the one
    writer of the payload that did not read the state field at all.
    """
    target = ledger(LEDGER_ROW, preamble=CLOSED_PREAMBLE)
    before = read(target)
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", target)
    assert res.returncode == 2, res.stdout
    body = res.stdout.splitlines()
    assert len(body) == 1, res.stdout
    assert body[0].startswith(f"{target}: ")
    assert "the round is CLOSED" in body[0]
    assert read(target) == before


def test_an_open_ledger_is_still_written(run, report, ledger):
    """The freeze reads the STATE, not the presence of the field."""
    target = ledger(LEDGER_ROW, preamble=OPEN_PREAMBLE)
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", target)
    assert res.returncode == 0, res.stdout
    assert "| GA-1 | major | first claim |  |  |  |  |  |" in read(target)


def test_stdout_mode_has_no_ledger_to_freeze(run, report):
    """`--stdout` writes nothing anywhere, so no state field applies to it."""
    res = run(SCRIPT, report(TWO_FINDINGS), "--stdout")
    assert res.returncode == 0, res.stderr
    assert "the round is CLOSED" not in res.stdout


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


# --- 0.3.0: the row form is the LEDGER'S, not a hard-wired eight -----------
# Three schemas are in use (7, 8 and 9 cells), and a row of the wrong width
# is a structural error of recount.py — so the width is READ from the target
# ledger, and where it cannot be read nothing is written at all.

HEADER_7 = ("| id | sev | claim | verdict | fix | verified | terminal |\n"
            "|---|---|---|---|---|---|---|\n")
HEADER_9 = ("| id | sev | zone | claim | verdict | criterion | fix | "
            "verified | terminal |\n"
            "|---|---|---|---|---|---|---|---|---|\n")


def test_a_v3_ledger_gets_nine_cell_rows_with_the_zone_stub(run, report,
                                                            tmp_path):
    """The emitted v3 row, exactly as the contract states it."""
    led = tmp_path / "v3.md"
    led.write_text(HEADER_9, encoding="utf-8")
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    assert res.returncode == 0, res.stdout
    assert "| GA-1 | major | · | first claim |  |  |  |  |  |" in read(led)
    assert "| GA-2 | minor | · | second claim |  |  |  |  |  |" in read(led)


def test_the_stub_is_the_only_thing_transcription_decides(run, report,
                                                          tmp_path):
    """Zone is a judgment: the stub is written, never a guessed zone."""
    led = tmp_path / "v3.md"
    led.write_text(HEADER_9, encoding="utf-8")
    run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    for zone in ("Z1", "Z2", "Z3"):
        assert f"| {zone} |" not in read(led)


def test_a_v1_ledger_gets_seven_cell_rows(run, report, tmp_path):
    """A row of the ledger's own width, not the current schema's."""
    led = tmp_path / "v1.md"
    led.write_text(HEADER_7, encoding="utf-8")
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    assert res.returncode == 0, res.stdout
    assert "| GA-1 | major | first claim |  |  |  |  |" in read(led)


def test_a_v2_ledger_still_gets_eight_cell_rows(run, report, tmp_path):
    led = tmp_path / "v2.md"
    led.write_text(HEADER_8, encoding="utf-8")
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    assert res.returncode == 0, res.stdout
    assert "| GA-1 | major | first claim |  |  |  |  |  |" in read(led)


def test_the_header_field_decides_the_width(run, report, tmp_path):
    """`Row schema:` is authoritative where the table agrees with it."""
    led = tmp_path / "declared.md"
    led.write_text("- Row schema: v3\n" + HEADER_9, encoding="utf-8")
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    assert res.returncode == 0, res.stdout
    assert "| GA-1 | major | · | first claim |" in read(led)


def test_a_field_contradicting_the_table_writes_nothing(run, report,
                                                        tmp_path):
    led = tmp_path / "conflict.md"
    before = "- Row schema: v2\n" + HEADER_9
    led.write_text(before, encoding="utf-8")
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    assert res.returncode == 2, res.stdout
    assert "refusing to write rows of either width" in res.stdout
    assert read(led) == before


def test_an_unknown_schema_name_writes_nothing(run, report, tmp_path):
    led = tmp_path / "unknown.md"
    before = "- Row schema: newest\n" + HEADER_8
    led.write_text(before, encoding="utf-8")
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    assert res.returncode == 2, res.stdout
    assert "refusing to guess the row form" in res.stdout
    assert read(led) == before


def test_a_header_of_an_unsupported_width_writes_nothing(run, report,
                                                         tmp_path):
    led = tmp_path / "narrow.md"
    before = "| id | sev | terminal |\n|---|---|---|\n"
    led.write_text(before, encoding="utf-8")
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", led)
    assert res.returncode == 2, res.stdout
    assert "refusing to emit a row of a width nothing reads" in res.stdout
    assert read(led) == before


def test_stdout_mode_prints_the_v3_form(run, report):
    """There is no ledger to ask; the caller places the row."""
    res = run(SCRIPT, report(TWO_FINDINGS), "--stdout")
    assert res.returncode == 0, res.stdout
    assert res.stdout.splitlines()[0] == (
        "| GA-1 | major | · | first claim |  |  |  |  |  |")


# --- the id contract is recount.py's, not a second one ---------------------
# A prefix is ONE OR MORE letter-led segments joined by dashes, so a
# verifier re-checking a lens writes the composite `V-CIT-1`. A shape
# recount.py counts as a row must be recognized as a finding header here,
# or the report carrying it is silently transcribed as nothing.


def test_a_composite_verifier_id_is_transcribed(run, report):
    res = run(SCRIPT, report("V-CIT-1 | minor | a composite id\n"), "--stdout")
    assert res.returncode == 0, res.stdout
    assert res.stdout == "| V-CIT-1 | minor | · | a composite id |  |  |  |  |  |\n"


def test_a_composite_verifier_id_reaches_the_ledger(run, report, ledger):
    target = ledger(LEDGER_ROW)
    res = run(SCRIPT, report("V-CIT-1 | minor | a composite id\n"),
              "--ledger", target)
    assert res.returncode == 0, res.stdout
    assert read(target).splitlines()[2] == (
        "| V-CIT-1 | minor | a composite id |  |  |  |  |  |")


@pytest.mark.parametrize("finding_id", ["DA-1", "L1-2", "V-CIT-1", "V-CIT-D-3"])
def test_the_id_shapes_recount_accepts_are_finding_headers(run, report,
                                                           finding_id):
    res = run(SCRIPT, report(f"{finding_id} | minor | claim\n"), "--stdout")
    assert res.returncode == 0, res.stdout
    assert res.stdout.split("|")[1].strip() == finding_id


@pytest.mark.parametrize("not_an_id", ["-1", "V--1", "1-V", "V-CIT-"])
def test_the_shapes_recount_rejects_are_not_finding_headers(run, report,
                                                            not_an_id):
    """The four non-ids recount.py's contract names, refused here too."""
    res = run(SCRIPT, report(f"{not_an_id} | minor | claim\n"), "--stdout")
    assert res.returncode == 2, res.stdout
    assert "no findings recognized in:" in res.stdout


# --- a `--stdout` row inserted by hand into a fresh ledger -----------------


def test_a_stdout_row_inserted_into_a_fresh_ledger_recounts_without_structural_errors(
    scripts_dir, templates_dir, sandbox_home, tmp_path, run, report
):
    """A `--stdout` row fits the ledger the shipped template makes.

    `--stdout` used to print the eight-cell form while the template's
    findings table is nine cells wide, so a row pasted into a fresh ledger
    was a malformed row and the recount refused the whole ledger with
    `STRUCTURAL ERRORS` (exit 2). A pasted row is well-formed now; its
    verdict is still empty, so the recount answers `ROUND NOT CLOSABLE`
    (exit 1) — the answer for an open row, not a structural refusal.
    """
    template = templates_dir / "ledger.md"
    fresh = tmp_path / "fix-ledger.md"
    new_result = subprocess.run(
        [sys.executable, str(scripts_dir / "ledger_md.py"), "new",
         "--template", str(template), "--out", str(fresh)],
        cwd=str(tmp_path),
        env={"PATH": "/usr/bin:/bin", "HOME": str(sandbox_home)},
        capture_output=True, text=True, check=False,
    )
    assert new_result.returncode == 0, new_result.stderr

    res = run(SCRIPT, report("GA-1 | major | a pasted claim\n"), "--stdout")
    assert res.returncode == 0, res.stderr
    row = res.stdout.splitlines()[0]

    lines = fresh.read_text(encoding="utf-8").splitlines()
    sep_index = next(
        i for i, ln in enumerate(lines)
        if ln.startswith("|---") and lines[i - 1].startswith("| id | sev | zone")
    )
    lines.insert(sep_index + 1, row)
    fresh.write_text("\n".join(lines) + "\n", encoding="utf-8")

    recount_res = run("recount.py", fresh)
    assert "STRUCTURAL ERRORS" not in recount_res.stdout, recount_res.stdout
    assert recount_res.returncode == 1, recount_res.stdout
    assert "ROUND NOT CLOSABLE" in recount_res.stdout, recount_res.stdout


# --- the temporary file is created exclusively -----------------------------


def test_a_symlink_at_the_temporary_path_stops_the_write(run, report, ledger,
                                                          tmp_path):
    """The tmp path is predictable: nothing is ever written THROUGH it."""
    target = ledger(LEDGER_ROW)
    outside = tmp_path / "outside.txt"
    outside.write_text("not ours\n", encoding="utf-8")
    planted = tmp_path / (target.name + ".transcribe.tmp")
    planted.symlink_to(outside)
    before = read(target)
    res = run(SCRIPT, report(TWO_FINDINGS), "--ledger", target)
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith("STRUCTURAL ERRORS — nothing was written:")
    assert "cannot create the temporary file" in res.stdout
    assert read(target) == before
    assert outside.read_text(encoding="utf-8") == "not ours\n"
    assert planted.is_symlink()
