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
  must not pass as an 8-cell row. A header too narrow for a row to hold
  id, severity, verified and terminal in distinct cells (the degenerate
  `| id |`) is reported by width and its rows are NOT read: the header
  diagnostic is the whole structural report, exit 2, never a traceback.
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
  The signature date must be a CALENDAR-VALID date: `9999-99-99` or
  `2026-02-30` is NON-terminal with a diagnostic — a date that cannot
  exist is not auditable. That is the ONLY date check: the script does
  NOT check that the date is not in the future, nor that it postdates
  the finding or the verification.
  Anything else — "open", a date, an empty cell, prose — is NON-terminal.
- A FROZEN ledger (header line `Ledger state:` containing "FROZEN") is
  never closable: the script reports the frozen state and exits 3.
  `superseded-by-rewrite` is a whole-ledger freeze marker, NOT a per-row
  terminal value.
- The row's status lives ONLY in its cells; prose never overrides it.

Also computed:
- The SEVERITY DISTRIBUTION (severity cell x terminal status). Severity is
  cell index 1 in BOTH schemas, so no schema detection is involved and the
  line is printed for 7-cell and 8-cell ledgers alike.
- The UPHELD/REFUTED split, which needs the criterion cell and is therefore
  8-cell only: a 7-cell ledger prints `n/a (v1 ledger — no criterion
  column)` rather than guessing. A row is UPHELD iff its criterion cell is
  not the literal em-dash "—", or its terminal cell begins with "refused".
- The new-findings CURVE from the "Verification passes" table (header
  starting `| # |`): the first integer of each "new findings" cell.
  Kill-criterion warning when the curve has not decayed for three
  consecutive passes. The "new findings" column is located BY NAME when the
  passes header names it and by index 3 otherwise, so the positional
  behaviour of older ledgers is preserved exactly.
  When that table carries `started` and `ended` as its last two columns the
  curve is ALSO printed on a time axis, with the wall-clock of each pass;
  when it does not, one line says why there is no time axis. A timestamp
  that is present but unparseable is REPORTED BY NAME and the time axis is
  suppressed — it NEVER changes the exit code, because those two columns
  exist only when observability is on and a measurement must not be able to
  fail a round.
- With `--trace <trace.jsonl>`: one report-only line counting the round's
  trace records and the unreadable lines skipped. A missing trace is
  `trace: none`; nothing about a trace changes the exit code.
- With `--prev <old-ledger.md>`: the inter-round DELTA — newly-terminal /
  regressed / still-open / new-open, by id, against the previous ledger.
  Completeness invariant: every currently NON-terminal id lands in
  exactly one of regressed / still-open / new-open — a brand-new open
  finding is never silently dropped from the delta.

Usage:  recount.py <ledger.md> [--prev <old-ledger.md>] [--trace <trace.jsonl>]
        recount.py -h | --help                       (this text, exit 0)
Exit codes: 0 = zero non-terminal rows (closable), or `-h`/`--help`;
1 = open rows remain; 2 = structural error (malformed table — fix before
trusting any count); 3 = ledger is FROZEN (superseded by a rewrite; not
closable).
"""  # noqa: D205, D301  # printed usage text; reflow/r-string would change output

import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypedDict

ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$")
# An owner signature is the literal `user-signed` IMMEDIATELY followed by an
# ISO date: an undated signature is not a signature.
SIGNED_DATE_RE = re.compile(r"user-signed\s+(\d{4}-\d{2}-\d{2})")
ESC = "\x00PIPE\x00"

# A markdown row must have at least the two delimiting pipes.
MIN_ROW_CELLS = 2
# The narrowest findings table whose ROWS can be addressed at all: a row
# addresses id first, severity second, verified and terminal last-but-one
# and last, so four distinct cells are the minimum. A header narrower than
# this is degenerate — a findings header of a single id cell — and its
# width diagnostic is the whole structural report: its rows are not read.
ADDRESSABLE_ROW_CELLS = 4
# Width of the current schema, the one that carries the criterion column.
CRITERION_SCHEMA_WIDTH = 8
# A verification-passes row must reach the "new findings" cell (index 3) —
# the positional fallback used when the passes header does not name it.
NEW_FINDINGS_INDEX = 3
# Header cell names the passes table is read by, when it carries them.
NEW_FINDINGS_NAME = "new findings"
STARTED_NAME = "started"
ENDED_NAME = "ended"
# Length of the window the kill criterion looks at.
KILL_CRITERION_WINDOW = 3
# Severity classes always reported, in this order; any other value observed
# in the severity cell is reported after them, sorted.
SEVERITY_ORDER = ("blocker", "major", "minor")
# A row whose criterion cell is exactly this is refuted/refused, never upheld.
NOT_NEEDED = "—"
# The passes table's timestamps: ISO-8601 UTC, seconds resolution.
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class Row(TypedDict):
    """One parsed findings-table row, addressed by cell name."""

    id: str
    severity: str
    verified: str
    terminal: str
    criterion: str | None
    line: int


class PassRow(TypedDict):
    """One parsed verification-passes row.

    `new` is None when the row does not reach the new-findings cell or that
    cell holds no integer; `started`/`ended` are None when the table has no
    such column at all (a v1 passes table) and the raw cell text otherwise —
    including the empty string, which is a v2 cell that cannot be read.
    """

    ordinal: str
    new: int | None
    started: str | None
    ended: str | None


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
                    if width < ADDRESSABLE_ROW_CELLS:
                        # Degenerate header (`| id |`): too narrow for a row
                        # to carry id/severity/verified/terminal in distinct
                        # cells, so no row of this table can be read — the
                        # width diagnostic above IS the structural report
                        # (exit 2 at the call site). Reading on would index
                        # past the end of the row and raise an IndexError,
                        # which the shell would see as exit 1 — the code that
                        # means "open rows remain".
                        break
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
            # Severity is cell index 1 in BOTH schemas (7-cell and 8-cell),
            # which is why the distribution needs no schema detection.
            "severity": cells[1],
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


def signature_date_error(row_id: str, terminal: str) -> str | None:
    """Return a diagnostic when the signature date is not a calendar date.

    CALENDAR VALIDITY ONLY: `9999-99-99` and `2026-02-30` are rejected
    because they name no day. The date is NOT checked against today (a
    future date passes) and NOT checked for ordering against the finding.
    """
    m = SIGNED_DATE_RE.search(terminal)
    if m is None:
        return None
    try:
        date.fromisoformat(m.group(1))
    except ValueError:
        return (
            f"{row_id}: signature date {m.group(1)!r} is not a "
            f"calendar date (YYYY-MM-DD)"
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
        bad_date = signature_date_error(row["id"], t)
        if bad_date:
            return False, bad_date
        return True, None
    if t.startswith("refused-user-signed"):
        if not SIGNED_DATE_RE.search(t):
            return False, (
                f"{row['id']}: refusal signature carries no date "
                f"— the literal is 'refused-user-signed <date>' "
                f"(YYYY-MM-DD)"
            )
        bad_date = signature_date_error(row["id"], t)
        if bad_date:
            return False, bad_date
        return True, None
    if t.startswith("refused"):
        return False, (
            f"{row['id']}: refusal without the literal "
            f"'refused-user-signed' — a refused security/PII "
            f"finding is terminal only with the owner signature"
        )
    return False, None


def severity_line(rows: list[Row], open_ids: set[str]) -> str:
    """Return the severity distribution line (severity x terminal status).

    Severity is cell index 1 in both the 7-cell and the 8-cell schema, so
    this is computed for v1 and v2 ledgers alike, with no schema detection.
    The three canonical classes are always named — a ledger with no blocker
    is a fact worth printing — and any other value found in the cell is
    reported after them under its own name.
    """
    counts: dict[str, list[int]] = {s: [0, 0] for s in SEVERITY_ORDER}
    for r in rows:
        key = r["severity"].strip().lower() or "(blank)"
        bucket = counts.setdefault(key, [0, 0])
        bucket[0] += 1
        if r["id"] not in open_ids:
            bucket[1] += 1
    names = list(SEVERITY_ORDER) + sorted(k for k in counts if k not in SEVERITY_ORDER)
    body = " | ".join(f"{n} {counts[n][1]}/{counts[n][0]}" for n in names)
    return f"severity distribution (terminal/rows): {body}"


def upheld_line(rows: list[Row]) -> str:
    """Return the upheld/refuted split, or why it cannot be computed.

    UPHELD: the criterion cell is not the literal em-dash, OR the terminal
    cell begins with `refused` (the claim stood and the owner refused to
    act — not the same thing as a refuted claim). The split needs the
    criterion column, so a 7-cell legacy ledger reports `n/a` instead of
    guessing: a legacy row has no cell to read, not an empty one.
    """
    if any(r["criterion"] is None for r in rows):
        return "upheld/refuted: n/a (v1 ledger — no criterion column)"
    upheld = sum(1 for r in rows if is_upheld(r))
    return f"upheld/refuted: {upheld} upheld, {len(rows) - upheld} refuted"


def is_upheld(row: Row) -> bool:
    """Whether a finding stood: a real criterion, or a signed refusal."""
    refused = row["terminal"].strip().lower().startswith("refused")
    return row["criterion"] != NOT_NEEDED or refused


def passes_table(lines: list[str]) -> tuple[list[PassRow], bool]:
    """Return (rows, has_time_columns) for the verification-passes table.

    Binds to the FIRST table whose first header cell is `#`, exactly as
    before. The new-findings column is located BY NAME when the header
    names it and by index 3 otherwise, so every passes-table width already
    in the wild keeps reading the same cell. `started`/`ended` are read
    only when the header carries both: their absence is a v1 table, never
    an error.
    """
    rows: list[PassRow] = []
    header: list[str] = []
    in_table = False
    for raw in lines:
        stripped = raw.strip()
        if not in_table:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and cells[0] == "#":
                in_table = True
                header = [c.strip().lower() for c in cells]
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("|") or re.fullmatch(r"\|[-| :]+\|", stripped):
            continue
        cells = split_row(stripped)
        if not cells:
            continue
        idx = (
            header.index(NEW_FINDINGS_NAME)
            if NEW_FINDINGS_NAME in header
            else NEW_FINDINGS_INDEX
        )
        new: int | None = None
        if len(cells) > idx:
            m = re.search(r"\d+", cells[idx])
            if m:
                new = int(m.group())
        rows.append(
            {
                "ordinal": cells[0] if cells[0].isdigit() else str(len(rows) + 1),
                "new": new,
                "started": cell_by_name(cells, header, STARTED_NAME),
                "ended": cell_by_name(cells, header, ENDED_NAME),
            },
        )
    has_time = STARTED_NAME in header and ENDED_NAME in header
    return rows, has_time


def cell_by_name(cells: list[str], header: list[str], name: str) -> str | None:
    """Return a row's cell for a named column, or None if there is no column.

    None means "this table has no such column" (a v1 passes table); the
    empty string means the column exists and the cell is empty, which is a
    v2 cell that cannot be read — the two are deliberately not merged.
    """
    if name not in header:
        return None
    i = header.index(name)
    return cells[i] if i < len(cells) else ""


def parse_ts(cell: str) -> datetime | None:
    """Parse an ISO-8601 UTC timestamp at seconds resolution, or None."""
    if not TS_RE.fullmatch(cell.strip()):
        return None
    try:
        return datetime.strptime(cell.strip(), TS_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def time_axis_lines(rows: list[PassRow], *, has_time: bool) -> list[str]:
    """Return the time-axis lines that accompany the ordinal curve.

    REPORT-ONLY, always: nothing here reaches an exit code. A table without
    the two columns is a v1 table and says so in one line; a timestamp that
    is present but unparseable is named by row and column and the time axis
    is suppressed, leaving the ordinal curve above untouched.
    """
    if not has_time:
        return ["time axis: n/a (no started/ended columns — v1 passes table)"]
    bad: list[str] = []
    parsed: list[tuple[PassRow, datetime, datetime]] = []
    for p in rows:
        started, ended = parse_ts(p["started"] or ""), parse_ts(p["ended"] or "")
        for name, value in ((STARTED_NAME, started), (ENDED_NAME, ended)):
            if value is None:
                bad.append(
                    f"passes: row {p['ordinal']} '{name}' unparseable "
                    f"— time axis suppressed",
                )
        if started is not None and ended is not None:
            parsed.append((p, started, ended))
    if bad:
        return bad
    # Unreachable while the caller prints the axis only when the ordinal
    # curve is non-empty: a curve value comes from a row, so `rows` — and
    # with no `bad` entries, `parsed` — cannot be empty here. The guard is
    # kept deliberately, so a future caller that drops that gate gets a
    # printed line instead of an IndexError on `parsed[0]`.
    if not parsed:
        return ["time axis: n/a (passes table has no rows)"]
    origin = parsed[0][1]
    axis = " | ".join(
        f"+{int((s - origin).total_seconds())}s -> "
        f"{'?' if p['new'] is None else p['new']}"
        for p, s, _ in parsed
    )
    wall = " | ".join(
        f"{p['ordinal']}: {int((e - s).total_seconds())}s" for p, s, e in parsed
    )
    return [
        f"time-indexed curve (from {origin.strftime(TS_FORMAT)}): {axis}",
        f"pass wall-clock: {wall}",
    ]


def trace_line(path: str) -> str:
    """Return the one report-only line about the round's trace file.

    Nothing about a trace can change an exit code: a missing file, a
    directory, an undecodable file and a corrupt line are all reported and
    counted, never raised. The trace is not the ledger.
    """
    p = Path(path)
    try:
        with p.open(encoding="utf-8") as fh:
            raw = fh.readlines()
    except FileNotFoundError:
        return "trace: none"
    except (OSError, UnicodeDecodeError):
        return f"trace: unreadable ({p.name})"
    records, unreadable = 0, 0
    for line in raw:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            unreadable += 1
            continue
        if isinstance(obj, dict):
            records += 1
        else:
            unreadable += 1
    if unreadable:
        return f"trace: {records} records, {unreadable} unreadable lines skipped"
    return f"trace: {records} records"


def load(path: str) -> tuple[list[str] | None, str | None]:
    """Read a ledger file: return (lines, None), or (None, message).

    An input that cannot be opened or decoded is a STRUCTURAL error
    (exit 2 at the call site), never an uncaught traceback that the shell
    reports as exit 1 — the code that means "open rows remain".
    """
    try:
        with Path(path).open(encoding="utf-8") as fh:
            return fh.readlines(), None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except UnicodeDecodeError as exc:
        return None, f"cannot decode {path} as UTF-8: {exc}"


def main() -> int:
    """Recount the ledger named on the command line and return the exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    prev_path = None
    if "--prev" in args:
        i = args.index("--prev")
        if i + 1 >= len(args):
            print("--prev needs a path")
            print(__doc__)
            return 2
        prev_path = args[i + 1]
        del args[i : i + 2]
    trace_path = None
    if "--trace" in args:
        i = args.index("--trace")
        if i + 1 >= len(args):
            print("--trace needs a path")
            print(__doc__)
            return 2
        trace_path = args[i + 1]
        del args[i : i + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    lines, load_error = load(args[0])
    if lines is None:
        print(load_error)
        return 2

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
    print(severity_line(rows, set(open_rows)))
    print(upheld_line(rows))

    pass_rows, has_time = passes_table(lines)
    c = [p["new"] for p in pass_rows if p["new"] is not None]
    if c:
        print("new-findings curve:", " -> ".join(map(str, c)))
        if len(c) >= KILL_CRITERION_WINDOW and c[-1] >= c[-2] >= c[-3] and c[-3] > 0:
            print(
                "  KILL-CRITERION WARNING: curve has not decayed for "
                "three consecutive passes — stop and fork to the user.",
            )
        for line in time_axis_lines(pass_rows, has_time=has_time):
            print("  " + line)
    if trace_path:
        print(trace_line(trace_path))

    if prev_path:
        prev_lines, prev_load_error = load(prev_path)
        if prev_lines is None:
            print(prev_load_error)
            return 2
        prev_rows, prev_errors = parse_findings(prev_lines)
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
            # Unreachable while the three predicates above stay exhaustive:
            # an open id is either absent from `prev` (-> new_open) or
            # present with a truthy (-> regressed) / falsy (-> still) value,
            # so `uncovered` is always empty. The guard is kept deliberately:
            # it makes a future edit to the bucket predicates fail loudly
            # instead of silently dropping ids from the delta.
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
