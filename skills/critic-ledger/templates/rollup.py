#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Reference rollup for a critic-ledger round — reads the round's T1 trace
(`trace.jsonl`) together with its ledger (`fix-ledger.md`) and writes
`round-summary.json` beside the ledger plus a human table on stdout.
Observability is optional and OFF by default; nothing here runs unless the
round switched it on, and a round that never wrote a trace still gets a
summary.

Exit codes, and why they are what they are
------------------------------------------
`trace.py` is the ONE script in this repository that must never fail
closed — this one is not that script, so it does have a non-zero code,
and it is reachable ONLY when the script was not given its input:

    0  the summary was written (whatever the data said), or `-h`/`--help`
    2  usage error — including a BARE invocation, which is not a help
       request — or the ledger could not be read or holds no findings
       table: nothing could be summarised

NO observability condition reaches an exit code. A missing, unreadable or
corrupt trace, a refused `mode`, an unmeasurable metric, a floor refusal,
a disagreement between the trace and the ledger: every one of them is
report-only and exits 0. Observability adds no blocking gate; no metric,
script or gate fails because tokens are absent; nothing on the closing
stage's list can fail a round; and aggregation changes no exit code. A
round is never failed by its own instrument.

No free text reaches the output
-------------------------------
Every value in `round-summary.json` and in the printed table is a count, a
duration, a metric value, or a string from a closed vocabulary. The ledger
is full of prose — claims, verdicts, criteria — and NONE of it is copied:
severity cells are bucketed into `blocker`/`major`/`minor`/`blank`/`other`,
terminal cells into the four canonical statuses plus `open`, and every
identifier written out (`round`, `object_slug`, `mode`, lens prefixes,
batch ids, commits) is re-checked against its anchored schema pattern
before it is written — `object_slug` and `mode` by THIS script, since they
live in the summary rather than in a span. A value that fails is refused
rather than written: one `schema-refused` diagnostic from the closed
error-class vocabulary, and the summary is written anyway.

What is computed
----------------
    M1 CFR   upheld(prefix)/raised(prefix) per LENS, the lenses being the
             `id_prefix` values of the round's `critic` spans — never the
             prefixes found in the ledger (M1's zero-lens carve-out)
    M2 FPL   landed-at-first-pass(B)/ids(B) per FIX BATCH, ids taken from
             the fixer span, credit only to the LAST batch carrying an id
             (RE-FIX ATTRIBUTION)
    M3 VP    upheld(V<p>)/raised(V<p>) per VERIFICATION PASS, `V<p>` being
             the pass's verifier-prefix off its verifier spans
             (VERIFICATION-RAISED)
    M4 TVR   a VECTOR — the four token counters, `fresh`, `reuse` and the
             always-available `seconds`, each over the round's terminal
             rows. No counter is pre-summed with a differently-priced one
    M5 FADS  fix-application-tagged share of the verification-raised rows

Every one of them is `n/a: <reason>` where its inputs are missing — never
`0`, never `1.0`, never silently omitted (EMPTY DENOMINATOR). A `null` is
never aggregated into a total: any group holding a span with
`tokens: null` yields `null` plus a coverage string.

The T2 line, and when it is written
-----------------------------------
`--rounds <path>` appends ONE line — an identifier-free PROJECTION of the
round summary, never the summary itself — to the cross-project rollup
`${CLAUDE_PLUGIN_DATA}/rounds.jsonl`. The path is passed in because the
placeholder is substituted in skill content, and because this script
shells out to nothing at all — it is forbidden a child process — and so
cannot resolve the placeholder itself. The projection drops
`object_slug`, replaces `round` with an opaque `round_key` (first 12 hex
of its SHA-256), replaces the absolute timestamps with the UTC day the
round closed, and drops every batch commit. It is built from the local
summary only — the trace is never re-read for it.
The closing stage appends the line BEFORE it closes the round span, so on
the ordinary path `ended` is not yet on disk and the day
comes from this script's own clock; the line is skipped only when the
round id itself was refused and no `round_key` can be computed.

Usage:  rollup.py <fix-ledger.md> [--trace <trace.jsonl>]
                  [--out <round-summary.json>] [--rounds <rounds.jsonl>]
        rollup.py -h | --help                        (this text, exit 0)
Defaults: `--trace` and `--out` sit beside the ledger; `--rounds` is not
written unless it is given.
"""  # noqa: D205  # printed usage text; reflowing it would change output

import hashlib
import json
import re
import sys
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypedDict

SUMMARY_NAME = "round-summary.json"
TRACE_NAME = "trace.jsonl"
PROJECTION_VERSION = 1

# The closed error-class vocabulary, shared with trace.py: widening one
# widens both.
ERROR_CLASSES = (
    "unreadable",
    "unparseable-line",
    "no-usage",
    "id-not-found",
    "schema-refused",
    "write-failed",
)
DIAGNOSTIC_RE = re.compile(
    r"^(unreadable|unparseable-line|no-usage|id-not-found|schema-refused"
    r"|write-failed): [\w./-]+(:\d+)?$",
)

SCHEMA_VERSION = 1
ROUND_SPAN = "s1.00"
ACTORS = (
    "orchestrator",
    "critic",
    "fixer",
    "verifier",
    "script",
    "subagent-observed",
)
# Actors that measure a spawn — the only spans that can carry usage at
# all, and therefore the coverage universe of the token totals (an
# `orchestrator` span's `tokens` is null permanently, which is a property
# of the main loop's spend, not a failed measurement).
SPAWN_ACTORS = ("critic", "fixer", "verifier", "subagent-observed")

ROUND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}-[a-z0-9][a-z0-9-]{0,39}$")
OBJECT_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
MODE_RE = re.compile(r"^(plan|impl)$")
SPAN_RE = re.compile(r"^s[1-9]\.\d{2,4}$")
PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,7}$")
PASS_UNIT_RE = re.compile(r"^P\d{1,4}$")
BATCH_UNIT_RE = re.compile(r"^[A-Z]{1,2}\d{1,3}[a-z]?$")
MODEL_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]{0,31}|n/a)$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_LENGTH = 10
ROUND_PREFIX_LENGTH = 18  # `YYYY-MM-DD-HHMMSS-`, before the object segment

MAX_ROUND_LEN = 58
MAX_SLUG_LEN = 32
MAX_MODEL_LEN = 34  # 32 for the pattern, or the literal `n/a`
MAX_COMMIT_LEN = 40
MAX_SPAN_LEN = 8
MAX_UNIT_LEN = 8
# The widest `unit` any actor may carry (`subagent-observed`).
MAX_UNIT_TEXT_LEN = 32
TAG_STAGE = 6
FIX_APPLICATION_TAG = "fix-application"

# The schema's slug derivation, applied before a value reaches any file.
SLUG_FALLBACK = "object"
NON_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Findings-table cell vocabularies. The ledger's cells are PROSE; these
# buckets are what the summary is allowed to carry.
SEVERITY_BUCKETS = ("blocker", "major", "minor", "blank", "other")
TERMINAL_BUCKETS = (
    "verified-landed",
    "refuted-with-reason",
    "accepted-residue",
    "refused-user-signed",
    "open",
)
# A row whose criterion cell is exactly this is refuted/refused, never
# upheld.
NOT_NEEDED = "—"
# An owner signature is the literal `user-signed` immediately followed by
# an ISO date — the recount's own contract, reused so that a terminal row
# here is a terminal row there.
SIGNED_DATE_RE = re.compile(r"user-signed\s+(\d{4}-\d{2}-\d{2})")
LEGACY_WIDTH = 7
CRITERION_WIDTH = 8
CRITERION_INDEX = 4
MIN_ROW_CELLS = 2
NEW_FINDINGS_NAME = "new findings"
NEW_FINDINGS_INDEX = 3
BUNDLED_NAME = "bundled"
ESC = "\x00PIPE\x00"

# The `n/a: <reason>` strings, closed. The first three are the EMPTY
# DENOMINATOR vocabulary; the rest name the other ways an input can be
# missing, and every one of them is a fixed string plus at most two
# bounded counts.
NA_NO_LENSES = "n/a: no lenses spawned"
NA_BATCH_NO_IDS = "n/a: batch has no ids"
NA_PASS_NO_FINDINGS = "n/a: pass raised no findings"  # noqa: S105  # a reason string
# The closed list above names the empty denominator of a PASS; a lens
# whose prefix carries no ledger row is the same shape one metric over,
# and it gets its own string rather than borrowing the pass's — a lens is
# not a pass, and a reason that names the wrong unit is a small lie in the
# one place this summary must be honest about what was not measured.
NA_LENS_NO_FINDINGS = "n/a: lens raised no findings"
NA_V1_LEDGER = "n/a: v1 ledger (no criterion column)"
NA_NO_BATCHES = "n/a: no fix batches"
NA_NO_PASSES = "n/a: no verification passes"
NA_NO_COVERING_PASS = "n/a: no verification pass covers this batch"  # noqa: S105
NA_NO_TERMINAL = "n/a: round has no terminal rows"
NA_NO_RAISED = "n/a: no verification-raised findings"
NA_NO_SPAWN_SPANS = "n/a: no span carries usage"

# The report-only defect classes this script prints, in their bounded
# form — a closed class plus one bounded locator, and nothing else. None
# of them changes the exit code.
DEFECT_CLASSES = (
    "duplicate-span",
    "wallclock-mismatch",
    "outcome-ledger-disagreement",
    "new-findings-disagreement",
    "bundled-disagreement",
    "pass-floor-refused",
)

TOKEN_KEYS = ("in", "out", "cache_write", "cache_read")
# The one OPTIONAL key of the `tokens` object. It is the tool result's
# `totalTokens`, kept on disk so `trace.py validate` can re-derive its
# cross-check; no sum here reads it and it reaches no output — the four
# counters are the priced quantities (M4).
TOKEN_TOTAL_KEY = "total"  # noqa: S105  # a JSON key name, not a credential


class Finding(TypedDict):
    """One parsed findings-table row, reduced to the cells the metrics read."""

    id: str
    severity: str
    verified: str
    terminal: str
    criterion: str | None


class PassRow(TypedDict):
    """One parsed verification-passes row: its ordinal and two cells."""

    ordinal: int
    new: int | None
    bundled: bool | None


class Trace(TypedDict):
    """The reduced trace: closed spans, plus what could not be reduced."""

    spans: list[dict[str, object]]
    opens: dict[str, dict[str, object]]
    unclosed: int
    refused: int
    defects: list[str]
    present: bool


# ---------------------------------------------------------------------------
# diagnostics and typed readers — never trust the shape of a line
# ---------------------------------------------------------------------------


def diagnostic(error_class: str, name: str, line: int | None = None) -> str:
    """Build the one diagnostic line: a closed class plus a file name.

    The name is reduced to its basename and every character outside
    `[A-Za-z0-9._-]` is replaced, so the line cannot carry content through
    a crafted path. A line that still fails the diagnostic form is
    replaced by a bounded last-resort line rather than printed.
    """
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", Path(name).name) or "rollup"
    text = f"{error_class}: {safe}" if line is None else f"{error_class}: {safe}:{line}"
    if error_class not in ERROR_CLASSES or not DIAGNOSTIC_RE.match(text):
        return "schema-refused: rollup"
    return text


def as_object(value: object) -> dict[str, object] | None:
    """Return a str-keyed mapping, or None when the value is not one."""
    if not isinstance(value, dict):
        return None
    out: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def as_str_list(value: object) -> list[str] | None:
    """Return a list of strings, or None when the value is not one."""
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        out.append(item)
    return out


def as_int(value: object) -> int | None:
    """Return an int, or None. `True` is a bool, not the integer 1."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def as_str(value: object) -> str | None:
    """Return a string, or None when the value is not one."""
    return value if isinstance(value, str) else None


def parse_timestamp(value: object) -> datetime | None:
    """Return the datetime of an ISO-8601 UTC second-resolution string."""
    text = as_str(value)
    if text is None or not TIMESTAMP_RE.match(text):
        return None
    try:
        return datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def bounded(value: object, pattern: re.Pattern[str], max_len: int) -> bool:
    """Report whether a value is a string matching an anchored, bounded pattern."""
    text = as_str(value)
    return text is not None and len(text) <= max_len and pattern.match(text) is not None


def slug(text: str) -> str:
    """Derive a bounded object slug from a name this project does not control.

    The schema's own derivation, verbatim: NFKC-normalize, lowercase,
    replace every run of characters outside `a-z0-9` with a single `-`,
    strip leading and trailing `-`, truncate to the maximum length, strip a
    trailing `-` again; an empty result becomes the literal `object`. The
    derivation is total and idempotent — no input, including one crafted to
    carry a path, a quote or a newline, can produce a value outside the
    pattern.
    """
    normalized = unicodedata.normalize("NFKC", text).lower()
    reduced = NON_SLUG_RE.sub("-", normalized).strip("-")
    return reduced[:MAX_SLUG_LEN].rstrip("-") or SLUG_FALLBACK


# ---------------------------------------------------------------------------
# the ledger — prose in, counts out
# ---------------------------------------------------------------------------


def split_row(line: str) -> list[str] | None:
    """Return the inner cells of a markdown table row, or None if malformed."""
    cells = [
        c.strip().replace(ESC, "|") for c in line.replace("\\|", ESC).strip().split("|")
    ]
    if len(cells) < MIN_ROW_CELLS or cells[0] != "" or cells[-1] != "":
        return None
    return cells[1:-1]


def parse_findings(lines: list[str]) -> tuple[list[Finding], int]:
    """Return the FIRST findings table's rows and its header width.

    The table is bound exactly as `recount.py` binds it — the first header
    whose first cell is `id`, rows up to the next markdown heading, 7 or 8
    cells wide — but a malformed row is SKIPPED here rather than made a
    structural error: the recount is the closure gate, this script is an
    instrument and may not fail a round over a table it did not write.
    """
    rows: list[Finding] = []
    in_table = False
    width = 0
    for raw in lines:
        stripped = raw.strip()
        if not in_table:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and cells[0].lower() == "id":
                in_table = True
                width = len(cells)
                if width not in (LEGACY_WIDTH, CRITERION_WIDTH):
                    return [], width
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("|") or re.fullmatch(r"\|[-| :]+\|", stripped):
            continue
        cells = split_row(stripped)
        if cells is None or len(cells) != width or not ID_RE.match(cells[0]):
            continue
        rows.append(
            {
                "id": cells[0],
                "severity": cells[1],
                "verified": cells[-2],
                "terminal": cells[-1],
                "criterion": (
                    cells[CRITERION_INDEX] if width == CRITERION_WIDTH else None
                ),
            },
        )
    return rows, width


def parse_passes(lines: list[str]) -> list[PassRow]:
    """Return the verification-passes rows: ordinal, new findings, bundled.

    Binds to the first table whose first header cell is `#`, and locates
    the new-findings column BY NAME where the header names it and by index
    3 otherwise — the positional behaviour of every passes table already in
    the wild. A table without a `bundled` column yields `None` there, which
    is a v1 table and neither a disagreement nor a defect.
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
        index = (
            header.index(NEW_FINDINGS_NAME)
            if NEW_FINDINGS_NAME in header
            else NEW_FINDINGS_INDEX
        )
        new: int | None = None
        if len(cells) > index:
            match = re.search(r"\d+", cells[index])
            if match:
                new = int(match.group())
        digits = re.search(r"\d+", cells[0])
        rows.append(
            {
                "ordinal": int(digits.group()) if digits else len(rows) + 1,
                "new": new,
                "bundled": ledger_bundled(cells, header),
            },
        )
    return rows


def ledger_bundled(cells: list[str], header: list[str]) -> bool | None:
    """Read the passes table's own `bundled` cell — the human twin of the flag.

    None means the table has no such column (a v1 passes table) or the
    cell holds neither word; the trace is the source of the value either
    way, and this cell is only ever cross-checked against it.
    """
    if BUNDLED_NAME not in header:
        return None
    index = header.index(BUNDLED_NAME)
    if index >= len(cells):
        return None
    text = cells[index].strip().lower()
    if text in ("yes", "true"):
        return True
    return False if text in ("no", "false") else None


def parse_mode(lines: list[str]) -> tuple[str | None, bool]:
    """Return (mode, refused) read from the ledger header's `- Mode:` line.

    The read is of THAT line specifically, never of the
    `Prerequisite (stage 0)` line's `{normal | DEGRADED}`, which is a
    different property carried by the trace's `degraded` flag. A
    line that is missing yields (None, False) — nothing to refuse; a line
    holding neither `plan` nor `impl` yields (None, True), one
    `schema-refused` diagnostic at the call site, and the summary is
    written anyway.
    """
    for raw in lines:
        match = re.match(r"^\s*-\s*mode:\s*(.*)$", raw.strip(), re.IGNORECASE)
        if match is None:
            continue
        value = match.group(1).strip().rstrip(".").strip()
        if MODE_RE.match(value):
            return value, False
        return None, True
    return None, False


def severity_bucket(cell: str) -> str:
    """Bucket a severity cell into the closed vocabulary the summary carries."""
    text = cell.strip().lower()
    if not text:
        return "blank"
    return text if text in SEVERITY_BUCKETS else "other"


def signed(text: str) -> bool:
    """Whether a terminal cell carries a signature with a CALENDAR-valid date.

    `9999-99-99` names no day and is not a signature; the date is not
    checked against today and not ordered against the finding — exactly
    the recount's own rule.
    """
    match = SIGNED_DATE_RE.search(text)
    if match is None:
        return False
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return False
    return True


def terminal_bucket(row: Finding) -> str:
    """Bucket a row's terminal status by the recount's own predicate.

    The metrics reuse the recount's LANDED and UPHELD predicates *"so a
    metric can never disagree with closure"*; terminality is bucketed under the
    same rule rather than off the cell's first word. A row whose terminal
    cell NAMES a status it does not satisfy — `verified-landed` with no
    LANDED verdict, `accepted-residue` or `refused-user-signed` without a
    dated owner signature, a bare `refused` — counts as `open` here
    because it counts as non-terminal there, and M4's denominator is
    `count(terminal rows)`.
    """
    text = row["terminal"].strip().lower()
    if text.startswith("verified-landed"):
        return "verified-landed" if is_landed(row["verified"]) else "open"
    if text.startswith("refuted-with-reason"):
        return "refuted-with-reason"
    if text.startswith("accepted-residue"):
        return "accepted-residue" if signed(text) else "open"
    if text.startswith("refused-user-signed"):
        return "refused-user-signed" if signed(text) else "open"
    return "open"


def is_landed(verified: str) -> bool:
    """Apply the LANDED predicate — the recount's own, deliberately reused.

    `LANDED OTHERWISE (...)` with a non-empty parenthetical counts as
    landed; an empty one does not, and neither does anything carrying
    `NOT LANDED`.
    """
    upper = verified.upper()
    if "NOT LANDED" in upper or "LANDED" not in upper:
        return False
    if re.search(r"LANDED\s+OTHERWISE", verified, re.IGNORECASE):
        match = re.search(r"LANDED\s+OTHERWISE\s*\(([^)]*)\)", verified, re.IGNORECASE)
        return bool(match and match.group(1).strip())
    return True


def is_not_landed(verified: str) -> bool:
    """Report whether a verified cell carries an explicit NOT LANDED verdict."""
    return "NOT LANDED" in verified.upper()


def is_partial(verified: str) -> bool:
    """Report whether a verified cell carries an explicit PARTIAL verdict.

    PARTIAL is READ, never inferred as the residue of the other two: an id
    a pass covered whose ledger row is missing or blank has no verdict at
    all, and counting it as `partial` would invent one. `ids_n` beside the
    three counts is where that gap stays visible.
    """
    if is_landed(verified) or is_not_landed(verified):
        return False
    return "PARTIAL" in verified.upper()


def is_upheld(row: Finding) -> bool:
    """Apply the UPHELD predicate: a real criterion, or a signed refusal."""
    if row["terminal"].strip().lower().startswith("refused"):
        return True
    return row["criterion"] != NOT_NEEDED


def prefix_rows(rows: list[Finding], prefix: str) -> list[Finding]:
    r"""Return rows whose id matches `^<prefix>-\d+$` — anchored, never startswith.

    A bare `id.startswith(prefix)` is a defect, not an implementation
    choice: under it a one-letter prefix `K` absorbs every `KI-*`
    row of a round that also ran a `KI` lens, and `V1` absorbs `V12`.
    """
    pattern = re.compile(r"^" + re.escape(prefix) + r"-\d+$")
    return [r for r in rows if pattern.match(r["id"])]


# ---------------------------------------------------------------------------
# the trace — read, reduce, and never invent
# ---------------------------------------------------------------------------


def valid_span(rec: dict[str, object]) -> bool:
    """Check the fields this script reads; a record failing any is refused.

    This is not a second copy of `trace.py validate` — that script owns
    the schema. What is checked here is exactly what the summary would
    otherwise carry: the identifiers written into the JSON, and the types
    of the numbers aggregated.
    """
    if as_int(rec.get("v")) != SCHEMA_VERSION:
        return False
    if rec.get("kind") not in ("open", "span"):
        return False
    if not bounded(rec.get("round"), ROUND_RE, MAX_ROUND_LEN):
        return False
    if not bounded(rec.get("span"), SPAN_RE, MAX_SPAN_LEN):
        return False
    actor = as_str(rec.get("actor"))
    if actor not in ACTORS:
        return False
    unit = as_str(rec.get("unit"))
    if unit is None or len(unit) > MAX_UNIT_TEXT_LEN:
        return False
    prefix = rec.get("id_prefix")
    if prefix is not None and not bounded(prefix, PREFIX_RE, MAX_UNIT_LEN):
        return False
    if parse_timestamp(rec.get("started")) is None:
        return False
    if rec.get("kind") == "open":
        return True
    if parse_timestamp(rec.get("ended")) is None:
        return False
    if as_int(rec.get("wallclock_s")) is None:
        return False
    if as_str_list(rec.get("ids")) is None or as_object(rec.get("id_tags")) is None:
        return False
    if as_str_list(rec.get("flags")) is None:
        return False
    commit = rec.get("commit")
    if commit is not None and not bounded(commit, COMMIT_RE, MAX_COMMIT_LEN):
        return False
    for field in ("model_assigned", "model_actual"):
        if not bounded(rec.get(field), MODEL_RE, MAX_MODEL_LEN):
            return False
    tokens = rec.get("tokens")
    if tokens is None:
        return True
    obj = as_object(tokens)
    # The four counters are mandatory and `total` is the ONE optional key
    # the schema admits; an unknown key is refused rather than carried,
    # exactly as the writer's own bounded-value rule requires.
    if obj is None or set(obj) - {*TOKEN_KEYS, TOKEN_TOTAL_KEY} != set():
        return False
    if not set(TOKEN_KEYS) <= set(obj):
        return False
    return all(as_int(obj[k]) is not None for k in obj)


def read_trace(path: Path) -> Trace:
    """Read and reduce a trace file. A missing or unreadable one is not an error.

    Reduction rule: a `kind: "span"` record supersedes the
    `open` record with the same id and the pair counts once; a second
    `span` for one id is the report-only defect `duplicate-span`. An
    `open` with no `span` is an UNCLOSED span — the round was interrupted
    — and contributes nothing to any metric: no wall-clock, no tokens, no
    outcome, and no invented `ended`.
    """
    empty: Trace = {
        "spans": [],
        "opens": {},
        "unclosed": 0,
        "refused": 0,
        "defects": [],
        "present": False,
    }
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        # A trace that is not there is the flag-off case and says
        # `trace: none`. A trace that IS there and could not be read is a
        # measurement failure, and the negative-claim rule forbids
        # reporting it as absence with nothing attached: it gets the
        # `unreadable` diagnostic from the closed vocabulary, so the two
        # cases are told apart on stdout. Neither reaches an exit code.
        try:
            present = path.exists()
        except OSError:  # pragma: no cover - an unstattable path
            present = True
        if present:
            print(diagnostic("unreadable", path.name))
        return empty
    opens: dict[str, dict[str, object]] = {}
    closed: dict[str, dict[str, object]] = {}
    order: list[str] = []
    refused = 0
    defects: list[str] = []
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            decoded: object = json.loads(stripped)
        except ValueError:
            print(diagnostic("unparseable-line", path.name, number))
            refused += 1
            continue
        rec = as_object(decoded)
        if rec is None or not valid_span(rec):
            print(diagnostic("schema-refused", path.name, number))
            refused += 1
            continue
        span_id = as_str(rec.get("span")) or ""
        if rec.get("kind") == "open":
            opens[span_id] = rec
            continue
        if span_id in closed:
            defects.append(f"defect: duplicate-span line {number}")
        else:
            order.append(span_id)
        rec["line"] = number
        closed[span_id] = rec
    spans = [closed[s] for s in order]
    defects.extend(filter(None, (span_defects(span) for span in spans)))
    return {
        "spans": spans,
        "opens": opens,
        "unclosed": len(set(opens) - set(closed)),
        "refused": refused,
        "defects": defects,
        "present": True,
    }


def span_defects(span: dict[str, object]) -> str:
    """Return the `wallclock_s`-vs-timestamps defect of one span, or the empty string.

    The rollup asserts `wallclock_s` agrees with `ended - started`
    and reports a mismatch as a defect — report-only, exit code untouched.
    """
    started = parse_timestamp(span.get("started"))
    ended = parse_timestamp(span.get("ended"))
    wallclock = as_int(span.get("wallclock_s"))
    if started is None or ended is None or wallclock is None:
        return ""
    if int((ended - started).total_seconds()) == wallclock:
        return ""
    return f"defect: wallclock-mismatch line {as_int(span.get('line')) or 0}"


def sum_tokens(spans: list[dict[str, object]]) -> dict[str, int] | None:
    """Sum the four counters over a group, or return None.

    A `null` is never aggregated into a total. Any group
    holding a span with `tokens: null` yields `null` — never a partial sum
    presented as a total — and the coverage string stands beside it.
    """
    if not spans:
        return None
    totals = dict.fromkeys(TOKEN_KEYS, 0)
    for span in spans:
        obj = as_object(span.get("tokens"))
        if obj is None:
            return None
        for key in TOKEN_KEYS:
            totals[key] += as_int(obj[key]) or 0
    return totals


def sum_wallclock(spans: list[dict[str, object]]) -> int:
    """Sum the spans' own `wallclock_s` — the value each span carries."""
    return sum(as_int(s.get("wallclock_s")) or 0 for s in spans)


def elapsed_wallclock(spans: list[dict[str, object]]) -> int:
    """Return earliest open to latest close across a group, in seconds.

    The multi-verifier rule: a pass's `started` is the earliest span
    open, its `ended` the latest span close, and its `wallclock_s` the
    difference — NOT the sum of the spans' own values, which stay on the
    spans. The two agree only while verifiers run sequentially in the
    foreground; the elapsed definition survives a round that deviates.
    """
    starts = [parse_timestamp(s.get("started")) for s in spans]
    ends = [parse_timestamp(s.get("ended")) for s in spans]
    known_starts = [s for s in starts if s is not None]
    known_ends = [e for e in ends if e is not None]
    if not known_starts or not known_ends:
        return 0
    return int((max(known_ends) - min(known_starts)).total_seconds())


def group_spans(
    spans: list[dict[str, object]],
    actor: str,
    key: str,
) -> dict[str, list[dict[str, object]]]:
    """Group one actor's spans by one field — never by the name alone.

    The aggregation discipline: every aggregation keys on the
    (unit, actor) pair. `P1` on a `verifier` span and `P1` on any other
    actor's span are different groups; a unit is only ever aggregated
    within one actor.
    """
    groups: dict[str, list[dict[str, object]]] = {}
    for span in spans:
        if span.get("actor") != actor:
            continue
        value = as_str(span.get(key))
        if value is None:
            continue
        groups.setdefault(value, []).append(span)
    return groups


def span_ids(spans: list[dict[str, object]]) -> set[str]:
    """Return the union of a group's finding ids, ids failing the contract dropped."""
    out: set[str] = set()
    for span in spans:
        for item in as_str_list(span.get("ids")) or []:
            if ID_RE.match(item):
                out.add(item)
    return out


# ---------------------------------------------------------------------------
# the five metrics, each `n/a: <reason>` where its inputs are absent
# ---------------------------------------------------------------------------


def ratio(numerator: int, denominator: int, reason: str) -> float | str:
    """Return a rounded ratio, or the reason string on an empty denominator.

    EMPTY DENOMINATOR: a zero denominator is `n/a: <reason>` — never
    `0`, never `1.0`, never silently omitted. Reporting `0.0` would read
    as "the pass raised only noise" and `1.0` as "the pass was perfectly
    precise"; both are inventions about findings never raised.
    """
    if denominator <= 0:
        return reason
    return round(numerator / denominator, 4)


def lens_entries(
    trace: Trace,
    rows: list[Finding],
    *,
    legacy: bool,
) -> tuple[list[dict[str, object]], object]:
    """Build `lenses[]` and M1 (CFR), keyed by the round's own critic spans.

    M1's zero-lens carve-out: the prefixes iterated over are exactly
    the `id_prefix` values of the round's `critic` spans — never the set
    of prefixes found in the ledger, which may name spec sections rather
    than lenses. A round with no `critic` span computes nothing.
    """
    groups = group_spans(trace["spans"], "critic", "id_prefix")
    entries: list[dict[str, object]] = []
    cfr: dict[str, object] = {}
    for prefix in sorted(groups):
        spans = groups[prefix]
        last = spans[-1]
        raised = prefix_rows(rows, prefix)
        upheld = None if legacy else sum(1 for r in raised if is_upheld(r))
        entries.append(
            {
                "prefix": prefix,
                "model_assigned": as_str(last.get("model_assigned")) or "n/a",
                "model_actual": as_str(last.get("model_actual")) or "unknown",
                "raised": len(raised),
                "upheld": upheld,
                "wallclock_s": sum_wallclock(spans),
                "tokens": sum_tokens(spans),
            },
        )
        cfr[prefix] = (
            NA_V1_LEDGER
            if upheld is None
            else ratio(upheld, len(raised), NA_LENS_NO_FINDINGS)
        )
    return entries, (cfr if entries else NA_NO_LENSES)


def pass_entries(
    trace: Trace,
    rows: list[Finding],
    ledger_passes: list[PassRow],
    *,
    legacy: bool,
) -> tuple[list[dict[str, object]], object, list[str], list[str]]:
    """Build `passes[]` and M3 (VP), plus the defects and floor refusals.

    A pass is a SET of spans — one per verifier agent, all carrying
    the pass ordinal in `unit`. Verdicts are read from the LEDGER's
    `verified` cells, never from a span: the spans say who ran and what it
    cost, the ledger says what was found. The aggregation floor
    — a verification pass has at least one verifier span — refuses a row
    rather than writing a plausible zero, so a pass row present only in
    the ledger is named and left out.
    """
    groups = group_spans(trace["spans"], "verifier", "unit")
    by_ordinal = {p["ordinal"]: p for p in ledger_passes}
    verdicts = {r["id"]: r["verified"] for r in rows}
    entries: list[dict[str, object]] = []
    vp: dict[str, object] = {}
    defects: list[str] = []
    refusals: list[str] = []
    for unit in sorted(groups, key=pass_ordinal):
        spans = groups[unit]
        if not PASS_UNIT_RE.match(unit):
            continue
        ordinal = pass_ordinal(unit)
        prefix = as_str(spans[0].get("id_prefix")) or ""
        ids = span_ids(spans)
        landed = sum(1 for i in ids if is_landed(verdicts.get(i, "")))
        not_landed = sum(1 for i in ids if is_not_landed(verdicts.get(i, "")))
        partial = sum(1 for i in ids if is_partial(verdicts.get(i, "")))
        bundled = any("bundled" in (as_str_list(s.get("flags")) or []) for s in spans)
        if len({"bundled" in (as_str_list(s.get("flags")) or []) for s in spans}) > 1:
            defects.append(f"defect: bundled-disagreement pass {ordinal}")
        ledger_row = by_ordinal.get(ordinal)
        if ledger_row is not None and ledger_row["bundled"] not in (None, bundled):
            defects.append(f"defect: bundled-disagreement pass {ordinal}")
        raised = prefix_rows(rows, prefix) if prefix else []
        new = ledger_row["new"] if ledger_row else None
        if new is not None and prefix and new != len(raised):
            defects.append(f"defect: new-findings-disagreement pass {ordinal}")
        upheld = None if legacy else sum(1 for r in raised if is_upheld(r))
        entries.append(
            {
                "ordinal": ordinal,
                "prefix": prefix,
                "spans_n": len(spans),
                "ids_n": len(ids),
                "landed": landed,
                "partial": partial,
                "not_landed": not_landed,
                "new": new,
                "bundled": bundled,
                "wallclock_s": elapsed_wallclock(spans),
                "tokens": sum_tokens(spans),
            },
        )
        vp[f"P{ordinal}"] = (
            NA_V1_LEDGER
            if upheld is None
            else ratio(upheld, len(raised), NA_PASS_NO_FINDINGS)
        )
    seen = {int(e["ordinal"]) for e in entries if isinstance(e["ordinal"], int)}
    # The key-level aggregation floor: a verification pass
    # has at least one verifier span, so a passes-table row with no span
    # behind it is REFUSED rather than written as a plausible zero. The
    # refusal is one bounded line and changes no exit code.
    refusals.extend(
        f"defect: pass-floor-refused pass {p['ordinal']}"
        for p in ledger_passes
        if p["ordinal"] not in seen
    )
    return entries, (vp if entries else NA_NO_PASSES), defects, refusals


def pass_ordinal(unit: str) -> int:
    """Return the pass ordinal carried by a `P<n>` unit, or 0."""
    digits = re.search(r"\d+", unit)
    return int(digits.group()) if digits else 0


def pass_scopes(trace: Trace) -> list[tuple[int, set[str]]]:
    """Return each pass's scope — the UNION of ALL its verifier spans' ids.

    M2 resolves "the first verification pass whose scope covers B"
    against that union, never against a single span, so a pass run by four
    per-batch verifiers is still one pass.
    """
    groups = group_spans(trace["spans"], "verifier", "unit")
    scopes = [
        (pass_ordinal(unit), span_ids(spans))
        for unit, spans in groups.items()
        if PASS_UNIT_RE.match(unit)
    ]
    return sorted(scopes, key=lambda item: item[0])


def batch_entries(
    trace: Trace,
    rows: list[Finding],
    scopes: list[tuple[int, set[str]]],
) -> tuple[list[dict[str, object]], object]:
    """Build `batches[]` and M2 (FPL) under the RE-FIX ATTRIBUTION rule.

    An id counts in `ids(B)` for EVERY batch whose fixer span carries it —
    the original and each re-fix alike, both memberships surviving on disk
    because the trace's `ids` field is append-only and per batch. Credit
    goes to the LAST batch carrying the id only, and that zero for the
    earlier batches is derived, not read: a later fixer span carries an id
    only because the earlier fix did not land.
    """
    groups = group_spans(trace["spans"], "fixer", "unit")
    order = [u for u in groups if BATCH_UNIT_RE.match(u)]
    last_batch: dict[str, str] = {}
    for unit in order:
        for item in span_ids(groups[unit]):
            last_batch[item] = unit
    verdicts = {r["id"]: r["verified"] for r in rows}
    entries: list[dict[str, object]] = []
    fpl: dict[str, object] = {}
    for unit in order:
        spans = groups[unit]
        ids = sorted(span_ids(spans))
        fixed, unworkable = fixer_outcome(spans)
        entries.append(
            {
                "id": unit,
                "ids_n": len(ids),
                "fixed": fixed,
                "unworkable": unworkable,
                "commit": last_commit(spans),
                "wallclock_s": sum_wallclock(spans),
                "tokens": sum_tokens(spans),
            },
        )
        fpl[unit] = batch_fpl(ids, unit, last_batch, verdicts, scopes)
    return entries, (fpl if entries else NA_NO_BATCHES)


def batch_fpl(
    ids: list[str],
    unit: str,
    last_batch: dict[str, str],
    verdicts: dict[str, str],
    scopes: list[tuple[int, set[str]]],
) -> float | str:
    """Return M2 for one batch: landed at the FIRST pass whose scope covers it.

    Numerator credit goes to the LAST batch carrying an id and to it only
    (RE-FIX ATTRIBUTION): a re-fixed id lowers the original batch's
    FPL and may raise the re-fix batch's, and that asymmetry is the
    measurement — whether THIS batch's fixes land at the first pass — not
    one id counted twice inside one figure.
    """
    if not ids:
        return NA_BATCH_NO_IDS
    if not any(scope & set(ids) for _, scope in scopes):
        return NA_NO_COVERING_PASS
    landed = sum(
        1 for i in ids if last_batch.get(i) == unit and is_landed(verdicts.get(i, ""))
    )
    return ratio(landed, len(ids), NA_BATCH_NO_IDS)


def fixer_outcome(spans: list[dict[str, object]]) -> tuple[int, int]:
    """Sum `fixed:<n>,unworkable:<m>` over a batch's fixer spans."""
    fixed = unworkable = 0
    for span in spans:
        match = re.match(
            r"^fixed:(\d{1,4}),unworkable:(\d{1,4})$",
            as_str(span.get("outcome")) or "",
        )
        if match:
            fixed += int(match.group(1))
            unworkable += int(match.group(2))
    return fixed, unworkable


def last_commit(spans: list[dict[str, object]]) -> str | None:
    """Return the last valid commit hash a batch's spans carry, or None."""
    found: str | None = None
    for span in spans:
        value = span.get("commit")
        if bounded(value, COMMIT_RE, MAX_COMMIT_LEN):
            found = as_str(value)
    return found


def outcome_defects(trace: Trace, rows: list[Finding]) -> list[str]:
    """Report a critic span's `findings:<n>` disagreeing with the ledger.

    Span `outcome` strings are not a metric input. Where the two disagree
    the LEDGER is the value and the disagreement is printed as a defect —
    report-only, and it changes no exit code.
    """
    defects: list[str] = []
    lenses = group_spans(trace["spans"], "critic", "id_prefix")
    for prefix in sorted(lenses):
        spans = lenses[prefix]
        claimed = 0
        seen = False
        for span in spans:
            match = re.match(r"^findings:(\d{1,4})$", as_str(span.get("outcome")) or "")
            if match:
                claimed += int(match.group(1))
                seen = True
        if seen and claimed != len(prefix_rows(rows, prefix)):
            defects.append(f"defect: outcome-ledger-disagreement lens {prefix}")
    return defects


def token_totals(trace: Trace) -> tuple[dict[str, int] | None, str, int, int]:
    """Return the round's token totals, the coverage string and its two counts.

    The coverage universe is the spans that COULD carry usage — the four
    spawn actors. An `orchestrator` span's `tokens` is null permanently
    and by construction (the main loop's spend belongs to the whole session
    and no documented seam separates it), so counting it as a measurement
    gap would make the round's totals unconditionally `null`; the rollup
    prints `orchestrator: n/a (not separable)` instead of an inviting zero.
    """
    spawn = [s for s in trace["spans"] if s.get("actor") in SPAWN_ACTORS]
    with_usage = [s for s in spawn if s.get("tokens") is not None]
    coverage = f"{len(with_usage)}/{len(spawn)} spans"
    totals = sum_tokens(spawn) if spawn and len(with_usage) == len(spawn) else None
    return totals, coverage, len(spawn) - len(with_usage), len(spawn)


def work_spans(trace: Trace) -> list[dict[str, object]]:
    """Return the round's spans MINUS its own root span `s1.00`.

    The root's `wallclock_s` is the envelope of every other span — *"its
    scope is the whole round even though its id names its writer"* — so
    adding it to a sum of the spans it contains counts the round twice
    — and, because the closing stage closes it only AFTER this script runs,
    it would also make M4's seconds depend on whether the rollup was run
    once at closure or again afterwards.
    """
    return [s for s in trace["spans"] if s.get("span") != ROUND_SPAN]


def tvr(
    trace: Trace,
    totals: dict[str, int] | None,
    terminal_rows: int,
    missing: tuple[int, int],
) -> dict[str, object]:
    """Return M4 — a VECTOR, never one number.

    No field is dropped and none is pre-summed with a differently-priced
    one: on a real measured span, `in+out` was 20 287 against
    `cache_write+cache_read` = 4 336 128, so a figure built from `in+out`
    alone would report ~0.5% of the volume the round actually moved.
    `fresh` and `reuse` are the two named summaries, and the wall-clock
    half still prints when the token half cannot.
    """
    keys = (*TOKEN_KEYS, "fresh", "reuse")
    seconds: float | str = (
        NA_NO_TERMINAL
        if terminal_rows <= 0
        else round(sum_wallclock(work_spans(trace)) / terminal_rows, 2)
    )
    if terminal_rows <= 0:
        return {**dict.fromkeys(keys, NA_NO_TERMINAL), "seconds": seconds}
    if totals is None:
        without, total = missing
        reason = (
            NA_NO_SPAWN_SPANS
            if total == 0
            else f"n/a: {without} of {total} spans without usage"
        )
        return {**dict.fromkeys(keys, reason), "seconds": seconds}
    values: dict[str, object] = {
        key: round(totals[key] / terminal_rows, 2) for key in TOKEN_KEYS
    }
    fresh = totals["in"] + totals["out"] + totals["cache_write"]
    values["fresh"] = round(fresh / terminal_rows, 2)
    values["reuse"] = round(totals["cache_read"] / terminal_rows, 2)
    values["seconds"] = seconds
    return values


def fads(trace: Trace, rows: list[Finding]) -> tuple[int, object]:
    r"""Return M5's numerator and the metric — one join, computed once.

    `findings.fix_application_n` IS M5's numerator, and
    `metrics.FADS` divides that same number by that same denominator, so
    the summary cannot print a numerator disagreeing with the metric
    printed beside it. The denominator is VERIFICATION-RAISED: rows
    whose id-prefix equals the `id_prefix` of some `verifier` span, tested
    against the anchored `^<prefix>-\\d+$` form and never by `startswith`.
    It is deliberately NOT the count of `fix-application` tags over all
    adjudicated ids — that wider figure has a different denominator.
    """
    prefixes = {
        as_str(s.get("id_prefix"))
        for s in trace["spans"]
        if s.get("actor") == "verifier"
    }
    raised: set[str] = set()
    for prefix in sorted(p for p in prefixes if p):
        raised.update(r["id"] for r in prefix_rows(rows, prefix))
    tagged: set[str] = set()
    for span in trace["spans"]:
        if as_int(span.get("stage")) != TAG_STAGE:
            continue
        for key, value in (as_object(span.get("id_tags")) or {}).items():
            if key in raised and FIX_APPLICATION_TAG in (as_str_list(value) or []):
                tagged.add(key)
    return len(tagged), ratio(len(tagged), len(raised), NA_NO_RAISED)


# ---------------------------------------------------------------------------
# the summary and its T2 projection
# ---------------------------------------------------------------------------


def round_window(trace: Trace) -> tuple[str | None, str | None, int | None]:
    """Return the round span's `started`, `ended` and wall-clock.

    An `open` with no `span` record is an UNCLOSED span and
    no reader may invent its `ended` — not "now", not the file's last
    timestamp, not the next span's `started`. The round span `s1.00` is
    closed by the closing stage AFTER this script runs, so on the ordinary
    path `ended` is legitimately `null` here and the unclosed count stands
    beside it; running the rollup again after closure fills it in.
    """
    closed = next((s for s in trace["spans"] if s.get("span") == ROUND_SPAN), None)
    opened = trace["opens"].get(ROUND_SPAN)
    source = closed or opened
    if source is None:
        return None, None, None
    started = as_str(source.get("started"))
    if closed is None:
        return started, None, None
    ended = as_str(closed.get("ended"))
    return started, ended, as_int(closed.get("wallclock_s"))


def round_identity(trace: Trace, ledger: Path) -> tuple[str | None, str, bool]:
    """Return (round, object_slug, refused) for the summary's two identifiers.

    The round id comes from the trace's own records; with no trace it
    falls back to the run-folder basename, which is the same string by
    construction. Either way it is re-checked against the schema's
    anchored pattern before it is written, and `object_slug` is DERIVED
    from its object segment by the schema's total, idempotent derivation
    and then re-checked against its own pattern — so no name this project
    does not control reaches the file unbounded; `object_slug` and `mode`
    are the two fields THIS script enforces.

    A `round` failing its pattern is REFUSED rather than written: the
    field is `null`, one `schema-refused` diagnostic is emitted and the
    summary is written anyway — the same rule `mode` follows, applied to
    the other bounded identifier. A slug of the offending name is deliberately
    NOT written into `round` instead: it would satisfy no reader and would
    claim a run folder that does not exist.
    """
    value = ""
    for span in trace["spans"]:
        value = as_str(span.get("round")) or ""
        break
    if not value:
        for record in trace["opens"].values():
            value = as_str(record.get("round")) or ""
            break
    if not value:
        value = ledger.resolve().parent.name
    if not bounded(value, ROUND_RE, MAX_ROUND_LEN):
        return None, checked_slug(value), True
    return value, checked_slug(value[ROUND_PREFIX_LENGTH:]), False


def checked_slug(text: str) -> str:
    """Derive an object slug and re-check it against the schema's own pattern.

    The derivation is total, so the check can only fail if the derivation
    itself were ever changed; it is here because `rollup.py` is the
    enforcement point for this field, and an enforcement that is only
    argued for is no enforcement at all.
    """
    derived = slug(text)
    if not bounded(derived, OBJECT_SLUG_RE, MAX_SLUG_LEN):
        print(diagnostic("schema-refused", SUMMARY_NAME))
        return SLUG_FALLBACK
    return derived


def build_summary(
    ledger: Path,
    rows: list[Finding],
    ledger_passes: list[PassRow],
    trace: Trace,
    mode: str | None,
) -> tuple[dict[str, object], list[str], list[str]]:
    """Assemble `round-summary.json` field for field, per its schema."""
    legacy = any(r["criterion"] is None for r in rows)
    round_id, object_slug, id_refused = round_identity(trace, ledger)
    started, ended, wallclock = round_window(trace)
    lenses, cfr = lens_entries(trace, rows, legacy=legacy)
    passes, vp, defects, refusals = pass_entries(
        trace,
        rows,
        ledger_passes,
        legacy=legacy,
    )
    batches, fpl = batch_entries(trace, rows, pass_scopes(trace))
    totals, coverage, without, total = token_totals(trace)
    by_severity = dict.fromkeys(SEVERITY_BUCKETS, 0)
    by_terminal = dict.fromkeys(TERMINAL_BUCKETS, 0)
    for row in rows:
        by_severity[severity_bucket(row["severity"])] += 1
        by_terminal[terminal_bucket(row)] += 1
    terminal_rows = len(rows) - by_terminal["open"]
    fix_application_n, fads_value = fads(trace, rows)
    defects.extend(outcome_defects(trace, rows))
    summary: dict[str, object] = {
        "round": round_id,
        "object_slug": object_slug,
        "mode": mode,
        "started": started,
        "ended": ended,
        "wallclock_s": wallclock,
        "lenses": lenses,
        "batches": batches,
        "passes": passes,
        "findings": {
            "by_severity": by_severity,
            "by_terminal": by_terminal,
            "fix_application_n": fix_application_n,
        },
        "totals": {"tokens": totals, "coverage": coverage},
        "metrics": {
            "CFR": cfr,
            "FPL": fpl,
            "VP": vp,
            "TVR": tvr(trace, totals, terminal_rows, (without, total)),
            "FADS": fads_value,
        },
    }
    if id_refused:
        refusals.append(diagnostic("schema-refused", ledger.name))
    return summary, defects, refusals


def project(summary: dict[str, object]) -> dict[str, object] | None:
    """Project the local summary into the T2 line — never a copy of it.

    Three things do not cross, each because no named consumer of T2 reads
    them and each is identity rather than measurement: `object_slug` is
    dropped and `round` replaced by an opaque `round_key`; `started`/
    `ended` are replaced by the UTC day the round closed; every
    `batches[].commit` is dropped. This is a DE-IDENTIFICATION, not
    anonymization, and is stated as such: a name that is guessed can be
    confirmed by hashing it. What it removes is enumeration.

    `date` is the UTC day the round CLOSED. On the ordinary path it is not
    yet on disk when this runs: the closing stage orders the T2 append
    BEFORE the closure span and before the round span's own close record,
    so `summary.ended` is legitimately `null` here and the day comes from
    this script's own clock — the same clock `trace.py` writes `ended`
    from, and never an agent's word about the time. Gating the append on a
    close record written afterwards would make the T2 line unreachable on
    every ordinary round.

    None is returned only when there is no `round` to key the line by: a
    refused round id leaves no `round_key` to compute, and a line
    without one is not addressable by any consumer.
    """
    round_id = as_str(summary.get("round"))
    if round_id is None:
        return None
    ended = as_str(summary.get("ended")) or ""
    day = (
        ended[:DATE_LENGTH]
        if len(ended) >= DATE_LENGTH
        else datetime.now(UTC).strftime("%Y-%m-%d")
    )
    digest = hashlib.sha256(round_id.encode("utf-8")).hexdigest()[:12]
    batches = [
        {k: v for k, v in batch.items() if k != "commit"}
        for batch in as_str_keyed(summary.get("batches"))
    ]
    return {
        "v": PROJECTION_VERSION,
        "round_key": digest,
        "date": day,
        "mode": summary.get("mode"),
        "wallclock_s": summary.get("wallclock_s"),
        "lenses": summary.get("lenses"),
        "batches": batches,
        "passes": summary.get("passes"),
        "findings": summary.get("findings"),
        "totals": summary.get("totals"),
        "metrics": summary.get("metrics"),
    }


# ---------------------------------------------------------------------------
# the human table — counts, durations and closed vocabularies only
# ---------------------------------------------------------------------------


def show(value: object) -> str:
    """Render a metric value for the table: a number, or its `n/a:` reason."""
    return str(value)


def human_table(summary: dict[str, object], trace: Trace) -> list[str]:
    """Return the printed table: one bounded line per group, then the totals."""
    metrics = as_object(summary.get("metrics")) or {}
    cfr = as_object(metrics.get("CFR"))
    fpl = as_object(metrics.get("FPL"))
    vp = as_object(metrics.get("VP"))
    wallclock = summary.get("wallclock_s")
    lines = [
        (
            f"round: {summary.get('round') or 'n/a'} "
            f"| object: {summary.get('object_slug')} "
            f"| mode: {summary.get('mode') or 'n/a'}"
        ),
        (
            f"window: {summary.get('started') or 'n/a'} -> "
            f"{summary.get('ended') or 'n/a'} "
            f"| wallclock: {'n/a' if wallclock is None else f'{wallclock}s'}"
        ),
    ]
    for lens in as_str_keyed(summary.get("lenses")):
        prefix = str(lens.get("prefix"))
        upheld = lens.get("upheld")
        lines.append(
            f"lens {prefix}: raised {lens.get('raised')} "
            f"upheld {upheld if upheld is not None else 'n/a'} "
            f"CFR {show(cfr.get(prefix) if cfr else metrics.get('CFR'))} "
            f"| {lens.get('wallclock_s')}s | tokens {token_text(lens.get('tokens'))}",
        )
    if not summary.get("lenses"):
        lines.append(f"lenses: none | CFR {show(metrics.get('CFR'))}")
    for batch in as_str_keyed(summary.get("batches")):
        name = str(batch.get("id"))
        lines.append(
            f"batch {name}: ids {batch.get('ids_n')} fixed {batch.get('fixed')} "
            f"unworkable {batch.get('unworkable')} "
            f"FPL {show(fpl.get(name) if fpl else metrics.get('FPL'))} "
            f"| {batch.get('wallclock_s')}s | tokens {token_text(batch.get('tokens'))}",
        )
    if not summary.get("batches"):
        lines.append(f"batches: none | FPL {show(metrics.get('FPL'))}")
    for entry in as_str_keyed(summary.get("passes")):
        name = f"P{entry.get('ordinal')}"
        lines.append(
            f"pass {name}: spans {entry.get('spans_n')} ids {entry.get('ids_n')} "
            f"L/P/NOT {entry.get('landed')}/{entry.get('partial')}/"
            f"{entry.get('not_landed')} new "
            f"{entry.get('new') if entry.get('new') is not None else 'n/a'} "
            f"bundled {'yes' if entry.get('bundled') else 'no'} "
            f"VP {show(vp.get(name) if vp else metrics.get('VP'))} "
            f"| {entry.get('wallclock_s')}s | tokens {token_text(entry.get('tokens'))}",
        )
    if not summary.get("passes"):
        lines.append(f"passes: none | VP {show(metrics.get('VP'))}")
    lines.extend(findings_lines(summary))
    lines.append("orchestrator: n/a (not separable)")
    lines.extend(metric_lines(metrics))
    lines.append(
        f"trace: {len(trace['spans'])} spans, {trace['unclosed']} unclosed, "
        f"{trace['refused']} refused lines, {len(trace['defects'])} defects"
        if trace["present"]
        else "trace: none",
    )
    return lines


def as_str_keyed(value: object) -> list[dict[str, object]]:
    """Return a list of str-keyed mappings — the shape the table iterates."""
    out: list[dict[str, object]] = []
    for item in value if isinstance(value, list) else []:
        obj = as_object(item)
        if obj is not None:
            out.append(obj)
    return out


def token_text(value: object) -> str:
    """Render a group's token object as one bounded string, or `n/a`."""
    obj = as_object(value)
    if obj is None:
        return "n/a"
    return "/".join(str(as_int(obj.get(k)) or 0) for k in TOKEN_KEYS)


def findings_lines(summary: dict[str, object]) -> list[str]:
    """Return the findings and totals lines of the table."""
    findings = as_object(summary.get("findings")) or {}
    severity = as_object(findings.get("by_severity")) or {}
    terminal = as_object(findings.get("by_terminal")) or {}
    totals = as_object(summary.get("totals")) or {}
    rows = sum(as_int(v) or 0 for v in severity.values())
    open_rows = as_int(terminal.get("open")) or 0
    spread = " ".join(f"{k} {as_int(severity.get(k)) or 0}" for k in SEVERITY_BUCKETS)
    tagged = as_int(findings.get("fix_application_n")) or 0
    return [
        (
            f"findings: rows {rows} | terminal {rows - open_rows} | {spread} "
            f"| fix-application {tagged}"
        ),
        (
            f"totals: tokens {token_text(totals.get('tokens'))} "
            f"| coverage {totals.get('coverage')}"
        ),
    ]


def metric_lines(metrics: dict[str, object]) -> list[str]:
    """Return the TVR vector line and the FADS line.

    The token half and the wall-clock half are printed separately because
    they fail separately: when any span's tokens are `null` the token half
    reads `n/a (k of n spans without usage)` — the honest shape, with its
    coverage inline — and the seconds still print.
    """
    vector = as_object(metrics.get("TVR")) or {}
    token_half = [vector.get(k) for k in (*TOKEN_KEYS, "fresh", "reuse")]
    reasons = {v for v in token_half if isinstance(v, str)}
    if len(reasons) == 1:
        # One shared reason: print it once, in the parenthesised form,
        # rather than six times over.
        body = "tokens " + reasons.pop().replace("n/a: ", "n/a (", 1) + ")"
    else:
        body = " ".join(
            f"{k} {show(vector.get(k))}" for k in (*TOKEN_KEYS, "fresh", "reuse")
        )
    return [
        f"TVR: {body} | seconds {show(vector.get('seconds'))}",
        f"FADS: {show(metrics.get('FADS'))}",
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

OPTION_NAMES = ("--trace", "--out", "--rounds")


def parse_args(args: list[str]) -> tuple[str, dict[str, str]] | None:
    """Return (ledger path, options), or None on a usage error."""
    path: str | None = None
    opt: dict[str, str] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if token in OPTION_NAMES:
            if index + 1 >= len(args):
                return None
            opt[token[2:]] = args[index + 1]
            index += 2
            continue
        if token.startswith("-") or path is not None:
            return None
        path = token
        index += 1
    return None if path is None else (path, opt)


def write_json(path: Path, payload: dict[str, object]) -> bool:
    """Write the summary; report success. A failed write is one diagnostic."""
    try:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        print(diagnostic("write-failed", path.name))
        return False
    return True


def append_projection(path: Path, summary: dict[str, object]) -> None:
    """Append the T2 line, or say why it was not appended. Never fatal."""
    line = project(summary)
    if line is None:
        print("rounds: skipped (no round key)")
        return
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(line, separators=(",", ":")) + "\n")
    except OSError:
        print(diagnostic("write-failed", path.name))
        return
    print(f"rounds: appended 1 line ({path.name})")


def main() -> int:
    """Roll a round up. Exit 0 unless the inputs themselves were not given."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    parsed = parse_args(args)
    if parsed is None:
        print(__doc__)
        return 2
    ledger_text, opt = parsed
    ledger = Path(ledger_text)
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError, ValueError):
        print(diagnostic("unreadable", ledger_text))
        return 2
    rows, width = parse_findings(lines)
    if width not in (LEGACY_WIDTH, CRITERION_WIDTH):
        print(diagnostic("schema-refused", ledger_text))
        return 2
    mode, refused = parse_mode(lines)
    if refused:
        print(diagnostic("schema-refused", ledger_text))
    trace = read_trace(Path(opt.get("trace", str(ledger.parent / TRACE_NAME))))
    summary, defects, refusals = build_summary(
        ledger, rows, parse_passes(lines), trace, mode
    )
    for line in [*trace["defects"], *defects, *refusals]:
        print(line)
    for line in human_table(summary, trace):
        print(line)
    out = Path(opt.get("out", str(ledger.parent / SUMMARY_NAME)))
    if write_json(out, summary):
        print(f"wrote: {out.name}")
    if "rounds" in opt:
        append_projection(Path(opt["rounds"]), summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
