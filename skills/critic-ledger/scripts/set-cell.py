#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Canonical writer of one already-decided cell of a ledger row (stage 6
for the adjudicator's three, stage 7 for `fix`, stage 8 for the other
two). The counts are
computed by `scripts/recount.py` and the rows are laid out by
`scripts/transcribe.py`; this is the third mechanical step — WRITING one
already-decided cell — and it exists for the same reason as the other two:
the ad-hoc edit that replaced it split rows on `" | "` and silently lost the
empty trailing cells of a row — a defect that recurs whenever a cell is
edited by hand, so a cell edited by hand is a defect of the same class as a
count made by hand.

Contract of the write
---------------------
- One call writes ONE cell of ONE row: `--ledger`, `--id`, `--column` and
  `--value`, each given exactly once. The columns are `fix`, `verified`
  and `terminal` — the three cells the fix and verification stages own —
  plus `zone`, `verdict` and `criterion`, the ADJUDICATOR's three at
  stage 6. Those three were edited by hand until this script learned
  them, which left the one class of write in the round with no atomicity
  and no grammar check at all.
- A cell that the row's schema does not have is refused, never invented:
  a v1 row has no `criterion` and no `zone`.
- The row is addressed in the FIRST findings table of the ledger (the
  table whose header's first cell is `id`), up to the next markdown
  heading — the same table `recount.py` counts. An id that is not a row
  of it, or that is a row TWICE, is a structural error.
- The cell is addressed from the END of the row — `fix` is the third cell
  from the end, `verified` the second, `terminal` the last, `criterion`
  the fourth — which is `recount.py`'s own addressing and is why one rule
  serves all three schemas (v1 = 7 cells, v2 = 8, v3 = 9). `zone` and
  `verdict` are the two cells the zone column moves, so they are the two
  taken from the START and the only two that depend on the width. No
  width is hard-wired anywhere: the row width comes from the ledger's own
  header (`Row schema:` where it is declared, the findings header's cell
  count where it is not, and a refusal where the two disagree), exactly as
  `scripts/transcribe.py` derives it.
- Rows are split on the RAW `|`, never on `" | "`, with `\\|` read as an
  escaped literal pipe — the cell grammar of `scripts/ledger_md.py`,
  which every reader and writer of a ledger imports instead of copying.
  A row of the
  findings table whose part count is not `width + 2` (the leading and
  trailing delimiters plus its cells) is a STRUCTURAL ERROR: a table the
  recount would refuse is a table this script refuses to write into.
- A value containing `|`, a newline, or any other control character is
  REFUSED. A pipe would have to be escaped, and a mis-escaped pipe is a
  known defect class of this format; a newline would forge table rows in
  a file that is versioned as evidence. The refusal is the point — a
  value that needs a pipe gets rephrased by its author, not escaped by
  this script. It is also LOUD: the pipe refusal names the cell, the
  1-based position of every pipe in the value and the escaped form that
  is deliberately not applied, so that a rejected write is visible
  without a recount.
- The write is ALL-OR-NOTHING: everything is parsed and every check
  passes BEFORE the ledger is touched, and the new text goes through a
  temporary file and an atomic replace (fail-closed like
  `transcribe.py`'s row-width and duplicate-id checks).
- A CLOSED round is refused in one line and nothing is written: a ledger
  whose `Ledger state:` reads `closed <date>` is finished evidence.
- A value is written BYTE FOR BYTE, an owner signature included: nothing
  in it is normalised or trimmed.
- Every write PRINTS what it did: `OK <id>.<column>`, and
  `OK <id>.<column> (unchanged)` where the cell already held that value.
  A run that writes nothing exits non-zero. A silent no-op — the failure
  mode this script was written against — is impossible by construction.

Usage:  set-cell.py --ledger <path> --id <id>
                    --column <fix|verified|terminal|zone|verdict|criterion>
                    --value "<text>"
        set-cell.py -h | --help                       (this text, exit 0)
Exit codes: 0 = the cell holds the value, or `-h`/`--help`;
2 = structural error or usage error — nothing was written.
"""  # noqa: D205, D301  # printed usage text; reflow/r-string would change output

import sys
from pathlib import Path

# The row grammar, the header grammar, the escaping and the atomic patcher
# all live in ONE place — `scripts/ledger_md.py`, beside this script — so
# that a row is read the same way by everything that touches a ledger. The
# import is resolved from THIS script's own directory: the payload ships
# loose files and there is no installed package (see `pyproject.toml`), so a
# copy of these scripts without `ledger_md.py` beside them does not run.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The import sits below the path insert above, which is what makes it work.
from ledger_md import (
    BANNED_IN_VALUE,
    EXIT_OK,
    EXIT_STRUCTURAL,
    WRITABLE_COLUMNS,
    escape_cell,
    write_cell,
)

# The temporary file this script's atomic write goes through, named after it.
TMP_SUFFIX = ".set-cell.tmp"


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


def pipe_refusal(column: str, value: str) -> list[str]:
    """The refusal lines a value carrying a pipe owes, or an empty list.

    LOUD by requirement: the cell being written, the POSITION of every
    offending character, and the escaped form the script will not apply on
    the author's behalf. A refusal that only says "structural error" is
    what made three cells of one round fail so quietly that the recount was
    the only thing that noticed.
    """
    positions = [i + 1 for i, ch in enumerate(value) if ch == BANNED_IN_VALUE]
    if not positions:
        return []
    where = ", ".join(str(p) for p in positions)
    return [
        (
            f"cell `{column}`: the value carries a pipe at position {where} "
            f"(1-based) — nothing was written"
        ),
        (
            f"the value is refused, not escaped: the escaped form would be "
            f"`{escape_cell(value)}`, and a mis-escaped pipe is the defect "
            f"class this script exists to remove — rephrase the value instead"
        ),
    ]


def main() -> int:
    """Write the cell named on the command line and return the exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return EXIT_OK

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
    if column is not None and column not in WRITABLE_COLUMNS:
        usage.append(
            f"--column {column!r} is not one of "
            f"{'/'.join(WRITABLE_COLUMNS)} — the first three are the fix and "
            f"verification stages', the last three the adjudicator's",
        )
    if usage:
        print("USAGE ERROR — nothing was written:")
        for u in usage:
            print("  " + u)
        return EXIT_STRUCTURAL
    # Every option is present and `--column` is one of the six: the four
    # values below are strings, which is what the reads after this assume.
    ledger, finding_id = str(ledger), str(finding_id)
    column, value = str(column), str(value)

    refusal = pipe_refusal(column, value)
    if refusal:
        # Before the ledger is even opened: the value is refused on its own
        # terms, and the refusal says which cell, where in the value, and
        # what the escaped form would have been.
        print("STRUCTURAL ERRORS — nothing was written:")
        for line in refusal:
            print("  " + line)
        return EXIT_STRUCTURAL

    try:
        with Path(ledger).open(encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"cannot read {ledger}: {exc}")
        return EXIT_STRUCTURAL

    before, errors = write_cell(
        ledger,
        lines,
        finding_id,
        column,
        value,
        suffix=TMP_SUFFIX,
        scope=ledger,
    )
    if errors:
        print("STRUCTURAL ERRORS — nothing was written:")
        for e in errors:
            print("  " + e)
        return EXIT_STRUCTURAL

    unchanged = " (unchanged)" if before == value else ""
    print(f"OK {finding_id}.{column}{unchanged}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
