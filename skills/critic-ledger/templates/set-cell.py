#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Canonical writer of a ledger row's `fix`, `verified` and `terminal`
cells (stage 7 for `fix`, stage 8 for the other two). The counts are
computed by `templates/recount.py` and the rows are laid out by
`templates/transcribe.py`; this is the third mechanical step — WRITING one
already-decided cell — and it exists for the same reason as the other two:
the ad-hoc edit that replaced it split rows on `" | "`, silently lost the
empty trailing cells of a row, and did so TWICE in one round; a different
round logged twenty silent no-ops of the same class. A cell edited by hand
is a defect of the same class as a count made by hand.

Contract of the write
---------------------
- One call writes ONE cell of ONE row: `--ledger`, `--id`, `--column` and
  `--value`, each given exactly once. The columns are `fix`, `verified`
  and `terminal` — the three cells the fix and verification stages own.
  `zone`, `verdict` and `criterion` are the ADJUDICATOR's at stage 6 and
  are deliberately not writable here.
- The row is addressed in the FIRST findings table of the ledger (the
  table whose header's first cell is `id`), up to the next markdown
  heading — the same table `recount.py` counts. An id that is not a row
  of it, or that is a row TWICE, is a structural error.
- The cell is addressed from the END of the row — `fix` is the third cell
  from the end, `verified` the second, `terminal` the last — which is
  `recount.py`'s own addressing and is why one rule serves all three
  schemas (v1 = 7 cells, v2 = 8, v3 = 9). No width is hard-wired
  anywhere: the row width comes from the ledger's own header (`Row
  schema:` where it is declared, the findings header's cell count where
  it is not, and a refusal where the two disagree), exactly as
  `templates/transcribe.py` derives it.
- Rows are split on the RAW `|`, never on `" | "`, with `\\|` read as an
  escaped literal pipe — the cell grammar of `recount.py`, replicated
  here character for character rather than re-invented. A row of the
  findings table whose part count is not `width + 2` (the leading and
  trailing delimiters plus its cells) is a STRUCTURAL ERROR: a table the
  recount would refuse is a table this script refuses to write into.
- A value containing `|`, a newline, or any other control character is
  REFUSED. A pipe would have to be escaped, and a mis-escaped pipe is a
  known defect class of this format; a newline would forge table rows in
  a file that is versioned as evidence. The refusal is the point — a
  value that needs a pipe gets rephrased by its author, not escaped by
  this script.
- The write is ALL-OR-NOTHING, like `transcribe.py`: everything is parsed
  and every check passes BEFORE the ledger is touched, and the new text
  goes through a temporary file and an atomic replace.
- Every write PRINTS what it did: `OK <id>.<column>`, and
  `OK <id>.<column> (unchanged)` where the cell already held that value.
  A run that writes nothing exits non-zero. A silent no-op — the failure
  mode this script was written against — is impossible by construction.

Usage:  set-cell.py --ledger <path> --id <id> --column <fix|verified|terminal>
                    --value "<text>"
        set-cell.py -h | --help                       (this text, exit 0)
Exit codes: 0 = the cell holds the value, or `-h`/`--help`;
2 = structural error or usage error — nothing was written.
"""  # noqa: D205, D301  # printed usage text; reflow/r-string would change output

import os
import re
import sys
from pathlib import Path
from typing import cast

# --- the cell grammar, replicated from recount.py -------------------------
# `templates/recount.py` and `templates/transcribe.py` split a row exactly
# this way. The three copies are held together by a test that runs the same
# fixture rows through all of them (tests/unit/test_set_cell.py).
ESC = "\x00PIPE\x00"
# A markdown row must have at least the two delimiting pipes.
MIN_ROW_CELLS = 2
# The three findings-table schemas, by cell count.
V1_WIDTH = 7
V2_WIDTH = 8
V3_WIDTH = 9
ROW_WIDTHS = (V1_WIDTH, V2_WIDTH, V3_WIDTH)
# The header field that declares the schema, and the width each name means.
ROW_SCHEMA_RE = re.compile(r"^\s*[-*]?\s*row schema:\s*(.*?)\s*$", re.IGNORECASE)
ROW_SCHEMA_WIDTHS = {"v1": V1_WIDTH, "v2": V2_WIDTH, "v3": V3_WIDTH}
SEPARATOR_RE = re.compile(r"\|[-| :]+\|")

# The writable columns, addressed from the END of the row — `recount.py`
# reads them at exactly these offsets, so one addressing serves v1, v2 and
# v3 alike and the zone column inserted third moves none of them.
COLUMN_FROM_END = {"fix": -3, "verified": -2, "terminal": -1}
# What a value may not carry: a pipe (it would need escaping) and any
# control character (a newline forges rows; the rest have no meaning in a
# cell of a file read as evidence).
BANNED_IN_VALUE = "|"
CONTROL_CHARS_MAX = 0x20


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


def value_error(value: str) -> str | None:
    """Return why `value` may not be written into a cell, or None."""
    if BANNED_IN_VALUE in value:
        return (
            f"the value carries a pipe: {value!r} — a pipe in a cell has to "
            f"be escaped as `\\|`, and a mis-escaped pipe is exactly the "
            f"defect class this script exists to remove; rephrase the value"
        )
    for ch in value:
        if ord(ch) < CONTROL_CHARS_MAX:
            name = "a newline" if ch in "\r\n" else f"the control character {ch!r}"
            return (
                f"the value carries {name} — a cell is one line of a table "
                f"that is versioned as evidence, and a value that spans "
                f"lines forges rows"
            )
    return None


def ledger_width(lines: list[str]) -> tuple[int | None, str | None]:
    """Return (the ledger's row width, error-or-None).

    Identical in rule to `templates/transcribe.py`: the header's `Row
    schema:` declaration is authoritative where it exists, the findings
    header's own cell count where it does not, and a disagreement between
    the two is refused rather than resolved.
    """
    declared: list[str] = []
    for raw in lines:
        m = ROW_SCHEMA_RE.match(raw.rstrip("\n"))
        if m:
            declared.append(m.group(1).strip())
    if len(declared) > 1:
        return None, (
            f"{len(declared)} `Row schema:` header fields — the schema is "
            f"declared once per ledger; refusing to pick one"
        )
    from_header: int | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if cells and cells[0].lower() == "id":
            from_header = len(cells)
            break
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
                f"findings header has {from_header} — refusing to touch a row "
                f"while the two disagree"
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
            f"one of {'/'.join(str(w) for w in ROW_WIDTHS)} — refusing to "
            f"write into a row of a width nothing reads"
        )
    return from_header, None


def find_rows(lines: list[str], width: int) -> tuple[list[int], list[str]]:
    """Return (line indices of the findings rows, errors).

    The table is the FIRST one whose header's first cell is `id`, read up
    to the next markdown heading — the same table `recount.py` counts.
    Every row of it is checked against `width + 2` parts here, not only the
    row about to be written: a table the recount would refuse is one this
    script refuses to write into.
    """
    errors: list[str] = []
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if not cells or cells[0].lower() != "id":
            continue
        if i + 1 >= len(lines) or not SEPARATOR_RE.fullmatch(lines[i + 1].strip()):
            return [], [
                (
                    f"line {i + 2}: the findings header at line {i + 1} is "
                    f"not followed by a separator row — refusing to guess "
                    f"where the rows are"
                ),
            ]
        rows: list[int] = []
        for j, raw2 in enumerate(lines[i + 2 :], i + 2):
            s = raw2.strip()
            if s.startswith("#"):
                break
            if not s.startswith("|") or SEPARATOR_RE.fullmatch(s):
                continue
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


def write_atomic(path: str, lines: list[str]) -> str | None:
    """Write `lines` to `path` through a temporary file and an atomic replace.

    The temporary path is PREDICTABLE, so the temporary file is created
    EXCLUSIVELY (`O_EXCL`): anything already sitting there — a leftover
    file, or a symlink pointing somewhere else entirely — makes the write
    REFUSE instead of writing through it, and that file is left exactly
    where it is, since it is not this script's to delete. Returns the
    error to report, or None when the replace happened.
    """
    tmp = path + ".set-cell.tmp"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except OSError as exc:
        return (
            f"cannot create the temporary file {tmp}: {exc} — something is "
            f"already there and is NOT overwritten (it is left as it is); "
            f"remove it once you know what it is, then run this again"
        )
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    Path(tmp).replace(path)
    return None


def take_option(args: list[str], name: str) -> tuple[str | None, str | None]:
    """Remove `--name <value>` from `args` and return (value, error-or-None)."""
    if args.count(name) > 1:
        return None, f"{name} is given more than once"
    if name not in args:
        return None, f"{name} is required"
    i = args.index(name)
    if i + 1 >= len(args):
        return None, f"{name} needs a value"
    value = args[i + 1]
    del args[i : i + 2]
    return value, None


def main() -> int:
    """Write the cell named on the command line and return the exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0

    usage: list[str] = []
    ledger, err = take_option(args, "--ledger")
    usage += [err] if err else []
    finding_id, err = take_option(args, "--id")
    usage += [err] if err else []
    column, err = take_option(args, "--column")
    usage += [err] if err else []
    value, err = take_option(args, "--value")
    usage += [err] if err else []
    if args:
        usage.append(f"unknown argument(s): {' '.join(args)}")
    if column is not None and column not in COLUMN_FROM_END:
        usage.append(
            f"--column {column!r} is not one of "
            f"{'/'.join(COLUMN_FROM_END)} — `zone`, `verdict` and "
            f"`criterion` belong to adjudication and are not written here",
        )
    if usage:
        print("USAGE ERROR — nothing was written:")
        for u in usage:
            print("  " + u)
        return 2
    # Every option is present and `--column` is one of the three: the four
    # values below are strings, which is what the reads after this assume.
    ledger, finding_id = str(ledger), str(finding_id)
    column, value = str(column), str(value)

    try:
        with Path(ledger).open(encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"cannot read {ledger}: {exc}")
        return 2

    errors: list[str] = []
    bad_value = value_error(value)
    if bad_value:
        errors.append(bad_value)
    width, width_err = ledger_width(lines)
    rows: list[int] = []
    if width_err is not None:
        errors.append(f"{ledger}: {width_err}")
    else:
        rows, row_errors = find_rows(lines, cast("int", width))
        errors += [f"{ledger}: {e}" for e in row_errors]

    matches = [
        i for i in rows if (split_row(lines[i].strip()) or [""])[0] == finding_id
    ]
    if not errors and not matches:
        errors.append(
            f"{ledger}: no row with id {finding_id!r} in the findings table "
            f"— nothing to write (a row is added by "
            f"templates/transcribe.py, never here)",
        )
    if len(matches) > 1:
        errors.append(
            f"{ledger}: id {finding_id!r} is a row {len(matches)} times "
            f"(lines {', '.join(str(i + 1) for i in matches)}) — a duplicate "
            f"id is a structural error, and picking one is guessing",
        )

    if errors:
        print("STRUCTURAL ERRORS — nothing was written:")
        for e in errors:
            print("  " + e)
        return 2

    index = matches[0]
    raw = lines[index]
    body = raw.rstrip("\n")
    indent = body[: len(body) - len(body.lstrip())]
    parts = split_raw(body.strip())
    inner = parts[1:-1]
    before = inner[COLUMN_FROM_END[column]].strip().replace("\\|", "|")
    inner[COLUMN_FROM_END[column]] = f" {value} " if value else "  "
    rebuilt = indent + "|".join(["", *inner, ""])
    lines[index] = rebuilt + ("\n" if raw.endswith("\n") else "")
    write_error = write_atomic(ledger, lines)
    if write_error is not None:
        print("STRUCTURAL ERRORS — nothing was written:")
        print("  " + write_error)
        return 2

    unchanged = " (unchanged)" if before == value else ""
    print(f"OK {finding_id}.{column}{unchanged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
