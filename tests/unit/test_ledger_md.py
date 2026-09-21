"""Tests for `scripts/ledger_md.py`, the one owner of the ledger grammar.

This module is the exception in this suite: it is first of all a module,
so nothing here goes through the `run` fixture. It is IMPORTED, from the
same `CRITIC_LEDGER_SCRIPTS_DIR` directory the scripts are taken from, and
the first thing pinned is exactly that — the scripts resolve the
module from their own directory, so a copy of them without it beside them
is not a runnable copy. Its three commands — `new`, `set-header` and
`add-pass-row` — are driven the same way the other non-fixture scripts
are: a subprocess call built here.

What the rest of the file pins: the three row schemas and the header line
that declares them, the `|` escaping, the atomic write (no temporary file
left behind when the write raises), the refusal every writer owes a CLOSED
round, an owner signature copied byte for byte, and the duplicate-field
rule that is the same rule for every header field alike.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys

import pytest

from conftest import HEADER_7, HEADER_8, HEADER_9, MODULE_NAMES, SCRIPT_NAMES

MODULE = "ledger_md.py"

ROW_7 = "| GA-1 | major | a claim | upheld |  |  |  |"
ROW_8 = "| GA-1 | major | a claim | upheld | crit |  |  |  |"
ROW_9 = "| GA-1 | major | Z1 | a claim | upheld | crit |  |  |  |"


@pytest.fixture(scope="module")
def ledger_md(scripts_dir):
    """The module under test, imported from the scripts directory itself."""
    spec = importlib.util.spec_from_file_location(
        "ledger_md_under_test",
        scripts_dir / MODULE,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["ledger_md_under_test"] = module
    spec.loader.exec_module(module)
    return module


def write(path, text: str) -> list[str]:
    """Write `text` and hand back its lines, the way a script reads them."""
    path.write_text(text, encoding="utf-8")
    with path.open(encoding="utf-8") as fh:
        return fh.readlines()


# --- the module is resolved from the scripts directory ---------------------


def test_the_module_ships_beside_the_scripts(scripts_dir):
    """The scripts and modules that import it find it here; it must be there."""
    assert (scripts_dir / MODULE).is_file()


@pytest.mark.parametrize(
    "script",
    ["recount.py", "set-cell.py", "transcribe.py"],
)
def test_a_script_resolves_the_module_from_its_own_directory(
    scripts_dir, tmp_path, sandbox_home, script,
):
    """A copy of the scripts WITHOUT the module is unusable, and says so.

    This is the whole content of the `CRITIC_LEDGER_SCRIPTS_DIR`
    indirection since the module exists: the variable names a directory
    that must hold `ledger_md.py` beside the scripts. The proof is a copy
    of one script alone, in a directory of its own, run from a working
    directory that is neither: the import fails, which is what "resolved
    from the script's own directory" means.
    """
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    (lonely / script).write_bytes((scripts_dir / script).read_bytes())
    env = {"PATH": "/usr/bin:/bin", "HOME": str(sandbox_home)}
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, str(lonely / script), "--help"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "ledger_md" in result.stderr

    beside = tmp_path / "beside"
    beside.mkdir()
    (beside / script).write_bytes((scripts_dir / script).read_bytes())
    # Every shipped module goes beside it: `recount.py` imports the five it
    # is split into as well, and the claim here is about `ledger_md.py`.
    for module in MODULE_NAMES:
        (beside / module).write_bytes((scripts_dir / module).read_bytes())
    ok = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, str(beside / script), "--help"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr


# --- the row grammar, all three schemas ------------------------------------


@pytest.mark.parametrize(
    ("row", "width"),
    [(ROW_7, 7), (ROW_8, 8), (ROW_9, 9)],
)
def test_every_schema_splits_into_its_own_cell_count(ledger_md, row, width):
    cells = ledger_md.split_row(row)
    assert cells is not None
    assert len(cells) == width
    assert cells[0] == "GA-1"


@pytest.mark.parametrize(
    ("header", "row", "width"),
    [(HEADER_7, ROW_7, 7), (HEADER_8, ROW_8, 8), (HEADER_9, ROW_9, 9)],
)
def test_the_header_line_gives_the_width_of_every_schema(
    ledger_md, header, row, width,
):
    lines = (header + row + "\n").splitlines()
    assert ledger_md.findings_header_width(lines) == width
    assert ledger_md.ledger_width(lines) == (width, None)


@pytest.mark.parametrize(
    "line",
    ["not a row at all", "| unterminated row", "", "text | with a pipe"],
)
def test_a_line_that_is_not_a_row_reads_as_none(ledger_md, line):
    assert ledger_md.split_row(line) is None


def test_the_row_schema_field_is_authoritative_over_the_header(ledger_md):
    lines = ("- Row schema: v3\n" + HEADER_8 + ROW_8 + "\n").splitlines()
    width, error = ledger_md.ledger_width(lines)
    assert width is None
    assert error is not None
    assert "declares 9 cells but the findings header has 8" in error


def test_the_two_refusal_wordings_name_what_is_refused(ledger_md):
    """One derivation, two callers: writing a cell and emitting a row."""
    lines = ("- Row schema: v3\n" + HEADER_8 + ROW_8 + "\n").splitlines()
    _, writing = ledger_md.ledger_width(lines, ledger_md.WIDTH_TAILS_WRITE_CELL)
    _, emitting = ledger_md.ledger_width(lines, ledger_md.WIDTH_TAILS_EMIT_ROW)
    assert writing is not None
    assert emitting is not None
    assert writing.endswith("refusing to touch a row while the two disagree")
    assert emitting.endswith(
        "refusing to write rows of either width while the two disagree",
    )


@pytest.mark.parametrize(
    ("column", "width", "index"),
    [
        ("fix", 8, -3), ("verified", 8, -2), ("terminal", 8, -1),
        ("criterion", 8, -4), ("criterion", 9, -4), ("criterion", 7, None),
        ("verdict", 7, 3), ("verdict", 8, 3), ("verdict", 9, 4),
        ("zone", 9, 2), ("zone", 8, None), ("zone", 7, None),
        ("claim", 9, None),
    ],
)
def test_the_cell_addressing_of_every_column(ledger_md, column, width, index):
    """The zone column moves `verdict` and nothing else — stated, not implied."""
    assert ledger_md.cell_index(column, width) == index


# --- the escaping ----------------------------------------------------------


def test_an_escaped_pipe_stays_inside_one_cell(ledger_md):
    row = "| GA-1 | major | a \\| b | upheld | crit |  |  |  |"
    cells = ledger_md.split_row(row)
    assert cells is not None
    assert len(cells) == 8
    assert cells[2] == "a | b"


def test_escaping_a_value_is_what_makes_it_one_cell(ledger_md):
    escaped = ledger_md.escape_cell("a | b")
    assert escaped == "a \\| b"
    row = f"| GA-1 | major | {escaped} | upheld | crit |  |  |  |"
    cells = ledger_md.split_row(row)
    assert cells is not None
    assert len(cells) == 8


def test_a_raw_split_keeps_the_escapes_and_the_padding(ledger_md):
    row = "| GA-1 | major | a \\| b | upheld | crit |  |  |  |"
    parts = ledger_md.split_raw(row)
    assert parts[3] == " a \\| b "


@pytest.mark.parametrize(
    "value",
    ["has | a pipe", "has\na newline", "bell\x07", "del\x7f"],
)
def test_a_value_that_cannot_be_a_cell_is_refused(ledger_md, value):
    """DEL rides beside the newline: it sits ABOVE the C0 block, so a bound
    on the ordinal alone used to let it through the refusal that names it.
    """  # noqa: D205  # two sentences, one rule
    assert ledger_md.value_error(value) is not None


# --- the header-field grammar ----------------------------------------------


def test_a_header_field_read_once_is_its_value(ledger_md):
    lines = ["# L\n", "- Security lens: SE\n", "- Mode: impl\n"]
    assert ledger_md.header_field(lines, "Security lens") == ("SE", None)


def test_an_absent_header_field_is_silence(ledger_md):
    assert ledger_md.header_field(["# L\n"], "Security lens") == (None, None)


def test_a_field_ending_at_the_colon_is_present_and_empty(ledger_md):
    """A gate whose arming hangs on a trailing space is not armed at all."""
    value, error = ledger_md.header_field(["- Process prefixes:\n"],
                                          "Process prefixes")
    assert (value, error) == ("", None)


def test_a_duplicate_header_field_is_a_structural_error(ledger_md):
    lines = ["- Security lens: SE\n", "- Security lens: SF\n"]
    value, error = ledger_md.header_field(lines, "Security lens")
    assert value is None
    assert error is not None
    assert "carries 2 `Security lens:` fields" in error
    assert "never a silent replacement" in error


# --- the atomic patcher ----------------------------------------------------


def test_a_write_that_raises_leaves_no_temporary_file(ledger_md, tmp_path):
    """All-or-nothing means the `.tmp` does not survive the failure either."""
    path = tmp_path / "fix-ledger.md"
    lines = write(path, HEADER_8 + ROW_8 + "\n")
    before = path.read_text(encoding="utf-8")
    with pytest.raises(TypeError):
        # `writelines` refuses a non-string; the patcher is mid-write.
        ledger_md.write_atomic(str(path), [*lines, object()], ".probe.tmp")
    assert not (tmp_path / "fix-ledger.md.probe.tmp").exists()
    assert path.read_text(encoding="utf-8") == before


def test_a_file_already_at_the_temporary_path_stops_the_write(ledger_md,
                                                              tmp_path):
    path = tmp_path / "fix-ledger.md"
    lines = write(path, HEADER_8 + ROW_8 + "\n")
    planted = tmp_path / "fix-ledger.md.probe.tmp"
    planted.write_text("left over\n", encoding="utf-8")
    error = ledger_md.write_atomic(str(path), lines, ".probe.tmp")
    assert error is not None
    assert "cannot create the temporary file" in error
    assert planted.read_text(encoding="utf-8") == "left over\n"


# --- the closed-round freeze -----------------------------------------------


CLOSED_PREAMBLE = "# Ledger\n\n- Ledger state: closed 2026-01-01\n\n"
OPEN_PREAMBLE = "# Ledger\n\n- Ledger state: open\n\n"


def test_a_closed_ledger_refuses_a_cell_write(ledger_md, tmp_path):
    path = tmp_path / "fix-ledger.md"
    lines = write(path, CLOSED_PREAMBLE + HEADER_8 + ROW_8 + "\n")
    before = path.read_text(encoding="utf-8")
    written, errors = ledger_md.write_cell(
        str(path), lines, "GA-1", "fix", "x",
        suffix=".probe.tmp", scope="L",
    )
    assert written is None
    assert len(errors) == 1
    assert "the round is CLOSED" in errors[0]
    assert path.read_text(encoding="utf-8") == before


FROZEN_PREAMBLE = (
    "# Ledger\n\n- Ledger state: FROZEN (superseded-by-rewrite, fixture)\n\n"
)


def test_a_frozen_ledger_refuses_every_writer(ledger_md, tmp_path):
    """A FROZEN ledger refuses every writer exactly as a CLOSED one does."""
    path = tmp_path / "fix-ledger.md"
    lines = write(path, FROZEN_PREAMBLE + HEADER_8 + ROW_8 + "\n")
    refusal = ledger_md.closed_refusal(lines)
    assert refusal is not None
    assert "FROZEN" in refusal

    before = path.read_text(encoding="utf-8")
    written, errors = ledger_md.write_cell(
        str(path), lines, "GA-1", "fix", "x",
        suffix=".probe.tmp", scope="L",
    )
    assert written is None
    assert len(errors) == 1
    assert "FROZEN" in errors[0]
    assert path.read_text(encoding="utf-8") == before


def test_the_two_write_refusing_states_are_one_tuple(ledger_md):
    """CLOSED and FROZEN are the same refusal shape, held in one tuple."""
    states = ledger_md.WRITE_REFUSING_STATES
    assert states[0][0] is ledger_md.CLOSED_STATE_RE
    assert states[0][1] == "CLOSED"
    assert states[1][0] is ledger_md.FROZEN_STATE_RE
    assert states[1][1] == "FROZEN"
    assert len(states) == 2

    assert ledger_md.FROZEN_STATE_RE.match("FROZEN (x)")
    assert ledger_md.FROZEN_STATE_RE.match("frozen")
    assert not ledger_md.FROZEN_STATE_RE.match("frozen-carried")
    assert not ledger_md.FROZEN_STATE_RE.match("open")


def test_an_open_ledger_is_not_frozen(ledger_md):
    lines = (OPEN_PREAMBLE + HEADER_8 + ROW_8 + "\n").splitlines()
    assert ledger_md.closed_refusal(lines) is None


def test_a_ledger_with_no_state_field_is_not_frozen(ledger_md):
    assert ledger_md.closed_refusal([HEADER_8]) is None


# --- the writers -----------------------------------------------------------


def test_the_owner_signature_is_copied_byte_for_byte(ledger_md, tmp_path):
    """Nothing in a signature is normalised — not even its inner spacing."""
    path = tmp_path / "fix-ledger.md"
    lines = write(path, OPEN_PREAMBLE + HEADER_8 + ROW_8 + "\n")
    signature = "accepted-residue  user-signed   2026-01-01"
    before, errors = ledger_md.write_cell(
        str(path), lines, "GA-1", "terminal", signature,
        suffix=".probe.tmp", scope="L",
    )
    assert errors == []
    assert before == ""
    assert f"| {signature} |" in path.read_text(encoding="utf-8")


def test_a_v2_row_has_no_zone_cell(ledger_md, tmp_path):
    path = tmp_path / "fix-ledger.md"
    lines = write(path, OPEN_PREAMBLE + HEADER_8 + ROW_8 + "\n")
    _, errors = ledger_md.write_cell(
        str(path), lines, "GA-1", "zone", "Z1",
        suffix=".probe.tmp", scope="L",
    )
    assert len(errors) == 1
    assert "has no `zone` cell" in errors[0]


def test_an_adjudication_cell_of_a_v3_row_is_written(ledger_md, tmp_path):
    path = tmp_path / "fix-ledger.md"
    lines = write(path, OPEN_PREAMBLE + HEADER_9 + ROW_9 + "\n")
    before, errors = ledger_md.write_cell(
        str(path), lines, "GA-1", "zone", "Z2",
        suffix=".probe.tmp", scope="L",
    )
    assert errors == []
    assert before == "Z1"
    row = path.read_text(encoding="utf-8").splitlines()[-1]
    assert ledger_md.split_row(row)[2] == "Z2"


# --- the one command: `new`, a ledger without the template's comments ------
#
# The template's instruction blocks used to be copied into every live
# ledger by a `cp`, where they are addressed to nobody and true of no
# round. What the command must do is remove exactly those blocks and
# nothing else, refuse to overwrite an existing ledger, and leave the
# skeleton itself — every header field, both table headers — untouched.

NEW_LEDGER_REFUSED = 2


def run_new(scripts_dir, sandbox_home, tmp_path, *args):
    """Invoke `ledger_md.py new` in a subprocess, the way stage 1 does."""
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, str(scripts_dir / MODULE), "new", *map(str, args)],
        cwd=str(tmp_path),
        env={"PATH": "/usr/bin:/bin", "HOME": str(sandbox_home)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_new_ledger_carries_no_template_comments(
    scripts_dir, templates_dir, sandbox_home, tmp_path,
):
    """The instantiated ledger holds not one `<!--`, and stays a ledger."""
    template = templates_dir / "ledger.md"
    assert template.is_file(), f"no ledger template in the templates directory: {template}"
    out = tmp_path / "fix-ledger.md"
    result = run_new(scripts_dir, sandbox_home, tmp_path,
                     "--template", template, "--out", out)
    assert result.returncode == 0, result.stderr
    text = out.read_text(encoding="utf-8")
    assert "<!--" not in text
    assert "-->" not in text
    # The skeleton itself survives: the header field the recount reads first
    # and both table headers are still there, and no run of blank lines is
    # left where a block was removed.
    assert "- Ledger state:" in text
    assert "| id | sev | zone |" in text
    assert "| # | pass (scope) |" in text
    assert "\n\n\n" not in text
    # Every line of the instantiated ledger came from the template.
    template_lines = set(template.read_text(encoding="utf-8").splitlines())
    assert [line for line in text.splitlines() if line not in template_lines] == []


def test_new_refuses_to_overwrite_an_existing_ledger(
    scripts_dir, templates_dir, sandbox_home, tmp_path,
):
    """A ledger already in place is evidence: one line, exit 2, no write."""
    template = templates_dir / "ledger.md"
    assert template.is_file(), f"no ledger template in the templates directory: {template}"
    out = tmp_path / "fix-ledger.md"
    out.write_text("a round's own ledger\n", encoding="utf-8")
    result = run_new(scripts_dir, sandbox_home, tmp_path,
                     "--template", template, "--out", out)
    assert result.returncode == NEW_LEDGER_REFUSED
    assert len(result.stdout.strip().splitlines()) == 1
    assert "refusing to overwrite" in result.stdout
    assert out.read_text(encoding="utf-8") == "a round's own ledger\n"


def test_strip_comments_removes_multi_line_blocks_and_collapses_blanks(
    ledger_md,
):
    """A block spanning lines goes whole, and leaves no hole behind."""
    text = (
        "# head\n"
        "\n"
        "<!-- one\n"
        "     two -->\n"
        "\n"
        "<!-- three -->\n"
        "\n"
        "- Ledger state: open\n"
    )
    assert ledger_md.strip_comments(text) == "# head\n\n- Ledger state: open\n"


# --- the two header and table writers: `set-header`, `add-pass-row` --------
#
# Stage prose tells the main session to write a handful of header fields and
# one row of the verification-passes table per pass. Both writes go through
# the module, atomically, and both refuse a closed round. `set-header` writes
# only the fields on its own allow-list; every other name is refused with
# nothing written, the name the profile line carries included.

PASSES_HEADER = (
    "| # | pass (scope) | verdicts (L/P/NOT) | new findings | bundled "
    "| second-pass-skipped | notes | verifiers |\n"
    "|---|---|---|---|---|---|---|---|\n"
)
WRITER_REFUSED = 2
TERMINAL_ROW_9 = "| GA-1 | major | Z1 | a claim | upheld | crit | f | LANDED | verified-landed |"


def header_ledger(state: str, rows: str = TERMINAL_ROW_9) -> str:
    """A small ledger: header bullets, a findings table, a passes table."""
    return (
        "# Ledger\n\n"
        f"- Ledger state: {state}\n"
        "- Profile: auto\n"
        "- Exit family: {clean-streak | residual-risk}\n"
        "- Scratchpad not cleaned: {reason, path | cleaned {date}}\n"
        "\n"
        + HEADER_9
        + rows
        + "\n\n## Verification passes\n\n"
        + PASSES_HEADER
        + "\nNew-findings curve by pass.\n"
    )


def run_md(scripts_dir, sandbox_home, tmp_path, *args):
    """Invoke `ledger_md.py` with any of its commands, in a subprocess."""
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, str(scripts_dir / MODULE), *map(str, args)],
        cwd=str(tmp_path),
        env={"PATH": "/usr/bin:/bin", "HOME": str(sandbox_home)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_set_header_writes_one_field(scripts_dir, sandbox_home, tmp_path):
    """One bullet changes, every other byte of the ledger stays."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("open")
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "set-header",
        "--ledger", path, "--field", "Exit family", "--value", "clean-streak",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "OK header.Exit family"
    assert path.read_text(encoding="utf-8") == before.replace(
        "- Exit family: {clean-streak | residual-risk}\n",
        "- Exit family: clean-streak\n",
    )
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_set_header_refuses_a_closed_round(scripts_dir, sandbox_home, tmp_path):
    """A closed ledger is evidence: nothing is written into its header."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("closed 2026-01-01")
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "set-header",
        "--ledger", path, "--field", "Exit family", "--value", "clean-streak",
    )
    assert result.returncode == WRITER_REFUSED
    assert "the round is CLOSED" in result.stdout
    assert path.read_text(encoding="utf-8") == before


def test_set_header_refuses_a_field_off_its_list(
    scripts_dir, sandbox_home, tmp_path,
):
    """`Profile` is in the header and still not this command's to write."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("open")
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "set-header",
        "--ledger", path, "--field", "Profile", "--value", "M",
    )
    assert result.returncode == WRITER_REFUSED
    assert "`Profile`" in result.stdout
    assert "nothing was written" in result.stdout
    assert path.read_text(encoding="utf-8") == before


def test_set_header_refuses_closed_before_the_ledger_is_closable(
    scripts_dir, sandbox_home, tmp_path,
):
    """`closed` is refused in the recount's own order of the four states."""
    open_row = "| GA-2 | minor | Z2 | c | upheld | crit | f |  |  |"
    signature = (
        "| DA-3 | minor | Z2 | c | upheld | crit | f | x "
        "| awaiting-signature (nominated 2026-01-01) |"
    )
    act = (
        "| DA-4 | minor | Z3 | c | upheld | crit | f | x "
        "| awaiting-logged-no-action (listed 2026-01-01) |"
    )
    cases = [
        (
            header_ledger("FROZEN (superseded-by-rewrite, fixture)"),
            "the ledger is FROZEN",
        ),
        (
            header_ledger("open", "\n".join([TERMINAL_ROW_9, open_row, signature])),
            "1 open rows",
        ),
        (
            header_ledger("open", "\n".join([signature, act])),
            "1 rows await the owner's signature",
        ),
        (header_ledger("open", act), "1 rows await the owner's act"),
    ]
    for before, reason in cases:
        path = tmp_path / "fix-ledger.md"
        path.write_text(before, encoding="utf-8")
        result = run_md(
            scripts_dir, sandbox_home, tmp_path, "set-header",
            "--ledger", path, "--field", "Ledger state",
            "--value", "closed 2026-01-02",
        )
        assert result.returncode == WRITER_REFUSED, reason
        assert result.stdout.startswith(
            "REFUSED: Ledger state: closed written before the ledger is "
            f"ROUND CLOSABLE — {reason}; "
        ), result.stdout
        assert path.read_text(encoding="utf-8") == before
    # And a closable ledger takes the value.
    path = tmp_path / "fix-ledger.md"
    path.write_text(header_ledger("open"), encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "set-header",
        "--ledger", path, "--field", "Ledger state",
        "--value", "closed 2026-01-02",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- Ledger state: closed 2026-01-02\n" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "bad_row",
    [
        # One cell short: the parser never counts it as a row.
        "| GA-2 | major | Z1 | open row one cell short | upheld | crit |  |",
        # Terminal with a blank criterion: rejected, so not counted either.
        "| GA-2 | major | Z1 | c | upheld |  | f | LANDED | verified-landed |",
    ],
    ids=["short-row", "blank-criterion"],
)
def test_set_header_refuses_closed_on_a_row_the_parser_rejects(
    scripts_dir, sandbox_home, tmp_path, bad_row,
):
    """A row the parser rejects is an unfinished row, never a closable one."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("open", "\n".join([TERMINAL_ROW_9, bad_row]))
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "set-header",
        "--ledger", path, "--field", "Ledger state",
        "--value", "closed 2026-01-02",
    )
    assert result.returncode == WRITER_REFUSED, result.stdout + result.stderr
    assert result.stdout.startswith(
        "REFUSED: Ledger state: closed written before the ledger is "
        "ROUND CLOSABLE — 1 findings-table rows the parser rejects; "
    ), result.stdout
    assert path.read_text(encoding="utf-8") == before
    assert "- Ledger state: open\n" in path.read_text(encoding="utf-8")


def test_set_header_names_the_frozen_state_before_open_rows(
    scripts_dir, sandbox_home, tmp_path,
):
    """A frozen ledger that also has open rows is refused as FROZEN."""
    open_row = "| GA-2 | minor | Z2 | c | upheld | crit | f |  |  |"
    path = tmp_path / "fix-ledger.md"
    before = header_ledger(
        "FROZEN (superseded-by-rewrite, fixture)",
        "\n".join([TERMINAL_ROW_9, open_row]),
    )
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "set-header",
        "--ledger", path, "--field", "Ledger state",
        "--value", "closed 2026-01-02",
    )
    assert result.returncode == WRITER_REFUSED, result.stdout + result.stderr
    assert result.stdout.startswith(
        "REFUSED: Ledger state: closed written before the ledger is "
        "ROUND CLOSABLE — the ledger is FROZEN; "
    ), result.stdout
    assert "open rows" not in result.stdout
    assert path.read_text(encoding="utf-8") == before


def test_add_pass_row_appends_one_row(scripts_dir, sandbox_home, tmp_path):
    """The row lands under the passes table, an escaped pipe stays one cell."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("open")
    path.write_text(before, encoding="utf-8")
    cells = r"1|full|L 3/P 0/NOT 0|3|no|no|a \| b|1"
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "add-pass-row",
        "--ledger", path, "--cells", cells,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "OK pass.1"
    row = r"| 1 | full | L 3/P 0/NOT 0 | 3 | no | no | a \| b | 1 |"
    assert path.read_text(encoding="utf-8") == before.replace(
        PASSES_HEADER, PASSES_HEADER + row + "\n"
    )


def test_add_pass_row_refuses_a_row_of_the_wrong_width(
    scripts_dir, sandbox_home, tmp_path,
):
    """Seven cells under an eight-column header are refused, nothing written."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("open")
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "add-pass-row",
        "--ledger", path, "--cells", "1|full|L 3|3|no|no|-",
    )
    assert result.returncode == WRITER_REFUSED
    assert "7 cells" in result.stdout
    assert "nothing was written" in result.stdout
    assert path.read_text(encoding="utf-8") == before


def test_add_pass_row_refuses_a_closed_round(scripts_dir, sandbox_home, tmp_path):
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("closed 2026-01-01")
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "add-pass-row",
        "--ledger", path, "--cells", "1|full|L 3/P 0/NOT 0|3|no|no|-|1",
    )
    assert result.returncode == WRITER_REFUSED
    assert "the round is CLOSED" in result.stdout
    assert path.read_text(encoding="utf-8") == before


PASS_ROW_1 = "| 1 | full | L 1/P 0/NOT 0 | 1 | no | no | - | 1 |"
PASS_ROW_2 = "| 2 | full | L 1/P 0/NOT 0 | 0 | no | no | - | 1 |"
PASS_ROW_3 = "| 3 | full | L 1/P 0/NOT 0 | 0 | no | no | - | 1 |"


def passes_only(table: str) -> str:
    """A ledger whose only table is the passes table, given verbatim."""
    return "- Ledger state: open\n\n## Verification passes\n\n" + table


@pytest.mark.parametrize(
    ("before", "cells", "after"),
    [
        # Under an existing row, not under the separator.
        (
            passes_only(PASSES_HEADER + PASS_ROW_1 + "\nNew-findings curve.\n"),
            "2|full|L 1/P 0/NOT 0|0|no|no|-|1",
            passes_only(
                PASSES_HEADER + PASS_ROW_1 + "\n" + PASS_ROW_2
                + "\nNew-findings curve.\n"
            ),
        ),
        # The last row ends the file without a newline.
        (
            passes_only(PASSES_HEADER + PASS_ROW_1),
            "2|full|L 1/P 0/NOT 0|0|no|no|-|1",
            passes_only(PASSES_HEADER + PASS_ROW_1 + "\n" + PASS_ROW_2 + "\n"),
        ),
        # A blank line between two rows: the reader sees both, so the new
        # row goes under the second one.
        (
            passes_only(PASSES_HEADER + PASS_ROW_1 + "\n\n" + PASS_ROW_2 + "\n"),
            "3|full|L 1/P 0/NOT 0|0|no|no|-|1",
            passes_only(
                PASSES_HEADER + PASS_ROW_1 + "\n\n" + PASS_ROW_2 + "\n"
                + PASS_ROW_3 + "\n"
            ),
        ),
    ],
    ids=["under-an-existing-row", "last-row-without-newline", "gap-in-table"],
)
def test_add_pass_row_goes_under_the_last_row(
    scripts_dir, sandbox_home, tmp_path, before, cells, after,
):
    """A later pass lands under every earlier one, as the reader orders them."""
    path = tmp_path / "fix-ledger.md"
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "add-pass-row",
        "--ledger", path, "--cells", cells,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert path.read_text(encoding="utf-8") == after


def test_add_pass_row_refuses_a_cell_with_a_control_character(
    scripts_dir, sandbox_home, tmp_path,
):
    """The value refusal is reached through the command, nothing written."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("open")
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "add-pass-row",
        "--ledger", path, "--cells", "1|full|L 3/P 0/NOT 0|3|no|no|a\x07b|1",
    )
    assert result.returncode == WRITER_REFUSED, result.stdout + result.stderr
    assert "nothing was written" in result.stdout
    assert path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "value",
    ["clean\nstreak", "clean\x07streak"],
    ids=["newline", "control-character"],
)
def test_set_header_refuses_a_value_that_cannot_be_a_cell(
    scripts_dir, sandbox_home, tmp_path, value,
):
    """The value refusal is reached through the command, nothing written."""
    path = tmp_path / "fix-ledger.md"
    before = header_ledger("open")
    path.write_text(before, encoding="utf-8")
    result = run_md(
        scripts_dir, sandbox_home, tmp_path, "set-header",
        "--ledger", path, "--field", "Exit family", "--value", value,
    )
    assert result.returncode == WRITER_REFUSED, result.stdout + result.stderr
    assert "nothing was written" in result.stdout
    assert path.read_text(encoding="utf-8") == before


# --- `Round-started:`, the ONE chronology pattern --------------------------
#
# The field used to be read by private copies of the pattern, one per
# reader, and every copy took the DATE alone. The pattern now lives here,
# takes the optional time, and its readers import it: a window of ledgers
# closed on ONE DAY is orderable because of this.


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("- Round-started: 2026-09-05T10:41:54Z", ("2026-09-05", "10:41:54")),
        # The `Z` is optional in the pattern and the separator may be a space.
        ("- Round-started: 2026-09-05T10:41:54", ("2026-09-05", "10:41:54")),
        ("- Round-started: 2026-09-05 10:41:54Z", ("2026-09-05", "10:41:54")),
        # LEGACY: a bare date stays accepted, and declares no time.
        ("- Round-started: 2026-09-05", ("2026-09-05", None)),
        ("* round-started: 2026-09-05", ("2026-09-05", None)),
        ("Round-started: 2026-09-05", ("2026-09-05", None)),
    ],
)
def test_the_round_started_pattern_takes_the_date_and_the_optional_time(
    ledger_md, line, expected
):
    """Group 1 is always the date; group 2 is the time or None."""
    match = ledger_md.ROUND_STARTED_RE.match(line)
    assert match is not None, line
    assert (match.group(1), match.group(2)) == expected


@pytest.mark.parametrize(
    "line",
    [
        "- Round-started: n/a",
        "- Round-started:",
        "- Previous run: 2026-09-05",
        "the round started on 2026-09-05",
    ],
)
def test_a_line_that_declares_no_round_start_does_not_match(ledger_md, line):
    """A field that is absent or unset is silence, never a guessed date."""
    assert ledger_md.ROUND_STARTED_RE.match(line) is None


def test_a_time_that_is_not_a_full_clock_leaves_the_date_alone(ledger_md):
    """A half-written time is not read as one: the date stands, the time is None."""
    match = ledger_md.ROUND_STARTED_RE.match("- Round-started: 2026-09-05T10:41")
    assert match is not None
    assert (match.group(1), match.group(2)) == ("2026-09-05", None)


# --- exit codes are named constants, never bare ints ------------------------

# The floor of the walk below: these scripts return named exit codes, so the
# universe derived from the sources must include each of them, and one that
# stopped naming its codes cannot leave the walk by that alone.
SCRIPTS_WITH_EXIT_CODES = (
    "recount.py",
    "transcribe.py",
    "set-cell.py",
    "validate-report.py",
    "deleted-lines.py",
)


def names_an_exit_code(node) -> bool:
    """Whether a syntax tree mentions one of the `EXIT_*` constants."""
    return any(
        (isinstance(sub, ast.Name) and sub.id.startswith("EXIT_"))
        or (isinstance(sub, ast.Attribute) and sub.attr.startswith("EXIT_"))
        for sub in ast.walk(node)
    )


def own_returns(func) -> list[ast.Return]:
    """The `Return` nodes of `func` itself, not of a definition nested in it."""
    found = []
    stack = list(func.body)
    while stack:
        node = stack.pop()
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            continue
        if isinstance(node, ast.Return):
            found.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return sorted(found, key=lambda node: node.lineno)


def holds_a_bare_int(node) -> bool:
    """Whether an int literal sits anywhere inside an expression."""
    return any(
        isinstance(sub, ast.Constant) and isinstance(sub.value, int)
        for sub in ast.walk(node)
    )


def is_an_int_annotation(node) -> bool:
    """Whether an annotation reads `int` or `int | None`, in either order."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        sides = (node.left, node.right)
        return any(
            isinstance(side, ast.Name) and side.id == "int" for side in sides
        ) and any(
            isinstance(side, ast.Constant) and side.value is None for side in sides
        )
    return isinstance(node, ast.Name) and node.id == "int"


def annotated_exit_slots(func) -> set[int]:
    """The tuple slot a return annotation declares for an exit code.

    `-> tuple[..., int]` and `-> tuple[..., int | None]` declare the LAST
    element one, counted from the end as `-1`; any other annotation, or none,
    declares no slot.
    """
    annotation = func.returns
    if not (
        isinstance(annotation, ast.Subscript)
        and isinstance(annotation.value, ast.Name)
        and annotation.value.id == "tuple"
        and isinstance(annotation.slice, ast.Tuple)
        and annotation.slice.elts
    ):
        return set()
    return {-1} if is_an_int_annotation(annotation.slice.elts[-1]) else set()


def test_every_exit_in_main_is_a_named_constant(scripts_dir, ledger_md):
    """No return the walk below places as an exit code holds a bare int.

    The universe is every shipped script and module that names an `EXIT_*`
    constant at all, derived from the sources, with `SCRIPTS_WITH_EXIT_CODES`
    as its floor. In each of those files a return carries an exit code in
    one of three ways, and each is walked at every depth of the part that
    carries it, not just its top shape:

    * every return of `main` and `fail` — `validate-report.py` returns a
      ternary (`Return(IfExp(...))`, not `Return(Constant)`), which a
      shallow check would not see into, and `deleted-lines.py`'s one
      exit-code return lives in `fail`, outside `main`;
    * every other non-tuple return of a function that returns a named code
      as a plain value;
    * in a function whose tuple returns carry a named code, the element at
      that same position, counted from the end, of EVERY tuple return; and
      in a function whose return annotation reads `tuple[..., int]` or
      `tuple[..., int | None]`, the LAST element of every tuple return,
      whether or not any return still names the code. The phase functions
      of `recount.py` and `new_ledger` in `ledger_md.py` hand the code back
      beside their output and declare that last slot in their annotation,
      which `mypy --strict` makes mandatory, so a bare int there is an exit
      code that no longer has a name — even when it was the function's only
      exit-carrying return, or the function never named one at all.

    A tuple position that neither carries a named code in its function nor is
    the last slot of such an annotation is not walked: counts, widths and
    indices are ordinary ints there. A function that returns a plain `int`
    and names no code anywhere is not walked either: its annotation alone
    cannot tell an exit code from a count.

    The `sys.exit(`/`fail(` conjunct below is vacuous today — every entry
    point calls `sys.exit(main())` and every `fail(` call passes a string —
    so its green proves nothing by itself; it guards only against a future
    regression where a bare int is passed directly to one of those calls.
    """
    trees = {
        name: ast.parse((scripts_dir / name).read_text(encoding="utf-8"))
        for name in (*SCRIPT_NAMES, *MODULE_NAMES)
    }
    carriers = [name for name, tree in trees.items() if names_an_exit_code(tree)]
    assert set(SCRIPTS_WITH_EXIT_CODES) <= set(carriers), carriers
    for script in carriers:
        tree = trees[script]
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            returns = [node for node in own_returns(func) if node.value is not None]
            tuples = [node for node in returns if isinstance(node.value, ast.Tuple)]
            plain = [node for node in returns if not isinstance(node.value, ast.Tuple)]
            slots = {
                index - len(node.value.elts)
                for node in tuples
                for index, elt in enumerate(node.value.elts)
                if names_an_exit_code(elt)
            } | annotated_exit_slots(func)
            for node in tuples:
                for slot in slots:
                    if -slot > len(node.value.elts):
                        continue
                    assert not holds_a_bare_int(node.value.elts[slot]), (
                        f"{script}:{func.name}:{node.lineno}: bare int exit code"
                    )
            if func.name in ("main", "fail"):
                whole = returns
            elif any(names_an_exit_code(node.value) for node in plain):
                whole = plain
            else:
                whole = []
            for node in whole:
                assert not holds_a_bare_int(node.value), (
                    f"{script}:{func.name}:{node.lineno}: bare int exit code"
                )

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_node = node.func
            is_sys_exit = (
                isinstance(func_node, ast.Attribute)
                and func_node.attr == "exit"
                and isinstance(func_node.value, ast.Name)
                and func_node.value.id == "sys"
            )
            is_fail_call = isinstance(func_node, ast.Name) and func_node.id == "fail"
            if not (is_sys_exit or is_fail_call):
                continue
            for arg in node.args:
                assert not (
                    isinstance(arg, ast.Constant)
                    and type(arg.value) is int
                ), f"{script}:{node.lineno}: bare int exit code"

    assert (
        ledger_md.EXIT_OK,
        ledger_md.EXIT_NOT_CLOSABLE,
        ledger_md.EXIT_PROBLEMS,
        ledger_md.EXIT_STRUCTURAL,
        ledger_md.EXIT_FROZEN,
        ledger_md.EXIT_REFUSED,
    ) == (0, 1, 1, 2, 3, 2)
