#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Reference recount script for a critic-ledger ledger (stage 8, and any
time a count is quoted). Ledger COUNTS, the new-findings CURVE, and the
inter-round DELTA are computed by THIS script, never by hand: manual
counting produced real errors in the rounds this discipline was derived
from; no errors were observed from programmatic counting.

Contract of ledger cell values
------------------------------
- The findings table is the FIRST markdown table whose header row starts
  with `| id |`. Only rows between that header and the next markdown
  heading are counted (a "Disposition of previous rounds" appendix with
  the same shape is NOT part of the round count).
- A row is one line, in one of TWO accepted schemas:
    * 8 cells (current): `| id | sev | claim | verdict | criterion | fix |
      verified | terminal |`;
    * 7 cells (legacy, written before the readiness-criterion column
      existed): the same row without `criterion`.
  Both stay recountable: the id is always the FIRST cell, while
  `verified` and `terminal` are addressed from the END of the row
  (`cells[-2]`, `cells[-1]`), so no schema branching is needed. A literal
  pipe inside any cell MUST be escaped as `\\|`.
- id: a lens/verifier prefix and a number: `<PREFIX>-<n>`, where PREFIX
  starts with a letter and may contain letters and digits (`DA`, `L1`).
  Range ids are banned; duplicate ids are a structural error.
- FAIL-CLOSED parsing (never silent): the accepted row width is the width
  of THIS table's own header — 7 or 8, and mixing the two inside one table
  is banned. Any line inside the findings table that starts with `|` but
  is not the header, the separator, or a well-formed row of exactly that
  width is a STRUCTURAL ERROR — the script exits 2 and names the line. A
  dropped row must be impossible, and an unescaped pipe in a 7-cell table
  must not pass as an 8-cell row.
- Readiness criterion (8-cell schema ONLY; a 7-cell row carries no such
  column and is not checked): a row whose terminal status is
  `verified-landed` or `accepted-residue` MUST carry a non-empty
  criterion cell that is not a dash (an accepted-residue finding is
  UPHELD — it keeps the criterion written at adjudication); a row whose
  terminal status is `refuted-with-reason` or `refused-user-signed` MUST
  carry exactly the em-dash "—" (deliberately not needed, as opposed to
  forgotten). Any violation is a STRUCTURAL ERROR — exit 2, no count is
  trustworthy until fixed.
- Terminal cell values that COUNT AS TERMINAL — exactly the four
  canonical names (aliases, including other-language ones mapped in the
  ledger header, must be normalized to these before the closing recount):
    * starts with "verified-landed" — AND the row's `verified` cell must
      contain "LANDED" and not "NOT LANDED" (consistency check). The
      verification outcome "fixed otherwise than the critic proposed"
      lives in the `verified` cell as the literal
      `LANDED OTHERWISE (<what was actually done>)`: compatible with the
      LANDED substring check, told apart by OTHERWISE, and terminal ONLY
      with a non-empty description in parentheses — a bare
      `LANDED OTHERWISE` or empty `()` is NON-terminal with a diagnostic
      (without a description the outcome is "partial", never terminal);
    * starts with "refuted-with-reason";
    * starts with "accepted-residue" — AND the cell must contain the
      literal "user-signed" (silence is not a signature) FOLLOWED by an
      ISO date: `user-signed <YYYY-MM-DD>`. An undated signature is
      NON-terminal with a diagnostic — the date is what makes the
      signature auditable;
    * starts with "refused-user-signed" — the machine-readable owner
      signature that alone makes a REFUSED security/PII finding terminal;
      it too must carry the date (`refused-user-signed <YYYY-MM-DD>`);
      a bare "refused" without that literal, or the literal without a
      date, is NON-terminal with a diagnostic, never silence.
  Anything else — "open", a date, an empty cell, prose — is NON-terminal.
- A FROZEN ledger (header line `Ledger state:` containing "FROZEN") is
  never closable: the script reports the frozen state and exits 3.
  `superseded-by-rewrite` is a whole-ledger freeze marker, NOT a per-row
  terminal value.
- The row's status lives ONLY in its cells; prose never overrides it.

Also computed:
- The new-findings CURVE from the "Verification passes" table (header
  starting `| # |`): the first integer of each "new findings" cell.
  Kill-criterion warning when the curve has not decayed for three
  consecutive passes.
- With `--prev <old-ledger.md>`: the inter-round DELTA — newly-terminal /
  regressed / still-open / new-open, by id, against the previous ledger.
  Completeness invariant: every currently NON-terminal id lands in
  exactly one of regressed / still-open / new-open — a brand-new open
  finding is never silently dropped from the delta.

Usage:  recount.py <ledger.md> [--prev <old-ledger.md>]
Exit codes: 0 = zero non-terminal rows (closable); 1 = open rows remain;
2 = structural error (malformed table — fix before trusting any count);
3 = ledger is FROZEN (superseded by a rewrite; not closable).
"""  # noqa: D205, D301  # printed usage text; reflow/r-string would change output

import re
import sys
from pathlib import Path
from typing import TypedDict

ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$")
# An owner signature is the literal `user-signed` IMMEDIATELY followed by an
# ISO date: an undated signature is not a signature.
SIGNED_DATE_RE = re.compile(r"user-signed\s+\d{4}-\d{2}-\d{2}")
ESC = "\x00PIPE\x00"

# A markdown row must have at least the two delimiting pipes.
MIN_ROW_CELLS = 2
# Width of the current schema, the one that carries the criterion column.
CRITERION_SCHEMA_WIDTH = 8
# A verification-passes row must reach the "new findings" cell (index 3).
CURVE_MIN_CELLS = 4
# Length of the window the kill criterion looks at.
KILL_CRITERION_WINDOW = 3


class Row(TypedDict):
    """One parsed findings-table row, addressed by cell name."""

    id: str
    verified: str
    terminal: str
    criterion: str | None
    line: int


def split_row(line: str) -> list[str] | None:
    """Return the inner cells of a markdown table row, or None if malformed."""
    cells = [
        c.strip().replace(ESC, "|") for c in line.replace("\\|", ESC).strip().split("|")
    ]
    if len(cells) < MIN_ROW_CELLS or cells[0] != "" or cells[-1] != "":
        return None
    return cells[1:-1]


def parse_findings(lines: list[str]) -> tuple[list[Row], list[str]]:
    """Return (rows, errors); rows = list of dicts for the FIRST findings
    table only (header `| id |` ... up to the next heading).
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    rows: list[Row] = []
    errors: list[str] = []
    in_table = False
    width = 0
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not in_table:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and cells[0].lower() == "id":
                in_table, width = True, len(cells)
                if width not in (7, 8):
                    errors.append(
                        f"line {n}: findings header has {width} "
                        f"cells; the table must be 7-cell (legacy) "
                        f"or 8-cell (with criterion)",
                    )
            continue
        if stripped.startswith("#"):
            break  # next heading ends the findings table
        if not stripped.startswith("|"):
            continue  # prose/blank inside the section
        if re.fullmatch(r"\|[-| :]+\|", stripped):
            continue  # separator
        cells = split_row(stripped)
        if cells is None or len(cells) != width:
            errors.append(
                f"line {n}: malformed row "
                f"({0 if cells is None else len(cells)} cells, "
                f"need {width} — this table's header width; "
                f"unescaped pipe?): {stripped[:80]}",
            )
            continue
        if not ID_RE.fullmatch(cells[0]):
            errors.append(
                f"line {n}: first cell is not a valid id "
                f"(<Prefix>-<n>, letter-led): {cells[0]!r}",
            )
            continue
        # verified/terminal are addressed from the END: one addressing
        # serves both the 7-cell (legacy) and the 8-cell schema.
        row: Row = {
            "id": cells[0],
            "verified": cells[-2],
            "terminal": cells[-1],
            "criterion": cells[4] if len(cells) == CRITERION_SCHEMA_WIDTH else None,
            "line": n,
        }
        problem = criterion_error(row)
        if problem:
            errors.append(problem)
            continue
        rows.append(row)
    return rows, errors


def criterion_error(row: Row) -> str | None:
    """Consistency of the readiness-criterion cell — a STRUCTURAL error
    (fail-closed), not a soft warning. 8-cell schema only: a 7-cell legacy
    row has no criterion column and is exempt.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    crit = row["criterion"]
    if crit is None:
        return None
    t = row["terminal"].lower()
    if t.startswith("verified-landed") and crit in ("", "-", "—"):
        return (
            f"line {row['line']}: {row['id']} is verified-landed but its "
            f"readiness-criterion cell is {crit!r} — a confirmed finding "
            f"must carry the criterion written at adjudication"
        )
    if t.startswith("accepted-residue") and crit in ("", "-", "—"):
        return (
            f"line {row['line']}: {row['id']} is accepted-residue but its "
            f"readiness-criterion cell is {crit!r} — an upheld finding "
            f"keeps the criterion written at adjudication (an empty or "
            f"dash cell is banned)"
        )
    if t.startswith(("refuted-with-reason", "refused")) and crit != "—":
        return (
            f"line {row['line']}: {row['id']} is refuted/refused but its "
            f"readiness-criterion cell is {crit!r} — it must be exactly "
            f"the em-dash '—' (deliberately not needed, not forgotten)"
        )
    return None


def terminal_status(row: Row) -> tuple[bool, str | None]:
    """Return (is_terminal, problem-or-None)."""
    t = row["terminal"].lower()
    if t.startswith("verified-landed"):
        v = row["verified"]
        if "NOT LANDED" in v.upper() or v.strip() in ("", "-", "—"):
            return False, (
                f"{row['id']}: terminal says verified-landed but "
                f"verified cell is {v.strip()!r}"
            )
        if "LANDED" not in v.upper():
            return False, (
                f"{row['id']}: terminal says verified-landed but "
                f"verified cell carries no LANDED verdict"
            )
        if re.search(r"LANDED\s+OTHERWISE", v, re.IGNORECASE):
            m = re.search(r"LANDED\s+OTHERWISE\s*\(([^)]*)\)", v, re.IGNORECASE)
            if not m or not m.group(1).strip():
                return False, (
                    f"{row['id']}: 'LANDED OTHERWISE' without a "
                    f"non-empty description in parentheses — "
                    f"fixed-otherwise is invalid without one and "
                    f"counts as partial"
                )
        return True, None
    if t.startswith("refuted-with-reason"):
        return True, None
    if t.startswith("accepted-residue"):
        if "user-signed" not in t:
            return False, (
                f"{row['id']}: accepted-residue without the "
                f"literal 'user-signed' — silence is not a "
                f"signature"
            )
        if not SIGNED_DATE_RE.search(t):
            return False, (
                f"{row['id']}: accepted-residue signature carries "
                f"no date — the literal is 'user-signed <date>' "
                f"(YYYY-MM-DD)"
            )
        return True, None
    if t.startswith("refused-user-signed"):
        if not SIGNED_DATE_RE.search(t):
            return False, (
                f"{row['id']}: refusal signature carries no date "
                f"— the literal is 'refused-user-signed <date>' "
                f"(YYYY-MM-DD)"
            )
        return True, None
    if t.startswith("refused"):
        return False, (
            f"{row['id']}: refusal without the literal "
            f"'refused-user-signed' — a refused security/PII "
            f"finding is terminal only with the owner signature"
        )
    return False, None


def curve(lines: list[str]) -> list[int]:
    """Return the new-findings counts read off the verification-passes table."""
    vals: list[int] = []
    in_table = False
    for raw in lines:
        stripped = raw.strip()
        if not in_table:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and cells[0] == "#":
                in_table = True
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("|") or re.fullmatch(r"\|[-| :]+\|", stripped):
            continue
        cells = split_row(stripped)
        if cells and len(cells) >= CURVE_MIN_CELLS:
            m = re.search(r"\d+", cells[3])
            if m:
                vals.append(int(m.group()))
    return vals


def load(path: str) -> list[str]:
    """Read a ledger file and return its lines."""
    with Path(path).open(encoding="utf-8") as fh:
        return fh.readlines()


def main() -> int:
    """Recount the ledger named on the command line and return the exit code."""
    args = sys.argv[1:]
    prev_path = None
    if "--prev" in args:
        i = args.index("--prev")
        prev_path = args[i + 1]
        del args[i : i + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    lines = load(args[0])

    frozen = [
        raw
        for raw in lines
        if raw.strip().lower().startswith(("- ledger state:", "ledger state:"))
        and "frozen" in raw.lower()
    ]
    if frozen:
        print("LEDGER IS FROZEN (superseded by a rewrite) — not closable:")
        print("  " + frozen[0].strip())
        return 3

    rows, errors = parse_findings(lines)
    if not rows and not errors:
        print("no ledger rows found — wrong file or broken table?")
        return 2
    seen: set[str] = set()
    for r in rows:
        if r["id"] in seen:
            errors.append(f"line {r['line']}: DUPLICATE ROW ID {r['id']}")
        seen.add(r["id"])
    if errors:
        print("STRUCTURAL ERRORS — no count is trustworthy until fixed:")
        for e in errors:
            print("  " + e)
        return 2

    open_rows: list[str] = []
    problems: list[str] = []
    for r in rows:
        ok, problem = terminal_status(r)
        if not ok:
            open_rows.append(r["id"])
            if problem:
                problems.append(problem)
    print(
        f"rows: {len(rows)} | terminal: {len(rows) - len(open_rows)} | "
        f"non-terminal: {len(open_rows)}",
    )
    for p in problems:
        print("  CONSISTENCY: " + p)

    c = curve(lines)
    if c:
        print("new-findings curve:", " -> ".join(map(str, c)))
        if len(c) >= KILL_CRITERION_WINDOW and c[-1] >= c[-2] >= c[-3] and c[-3] > 0:
            print(
                "  KILL-CRITERION WARNING: curve has not decayed for "
                "three consecutive passes — stop and fork to the user.",
            )

    if prev_path:
        prev_rows, prev_errors = parse_findings(load(prev_path))
        if prev_errors:
            print("--prev ledger has structural errors; delta skipped.")
        else:
            prev = {r["id"]: terminal_status(r)[0] for r in prev_rows}
            cur = {r["id"]: terminal_status(r)[0] for r in rows}
            newly = sorted(i for i, t in cur.items() if t and not prev.get(i, False))
            regressed = sorted(
                i for i, t in cur.items() if not t and prev.get(i, False)
            )
            still = sorted(
                i for i, t in cur.items() if not t and i in prev and not prev[i]
            )
            new_open = sorted(i for i, t in cur.items() if not t and i not in prev)
            print(
                f"DELTA vs {prev_path}: newly-terminal {newly or '[]'} | "
                f"regressed {regressed or '[]'} | still-open "
                f"{still or '[]'} | new-open {new_open or '[]'}",
            )
            uncovered = (
                {i for i, t in cur.items() if not t}
                - set(regressed)
                - set(still)
                - set(new_open)
            )
            if uncovered:
                print(
                    "  DELTA COMPLETENESS ERROR — open ids missing from every bucket:",
                    ", ".join(sorted(uncovered)),
                )
                return 2

    if open_rows:
        print("non-terminal ids:", ", ".join(open_rows))
        return 1
    print("ROUND CLOSABLE: zero non-terminal rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
