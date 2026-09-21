#!/usr/bin/env python3
# The payload ships loose files rather than a package, so this module sits
# in no __init__.py: it is imported from `recount.py`'s own directory.
"""Counts over the rows of a critic-ledger ledger: classes, kills, batches, plateau.

Imported by `recount.py` from its own directory. Nothing here prints.
"""

import re

from ledger_md import (
    ID_PATTERN,
)
from ledger_model import (
    Row,
)
from statuses import (
    AWAITING_LOGGED_NO_ACTION,
    AWAITING_SIGNATURE,
    FROZEN_CARRIED,
    LOGGED_NO_ACTION,
    OUT_OF_SCOPE,
    is_upheld,
    terminal_status,
)
from structural_checks import (
    CLASS_TAG_RE,
    SECURITY_PII_SLUG,
    SHELF_TAG_RE,
)

# The DEFECT CLASS / SIGNATURE MODE split, in one written literal. Every row
# of the declared security lens must carry `class:security-pii` — the
# backstop below obliges it — so that slug on such a row says which lens
# raised the finding, not that a defect class recurred. The adjudicator who
# means the class itself says so in the same cell, and only then does the
# tag count toward a class-kill. Written out rather than inferred: an origin
# that has to be guessed is an origin no counter can rely on.
CLASS_ORIGIN_ADJUDICATOR = "class-origin:adjudicator"
CLASS_ORIGIN_ADJUDICATOR_RE = re.compile(
    r"class-origin:adjudicator(?![a-z0-9-])",
)

# The gate's OWN ledger row, tagged with the class it kills. It is the one
# thing the class-kill warning speaks of and nothing used to show: while
# such a row is not terminal, the kill is in flight.
CLASS_KILL_TAG_RE = re.compile(r"class-kill:([a-z0-9-]{1,32})(?![a-z0-9-])")
FIX_APPLICATION_TAG = "origin:fix-application"
FROM_TAG_RE = re.compile(r"from:([a-z0-9-]{1,40})(?![a-z0-9-])")

# The batch key inside a `fix` cell: the first HASH-LIKE token, whatever
# label precedes it. A cell is written by hand and reads `F3 c447822`,
# `c447822`, `F3 c447822 (touch-up)` — one batch under three literals, and
# grouping by the whole cell counted it as three, each with its own
# denominator. Hash-like is deliberately narrow: 7 to 40 hex characters AND
# not all digits, so a bare date or an ordinal (`20260904`, `1234567`) is
# not mistaken for a commit and a cell with no hash at all keeps its whole
# literal as the key — a snapshot name is a batch identifier too.
HASH_TOKEN_RE = re.compile(r"^(?=.*[a-f])[0-9a-f]{7,40}$")

# The `=<primary-id>` gloss a duplicate row carries in its criterion cell:
# the same cross-lens deduplication convention adjudication already uses.
# The pointer names an id under the same contract as `ID_RE` above,
# composite prefixes included: `=V-CIT-1` is a pointer, not prose. It is
# BUILT from that one grammar rather than restating it: a pointer wider or
# narrower than the ids it may name is how this divergence recurred once
# already, after the id patterns themselves had been aligned.
DUPLICATE_OF_RE = re.compile(r"^=\s*(" + ID_PATTERN + r")")

# The severity-weighted plateau: a moving average over a window of THREE
# ledgers (the current one and two `--prev`), which is two deltas, and the
# severities that carry weight in it.
PLATEAU_WINDOW = 3
MAX_PREV = 2
PLATEAU_SEVERITIES = ("blocker", "major")


def class_groups(rows: list[Row]) -> dict[str, list[str]]:
    """Map each `class:` slug to the ids of the UPHELD rows carrying it.

    Only upheld rows count: a refuted claim is not a recurrence of
    anything. On a 7-cell legacy ledger `is_upheld` has no criterion cell
    to read and treats every row as upheld — legacy ledgers predate the
    tag and carry none, so the two never meet in practice.
    """
    groups: dict[str, list[str]] = {}
    for r in rows:
        if not is_upheld(r):
            continue
        # dict.fromkeys: one row naming the same class twice is one row.
        for slug in dict.fromkeys(CLASS_TAG_RE.findall(r["verdict"])):
            groups.setdefault(slug, []).append(r["id"])
    return groups


def _gap(tag: tuple[int, int], marker: tuple[int, int]) -> int:
    """Characters between two spans; 0 when they touch or overlap."""
    return max(tag[0] - marker[1], marker[0] - tag[1], 0)


def marked_by_adjudicator(verdict: str, slug: str) -> bool:
    """Whether a `class-origin:adjudicator` marker stands BESIDE `slug`.

    Stage 6.17 puts the marker `beside the tag`, and beside is resolved
    by DISTANCE: each marker qualifies the `class:` tag nearest to it in
    the cell, ties going to the leftmost, so writing the pair in either
    order reads the same. Searching the WHOLE cell instead made every
    tag in it adjudicator-chosen, which is how a security row that also
    carried a real, marked defect class fired the kill on the lens's own
    backstop.
    """
    tags = list(CLASS_TAG_RE.finditer(verdict))
    if not tags:
        return False
    for marker in CLASS_ORIGIN_ADJUDICATOR_RE.finditer(verdict):
        nearest = min(tags, key=lambda t: _gap(t.span(), marker.span()))
        if nearest.group(1) == slug:
            return True
    return False


def lens_default_class(row: Row, slug: str, prefix: str | None) -> bool:
    """Whether this `class:` tag is the security lens's DEFAULT, not a call.

    True for exactly one shape: the reserved `security-pii` slug, on a row
    of the DECLARED security lens, with no `class-origin:adjudicator`
    beside that tag. Everything else is a class somebody chose — another
    slug, another lens's row, a ledger declaring no security lens, or the
    written statement that the adjudicator meant this one — and a class
    somebody chose is what a recurrence is made of.
    """
    if slug != SECURITY_PII_SLUG or prefix is None:
        return False
    if row["id"].rsplit("-", 1)[0] != prefix:
        return False
    return not marked_by_adjudicator(row["verdict"], slug)


def kill_groups(
    rows: list[Row],
    prefix: str | None,
) -> dict[str, list[str]]:
    """`class_groups` minus the tags no adjudicator chose.

    The census counts every tag; the KILL counts defect classes. The two
    differ only where the security lens's default is in play, and where
    they differ the report says so on its own line rather than leaving a
    reader to work out why two upheld rows raised no kill.
    """
    groups: dict[str, list[str]] = {}
    for r in rows:
        if not is_upheld(r):
            continue
        for slug in dict.fromkeys(CLASS_TAG_RE.findall(r["verdict"])):
            if lens_default_class(r, slug, prefix):
                continue
            groups.setdefault(slug, []).append(r["id"])
    return groups


def kill_row_state(rows: list[Row], slug: str) -> str | None:
    """`"in flight"` / `"done"` for an existing `class-kill:<slug>` row.

    None where the class has no kill row at all — which is the only state
    in which the kill is still DUE. A row that carries the tag IS the
    gate's ledger row for that class: while it is non-terminal the kill is
    being built, once it is terminal the kill has landed, and in neither
    case is telling the adjudicator to open one a true statement. Telling
    him so anyway is what made the line noise the eye learned to skip.
    An open row wins over a closed one: a class with a landed kill AND a
    fresh open row has a kill in flight again.
    """
    state: str | None = None
    for r in rows:
        if slug not in CLASS_KILL_TAG_RE.findall(r["verdict"]):
            continue
        if not terminal_status(r)[0]:
            return "in flight"
        state = "done"
    return state


def awaits_a_batch(row: Row) -> bool:
    """Whether a row's fix was, or was to be, applied by a fix batch.

    Refuted rows were never fixed and residue/refusal rows were fixed by
    nobody on purpose; none of them belongs to a batch, so none of them is
    evidence that a batch could not be identified. A row in either named
    wait is on the same footing: a nominee is residue that has not been
    signed yet, and a row logged as no-action — waiting for that act or
    closed by it — was never handed to a fixer.
    The two statuses the round contract brings sit there for the same
    reason: a row the contract put out of scope, and a row the stop rule
    froze and carried, were never handed to a fixer either.
    """
    t = row["terminal"].strip().lower()
    return is_upheld(row) and not t.startswith(
        (
            "accepted-residue",
            "refused",
            AWAITING_SIGNATURE,
            AWAITING_LOGGED_NO_ACTION,
            LOGGED_NO_ACTION,
            OUT_OF_SCOPE,
            FROZEN_CARRIED,
        ),
    )


def batch_key(fix_cell: str) -> str:
    """The batch a `fix` cell names: its first hash-like token, or the cell.

    The cell is prose written by hand — `F3 c447822`, `c447822 (touch-up)`,
    a bare snapshot name — and what identifies the batch inside it is the
    commit,
    not the label the fixer happened to prefix. Grouping by the literal
    cell split one batch into as many batches as it had wordings, and every
    piece then carried its own denominator. Where there is no hash the
    whole stripped cell stays the key, so snapshot-named batches and the
    `BLANK_CELL` literals behave exactly as before.
    """
    stripped = fix_cell.strip()
    for token in stripped.split():
        if HASH_TOKEN_RE.match(token):
            return token
    return stripped


def capture_sets(rows: list[Row], prefixes: list[str]) -> tuple[int, int]:
    """Return (D, f1) — distinct findings RAISED, and those raised by one lens.

    The capture-recapture sets are PER-LENS, so only rows whose id prefix is
    one of the declared lenses take part: a row a verifier raised was found
    by no lens at all and would inflate both counts.

    Findings are counted BEFORE adjudication (a refuted claim was still
    raised) and cross-lens duplicates are collapsed by the existing `=id`
    convention: a duplicate row's criterion cell opens with `=<primary-id>`,
    so its row joins the primary's group and the group's lens set is the
    union of the prefixes of every row in it. `D` is the number of groups,
    `f1` the number of groups exactly one lens contributed to.
    """
    groups: dict[str, set[str]] = {}
    for r in rows:
        prefix = r["id"].rsplit("-", 1)[0]
        if prefix not in prefixes:
            continue
        criterion = r["criterion"] or ""
        dup = DUPLICATE_OF_RE.match(criterion.strip())
        key = dup.group(1) if dup else r["id"]
        groups.setdefault(key, set()).add(prefix)
    return len(groups), sum(1 for s in groups.values() if len(s) == 1)


def plateau_count(rows: list[Row]) -> int:
    """Return a ledger's major+blocker row count — the plateau's quantity."""
    return sum(1 for r in rows if r["severity"].strip().lower() in PLATEAU_SEVERITIES)


def not_landed(verdicts_cell: str) -> int | None:
    """The NOT-LANDED count of a verification pass, or None if unreadable.

    The cell is prose written by hand and only two shapes of it are read,
    both taken from the ledgers in the corpus: the compact `<L>/<P>/<NOT>`
    triple, and a spelled-out `... 0 NOT` (`23 L (+1 …) / 0 P / 0 NOT`).
    Anything else is None — UNREADABLE, never zero. Reading an unparsed
    cell as a clean pass is the one error that would let this line announce
    a convergence nobody measured, so the unreadable case is reported as
    such and the criterion stays "not met".
    """
    triple = re.search(r"(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", verdicts_cell)
    if triple:
        return int(triple.group(3))
    spelled = re.search(r"(\d+)\s*NOT\b", verdicts_cell)
    if spelled:
        return int(spelled.group(1))
    return None


def new_findings_severity(cell: str) -> str | None:
    """The severity a new-findings cell names, or None where it names none.

    Returns the WORST severity written in the cell — `blocker` outranks
    `major` outranks `minor` — reading the prose the passes table carries
    beside the count (`1 (V1-1, minor)`). None means the cell counts
    findings and says nothing about their severity, which is not the same
    as `minor` and is never read as it.
    """
    text = cell.lower()
    for severity in (*PLATEAU_SEVERITIES, "minor"):
        if severity in text:
            return severity
    return None


def shelf_slugs(row: Row) -> list[str]:
    """Return the `shelf:` slugs a verdict cell carries (usually none)."""
    return SHELF_TAG_RE.findall(row["verdict"])
