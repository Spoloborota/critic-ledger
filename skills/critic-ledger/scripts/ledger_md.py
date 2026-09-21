#!/usr/bin/env python3
# The payload ships loose files rather than a package, so this module sits
# in no __init__.py: the scripts and modules beside it that import it resolve
# it through the invoked script's own directory.
r"""The ONE owner of the fix-ledger's markdown grammar.

This file is first of all a MODULE, imported from the ONE directory it
shares with its importers: the scripts `recount.py`, `set-cell.py`, `transcribe.py`,
`validate-report.py` and `deleted-lines.py`, and by the modules
`recount.py` is split into (`ledger_model.py`, `statuses.py`,
`structural_checks.py`, `metrics.py`, `report.py`) — there is no
installed package (see `pyproject.toml`), so the import is resolved
through the directory the invoked script inserts on `sys.path`. A copy of
any of those files without this file beside it is not a working copy.
Importing it runs no argument handling and nothing else.

It also carries THREE commands. `new` instantiates a round's blank ledger
from `templates/ledger.md` at stage 1; `set-header` writes one header field
of an existing ledger; `add-pass-row` adds one row to its verification-passes
table. They live here rather than in scripts of their own because each is a
transformation of the ledger's own text, which is this file's subject: what
stage 1 gets is the template WITHOUT its `<!-- … -->` instruction blocks,
which used to be copied verbatim into every live ledger, and the two writers
replace the hand edits the stages used to prescribe for the same lines.

Why it exists
-------------
The grammar of one ledger row lived in four hand-copied places, and one of
them had already drifted: it read a row the other three would refuse. A row
read one way and written another is the defect class `set-cell.py` was
written to remove, so the grammar is now stated ONCE, here, and every
reader and writer of a ledger goes through it.

What it owns
------------
- the row grammar: the three accepted schemas (v3 nine cells, v2 eight,
  v1 seven), the raw-pipe split with `\|` as an escaped literal, the
  cell addressing (from the END for `criterion`/`fix`/`verified`/
  `terminal`, from the start for `zone` and `verdict`), and the header's
  `Row schema:` declaration;
- the header-field grammar: `header_field` reads a named field and holds
  it to EXACTLY ONE occurrence — a second declaration is an overwrite,
  never a silent replacement, and an absent field is silence;
- escaping of a value that carries a pipe, and the refusal of a value
  that carries a pipe or a control character where escaping is not the
  answer;
- the atomic region patcher: a temporary file created EXCLUSIVELY, then
  an atomic replace; nothing is ever written through a path that already
  holds something, and no temporary file survives a failed write;
- the writers: one header field, one row of the verification-passes
  table, one cell of one row — including the three ADJUDICATION cells
  (`zone`, `verdict`, `criterion`) that used to be edited by hand with no
  atomicity at all;
- the closed-round freeze: every writer here refuses a ledger whose
  `Ledger state:` reads `closed …`. A closed round is evidence.

What it does NOT own
--------------------
The finding-id contract (each script states its own `ID_RE`, held
together by the payload's own gate), the batch semantics, and every
verdict/terminal vocabulary: those are meanings, not grammar.

An owner signature is copied BYTE FOR BYTE. A cell value such as
`user-signed 2026-01-01` is written exactly as it was given — nothing is
normalised, nothing inside it is trimmed — because a signature that a
script reformatted is no longer the owner's.
"""

import argparse
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path

# --- the cell grammar ------------------------------------------------------
# An escaped pipe is parked under a sentinel while the row is split, so that
# `\|` inside a cell never opens a new cell. The sentinel is a NUL-wrapped
# word: it cannot occur in a markdown file that is versioned as evidence.
ESC = "\x00PIPE\x00"
# A markdown row must have at least the two delimiting pipes.
MIN_ROW_CELLS = 2
# The narrowest findings table whose ROWS can be addressed at all: a row
# addresses id first, severity second, verified and terminal last-but-one
# and last, so four distinct cells are the minimum. A header narrower than
# this is degenerate and its rows are not read at all.
ADDRESSABLE_ROW_CELLS = 4
# The three accepted findings-table widths, by schema version.
V1_WIDTH = 7
V2_WIDTH = 8
V3_WIDTH = 9
ROW_WIDTHS = (V1_WIDTH, V2_WIDTH, V3_WIDTH)
# From this width up the schema carries the readiness-criterion column, and
# the cell is addressed from the END (`cells[-4]`) at widths 8 and 9 alike.
CRITERION_MIN_WIDTH = V2_WIDTH
CRITERION_FROM_END = -4
# `verdict` is the one cell an inserted `zone` column DOES move, so it is the
# one cell still addressed from the start: index 3 at widths 7 and 8, index 4
# at width 9.
VERDICT_INDEX = 3
VERDICT_INDEX_V3 = 4
# The zone cell of a v3 row: THIRD, so that end-addressing survives it.
ZONE_INDEX = 2
# What `transcribe.py` writes into `zone`: transcription is literal copying,
# so the zone is left for the adjudicator behind a visible stub.
ZONE_PLACEHOLDER = "·"
# The optional header declaration of the row schema, and the width each
# version names. Absent = nothing changes; present and disagreeing with the
# table = a structural error.
ROW_SCHEMA_FIELD_RE = re.compile(r"^\s*[-*]?\s*row schema:\s*(.*?)\s*$", re.IGNORECASE)
ROW_SCHEMA_WIDTHS = {"v1": V1_WIDTH, "v2": V2_WIDTH, "v3": V3_WIDTH}
SEPARATOR_RE = re.compile(r"\|[-| :]+\|")
# The single set of finding severities, and the placeholder a blank cell may
# carry across the ledger's writers and readers.
SEVERITIES = ("blocker", "major", "minor")
BLANK_CELL = ("", "-", "—")
# A fenced code block's opening/closing marker.
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
# A fence needs an opening and a closing marker before it can wrap anything.
MIN_FENCE_MARKERS = 2
# How many finding headers an outer fence must hold to count as a wrapper.
MIN_WRAPPED_FINDINGS = 2

# --- the finding-id contract -----------------------------------------------
# ONE definition, and it is this one: a prefix of one or more dash-joined
# letter-led segments, then the number. The composite form is what lets a
# verifier keep the lens it re-checked inside the id (`V-CIT-1`) instead of
# renaming the row after a recount refuses it; every segment stays non-empty
# and letter-led, so `-1`, `V--1`, `1-V` and `V-CIT-` remain structural
# errors. The pattern is the BODY only — no anchors and no capture group —
# so each reader wraps it the way its own use needs. Scripts beside this
# module import it rather than restating it: the divergence this replaces
# had already happened twice (`transcribe.py`; and two since-removed scripts).
ID_PATTERN = r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)*-\d+"

# --- the writable columns --------------------------------------------------
# The three cells the fix and verification stages own, addressed from the END
# of the row: one addressing serves v1, v2 and v3 alike.
COLUMN_FROM_END = {"fix": -3, "verified": -2, "terminal": -1}
# The three cells the ADJUDICATOR owns. `criterion` is addressed from the end
# like the three above; `zone` and `verdict` are the two cells the zone
# column moves, so they are addressed from the start and depend on the width.
ADJUDICATION_COLUMNS = ("zone", "verdict", "criterion")
WRITABLE_COLUMNS = (*COLUMN_FROM_END, *ADJUDICATION_COLUMNS)
# What a value may not carry: a pipe (it would need escaping) and any
# control character (a newline forges rows; the rest have no meaning in a
# cell of a file read as evidence).
BANNED_IN_VALUE = "|"
CONTROL_CHARS_MAX = 0x20
# DEL sits ABOVE the C0 block rather than inside it, so a bound alone lets
# it through. It is a control character all the same, and a value carrying
# one is refused like every other: the rule this module states is the rule
# it applies.
DEL_CHAR = "\x7f"

# --- the header fields this module reads by name ---------------------------
LEDGER_STATE_FIELD = "Ledger state"
CLOSED_STATE_RE = re.compile(r"^closed(\s|$)", re.IGNORECASE)
FROZEN_STATE_RE = re.compile(r"^frozen(\s|$)", re.IGNORECASE)
# The two states that refuse every writer, one vocabulary: CLOSED is
# finished evidence, FROZEN is a ledger superseded by a rewrite.
# `recount.py` reads the frozen pattern from here.
WRITE_REFUSING_STATES = (
    (CLOSED_STATE_RE, "CLOSED"),
    (FROZEN_STATE_RE, "FROZEN"),
)
# The two header fields every reader locates as a `- <Field>:` bullet, with
# whether the VALUE sits on that same line. `Lenses:` is the one that does
# not: its machine part is the run of ` - <PREFIX> | <lens> | <model>` lines
# directly under it, so a bullet ending at the colon is its correct form and
# demanding a value there would refuse every ledger ever written.
HEADER_BULLET_FIELDS = (
    ("Mode", True),
    ("Lenses", False),
)

# --- the `Round-started:` field, the ONE chronology source -----------------
# The chronology of a WINDOW of ledgers is derived from this field and never
# from the order in which the ledgers were passed as arguments, so the script
# that orders a window — `recount.py` — reads it through this ONE definition
# rather than through a copy of its own. It used to be a copy each, and every
# copy took the DATE alone: two ledgers of the same day were then
# indistinguishable and the window had no order at all.
#
# The TIME is optional in the grammar and not in the template: a ledger
# written before the field carried one declares a bare date, which stays
# accepted (legacy) and sorts as `T00:00:00Z`. Group 1 is always the date;
# group 2 is the `HH:MM:SS` or None. A `Z` after the time is accepted and
# dropped — the field is UTC by the template, and no other offset is read.
ROUND_STARTED_RE = re.compile(
    r"^\s*[-*]?\s*round-started:\s*(\d{4}-\d{2}-\d{2})"
    r"(?:[T ](\d{2}:\d{2}:\d{2})\s*Z?)?",
    re.IGNORECASE,
)

# --- the two width-refusal wordings ----------------------------------------
# `ledger_width` serves a script that WRITES ONE CELL of an existing row and
# a script that EMITS NEW ROWS; the refusal has to name what is being
# refused, so the two tails are given by the caller rather than blurred into
# one sentence that fits neither.
WIDTH_TAILS_WRITE_CELL = (
    "refusing to touch a row while the two disagree",
    "refusing to write into a row of a width nothing reads",
)
WIDTH_TAILS_EMIT_ROW = (
    "refusing to write rows of either width while the two disagree",
    "refusing to emit a row of a width nothing reads",
)


def as_lines(text: list[str] | str) -> list[str]:
    """Return `text` as a list of lines, whichever form it arrived in."""
    return text.splitlines() if isinstance(text, str) else text


def split_row(line: str) -> list[str] | None:
    """Return the inner cells of a markdown table row, or None if malformed."""
    cells = [
        c.strip().replace(ESC, "|") for c in line.replace("\\|", ESC).strip().split("|")
    ]
    if len(cells) < MIN_ROW_CELLS or cells[0] != "" or cells[-1] != "":
        return None
    return cells[1:-1]


def split_raw(line: str) -> list[str]:
    """Return the parts of a row VERBATIM, split on unescaped pipes.

    `split_row` gives the cell VALUES (stripped, unescaped) — what a reader
    of the ledger sees. This gives the parts as they stand in the file,
    escapes and padding included, so that a rewritten row differs from the
    old one in exactly one cell and nowhere else.
    """
    return [part.replace(ESC, "\\|") for part in line.replace("\\|", ESC).split("|")]


def escape_cell(value: str) -> str:
    r"""Return `value` with every literal pipe escaped as `\|`.

    This is the ONE escaping in the format. It is applied to text that is
    COPIED into a cell (a critic's claim, for instance); a value a human
    typed for a cell is refused rather than escaped — see `value_error`.
    """
    return value.replace("|", "\\|")


def value_error(value: str) -> str | None:
    """Return why `value` may not be written into a cell, or None."""
    if BANNED_IN_VALUE in value:
        return (
            f"the value carries a pipe: {value!r} — a pipe in a cell has to "
            f"be escaped as `\\|`, and a mis-escaped pipe is exactly the "
            f"defect class this script exists to remove; rephrase the value"
        )
    for ch in value:
        if ord(ch) < CONTROL_CHARS_MAX or ch == DEL_CHAR:
            name = "a newline" if ch in "\r\n" else f"the control character {ch!r}"
            return (
                f"the value carries {name} — a cell is one line of a table "
                f"that is versioned as evidence, and a value that spans "
                f"lines forges rows"
            )
    return None


# --- the header-field grammar ----------------------------------------------


def header_field_values(text: list[str] | str, name: str) -> list[str]:
    """Return every value the header carries for the field `name`.

    The value group is ZERO-WIDTH-CAPABLE (`.*?`, not `.+?`) on purpose: a
    line ending AT THE COLON must read as a PRESENT field with an empty
    value, which the caller then refuses. With a one-or-more group that line
    matches nothing and is indistinguishable from an absent field, so a
    fail-closed reading would hang on a trailing space an editor is free to
    strip.
    """
    pattern = re.compile(
        r"^\s*[-*]?\s*" + re.escape(name) + r":\s*(.*?)\s*$",
        re.IGNORECASE,
    )
    values: list[str] = []
    for raw in as_lines(text):
        match = pattern.match(raw.rstrip("\n"))
        if match:
            values.append(match.group(1).strip())
    return values


def header_field(text: list[str] | str, name: str) -> tuple[str | None, str | None]:
    """Return (the single value of header field `name`, error-or-None).

    EXACTLY ONE occurrence is the rule, for every field alike. An ABSENT
    field yields (None, None) — silence, which is what makes every ledger
    written before a field existed read unchanged. A field written TWICE is
    a STRUCTURAL error and never "take the first and say nothing": the
    second line is an overwrite the first reader would never see.
    """
    values = header_field_values(text, name)
    if not values:
        return None, None
    if len(values) > 1:
        return None, (
            f"the header carries {len(values)} `{name}:` fields — "
            f"the field is declared ONCE per ledger; a second declaration is "
            f"an overwrite, never a silent replacement"
        )
    return values[0], None


def closed_refusal(text: list[str] | str) -> str | None:
    """Return the refusal a WRITER owes a closed or frozen ledger, or None.

    A round whose `Ledger state:` reads `closed …` is finished evidence:
    its ledger is not edited again, by a script or by hand. A round whose
    `Ledger state:` reads `frozen …` was superseded by a rewrite and is
    refused the same way. A ledger with no such field at all is not
    closed or frozen — absence is silence here too.
    """
    value, error = header_field(text, LEDGER_STATE_FIELD)
    if error is not None:
        return error
    if value is None:
        return None
    stripped = value.strip()
    for pattern, state in WRITE_REFUSING_STATES:
        if pattern.match(stripped):
            return (
                f"`{LEDGER_STATE_FIELD}: {value}` — the round is {state} and "
                f"its ledger is frozen evidence; nothing is written into it"
            )
    return None


# --- the row schema, declared and derived ----------------------------------


def findings_header_width(text: list[str] | str) -> int:
    """Return the cell count of the FIRST findings header, or 0 if there is none."""
    for raw in as_lines(text):
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if cells and cells[0].lower() == "id":
            return len(cells)
    return 0


def row_schema_error(text: list[str] | str, width: int) -> str | None:
    """Check the header's optional `Row schema:` declaration against the table.

    The field exists so that a reader knows what it parses without counting
    cells first, which is worth nothing if the declaration may disagree with
    the table. Absent, it changes nothing at all — every ledger written
    before the field has none, and its width keeps coming from the findings
    header exactly as it always did.
    """
    found = [m.strip() for m in row_schema_declarations(text)]
    if not found:
        return None
    if len(found) > 1:
        return (
            f"{len(found)} `Row schema:` header fields — the schema is "
            f"declared ONCE per ledger; a second declaration is an overwrite, "
            f"never a silent replacement"
        )
    value = found[0].lower()
    if value not in ROW_SCHEMA_WIDTHS:
        return (
            f"`Row schema: {found[0]}` is not one of "
            f"{'/'.join(ROW_SCHEMA_WIDTHS)} — a schema declared in a "
            f"vocabulary nothing reads is worse than none"
        )
    declared = ROW_SCHEMA_WIDTHS[value]
    if declared != width:
        return (
            f"`Row schema: {found[0]}` declares {declared} cells but the "
            f"findings header has {width} — a declaration that contradicts "
            f"the table is a structural error, not a hint"
        )
    return None


def row_schema_declarations(text: list[str] | str) -> list[str]:
    """Return every `Row schema:` value the header declares, in file order."""
    declared: list[str] = []
    for raw in as_lines(text):
        match = ROW_SCHEMA_FIELD_RE.match(raw.rstrip("\n"))
        if match:
            declared.append(match.group(1).strip())
    return declared


def ledger_width(
    text: list[str] | str,
    tails: tuple[str, str] = WIDTH_TAILS_WRITE_CELL,
) -> tuple[int | None, str | None]:
    """Return (the ledger's row width, error-or-None).

    The header's `Row schema:` declaration is authoritative where it exists,
    the findings header's own cell count where it does not, and a
    disagreement between the two is refused rather than resolved: the one
    thing this function may not do is hand back a width that would make
    every row it touches a structural error of the recount.

    `tails` gives the two refusal endings — what the CALLER is refusing to
    do — because a script emitting new rows and a script writing one cell
    of an existing row are refused for the same reason but not in the same
    words.
    """
    declared = row_schema_declarations(text)
    if len(declared) > 1:
        return None, (
            f"{len(declared)} `Row schema:` header fields — the schema is "
            f"declared once per ledger; refusing to pick one"
        )
    from_header: int | None = findings_header_width(text) or None
    if declared:
        value = declared[0].lower()
        if value not in ROW_SCHEMA_WIDTHS:
            return None, (
                f"`Row schema: {declared[0]}` is not one of "
                f"{'/'.join(ROW_SCHEMA_WIDTHS)} — refusing to guess the "
                f"row form"
            )
        width = ROW_SCHEMA_WIDTHS[value]
        if from_header is not None and from_header != width:
            return None, (
                f"`Row schema: {declared[0]}` declares {width} cells but the "
                f"findings header has {from_header} — {tails[0]}"
            )
        return width, None
    if from_header is None:
        return None, (
            "no findings table found (no header row whose first cell is "
            "`id`) and no `Row schema:` field — the row form is not derivable"
        )
    if from_header not in ROW_WIDTHS:
        return None, (
            f"the findings header has {from_header} cells; the row form is "
            f"one of {'/'.join(str(w) for w in ROW_WIDTHS)} — {tails[1]}"
        )
    return from_header, None


def cell_index(column: str, width: int) -> int | None:
    """Return the index of `column` in a row of `width` cells, or None.

    None means the schema has no such cell: a v1 row has no `criterion`
    and no `zone`, and asking for one is answered rather than guessed.
    `criterion`, `fix`, `verified` and `terminal` are addressed from the
    END — the zone column was inserted THIRD precisely so that they can
    be — while `zone` and `verdict` are the two the insertion moves.
    """
    if column in COLUMN_FROM_END:
        return COLUMN_FROM_END[column]
    if column == "criterion":
        return CRITERION_FROM_END if width >= CRITERION_MIN_WIDTH else None
    if column == "verdict":
        return VERDICT_INDEX_V3 if width == V3_WIDTH else VERDICT_INDEX
    if column == "zone":
        return ZONE_INDEX if width == V3_WIDTH else None
    return None


# --- the findings table ----------------------------------------------------


def scan_table(
    lines: list[str] | str, *, first_cell: str, fold_case: bool = True
) -> tuple[int, list[str], list[tuple[int, str, list[str] | None]]]:
    """Return (header line number, header cells, candidate rows) — policy-free.

    The ONE scan of a markdown table, shared by the findings table, the
    residue register and the verification-passes table. The table is the
    FIRST one whose header's first cell equals `first_cell` (lower-cased
    before the comparison when `fold_case`), read up to the next markdown
    heading. The header cells are returned as they stand in the file. A
    candidate row is `(1-based line number, the stripped line, its cells or
    None)`; separators, prose and blank lines are not candidates. Nothing
    is judged here: no separator is required under the header and no
    diagnostic is produced — both are the caller's policy.

    (0, [], []) means there is no such table at all.
    """
    rows: list[tuple[int, str, list[str] | None]] = []
    header_line = 0
    header: list[str] = []
    for n, raw in enumerate(as_lines(lines), 1):
        stripped = raw.strip()
        if not header_line:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and (cells[0].lower() if fold_case else cells[0]) == first_cell:
                header_line, header = n, cells
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("|") or SEPARATOR_RE.fullmatch(stripped):
            continue
        rows.append((n, stripped, split_row(stripped)))
    return header_line, header, rows


def scan_findings(
    text: list[str] | str,
) -> tuple[int, int, list[tuple[int, str, list[str] | None]]]:
    """Return (header line number, header width, candidate rows) — policy-free.

    The table is the FIRST one whose header's first cell is `id`, read up
    to the next markdown heading. A candidate row is `(1-based line number,
    the stripped line, its cells or None)`; separators, prose and blank
    lines are not candidates. NOTHING is judged here: whether a malformed
    row is a structural error or a row to skip is the caller's policy, and
    that difference is exactly why the five sites of this scan drifted
    before they were folded into `scan_table`.

    (0, 0, []) means there is no findings table at all.
    """
    header_line, header, rows = scan_table(text, first_cell="id")
    return header_line, len(header), rows


def find_table(
    text: list[str] | str,
) -> tuple[int | None, list[str] | None, str | None]:
    """Return (insert_index, existing_ids, error).

    `insert_index` is the line INDEX right after the separator of the first
    findings table — where a new row goes. The separator has to be there:
    a header with no separator under it is a table whose row region cannot
    be located, and guessing one is how a row lands outside the table.
    """
    lines = as_lines(text)
    header_line, _, candidates = scan_table(lines, first_cell="id")
    if header_line:
        i = header_line - 1
        if i + 1 >= len(lines) or not SEPARATOR_RE.fullmatch(lines[i + 1].strip()):
            return (
                None,
                None,
                (
                    f"line {i + 2}: the findings header at line "
                    f"{i + 1} is not followed by a separator row "
                    f"— refusing to guess where rows go"
                ),
            )
        existing = [cells2[0] for _n, _s, cells2 in candidates if cells2]
        return i + 2, existing, None
    return (
        None,
        None,
        (
            "no findings table found (no header row whose first "
            "cell is `id`) — wrong file or broken table?"
        ),
    )


def find_rows(text: list[str] | str, width: int) -> tuple[list[int], list[str]]:
    """Return (line INDICES of the findings rows, errors).

    Every row of the table is checked against `width + 2` parts here, not
    only the row about to be written: a table the recount would refuse is
    one a writer refuses to write into.
    """
    lines = as_lines(text)
    errors: list[str] = []
    header_line, _, candidates = scan_table(lines, first_cell="id")
    if header_line:
        i = header_line - 1
        if i + 1 >= len(lines) or not SEPARATOR_RE.fullmatch(lines[i + 1].strip()):
            return [], [
                (
                    f"line {i + 2}: the findings header at line {i + 1} is "
                    f"not followed by a separator row — refusing to guess "
                    f"where the rows are"
                ),
            ]
        rows: list[int] = []
        for n, s, _cells in candidates:
            j = n - 1
            parts = split_raw(s)
            if len(parts) != width + 2 or parts[0].strip() or parts[-1].strip():
                errors.append(
                    f"line {j + 1}: malformed row ({len(parts) - 2} cells, "
                    f"need {width} — this table's header width; unescaped "
                    f"pipe?): {s[:80]}",
                )
                continue
            rows.append(j)
        return rows, errors
    return [], [
        (
            "no findings table found (no header row whose first cell is "
            "`id`) — wrong file or broken table?"
        ),
    ]


# --- the salvage-fence wrapper ----------------------------------------------


def unwrap_salvage_fence(
    lines: list[str],
    *,
    is_finding: Callable[[str], bool],
) -> list[str]:
    """Neutralize an OUTER fence that wraps a whole critic report.

    Some agents deliver their report inside one code fence, and the salvage
    rule forbids editing the text, so the markers survive into the salvage.
    That wrapper is not an evidence quote, and skipping it would hide every
    finding in the file.
    The candidate is the FIRST fenced block — the first two markers, paired
    by the same toggling the scanner uses, NOT the outermost markers of the
    file (pairing marker[0] with marker[-1] swallows a report whose
    evidence blocks merely happen to be several). It is a wrapper only when
    its interior holds MORE THAN ONE well-formed finding header and nothing
    outside it holds any — an evidence quote never looks like that. The two
    markers are blanked in place (line numbers stay exact) and fences
    INSIDE the wrapper keep toggling normally.

    `is_finding` is the caller's own notion of a finding header — the two
    scripts that use this skeleton disagree on it (one strict, one loose),
    and each keeps its own reasoning at its call site.
    """
    marks = [i for i, ln in enumerate(lines) if FENCE_RE.match(ln)]
    if len(marks) < MIN_FENCE_MARKERS:
        return lines
    first, close = marks[0], marks[1]
    outside = lines[:first] + lines[close + 1 :]
    if any(is_finding(ln) for ln in outside):
        return lines
    inner = sum(1 for ln in lines[first + 1 : close] if is_finding(ln))
    if inner < MIN_WRAPPED_FINDINGS:
        return lines
    out = list(lines)
    out[first] = out[close] = "\n"
    return out


# --- the atomic patcher ----------------------------------------------------


def write_atomic(path: str, lines: list[str], suffix: str) -> str | None:
    """Write `lines` to `path` through a temporary file and an atomic replace.

    The temporary path is PREDICTABLE, so the temporary file is created
    EXCLUSIVELY (`O_EXCL`): anything already sitting there — a leftover
    file, or a symlink pointing somewhere else entirely — makes the write
    REFUSE instead of writing through it, and that file is left exactly
    where it is, since it is not this script's to delete. A write that
    fails midway leaves NO temporary file behind either: the half-written
    one is removed and the target is untouched, so the only two outcomes
    are the whole change and no change. Returns the error to report, or
    None when the replace happened.
    """
    tmp = path + suffix
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except OSError as exc:
        return (
            f"cannot create the temporary file {tmp}: {exc} — something is "
            f"already there and is NOT overwritten (it is left as it is); "
            f"remove it once you know what it is, then run this again"
        )
    replaced = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        Path(tmp).replace(path)
        replaced = True
    finally:
        if not replaced:
            Path(tmp).unlink(missing_ok=True)
    return None


# --- the writers -----------------------------------------------------------


def replace_cell(raw: str, index: int, value: str) -> str:
    """Return `raw` with the cell at `index` replaced by `value`, verbatim.

    The row is rebuilt from its RAW parts, so it differs from the old line
    in exactly one cell and nowhere else — indentation, padding and the
    escapes of every other cell survive untouched. `value` is written as it
    was given: an owner signature such as `user-signed 2026-01-01` reaches
    the file byte for byte, because a signature a script reformatted is no
    longer the owner's.
    """
    body = raw.rstrip("\n")
    indent = body[: len(body) - len(body.lstrip())]
    parts = split_raw(body.strip())
    inner = parts[1:-1]
    inner[index] = f" {value} " if value else "  "
    rebuilt = indent + "|".join(["", *inner, ""])
    return rebuilt + ("\n" if raw.endswith("\n") else "")


def cell_before(raw: str, index: int) -> str:
    """Return the CURRENT value of the cell at `index` of row `raw`."""
    inner = split_raw(raw.rstrip("\n").strip())[1:-1]
    return inner[index].strip().replace("\\|", "|")


def write_cell(  # noqa: PLR0913  # each argument is one decided fact of the write
    path: str,
    lines: list[str],
    row_id: str,
    column: str,
    value: str,
    *,
    suffix: str,
    scope: str,
) -> tuple[str | None, list[str]]:
    """Write ONE cell of ONE row atomically. Returns (previous value, errors).

    Errors non-empty means NOTHING was written. `scope` is what the caller
    named the ledger on its command line; every error ABOUT THE LEDGER
    carries it as a prefix, while an error about the VALUE does not — the
    value came from the command line and needs no address.

    `column` may be any of the six writable cells — the three the fix and
    verification stages own and the three the ADJUDICATOR owns. The
    adjudication cells used to be edited by hand, which is why they had no
    atomic write and no grammar check at all.

    A CLOSED round is refused in ONE line and nothing else is even looked
    at: a finished ledger is evidence, and listing further faults in it
    would read as an invitation to fix them.
    """
    refusal = closed_refusal(lines)
    if refusal is not None:
        return None, [f"{scope}: {refusal}"]
    if column not in WRITABLE_COLUMNS:
        return None, [f"`{column}` is not one of {'/'.join(WRITABLE_COLUMNS)}"]
    errors: list[str] = []
    bad_value = value_error(value)
    if bad_value is not None:
        errors.append(bad_value)
    width, width_err = ledger_width(lines)
    rows: list[int] = []
    if width_err is not None:
        errors.append(f"{scope}: {width_err}")
    else:
        rows, row_errors = find_rows(lines, width or 0)
        errors += [f"{scope}: {e}" for e in row_errors]
    matches = [i for i in rows if (split_row(lines[i].strip()) or [""])[0] == row_id]
    if not errors and not matches:
        errors.append(
            f"{scope}: no row with id {row_id!r} in the findings table "
            f"— nothing to write (a row is added by "
            f"scripts/transcribe.py, never here)",
        )
    if len(matches) > 1:
        errors.append(
            f"{scope}: id {row_id!r} is a row {len(matches)} times "
            f"(lines {', '.join(str(i + 1) for i in matches)}) — a duplicate "
            f"id is a structural error, and picking one is guessing",
        )
    index = None if width is None else cell_index(column, width)
    if index is None and not errors:
        errors.append(
            f"{scope}: a {width}-cell row has no `{column}` cell — the column "
            f"exists only in the wider schemas",
        )
    if errors:
        return None, errors
    line_index = matches[0]
    cell = int(index or 0)
    before = cell_before(lines[line_index], cell)
    out = list(lines)
    out[line_index] = replace_cell(lines[line_index], cell, value)
    write_error = write_atomic(path, out, suffix)
    if write_error is not None:
        return None, [write_error]
    return before, []


# --- the three commands ----------------------------------------------------
# `new`: the template carries its instructions as HTML comment blocks, and
# stage 1 used to COPY the file: every live ledger then shipped those
# instructions back as evidence, where they are neither read nor true of that
# round. The command writes the same skeleton with the comment blocks removed
# and the blank runs they leave behind collapsed to one — nothing else is
# touched, so what remains is the template's own text, cell for cell.
# `set-header` and `add-pass-row` are the two writers the stages name for the
# header fields and the passes table; the first command's name is its own
# constant because stage 1 is checked against it.
NEW = "new"
SUBCOMMANDS = (NEW, "set-header", "add-pass-row")
SET_HEADER, ADD_PASS_ROW = SUBCOMMANDS[1:]
# The ONE list of header fields `set-header` writes: exactly the fields the
# stage prose tells the main session to write mechanically. Any other name is
# refused with nothing written, whether or not the ledger's header carries it
# — a field that is filled by judgment stays out of this list on purpose.
SET_HEADER_FIELDS = (
    "Ledger state",
    "Precedents file",
    "Contract amendments",
    "Exit family",
    "Scratchpad not cleaned",
)
SET_HEADER_SUFFIX = ".set-header.tmp"
NEW_ROW_SUFFIX = ".add-pass-row.tmp"
# The first header cell of the verification-passes table.
PASSES_FIRST_CELL = "#"
# `Ledger state: closed …` is refused on a frozen ledger, on one whose findings
# table carries a row the parser rejects (an unfinished row), and on one with
# open or waiting rows; the reason is the FIRST of those states the recount
# decides.
CLOSABLE_REFUSAL = (
    "REFUSED: Ledger state: closed written before the ledger is ROUND CLOSABLE"
    " — {reason}; make every row terminal and every wait discharged first"
    " — a FROZEN ledger is never closed"
)
COMMENT_BLOCK_RE = re.compile(r"<!--.*?-->", re.DOTALL)
BLANK_RUN_RE = re.compile(r"\n{3,}")
NEW_LEDGER_SUFFIX = ".new.tmp"
EXIT_REFUSED = 2
# Process exit codes shared by `recount.py`, `validate-report.py`,
# `transcribe.py`, `set-cell.py`, `deleted-lines.py`, `ledger_md.py` and
# `extract_final.py`.
# `check-frontmatter.py` and `cleanup-scratchpad.py` are not covered by this
# table: they keep their own integer exit codes, and both return 1 by their
# own documented contract.
#
# recount.py
#   0  EXIT_OK            zero non-terminal rows (closable), or `-h`
#   1  EXIT_NOT_CLOSABLE  open rows remain / awaiting ratification /
#                         awaiting an owner act: three states, one code,
#                         told apart by the status lines
#   2  EXIT_STRUCTURAL    a structural error
#   3  EXIT_FROZEN        `LEDGER IS FROZEN`
# validate-report.py
#   0  EXIT_OK            zero problems found (labels allowed), or `-h`
#   1  EXIT_PROBLEMS      problems were found; what they mean is the
#                         orchestrator's call
#   2  EXIT_STRUCTURAL    the report cannot be parsed at all
# transcribe.py
#   0  EXIT_OK            everything recognised was transcribed or printed,
#                         or `-h`; a SKIPPED finding does not move the code
#   2  EXIT_STRUCTURAL    a structural or usage error, no finding
#                         recognised, or a duplicate id rejected in
#                         `--ledger`
# set-cell.py
#   0  EXIT_OK            the cell holds the value, or `-h`
#   2  EXIT_STRUCTURAL    a structural or usage error, nothing written
# deleted-lines.py
#   0  EXIT_OK            the listing was built (including an honestly
#                         empty one)
#   2  EXIT_STRUCTURAL    fail-closed: bad arguments, no repository, commit
#                         or range, a `--repo` with no working tree (a bare
#                         repository or a git directory), or a pathspec
#                         that matched nothing
# ledger_md.py
#   0  EXIT_OK            the blank ledger, the header field or the pass row
#                         was written, or `-h`
#   2  EXIT_REFUSED       a writer's refusal, nothing written
#   2  EXIT_STRUCTURAL    `Ledger state: closed` refused on a frozen ledger,
#                         one whose findings table carries rows the parser
#                         rejects, or one with open or waiting rows, nothing
#                         written
# extract_final.py
#   0  EXIT_OK            the final message was written, or `-h`
#   2  EXIT_STRUCTURAL    no report found in the transcript, the salvage file
#                         could not be written, or a usage error
#
# Scope: this table covers exactly the seven files listed above. `1` is
# returned only by `recount.py` and `validate-report.py`; the other five
# never return it, and a 1 from any of them would mean an uncaught
# traceback. `1` is not an "error": it means "not closable" for
# `recount.py` and "problems found" for `validate-report.py`.
# `EXIT_STRUCTURAL` and `EXIT_REFUSED` share the value 2 but differ in
# meaning: `ledger_md.py` is the one file of this table that returns
# `EXIT_REFUSED`, a writer's refusal; the other six never return it.
EXIT_OK = 0
EXIT_NOT_CLOSABLE = 1
EXIT_PROBLEMS = 1
EXIT_STRUCTURAL = 2
EXIT_FROZEN = 3


def strip_comments(text: str) -> str:
    """Return `text` without its `<!-- … -->` blocks, blank runs collapsed.

    A block may span lines, and a whole-line block leaves an empty line
    behind, so the collapse is part of the same transformation rather than
    cosmetic: two instruction blocks in a row would otherwise leave a hole
    the size of the text that was removed.
    """
    stripped = COMMENT_BLOCK_RE.sub("", text)
    stripped = "\n".join(line.rstrip() for line in stripped.split("\n"))
    return BLANK_RUN_RE.sub("\n\n", stripped).lstrip("\n")


def new_ledger(template: Path, out: Path) -> tuple[str, int]:
    """Write the blank ledger `out` from `template`. Returns (line, code)."""
    if out.exists() or out.is_symlink():
        return (
            (
                f"{out}: something is already there — refusing to overwrite "
                f"a ledger (a repeat round is a NEW run folder)"
            ),
            EXIT_REFUSED,
        )
    try:
        text = template.read_text(encoding="utf-8")
    except OSError as exc:
        return f"{template}: cannot be read: {exc}", EXIT_REFUSED
    body = strip_comments(text)
    error = write_atomic(str(out), [body], NEW_LEDGER_SUFFIX)
    if error is not None:
        return error, EXIT_REFUSED
    return f"OK {out} ({len(body.splitlines())} lines, comments stripped)", EXIT_OK


def unclosable_reason(path: str, lines: list[str]) -> str | None:
    """Return which of five unclosable states the ledger is in, or None.

    The five states are taken in the order the recount DECIDES them: a
    frozen `Ledger state:` first (its structural phase stops there), then
    findings-table rows the parser rejects, then open rows, rows awaiting
    the owner's signature, rows awaiting the owner's act — the three
    buckets of its count phase. A findings-table row the parser rejects as
    a structural error (a malformed row, or one whose criterion or status
    cell is invalid) is an unfinished row: it is refused after the frozen
    state and before the buckets, with its own reason, because the parser
    never counts it as a row. The ledger's own
    current text is read through the same modules the recount reads it
    with; nothing is run and no earlier recount is consulted.
    """
    # Imported here and not at the top: these modules import this one, so a
    # top-level import would be circular.
    from ledger_model import read_ledger  # noqa: PLC0415  # circular at top
    from statuses import (  # noqa: PLC0415  # circular at top
        AWAITING_LOGGED_NO_ACTION,
        AWAITING_SIGNATURE,
        terminal_status,
        waiting_state,
    )

    ledger, row_errors = read_ledger(lines, ledger_path=path, register_arg=None)
    if ledger.ledger_state:
        return "the ledger is FROZEN"
    if row_errors:
        # A row the parser rejects is never counted as a row, so it would
        # escape the open-row bucket below: it is an unfinished row, refused
        # like one.
        return f"{len(row_errors)} findings-table rows the parser rejects"
    buckets = {None: 0, AWAITING_SIGNATURE: 0, AWAITING_LOGGED_NO_ACTION: 0}
    for row in ledger.rows:
        terminal, _ = terminal_status(row)
        if terminal:
            continue
        wait, _ = waiting_state(row)
        buckets[wait] += 1
    if buckets[None]:
        return f"{buckets[None]} open rows"
    if buckets[AWAITING_SIGNATURE]:
        return f"{buckets[AWAITING_SIGNATURE]} rows await the owner's signature"
    if buckets[AWAITING_LOGGED_NO_ACTION]:
        return f"{buckets[AWAITING_LOGGED_NO_ACTION]} rows await the owner's act"
    return None


def set_header(path: str, lines: list[str], name: str, value: str) -> tuple[str, int]:
    """Write ONE header field `- <name>: <value>`. Returns (line, code).

    Only the fields of `SET_HEADER_FIELDS` are written, and only where the
    header carries the field as exactly one `- <name>:` line; any other
    name, and a listed name the header does not carry, get the same one
    refusal. Only the bullet line is replaced — the field's value, never an
    explanation under it. A closed or frozen ledger is refused, and so is
    the value `closed …` on a frozen ledger, one with open or waiting rows,
    or one whose findings table carries a row the parser rejects. A duplicate
    row id and every other structural error the recount reports are not
    checked here: they are the recount's, whose `ROUND CLOSABLE` comes first.
    """
    field_refusal = (
        f"`{name}` is not a header field {SET_HEADER} writes — it writes "
        f"{', '.join(SET_HEADER_FIELDS)}, each only where the header carries "
        f"it as one `- <field>:` line; nothing was written"
    )
    if name not in SET_HEADER_FIELDS:
        return field_refusal, EXIT_REFUSED
    if name == LEDGER_STATE_FIELD and CLOSED_STATE_RE.match(value.strip()):
        reason = unclosable_reason(path, lines)
        if reason is not None:
            return CLOSABLE_REFUSAL.format(reason=reason), EXIT_STRUCTURAL
    refusal = closed_refusal(lines)
    if refusal is not None:
        return f"{path}: {refusal}", EXIT_REFUSED
    bad_value = value_error(value)
    if bad_value is not None:
        return f"{bad_value}; nothing was written", EXIT_REFUSED
    _, duplicate = header_field(lines, name)
    if duplicate is not None:
        return f"{path}: {duplicate}", EXIT_REFUSED
    bullet = re.compile(r"^- " + re.escape(name) + r":")
    hits = [i for i, line in enumerate(lines) if bullet.match(line)]
    if len(hits) != 1:
        return field_refusal, EXIT_REFUSED
    out = list(lines)
    out[hits[0]] = f"- {name}: {value}\n"
    error = write_atomic(path, out, SET_HEADER_SUFFIX)
    if error is not None:
        return error, EXIT_REFUSED
    return f"OK header.{name}", EXIT_OK


def add_pass_row(path: str, lines: list[str], cells_arg: str) -> tuple[str, int]:
    r"""Add ONE row to the verification-passes table. Returns (line, code).

    `cells_arg` is the row's cells joined by `|`; a `\|` inside it is an
    escaped literal pipe and stays one cell, written escaped. The row must be
    exactly as wide as the table's own header — the first table whose header
    starts with `#` — and it goes under the table's last row. A closed or
    frozen ledger is refused, and so is a cell carrying a control character.
    """
    refusal = closed_refusal(lines)
    if refusal is not None:
        return f"{path}: {refusal}", EXIT_REFUSED
    cells = [part.strip() for part in split_raw(f"|{cells_arg}|")[1:-1]]
    header_line, header, table_rows = scan_table(
        lines, first_cell=PASSES_FIRST_CELL, fold_case=False
    )
    if len(cells) != len(header):
        return (
            f"{path}: --cells carries {len(cells)} cells; the verification-passes "
            f"table (the first table whose header starts with "
            f"`{PASSES_FIRST_CELL}`) has {len(header)} — nothing was written"
        ), EXIT_REFUSED
    for cell in cells:
        bad_value = value_error(cell.replace("\\|", ""))
        if bad_value is not None:
            return f"{bad_value}; nothing was written", EXIT_REFUSED
    at = header_line + 1
    if header_line >= len(lines) or not SEPARATOR_RE.fullmatch(
        lines[header_line].strip()
    ):
        return (
            f"{path}: line {header_line + 1}: the verification-passes header at "
            f"line {header_line} is not followed by a separator row — refusing "
            f"to guess where rows go"
        ), EXIT_REFUSED
    if table_rows:
        # Under the LAST row the reader sees: `scan_table` keeps collecting
        # rows across blank or prose lines up to the next heading, so the
        # first run of pipe lines is not necessarily the whole table.
        at = max(at, table_rows[-1][0])
    out = list(lines)
    if at == len(out) and out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    out.insert(at, "| " + " | ".join(cells) + " |\n")
    error = write_atomic(path, out, NEW_ROW_SUFFIX)
    if error is not None:
        return error, EXIT_REFUSED
    return f"OK pass.{cells[0]}", EXIT_OK


def read_lines(path: str) -> tuple[list[str], str | None]:
    """Return (the ledger's lines, error-or-None)."""
    try:
        with Path(path).open(encoding="utf-8") as fh:
            return fh.readlines(), None
    except (OSError, UnicodeDecodeError) as exc:
        return [], f"{path}: cannot be read: {exc}"


def main(argv: list[str] | None = None) -> int:
    """Run one of the three commands. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="ledger_md.py",
        description=(
            "Instantiate a round's blank fix-ledger from the ledger template, "
            "write one of its header fields, or add one verification-pass row."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser(
        NEW,
        help="write a blank ledger from the template, without its comments",
    )
    new.add_argument("--template", required=True, help="path of templates/ledger.md")
    new.add_argument("--out", required=True, help="path of the ledger to create")
    header = commands.add_parser(
        SET_HEADER,
        help=f"write one header field: {', '.join(SET_HEADER_FIELDS)}",
    )
    header.add_argument("--ledger", required=True, help="path of the fix-ledger")
    header.add_argument("--field", required=True, help="the field's name")
    header.add_argument("--value", required=True, help="the field's new value")
    passes = commands.add_parser(
        ADD_PASS_ROW,
        help="add one row to the verification-passes table",
    )
    passes.add_argument("--ledger", required=True, help="path of the fix-ledger")
    passes.add_argument(
        "--cells",
        required=True,
        help="the row's cells joined by | (a literal pipe is written \\|)",
    )
    args = parser.parse_args(argv)
    if args.command == NEW:
        line, code = new_ledger(Path(args.template), Path(args.out))
    else:
        lines, error = read_lines(args.ledger)
        if error is not None:
            line, code = error, EXIT_REFUSED
        elif args.command == SET_HEADER:
            line, code = set_header(args.ledger, lines, args.field, args.value)
        else:
            line, code = add_pass_row(args.ledger, lines, args.cells)
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
