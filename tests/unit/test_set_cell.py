"""Characterization tests for set-cell.py.

The script writes ONE cell (`fix`, `verified` or `terminal`) of ONE row of
a ledger's findings table. Exit codes: 0 = the cell holds the value (help
is 0 too), 2 = structural or usage error and nothing was written.

The cases the requirement names by hand are all here: a row with an EMPTY
trailing cell, a row of the legacy seven-cell schema, a value carrying a
pipe, a value carrying a newline, an id that is not a row, and the
successful write with its `OK <id>.<column>` line. Two more classes are
pinned because they are the reason the script exists: nothing but the
target cell may move in the file, and the row grammar must be the SAME one
`recount.py` and `transcribe.py` use — the last is asserted by running one
fixture set through all three implementations.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

from conftest import HEADER_7, HEADER_8, HEADER_9

SCRIPT = "set-cell.py"

# A v2 row whose four trailing cells are EMPTY — the shape an ad-hoc
# `" | "` split silently truncates, which is the defect this script closes.
ROW_8 = "| GA-1 | major | a claim | upheld |  |  |  |  |"
ROW_8_OTHER = "| GB-2 | minor | other claim | upheld | crit |  |  |  |"
# The legacy seven-cell row: no criterion column at all.
ROW_7 = "| GA-1 | major | a claim | upheld |  |  |  |"
# The v3 row, zone third.
ROW_9 = "| GA-1 | major | Z1 | a claim | upheld | crit |  |  |  |"


def read(path):
    return path.read_text(encoding="utf-8")


def cells(line: str) -> list[str]:
    """The row's cell values, the way recount.py reads them."""
    esc = "\x00PIPE\x00"
    return [
        c.strip().replace(esc, "|")
        for c in line.replace("\\|", esc).strip().split("|")
    ][1:-1]


# --- the successful write --------------------------------------------------


def test_writing_the_fix_cell_prints_ok_and_exits_zero(run, ledger):
    path = ledger(ROW_8 + "\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "batch B1, commit abc1234")
    assert res.returncode == 0, res.stdout + res.stderr
    assert res.stdout == "OK GA-1.fix\n"
    assert cells(read(path).splitlines()[2])[5] == "batch B1, commit abc1234"


def test_a_row_with_empty_trailing_cells_keeps_every_other_cell(run, ledger):
    """The defect of record: an empty trailing cell must not be lost."""
    path = ledger(ROW_8 + "\n")
    before = cells(read(path).splitlines()[2])
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "verified",
              "--value", "LANDED")
    assert res.returncode == 0, res.stdout
    after = cells(read(path).splitlines()[2])
    assert len(after) == len(before) == 8
    assert after[:6] == before[:6]
    assert after[6] == "LANDED"
    assert after[7] == ""


def test_the_legacy_seven_cell_row_is_written_by_the_same_addressing(run, ledger):
    path = ledger(ROW_7 + "\n", header=HEADER_7)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "terminal",
              "--value", "verified-landed")
    assert res.returncode == 0, res.stdout
    row = cells(read(path).splitlines()[2])
    assert len(row) == 7
    assert row[-1] == "verified-landed"
    assert row[:4] == ["GA-1", "major", "a claim", "upheld"]


def test_the_nine_cell_row_is_written_by_the_same_addressing(run, ledger):
    path = ledger(ROW_9 + "\n", header=HEADER_9)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "B2 / f00ba12")
    assert res.returncode == 0, res.stdout
    row = cells(read(path).splitlines()[2])
    assert len(row) == 9
    assert row[6] == "B2 / f00ba12"
    assert row[2] == "Z1"


@pytest.mark.parametrize(("column", "index"), [
    ("fix", 5), ("verified", 6), ("terminal", 7),
])
def test_each_writable_column_lands_in_its_own_cell(run, ledger, column, index):
    path = ledger(ROW_8 + "\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", column,
              "--value", "X")
    assert res.returncode == 0, res.stdout
    row = cells(read(path).splitlines()[2])
    assert row[index] == "X"
    assert [c for i, c in enumerate(row) if i != index] == [
        "GA-1", "major", "a claim", "upheld", "", "", "",
    ]


def test_only_the_target_line_changes(run, ledger):
    path = ledger(ROW_8 + "\n" + ROW_8_OTHER + "\n",
                  preamble="# Ledger\n\n- Row schema: v2\n\n",
                  suffix="\n## Appendix\n\ntail prose\n")
    before = read(path).splitlines()
    res = run(SCRIPT, "--ledger", path, "--id", "GB-2", "--column", "terminal",
              "--value", "verified-landed")
    assert res.returncode == 0, res.stdout
    after = read(path).splitlines()
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert len(before) == len(after)
    assert len(differing) == 1
    assert cells(after[differing[0]])[0] == "GB-2"


def test_an_escaped_pipe_in_another_cell_survives_verbatim(run, ledger):
    path = ledger("| GA-1 | major | a \\| b | upheld |  |  |  |  |\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "done")
    assert res.returncode == 0, res.stdout
    assert "| a \\| b |" in read(path)
    assert cells(read(path).splitlines()[2])[2] == "a | b"


def test_an_empty_value_clears_the_cell(run, ledger):
    path = ledger("| GA-1 | major | a claim | upheld |  |  | LANDED |  |\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "verified",
              "--value", "")
    assert res.returncode == 0, res.stdout
    assert res.stdout == "OK GA-1.verified\n"
    assert cells(read(path).splitlines()[2])[6] == ""


def test_rewriting_the_same_value_is_reported_rather_than_silent(run, ledger):
    path = ledger("| GA-1 | major | a claim | upheld |  |  | LANDED |  |\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "verified",
              "--value", "LANDED")
    assert res.returncode == 0, res.stdout
    assert res.stdout == "OK GA-1.verified (unchanged)\n"


def test_the_write_leaves_no_temporary_file(run, ledger, tmp_path):
    path = ledger(ROW_8 + "\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 0, res.stdout
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_a_row_of_a_later_table_is_not_addressed(run, ledger):
    path = ledger(
        ROW_8 + "\n",
        suffix="\n## Disposition of previous rounds\n\n" + HEADER_8
        + "| XX-9 | minor | old | upheld |  |  |  |  |\n",
    )
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "XX-9", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "no row with id 'XX-9'" in res.stdout
    assert read(path) == before


# --- refusals --------------------------------------------------------------


@pytest.mark.parametrize("value", ["a | b", "|", "a \\| b"])
def test_a_value_carrying_a_pipe_is_refused(run, ledger, value):
    path = ledger(ROW_8 + "\n")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", value)
    assert res.returncode == 2
    assert "STRUCTURAL ERRORS — nothing was written:" in res.stdout
    assert "carries a pipe" in res.stdout
    assert read(path) == before


def test_a_value_carrying_a_newline_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "first line\nsecond line")
    assert res.returncode == 2
    assert "carries a newline" in res.stdout
    assert read(path) == before


def test_a_value_carrying_a_control_character_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "a\tb")
    assert res.returncode == 2
    assert "control character" in res.stdout


def test_an_id_that_is_not_a_row_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "ZZ-9", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "no row with id 'ZZ-9'" in res.stdout
    assert read(path) == before


def test_a_duplicate_id_is_refused_rather_than_picked(run, ledger):
    path = ledger(ROW_8 + "\n" + ROW_8 + "\n")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "is a row 2 times" in res.stdout
    assert read(path) == before


def test_a_malformed_row_elsewhere_in_the_table_stops_the_write(run, ledger):
    """A table the recount would refuse is one this script refuses to write."""
    path = ledger(ROW_8 + "\n| GB-2 | minor | unescaped | pipe | here |  |  |  |  |\n")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "malformed row (9 cells, need 8" in res.stdout
    assert read(path) == before


def test_a_row_schema_field_contradicting_the_table_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n", preamble="- Row schema: v3\n\n")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "declares 9 cells but the findings header has 8" in res.stdout
    assert read(path) == before


def test_a_declared_row_schema_is_what_the_width_check_uses(run, ledger):
    path = ledger(ROW_9 + "\n", header=HEADER_9,
                  preamble="- Row schema: v3\n\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "terminal",
              "--value", "verified-landed")
    assert res.returncode == 0, res.stdout
    assert cells(read(path).splitlines()[4])[-1] == "verified-landed"


def test_two_row_schema_fields_are_refused(run, ledger):
    path = ledger(ROW_8 + "\n",
                  preamble="- Row schema: v2\n- Row schema: v2\n\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "2 `Row schema:` header fields" in res.stdout


def test_an_unknown_row_schema_value_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n", preamble="- Row schema: v9\n\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "is not one of v1/v2/v3" in res.stdout


def test_a_findings_header_of_an_unknown_width_is_refused(run, tmp_path):
    path = tmp_path / "narrow.md"
    path.write_text(
        "| id | sev | claim | verdict | fix | verified |\n"
        "|---|---|---|---|---|---|\n"
        "| GA-1 | major | c | v | f | LANDED |\n",
        encoding="utf-8",
    )
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "the findings header has 6 cells" in res.stdout


def test_a_declared_schema_without_a_findings_table_is_refused(run, tmp_path):
    path = tmp_path / "declared-only.md"
    path.write_text("- Row schema: v2\n\njust prose\n", encoding="utf-8")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "no findings table found" in res.stdout


def test_an_unrelated_table_above_the_findings_table_is_skipped(run, ledger):
    path = ledger(
        ROW_8 + "\n",
        preamble="| # | pass | verdicts |\n|---|---|---|\n| 1 | P1 | 3/0/0 |\n\n",
    )
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 0, res.stdout
    assert "| 1 | P1 | 3/0/0 |" in read(path)


def test_a_ledger_without_a_findings_table_is_refused(run, tmp_path):
    path = tmp_path / "no-table.md"
    path.write_text("# Ledger\n\njust prose\n", encoding="utf-8")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "no findings table found" in res.stdout


def test_a_missing_ledger_file_is_refused(run, tmp_path):
    res = run(SCRIPT, "--ledger", tmp_path / "absent.md", "--id", "GA-1",
              "--column", "fix", "--value", "x")
    assert res.returncode == 2
    assert "cannot read" in res.stdout


def test_a_header_without_a_separator_row_is_refused(run, tmp_path):
    path = tmp_path / "no-sep.md"
    path.write_text(
        "| id | sev | claim | verdict | criterion | fix | verified | terminal |\n"
        + ROW_8 + "\n",
        encoding="utf-8",
    )
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "not followed by a separator row" in res.stdout


# --- the command line ------------------------------------------------------


@pytest.mark.parametrize("missing", ["--ledger", "--id", "--column", "--value"])
def test_every_option_is_required(run, ledger, missing):
    path = ledger(ROW_8 + "\n")
    argv = ["--ledger", str(path), "--id", "GA-1", "--column", "fix",
            "--value", "x"]
    i = argv.index(missing)
    del argv[i:i + 2]
    res = run(SCRIPT, *argv)
    assert res.returncode == 2
    assert res.stdout.startswith("USAGE ERROR — nothing was written:")
    assert f"{missing} is required" in res.stdout


def test_an_option_given_twice_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--id", "GB-2",
              "--column", "fix", "--value", "x")
    assert res.returncode == 2
    assert "--id is given more than once" in res.stdout


def test_an_option_without_a_value_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value")
    assert res.returncode == 2
    assert "--value needs a value" in res.stdout


def test_an_unknown_argument_is_refused(run, ledger):
    path = ledger(ROW_8 + "\n")
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x", "--force")
    assert res.returncode == 2
    assert "unknown argument(s): --force" in res.stdout


@pytest.mark.parametrize("column", ["zone", "verdict", "criterion", "claim", ""])
def test_only_the_three_writable_columns_are_accepted(run, ledger, column):
    path = ledger(ROW_8 + "\n")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", column,
              "--value", "x")
    assert res.returncode == 2
    assert "is not one of fix/verified/terminal" in res.stdout
    assert read(path) == before


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_prints_the_contract_and_exits_zero(run, flag):
    res = run(SCRIPT, flag)
    assert res.returncode == 0
    assert "--column <fix|verified|terminal>" in res.stdout
    assert "OK <id>.<column>" in res.stdout


# --- one grammar, three scripts --------------------------------------------


def load(scripts_dir, name):
    """Import one of the shipped scripts by path, under a legal module name."""
    module_name = name.removesuffix(".py").replace("-", "_") + "_under_test"
    spec = importlib.util.spec_from_file_location(module_name, scripts_dir / name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


GRAMMAR_FIXTURES = [
    "| GA-1 | major | a claim | upheld |  |  |  |  |",
    "| GA-1 | major | a \\| b | upheld |  |  |  |  |",
    "| GA-1 | major |  |  |  |  |  |  |",
    "|GA-1|major|tight|upheld|||||",
    "   | GA-1 | major | indented | upheld |  |  |  |  |   ",
    "| id | sev | claim | verdict | criterion | fix | verified | terminal |",
    "|---|---|---|---|---|---|---|---|",
    "not a row at all",
    "| unterminated row",
    "",
]


@pytest.mark.parametrize("line", GRAMMAR_FIXTURES)
def test_the_three_scripts_read_a_row_identically(scripts_dir, line):
    """set-cell.py must not fork a second cell grammar.

    `recount.py` counts the rows, `transcribe.py` lays them out and
    `set-cell.py` writes into them; a divergence between the three would
    show up as a cell written into the wrong place, which is the class of
    defect all three exist to remove.
    """
    recount = load(scripts_dir, "recount.py")
    transcribe = load(scripts_dir, "transcribe.py")
    set_cell = load(scripts_dir, SCRIPT)
    assert set_cell.split_row(line) == recount.split_row(line)
    assert set_cell.split_row(line) == transcribe.split_row(line)


def test_the_written_row_still_recounts(run, ledger):
    """The end-to-end claim: a cell written here closes the row for recount.py."""
    path = ledger(
        "| GA-1 | major | a claim | upheld | probe: exit 0 |  |  |  |\n",
        preamble="# Ledger\n\n- Ledger state: OPEN\n\n",
    )
    for column, value in (
        ("fix", "B1 / abc1234"),
        ("verified", "LANDED"),
        ("terminal", "verified-landed"),
    ):
        res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", column,
                  "--value", value)
        assert res.returncode == 0, res.stdout
    recounted = run("recount.py", path)
    assert recounted.returncode == 0, recounted.stdout + recounted.stderr
    assert "ROUND CLOSABLE" in recounted.stdout


# --- the temporary file is created exclusively -----------------------------


def test_a_symlink_at_the_temporary_path_stops_the_write(run, ledger, tmp_path):
    """The tmp path is predictable: nothing is ever written THROUGH it."""
    path = ledger(ROW_8 + "\n")
    outside = tmp_path / "outside.txt"
    outside.write_text("not ours\n", encoding="utf-8")
    planted = tmp_path / (path.name + ".set-cell.tmp")
    planted.symlink_to(outside)
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert res.stdout.startswith("STRUCTURAL ERRORS — nothing was written:")
    assert "cannot create the temporary file" in res.stdout
    assert read(path) == before
    assert outside.read_text(encoding="utf-8") == "not ours\n"
    assert planted.is_symlink()


def test_a_file_already_at_the_temporary_path_is_left_alone(run, ledger,
                                                            tmp_path):
    """A leftover tmp file is not ours to overwrite and not ours to delete."""
    path = ledger(ROW_8 + "\n")
    planted = tmp_path / (path.name + ".set-cell.tmp")
    planted.write_text("left over\n", encoding="utf-8")
    before = read(path)
    res = run(SCRIPT, "--ledger", path, "--id", "GA-1", "--column", "fix",
              "--value", "x")
    assert res.returncode == 2
    assert "cannot create the temporary file" in res.stdout
    assert read(path) == before
    assert planted.read_text(encoding="utf-8") == "left over\n"
