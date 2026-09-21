#!/usr/bin/env python3
# The payload ships loose files rather than a package, so this module sits
# in no __init__.py: it is imported from `recount.py`'s own directory.
"""Structural checks of a critic-ledger ledger row, header and register.

Imported by `recount.py` from its own directory. Each check returns the
error it found, or nothing; the caller collects and prints them.
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

from ledger_md import (
    BLANK_CELL,
    V1_WIDTH,
    V2_WIDTH,
    V3_WIDTH,
)
from statuses import (
    AWAITING_SIGNATURE,
    BLOCKER,
    LOGGED_NO_ACTION,
    OUT_OF_SCOPE,
    SIGNED_DATE_RE,
)

if TYPE_CHECKING:
    from ledger_model import Row

# The zone vocabulary of the round contract's zone map.
ZONE_MECHANICAL = "Z1"
ZONE_NORMATIVE = "Z2"
ZONE_INFORMATIVE = "Z3"
ZONES = (ZONE_MECHANICAL, ZONE_NORMATIVE, ZONE_INFORMATIVE)

# --- verdict-cell tags -----------------------------------------------------
# The verdict cell is free adjudication prose, so a tag inside it is given a
# fixed boundary — an alphabet and a terminator — like every other literal
# this script parses. See the tag bullet in the module docstring.
CLASS_TAG = "class:"
CLASS_TAG_RE = re.compile(r"class:([a-z0-9-]{1,32})(?![a-z0-9-])")

# Non-whitespace characters after which `class:` is PROSE rather than an
# attempted tag; whitespace and the end of the cell say the same thing.
CLASS_TAG_PROSE = ("|",)

# The slug alphabet's ceiling, shared by every verdict-cell tag that takes
# one: a boundary readers can rely on is one boundary, not one per tag.
SLUG_MAX = 32

# `shelf:<slug>` — a refutation closed WHOLLY by a pre-signed disposition of
# the round's contract, the slug naming that disposition. Read by exactly
# one report, the shelf share printed beside the per-lens sustained rate.
SHELF_TAG = "shelf:"
SHELF_TAG_RE = re.compile(r"shelf:([a-z0-9-]{1,32})(?![a-z0-9-])")

# The security/PII class marker: ONE literal, and this is it. Every check
# keyed on the class reads this slug and no synonym of it.
SECURITY_PII_SLUG = "security-pii"

# The written removal of the security/PII default, in the same row: the
# literal plus a reason that is free prose but never empty.
DECLASSED_TAG = "declassed:security-pii"
DECLASSED_RE = re.compile(r"declassed:security-pii\s*—\s*\S")

# The register's four statuses, each carrying the date it was set; only
# `expired-reopened` may carry its cycle counter; the pattern refuses one on
# any other status.
REGISTER_STATUS_RE = re.compile(
    r"^(?!(?:nominated|ratified|withdrawn)\s.*\(#)"
    r"(nominated|ratified|expired-reopened|withdrawn)\s+(\d{4}-\d{2}-\d{2})"
    r"(?:\s+\(#(\d+)\))?$",
)
REGISTER_STATUSES = ("nominated", "ratified", "expired-reopened", "withdrawn")


def criterion_error(row: Row) -> str | None:
    """Consistency of the readiness-criterion cell — a STRUCTURAL error
    (fail-closed), not a soft warning. 8- and 9-cell schemas only: a 7-cell
    legacy row has no criterion column and is exempt.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    crit = row["criterion"]
    if crit is None:
        return None
    t = row["terminal"].lower()
    if t.startswith("verified-landed") and crit in BLANK_CELL:
        return (
            f"line {row['line']}: {row['id']} is verified-landed but its "
            f"readiness-criterion cell is {crit!r} — a confirmed finding "
            f"must carry the criterion written at adjudication"
        )
    if t.startswith("accepted-residue") and crit in BLANK_CELL:
        return (
            f"line {row['line']}: {row['id']} is accepted-residue but its "
            f"readiness-criterion cell is {crit!r} — an upheld finding "
            f"keeps the criterion written at adjudication (an empty or "
            f"dash cell is banned)"
        )
    if t.startswith(AWAITING_SIGNATURE) and crit in BLANK_CELL:
        return (
            f"line {row['line']}: {row['id']} is {AWAITING_SIGNATURE} but "
            f"its readiness-criterion cell is {crit!r} — a residue NOMINEE "
            f"is an upheld finding and keeps the criterion written at "
            f"adjudication, exactly as a ratified residue does"
        )
    if t.startswith(("refuted-with-reason", "refused")) and crit != "—":
        return (
            f"line {row['line']}: {row['id']} is refuted/refused but its "
            f"readiness-criterion cell is {crit!r} — it must be exactly "
            f"the em-dash '—' (deliberately not needed, not forgotten)"
        )
    return None


def nomination_error(row: Row) -> str | None:
    """Reject a BLOCKER nominated into the residue queue.

    Blockers are categorically non-nominable: residue is the route for risk
    that may be CARRIED, and by the severity taxonomy a blocker means the
    object is unfit for its purpose — there is nothing there to carry. The
    combination is a STRUCTURAL error rather than a warning, because a rule
    that only warns is a rule that gets walked past.
    """
    if not row["terminal"].strip().lower().startswith(AWAITING_SIGNATURE):
        return None
    if row["severity"].strip().lower() != BLOCKER:
        return None
    return (
        f"line {row['line']}: {row['id']} is severity {BLOCKER} and carries "
        f"`{AWAITING_SIGNATURE}` — a blocker is categorically non-nominable: "
        f"it closes through a fix, through a gate or through a refutation, "
        f"never through residue"
    )


def class_slugs(row: Row) -> list[str]:
    """The `class:` slugs the row's verdict cell carries, by exact match."""
    return CLASS_TAG_RE.findall(row["verdict"])


def contract_status_error(row: Row) -> str | None:
    """Reject a security/PII row disposed of by the contract's pre-signature.

    `out-of-scope-by-contract` closes a finding on a signature given BEFORE
    the round, when the Non-Goals were authored. The security/PII class is
    the one class both of whose outcomes — accept and refuse — need the
    owner's live word, so a pre-signed disposition does not reach it: the
    combination is a STRUCTURAL error unless the row also carries a live
    `user-signed <date>` in its terminal cell. A warning would not do; a rule
    that only warns is a rule that gets walked past.
    """
    if not row["terminal"].strip().lower().startswith(OUT_OF_SCOPE):
        return None
    if SECURITY_PII_SLUG not in class_slugs(row):
        return None
    if SIGNED_DATE_RE.search(row["terminal"]):
        return None
    return (
        f"line {row['line']}: {row['id']} carries `class:{SECURITY_PII_SLUG}` "
        f"and `{OUT_OF_SCOPE}` with no live `user-signed <date>` — the "
        f"contract's pre-signed disposition does not reach a class both of "
        f"whose outcomes require the owner's own word"
    )


def logged_no_action_error(row: Row) -> str | None:
    """Reject a `logged-no-action` the zone does not authorize.

    The status closes an INFORMATIVE finding in a batch the owner signs off
    in one act, and the only thing that says a finding is informative is the
    contract's zone map, carried in the row's `zone` cell. So the status is
    readable only where that cell exists (the v3 schema) and only where it
    reads `Z3`. In a 7- or 8-cell row there is no cell to check the
    condition against at all — that is a STRUCTURAL error rather than an
    undefined case, because a mass closure route accepted on no condition is
    exactly the hole the zone was introduced to avoid. The security/PII
    exception is the one `contract_status_error` states for the other
    pre-signed route, word for word: a class both of whose outcomes need the
    owner's own word is never disposed of inside a batch act.
    """
    t = row["terminal"].strip().lower()
    if not t.startswith(LOGGED_NO_ACTION):
        return None
    zone = row["zone"]
    if zone is None:
        return (
            f"line {row['line']}: {row['id']} carries `{LOGGED_NO_ACTION}` in a "
            f"{V1_WIDTH}- or {V2_WIDTH}-cell row — the status exists only in "
            f"the {V3_WIDTH}-cell (v3) schema, where the `zone` cell its "
            f"condition reads exists at all"
        )
    if zone.strip().upper() != ZONE_INFORMATIVE:
        return (
            f"line {row['line']}: {row['id']} carries `{LOGGED_NO_ACTION}` with "
            f"zone {zone.strip()!r} — the status is accepted at zone "
            f"{ZONE_INFORMATIVE} alone; a finding outside the informative zone "
            f"closes through a fix, a refutation or residue"
        )
    if SECURITY_PII_SLUG in class_slugs(row) and not SIGNED_DATE_RE.search(
        row["terminal"],
    ):
        return (
            f"line {row['line']}: {row['id']} carries `class:{SECURITY_PII_SLUG}` "
            f"and `{LOGGED_NO_ACTION}` with no live `user-signed <date>` — a "
            f"class both of whose outcomes require the owner's own word is "
            f"never closed inside a batch act"
        )
    return None


def class_tag_error(row: Row) -> str | None:
    """Reject a `class:` tag whose slug is outside the tag alphabet.

    Fail-closed, like every other literal this script parses: a `class:`
    that ATTEMPTS a slug and produces none readable under
    `class:([a-z0-9-]{1,32})(?![a-z0-9-])` is a STRUCTURAL error rather
    than a guess at where the slug ends.

    ONE case is deliberately not an error: `class:` immediately followed
    by whitespace, by a `|`, or by the end of the cell is English PROSE,
    not an attempted tag — it is ignored, groups nothing and reports
    nothing. The reason is compatibility, which outranks the widest
    reading of the fail-closed rule: verdict cells written before the tag
    existed carry the hand convention `[class: <name>]` and ordinary
    sentences ending "... the security class: user-signed <date>", and an
    old ledger must recount exactly as it did in 0.2.0. A tag never
    attaches a slug across whitespace, so nothing readable is lost by
    skipping these; what stays an error is `class:Foo`, `class:.x` and a
    slug longer than 32 — a boundary that is sometimes guessed is a
    boundary no reader can rely on.
    """
    # The `class:` + whitespace prose branch is a compatibility branch.
    # no live writer; kept for c29…c34, c73.
    return tag_slug_error(row, CLASS_TAG, CLASS_TAG_RE)


def shelf_tag_error(row: Row) -> str | None:
    """Reject a `shelf:` tag whose slug is outside the tag alphabet.

    The same rule as `class:`, deliberately and not by coincidence: one
    boundary for every verdict-cell tag that takes a slug. A `shelf:`
    followed straight away by whitespace, a `|` or the end of the cell is
    prose here too — the tag is optional, and a ledger that never sets it
    must recount exactly as it did before the tag existed.
    """
    return tag_slug_error(row, SHELF_TAG, SHELF_TAG_RE)


def tag_slug_error(
    row: Row,
    tag: str,
    pattern: re.Pattern[str],
) -> str | None:
    """Return the diagnostic for a slug-carrying verdict tag, or None.

    The shared body of the two checks above: find each occurrence of the
    tag, skip the ones that are prose by the boundary rule, and refuse the
    rest unless the slug parses under the tag's own pattern.
    """
    verdict = row["verdict"]
    at = verdict.find(tag)
    while at != -1:
        after = verdict[at + len(tag) : at + len(tag) + 1]
        prose = after == "" or after.isspace() or after in CLASS_TAG_PROSE
        if not prose and pattern.match(verdict, at) is None:
            return (
                f"line {row['line']}: {row['id']} carries a `{tag}` tag "
                f"whose slug is not 1-{SLUG_MAX} characters of [a-z0-9-]: "
                f"{verdict[at : at + 40]!r}"
            )
        at = verdict.find(tag, at + len(tag))
    return None


def process_prefix_errors(declared: list[str], lenses: list[str]) -> list[str]:
    """Reject a process prefix that is also declared as a lens.

    The whole point of the field is that a process row is tellable from a
    lens's row; a prefix written in both places tells them apart nowhere,
    and it would put the process's rows inside `k`'s own lens.
    """
    collisions = [p for p in declared if p in lenses]
    if not collisions:
        return []
    return [
        (
            f"header field `Process prefixes:` names {', '.join(collisions)}, "
            f"which the `Lenses:` field also declares — a process prefix is "
            f"what is NOT a lens, so it must be distinct from every lens "
            f"prefix"
        ),
    ]


def security_lens_errors(rows: list[Row], prefix: str | None) -> list[str]:
    """Reject a security-lens row that carries neither the class nor a declass.

    The DEFAULT is the point: a finding raised by the lens the owner declared
    the security lens IS of the security/PII class, and the adjudicator marks
    it without deciding the question again. Removing the default is allowed —
    the adjudicator is the one who knows — but only IN WRITING and in the
    same row: `declassed:security-pii — <reason>`, the reason free prose and
    never empty. Silence is what this closes: an unmarked row on a security
    lens used to walk past every gate keyed on the class.

    An EMPTY verdict cell is not that silence. It is the state "not
    adjudicated" — a stage-5 layout the adjudicator has not reached yet —
    and it is reported by its own line rather than refused here. The
    relaxation is exactly the empty case: a FILLED cell that leaves the
    class out is a judgment that was made and left the class out, and it
    stays the structural error it always was.
    """
    if prefix is None:
        return []
    out: list[str] = []
    for r in rows:
        if r["id"].rsplit("-", 1)[0] != prefix:
            continue
        if not r["verdict"].strip():
            continue
        if SECURITY_PII_SLUG in class_slugs(r):
            continue
        if DECLASSED_TAG in r["verdict"]:
            if DECLASSED_RE.search(r["verdict"]) is None:
                out.append(
                    f"line {r['line']}: {r['id']} carries "
                    f"`{DECLASSED_TAG}` with an empty reason — removing the "
                    f"security lens's default class takes a written reason "
                    f"in the same cell, `{DECLASSED_TAG} — <reason>`",
                )
            continue
        out.append(
            f"line {r['line']}: {r['id']} was raised by the declared security "
            f"lens {prefix} and carries neither `class:{SECURITY_PII_SLUG}` "
            f"nor `{DECLASSED_TAG} — <reason>` — a finding of the security "
            f"lens takes the class by DEFAULT, and the default is removed in "
            f"writing or not at all",
        )
    return out


def register_row_error(cells: list[str], n: int) -> str | None:
    """Return the first structural defect of one register row, or None.

    Fail-closed, exactly like the ledger's own row parsing: the register is
    the durable record of accepted risk, and a row nobody can read is a
    risk nobody re-counts. A blank `rationale` or `compensating-control` is
    a defect and not a gap to be filled later — the whole point of the two
    cells is that the acceptance was argued when it was made.
    """
    rid, severity, _hook, rationale, control, review_by, status = cells[:7]
    if severity.strip().lower() == BLOCKER:
        return (
            f"line {n}: {rid} is severity {BLOCKER} — a blocker is "
            f"categorically non-nominable and may not appear in the register"
        )
    if rationale.strip() in BLANK_CELL:
        return f"line {n}: {rid} has a blank `rationale` — a mandatory field"
    if control.strip() in BLANK_CELL:
        return (
            f"line {n}: {rid} has a blank `compensating-control` — the "
            f"literal 'none — direct risk accepted' is allowed, a blank cell "
            f"is not"
        )
    try:
        date.fromisoformat(review_by.strip())
    except ValueError:
        return (
            f"line {n}: {rid} has `review-by` {review_by.strip()!r} — it must "
            f"be a calendar-valid ISO date (YYYY-MM-DD)"
        )
    m = REGISTER_STATUS_RE.match(status.strip())
    if m is None:
        return (
            f"line {n}: {rid} has `status` {status.strip()!r} — it must be "
            f"one of {', '.join(REGISTER_STATUSES)}, each followed by an ISO "
            f"date, expired-reopened optionally by its cycle counter '(#<n>)'"
        )
    try:
        date.fromisoformat(m.group(2))
    except ValueError:
        return (
            f"line {n}: {rid} has status date {m.group(2)!r} — not a calendar "
            f"date (YYYY-MM-DD)"
        )
    return None
