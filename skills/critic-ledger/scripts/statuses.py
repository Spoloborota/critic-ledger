#!/usr/bin/env python3
# The payload ships loose files rather than a package, so this module sits
# in no __init__.py: it is imported from `recount.py`'s own directory.
"""Row statuses of a critic-ledger ledger: which rows are terminal, and which wait.

Imported by `recount.py` from its own directory. Nothing here prints: every
function returns its verdict, and the caller decides what reaches stdout.
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

from ledger_md import (
    BLANK_CELL,
)

if TYPE_CHECKING:
    from ledger_model import Row

# An owner signature is the literal `user-signed` IMMEDIATELY followed by an
# ISO date: an undated signature is not a signature.
SIGNED_DATE_RE = re.compile(r"user-signed\s+(\d{4}-\d{2}-\d{2})")

# A row whose criterion cell is exactly this is refuted/refused, never upheld.
NOT_NEEDED = "—"

# --- the round contract: the two statuses it brings with it ----------------
# A finding whose whole claim is covered by a declared Non-Goal reaches a
# terminal status with NO live signature — the signature was given when the
# Non-Goals were authored — which is precisely why the literal is recognized
# only COMPLETE: the Non-Goal is named and the contract's signing date is in
# the cell, or the row is not disposed of by the contract at all.
OUT_OF_SCOPE = "out-of-scope-by-contract"
OUT_OF_SCOPE_RE = re.compile(
    r"out-of-scope-by-contract\s*\(NG-\d+,\s*signed\s+(\d{4}-\d{2}-\d{2})\)",
)

# --- the stop rule's freeze, which is NOT `superseded-by-rewrite` ----------
# A row still open when the contract's stop rule fires is frozen and carried,
# and that is a TERMINAL status: it closes the round, not the finding. The
# header field it leans on is ONE per ledger and written ONCE — the collision
# rule, since the field has two independent writers (a stop rule firing, and
# the one-off freeze of an exhausted blocker).
FROZEN_CARRIED = "frozen-carried"
FROZEN_CARRIED_RE = re.compile(
    r"frozen-carried\s*\(stop-rule,\s*(\d{4}-\d{2}-\d{2})\)",
)

# --- residue: the two named waits and the durable register -----------------
# A residue nominee sits in a NAMED non-terminal state until the owner
# ratifies it, and a second named wait holds rows waiting for an act of the
# owner's own. Both are non-terminal (exit 1) and both are counted apart
# from an ordinary open row. See the two bullets in the module docstring.
AWAITING_SIGNATURE = "awaiting-signature"
AWAITING_LOGGED_NO_ACTION = "awaiting-logged-no-action"

# The terminal status the Z3 closing act produces. Recognized only in the v3
# schema and only at zone Z3 — see the docstring's terminal-status list.
LOGGED_NO_ACTION = "logged-no-action"
NOMINATED_RE = re.compile(r"nominated\s+(\d{4}-\d{2}-\d{2})")
LISTED_RE = re.compile(r"listed\s+(\d{4}-\d{2}-\d{2})")

# The severity that may never be nominated into residue.
BLOCKER = "blocker"

# An UNRATIFIED nomination has a deadline of its own: 30 days is OURS,
# marked as ours — no standard supplies it.
NOMINATION_MAX_DAYS = 30


def waiting_state(row: Row) -> tuple[str | None, str | None]:
    """Return (the row's named wait or None, problem-or-None).

    A named wait is non-terminal but is NOT an open row: it is counted and
    printed apart from one, and it is what the second and third exit buckets
    read. An `awaiting-signature` cell whose `nominated <date>` is missing or
    is not a calendar date names no wait at all — the row falls back to
    ORDINARY OPEN with a diagnostic, because a nomination whose age cannot be
    read cannot be chased for its deadline.
    """
    t = row["terminal"].strip().lower()
    if t.startswith(AWAITING_SIGNATURE):
        m = NOMINATED_RE.search(t)
        if m is None:
            return None, (
                f"{row['id']}: {AWAITING_SIGNATURE} without the literal "
                f"'nominated <date>' (YYYY-MM-DD) — a nomination carries "
                f"the date it was made; counted as an open row"
            )
        try:
            date.fromisoformat(m.group(1))
        except ValueError:
            return None, (
                f"{row['id']}: nomination date {m.group(1)!r} is not a "
                f"calendar date (YYYY-MM-DD); counted as an open row"
            )
        return AWAITING_SIGNATURE, None
    if t.startswith(AWAITING_LOGGED_NO_ACTION):
        # The date does NOT name this wait: the row belongs to the queue the
        # owner's closing act drains whether or not it can be aged, so it
        # stays in bucket 3 either way. What an unreadable date costs is the
        # 30-day limit, and that is reported rather than passed over.
        m = LISTED_RE.search(t)
        if m is None:
            return AWAITING_LOGGED_NO_ACTION, (
                f"{row['id']}: {AWAITING_LOGGED_NO_ACTION} without the literal "
                f"'listed <date>' (YYYY-MM-DD) — the wait is counted, but its "
                f"age cannot be read and the {NOMINATION_MAX_DAYS}-day limit "
                f"cannot be applied to it"
            )
        try:
            date.fromisoformat(m.group(1))
        except ValueError:
            return AWAITING_LOGGED_NO_ACTION, (
                f"{row['id']}: listed date {m.group(1)!r} is not a calendar "
                f"date (YYYY-MM-DD); the wait is counted, its age is not"
            )
        return AWAITING_LOGGED_NO_ACTION, None
    return None, None


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
        if "NOT LANDED" in v.upper() or v.strip() in BLANK_CELL:
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
    if t.startswith(OUT_OF_SCOPE):
        return complete_literal(
            row,
            OUT_OF_SCOPE_RE,
            f"{OUT_OF_SCOPE} (NG-<n>, signed <YYYY-MM-DD>)",
            "a pre-signed disposition is recognized only in full, so that "
            "the Non-Goal it invokes is named and the contract's signing "
            "date stands in the cell",
        )
    if t.startswith(LOGGED_NO_ACTION):
        # The zone condition and the security/PII exception are STRUCTURAL
        # errors checked at parse time (`logged_no_action_error`), so a row
        # that reaches here has passed both: at zone Z3, in a v3 row, and
        # with the owner's live signature where the class demands one.
        return True, None
    if t.startswith(FROZEN_CARRIED):
        return complete_literal(
            row,
            FROZEN_CARRIED_RE,
            f"{FROZEN_CARRIED} (stop-rule, <YYYY-MM-DD>)",
            "a freeze is recognized only in full, because the date in the "
            "cell is the date THIS row was frozen and the header's single "
            "freeze field cannot supply it for a second occasion",
        )
    return False, None


def complete_literal(
    row: Row,
    pattern: re.Pattern[str],
    shape: str,
    why: str,
) -> tuple[bool, str | None]:
    """Terminality of a status recognized only under its COMPLETE literal.

    Both statuses the round CONTRACT brings close a finding without a live
    signature, so neither is allowed to close it by its opening words: the
    full shape carries the reference (`NG-<n>`) and the date that make the
    closure auditable months later. A partial match is NON-terminal with a
    diagnostic, never a structural error — the row is simply not yet closed.
    """
    m = pattern.search(row["terminal"])
    if m is None:
        return False, f"{row['id']}: expected the complete literal `{shape}` — {why}"
    try:
        date.fromisoformat(m.group(1))
    except ValueError:
        return False, (
            f"{row['id']}: date {m.group(1)!r} in `{shape}` is not a "
            f"calendar date (YYYY-MM-DD)"
        )
    return True, None


def is_upheld(row: Row) -> bool:
    """Whether a finding stood: a real criterion, or a signed refusal."""
    refused = row["terminal"].strip().lower().startswith("refused")
    return row["criterion"] != NOT_NEEDED or refused


def frozen_carried_ids(rows: list[Row]) -> list[str]:
    """The ids the stop rule's freeze carried — valid literal or not.

    Membership is read off the status word alone, so a row whose literal is
    incomplete still counts as a carry for the header check below: a
    malformed freeze must not be able to hide the missing header field.
    """
    return [
        r["id"]
        for r in rows
        if r["terminal"].strip().lower().startswith(FROZEN_CARRIED)
    ]
