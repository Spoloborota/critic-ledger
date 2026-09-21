#!/usr/bin/env python3
# The payload ships loose files rather than a package, so this module sits
# in no __init__.py: it is imported from `recount.py`'s own directory.
"""The ledger as data: its rows, its passes table, its register and its header.

Imported by `recount.py` from its own directory. Reading happens here once;
nothing here prints.
"""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypedDict

from ledger_md import (
    ADDRESSABLE_ROW_CELLS,
    CRITERION_FROM_END,
    CRITERION_MIN_WIDTH,
    FROZEN_STATE_RE,
    ID_PATTERN,
    ROUND_STARTED_RE,
    ROW_WIDTHS,
    V1_WIDTH,
    V2_WIDTH,
    V3_WIDTH,
    VERDICT_INDEX,
    VERDICT_INDEX_V3,
    ZONE_INDEX,
    header_field,
    scan_findings,
    scan_table,
)
from structural_checks import (
    REGISTER_STATUS_RE,
    class_tag_error,
    contract_status_error,
    criterion_error,
    logged_no_action_error,
    nomination_error,
    register_row_error,
    shelf_tag_error,
)

# The id contract, anchored: the grammar itself is `ledger_md.ID_PATTERN`,
# the ONE definition in the payload, and what is this script's own is only
# the anchoring — a cell is an id or it is not, there is no id INSIDE a
# cell. A second copy of the grammar here is exactly the divergence the
# single definition removes.
ID_RE = re.compile("^" + ID_PATTERN + "$")

# A verification-passes row must reach the "new findings" cell (index 3) —
# the positional fallback used when the passes header does not name it.
NEW_FINDINGS_INDEX = 3

# Header cell names the passes table is read by, when it carries them.
NEW_FINDINGS_NAME = "new findings"
STARTED_NAME = "started"
ENDED_NAME = "ended"

# The verdicts column is named `verdicts (L/P/NOT)` in the template and
# `verdicts` in older tables, so it is matched by PREFIX rather than by the
# full literal; index 2 is the positional fallback, as index 3 is for the
# new-findings cell.
VERDICTS_PREFIX = "verdicts"
VERDICTS_INDEX = 2

# The passes table's timestamps: ISO-8601 UTC, seconds resolution.
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# The security lens is declared in its own header field, in the same prefix
# alphabet and from the same source as `Lenses:`. The field is read by
# `ledger_md.header_field`, which holds every named field to EXACTLY ONE
# occurrence — the rule `Process prefixes:` below has always had and this
# one silently lacked while the two were parsed by two hand-made regexes.
SECURITY_LENS_FIELD = "Security lens"
LENS_PREFIX_RE = re.compile(r"[A-Z][A-Z0-9]{0,3}")
NO_SECURITY_LENS = "none"

# --- the prefixes that belong to a PROCESS rather than to a lens -----------
# Two writers put rows in the findings table that no lens raised: the
# fixer's `NOTICED OUTSIDE BATCH` channel and a class-kill gate. Their rows
# take an id prefix under the same contract as a lens's, so without a
# declaration they are machine-indistinguishable from a lens's rows. The
# field is read as a HEADER FIELD like any other and never through
# `LENSES_FIELD_RE`/`LENS_LINE_RE`, because a process prefix reaching
# `lens_prefixes` would inflate `k`. The field says what is NOT a lens; it
# never adds to what is.
PROCESS_PREFIXES_FIELD = "Process prefixes"
NO_PROCESS_PREFIXES = "none"

# Loose first, strict second: the loose form is what COUNTS the field (two of
# them is the observable collision), the strict one is what reads its value.
FREEZE_FIELD_RE = re.compile(r"^\s*[-*]?\s*stop-rule freeze:", re.IGNORECASE)
FREEZE_VALUE_RE = re.compile(
    r"^\s*[-*]?\s*stop-rule freeze:\s*(\d{4}-\d{2}-\d{2})\s*\|\s*"
    r"carried-to:\s*(\S.*?)\s*$",
    re.IGNORECASE,
)
CARRIED_TO_PENDING = "pending"

# Layout convention the register path is derived from when `--register` is
# absent; the docstring's register bullet states it as the contract.
RUN_ROOT_DIR = ".critic-ledger"
REGISTER_NAME = "residue-register.md"
REGISTER_HEADER_FIRST = "run-qualified id"
REGISTER_WIDTH = 8

# --- stopping metrics: the residual-defect ESTIMATE and the plateau --------
# k comes from ONE declared source — the machine part of the ledger header's
# `Lenses:` field, one line per lens, ` - <PREFIX> | <lens name> | <model>`.
# It is NEVER a count of distinct id prefixes in the findings table: a
# verifier pass writes its rows under the SAME id contract (`V1`, `V2`, …),
# so counting prefixes would inflate k with every verification pass. The
# verifier prefixes are declared in their own header field and never here,
# so they stay out of k by construction rather than by a guessing filter.
LENSES_FIELD_RE = re.compile(r"^\s*[-*]?\s*lenses:", re.IGNORECASE)
LENS_LINE_RE = re.compile(
    r"^\s+[-*]\s+([A-Z][A-Z0-9]{0,3})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*$",
)


# Chronology is DERIVED, never taken on trust from the argument order: each
# passed ledger declares its own start in this header field. The pattern is
# `ledger_md.ROUND_STARTED_RE`, imported above — this script used to carry a
# second copy of it, and what this script needs of it is the DATE (group 1)
# alone: its own window is ordered by calendar day.


class Row(TypedDict):
    """One parsed findings-table row, addressed by cell name."""

    id: str
    severity: str
    verdict: str
    verified: str
    terminal: str
    criterion: str | None
    zone: str | None
    fix: str
    line: int


class PassRow(TypedDict):
    """One parsed verification-passes row.

    `new` is None when the row does not reach the new-findings cell or that
    cell holds no integer; `started`/`ended` are None when the table has no
    such column at all (a v1 passes table) and the raw cell text otherwise —
    including the empty string, which is a v2 cell that cannot be read.
    `verdicts` is the raw cell text of the verdicts column, or None when the
    row does not reach it: what it MEANS is decided by `not_landed`, which
    is the one place that reads it, and never here. `new_text` is the raw
    new-findings cell beside the integer `new`, for the same reason: the
    severity of those findings is written there in prose (`1 (V1-1,
    minor)`) and only `new_findings_severity` reads it.
    """

    ordinal: str
    new: int | None
    new_text: str | None
    verdicts: str | None
    started: str | None
    ended: str | None


class RegisterRow(TypedDict):
    """One parsed residue-register row, addressed by cell name.

    `status` is the bare status word and `status_date` the date that word
    carries; `cycle` is the re-open counter, 1 unless the row spells a
    higher one out as `(#<n>)`.
    """

    rid: str
    severity: str
    review_by: date
    status: str
    status_date: date
    cycle: int
    line: int


def parse_findings(lines: list[str]) -> tuple[list[Row], list[str]]:
    """Return (rows, errors); rows = list of dicts for the FIRST findings
    table only (header `| id |` ... up to the next heading).
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    rows: list[Row] = []
    errors: list[str] = []
    header_line, width, candidates = scan_findings(lines)
    if header_line == 0:
        return rows, errors
    if width not in ROW_WIDTHS:
        errors.append(
            f"line {header_line}: findings header has {width} "
            f"cells; the table must be {V1_WIDTH}-cell (v1, "
            f"legacy), {V2_WIDTH}-cell (v2, with criterion) "
            f"or {V3_WIDTH}-cell (v3, with zone)",
        )
        if width < ADDRESSABLE_ROW_CELLS:
            # Degenerate header (`| id |`): too narrow for a row to carry
            # id/severity/verified/terminal in distinct cells, so no row of
            # this table can be read — the width diagnostic above IS the
            # structural report (exit 2 at the call site). Reading on would
            # index past the end of the row and raise an IndexError, which
            # the shell would see as exit 1 — the code that means "open rows
            # remain".
            return rows, errors
    for n, stripped, cells in candidates:
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
                f"(<Prefix>-<n>, every prefix segment letter-led, "
                f"dash-joined segments allowed as in `V-CIT-1`): "
                f"{cells[0]!r}",
            )
            continue
        # criterion/fix/verified/terminal are addressed from the END: one
        # addressing serves all three schemas (7-, 8- and 9-cell), and the
        # zone column was inserted THIRD so that it stays that way. A hard
        # index from the start would read `verdict` prose as the criterion
        # of a v3 row — a check silently switched off.
        row: Row = {
            "id": cells[0],
            # Severity is cell index 1 in ALL THREE schemas, which is why
            # the distribution needs no schema detection.
            "severity": cells[1],
            # `verdict` is the one cell the zone column displaces, so it is
            # the one cell still taken by a start index — and the branch is
            # written out rather than inferred.
            "verdict": cells[VERDICT_INDEX_V3 if width == V3_WIDTH else VERDICT_INDEX],
            "verified": cells[-2],
            "terminal": cells[-1],
            "criterion": (
                cells[CRITERION_FROM_END] if width >= CRITERION_MIN_WIDTH else None
            ),
            "zone": cells[ZONE_INDEX] if width == V3_WIDTH else None,
            "fix": cells[-3],
            "line": n,
        }
        problem = (
            criterion_error(row)
            or class_tag_error(row)
            or shelf_tag_error(row)
            or nomination_error(row)
            or contract_status_error(row)
            or logged_no_action_error(row)
        )
        if problem:
            errors.append(problem)
            continue
        rows.append(row)
    return rows, errors


def lens_prefixes(lines: list[str]) -> list[str]:
    """Return the lens id prefixes declared in the header's `Lenses:` field.

    ONE source, and it is this one. The field's machine part is a run of
    lines directly under it, each ` - <PREFIX> | <lens name> | <model>`;
    reading stops at the first line that does not take that shape, so
    nothing further down the header can drift into the count. A prefix is
    counted once however many times it is written.

    What this deliberately does NOT do is count distinct id prefixes in the
    findings table: verifier passes write their rows under `V1`, `V2`, … by
    the same id contract as a lens, so that count would grow with every
    verification pass. Verifier prefixes are declared in their own header
    field and never in this one.
    """
    out: list[str] = []
    seen: set[str] = set()
    for n, raw in enumerate(lines):
        if not LENSES_FIELD_RE.match(raw.rstrip("\n")):
            continue
        for follower in lines[n + 1 :]:
            m = LENS_LINE_RE.match(follower.rstrip("\n"))
            if m is None:
                break
            if m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(m.group(1))
        break
    return out


def security_lens(lines: list[str]) -> tuple[str | None, str | None]:
    """Return (the declared security lens's prefix, error-or-None).

    The field is `Security lens: <PREFIX> | none`, in the same alphabet as
    the `Lenses:` prefixes. `none` and an ABSENT field both mean there is no
    security lens and no backstop — the absent case is what makes every
    ledger written before this field recount unchanged. A field that is
    present but reads as neither is a STRUCTURAL error rather than a silent
    "no backstop": this field arms a gate, and a gate that disarms itself on
    a typo is worse than no gate. TWO such fields are a structural error for
    the same reason, which is `ledger_md.header_field`'s rule for every
    named field alike: reading the first and saying nothing hides the
    overwrite the second line is.
    """
    value, field_error = header_field(lines, SECURITY_LENS_FIELD)
    if field_error is not None:
        return None, field_error
    if value is None:
        return None, None
    if value.lower() == NO_SECURITY_LENS:
        return None, None
    if LENS_PREFIX_RE.fullmatch(value):
        return value, None
    return None, (
        f"header field `Security lens:` reads {value!r} — it must be a "
        f"lens prefix ([A-Z][A-Z0-9]{{0,3}}, the `Lenses:` alphabet) or "
        f"the literal `{NO_SECURITY_LENS}`"
    )


def process_prefixes(lines: list[str]) -> tuple[list[str], str | None]:
    """Return (the declared process-row prefixes, error-or-None).

    The field is `Process prefixes: <PREFIX>[, <PREFIX>…]` or the literal
    `none`, in the same alphabet as the `Lenses:` prefixes and read as a
    header field like any other. It is a declaration of what is NOT a lens:
    the fixer's `NOTICED OUTSIDE BATCH` channel and a class-kill gate write
    rows under a prefix of the same shape as a lens's, and a reader with no
    such field cannot tell the two apart machine-side.

    `none` and an ABSENT field both mean no process prefix was declared, and
    the absent case is what makes every ledger written before this field
    recount unchanged — `k` in particular is untouched either way, because
    this parse never feeds `lens_prefixes`. A field that is present but reads
    as neither is a STRUCTURAL error rather than a silent "none", for the
    same reason the security-lens field is: a declaration that disarms itself
    on a typo is worse than no declaration. PRESENCE is read off the field
    NAME, so a line that ends AT THE COLON is a present field with an empty
    value and not an absent one: a gate whose arming hangs on a trailing
    space an editor may strip is not armed at all. And the field is ONE per
    ledger — two such lines are a STRUCTURAL error, never "take the first
    and say nothing".
    """
    value, field_error = header_field(lines, PROCESS_PREFIXES_FIELD)
    if field_error is not None:
        return [], field_error
    if value is None:
        return [], None
    if value.lower() == NO_PROCESS_PREFIXES:
        return [], None
    parts = [part.strip() for part in value.split(",")]
    if all(LENS_PREFIX_RE.fullmatch(part) for part in parts) and parts:
        return list(dict.fromkeys(parts)), None
    return [], (
        f"header field `Process prefixes:` reads {value!r} — it must be "
        f"comma-separated prefixes ([A-Z][A-Z0-9]{{0,3}}, the `Lenses:` "
        f"alphabet) or the literal `{NO_PROCESS_PREFIXES}`"
    )


def stop_rule_freeze(
    lines: list[str],
) -> tuple[tuple[date, str] | None, str | None]:
    """Return ((freeze date, carried-to), error-or-None) from the header.

    ONE field per ledger, written ONCE by whichever freeze occasion came
    first. The field has two independent writers — the contract's stop rule
    firing, and the one-off freeze of an exhausted blocker — so a second one
    finding the field already filled must not overwrite it, and the shape
    that overwrite would take in the file is a SECOND field line. That is
    what is rejected here: two lines are a structural error, never "take the
    first and say nothing".
    """
    found = [raw.rstrip("\n") for raw in lines if FREEZE_FIELD_RE.match(raw)]
    if not found:
        return None, None
    if len(found) > 1:
        return None, (
            f"the header carries {len(found)} `Stop-rule freeze:` fields — "
            f"the field is ONE per ledger and is written ONCE, by the first "
            f"freeze occasion; a later occasion keeps the first date and "
            f"dates its own row instead. Overwriting it is a structural "
            f"error, not a silent replacement"
        )
    m = FREEZE_VALUE_RE.match(found[0])
    if m is None:
        return None, (
            f"header field `Stop-rule freeze:` does not take its literal "
            f"shape `Stop-rule freeze: <YYYY-MM-DD> | carried-to: <next run "
            f"id | pending>`: {found[0].strip()!r}"
        )
    try:
        when = date.fromisoformat(m.group(1))
    except ValueError:
        return None, (
            f"header field `Stop-rule freeze:` carries date {m.group(1)!r} — "
            f"not a calendar date (YYYY-MM-DD)"
        )
    return (when, m.group(2)), None


def round_started(lines: list[str]) -> date | None:
    """Return the ledger's `Round-started:` date, or None if it is not read.

    A date that is absent, unparseable or not a calendar-valid one is None:
    the chronology of a window of ledgers is DERIVED from this field, and a
    field that cannot be read never becomes a guess.
    """
    for raw in lines:
        m = ROUND_STARTED_RE.match(raw.rstrip("\n"))
        if m is None:
            continue
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def resolve_register(ledger_path: str, explicit: str | None) -> tuple[Path | None, str]:
    """Return (the residue register's path, reason-when-None).

    With `--register` the path is taken as given, whatever it is. Without
    the flag it is DERIVED from the layout convention the docstring states
    as this script's contract: the register sits beside the run folders, in
    the `.critic-ledger/` directory that CONTAINS the ledger. Walking the
    ledger's ancestors for that directory name serves both the ordinary
    address and an archived one nested further down, without either being
    special-cased. A ledger outside such a directory derives nothing.
    """
    if explicit is not None:
        return Path(explicit), ""
    for parent in Path(ledger_path).resolve().parents:
        if parent.name == RUN_ROOT_DIR:
            return parent / REGISTER_NAME, ""
    return None, (
        f"path not derived — the ledger is outside a {RUN_ROOT_DIR}/ directory"
    )


def parse_register(lines: list[str]) -> tuple[list[RegisterRow], list[str]]:
    """Return (rows, errors) for the residue register's single table.

    The table is the FIRST one whose header's first cell is
    `run-qualified id`; rows are read up to the next markdown heading. The
    width is fixed at eight — the register is a new file with one schema,
    so it has no legacy width to accept.
    """
    rows: list[RegisterRow] = []
    errors: list[str] = []
    header_line, header, candidates = scan_table(
        lines, first_cell=REGISTER_HEADER_FIRST
    )
    if header_line and len(header) != REGISTER_WIDTH:
        errors.append(
            f"line {header_line}: register header has {len(header)} cells; "
            f"the table is {REGISTER_WIDTH}-cell",
        )
        candidates = []
    for n, stripped, cells in candidates:
        if cells is None or len(cells) != REGISTER_WIDTH:
            errors.append(
                f"line {n}: malformed register row "
                f"({0 if cells is None else len(cells)} cells, need "
                f"{REGISTER_WIDTH} — unescaped pipe?): {stripped[:80]}",
            )
            continue
        problem = register_row_error(cells, n)
        if problem:
            errors.append(problem)
            continue
        m = REGISTER_STATUS_RE.match(cells[6].strip())
        if m is None:
            # Unreachable: `register_row_error` above returns a message for
            # exactly this case and the row was skipped there. The guard
            # narrows the type without an assert, and a future edit that
            # loosens that check drops the row instead of raising.
            continue
        rows.append(
            {
                "rid": cells[0],
                "severity": cells[1],
                "review_by": date.fromisoformat(cells[5].strip()),
                "status": m.group(1),
                "status_date": date.fromisoformat(m.group(2)),
                "cycle": int(m.group(3)) if m.group(3) else 1,
                "line": n,
            },
        )
    seen: set[str] = set()
    for r in rows:
        if r["rid"] in seen:
            errors.append(
                f"line {r['line']}: DUPLICATE REGISTER ID {r['rid']} — one "
                f"row per nominee",
            )
        seen.add(r["rid"])
    return rows, errors


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
    _, header_cells, candidates = scan_table(lines, first_cell="#", fold_case=False)
    header = [c.strip().lower() for c in header_cells]
    for _n, _stripped, cells in candidates:
        if not cells:
            continue
        # Compatibility branches: the index-3 fallback of `idx` below and the
        # tolerant `started`/`ended` read.
        # no live writer; kept for c29…c34, c73.
        idx = (
            header.index(NEW_FINDINGS_NAME)
            if NEW_FINDINGS_NAME in header
            else NEW_FINDINGS_INDEX
        )
        new: int | None = None
        new_text: str | None = cells[idx] if len(cells) > idx else None
        if new_text is not None:
            m = re.search(r"\d+", new_text)
            if m:
                new = int(m.group())
        vidx = next(
            (i for i, h in enumerate(header) if h.startswith(VERDICTS_PREFIX)),
            VERDICTS_INDEX,
        )
        rows.append(
            {
                "ordinal": cells[0] if cells[0].isdigit() else str(len(rows) + 1),
                "new": new,
                "new_text": new_text,
                "verdicts": cells[vidx] if vidx < len(cells) else None,
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


@dataclass(frozen=True)
class Ledger:
    """One ledger as it is read once: header fields, tables and register inputs.

    Each header field sits beside its own error, exactly as its reader
    returns the pair, because the structural phase appends those errors
    between the ones derived from the rows. `ledger_state` holds the state
    lines that mark the ledger frozen, and is empty when it is not. The
    residue register is carried as the two inputs of its resolution, the
    ledger path and the literal `--register` value, never as a resolved
    register: whether it is in play depends on the nominations, and those
    are counted later.
    """

    lens_prefixes: list[str]
    security_lens: str | None
    security_lens_error: str | None
    process_prefixes: list[str]
    process_prefixes_error: str | None
    stop_rule_freeze: tuple[date, str] | None
    stop_rule_freeze_error: str | None
    ledger_state: list[str]
    rows: list[Row]
    pass_rows: list[PassRow]
    has_time: bool
    ledger_path: str
    register_arg: str | None


def read_ledger(
    lines: list[str],
    *,
    ledger_path: str,
    register_arg: str | None,
) -> tuple[Ledger, list[str]]:
    """Read a ledger's header fields and tables: (ledger, findings-table errors).

    Every header field is read here ONCE, by its own reader, and nowhere
    else. The errors returned are the findings table's own; a header
    field's error travels in the ledger beside its field. Nothing here
    resolves, reads or weighs the residue register: the path and the flag
    value are stored as given.
    """
    lenses = lens_prefixes(lines)
    security, security_error = security_lens(lines)
    process, process_error = process_prefixes(lines)
    freeze, freeze_error = stop_rule_freeze(lines)
    state = [
        raw
        for raw in lines
        if raw.strip().lower().startswith(("- ledger state:", "ledger state:"))
        and FROZEN_STATE_RE.match(raw.split(":", 1)[1].strip())
    ]
    rows, errors = parse_findings(lines)
    pass_rows, has_time = passes_table(lines)
    ledger = Ledger(
        lens_prefixes=lenses,
        security_lens=security,
        security_lens_error=security_error,
        process_prefixes=process,
        process_prefixes_error=process_error,
        stop_rule_freeze=freeze,
        stop_rule_freeze_error=freeze_error,
        ledger_state=state,
        rows=rows,
        pass_rows=pass_rows,
        has_time=has_time,
        ledger_path=ledger_path,
        register_arg=register_arg,
    )
    return ledger, errors
