#!/usr/bin/env python3
# The payload ships loose files rather than a package, so this module sits
# in no __init__.py: it is imported from `recount.py`'s own directory.
"""The report lines of a critic-ledger recount.

Imported by `recount.py` from its own directory. Every function returns the
lines it renders; only the entry point prints them, in its own order.
"""

from datetime import UTC, date, datetime

from ledger_md import (
    BLANK_CELL,
    SEVERITIES,
)
from ledger_model import (
    ENDED_NAME,
    STARTED_NAME,
    TS_FORMAT,
    PassRow,
    RegisterRow,
    Row,
    load,
    parse_register,
    parse_ts,
    resolve_register,
)
from metrics import (
    CLASS_KILL_TAG_RE,
    CLASS_ORIGIN_ADJUDICATOR,
    FIX_APPLICATION_TAG,
    FROM_TAG_RE,
    PLATEAU_SEVERITIES,
    PLATEAU_WINDOW,
    awaits_a_batch,
    batch_key,
    capture_sets,
    class_groups,
    kill_groups,
    kill_row_state,
    new_findings_severity,
    not_landed,
    shelf_slugs,
)
from statuses import (
    LISTED_RE,
    NOMINATION_MAX_DAYS,
    is_upheld,
    terminal_status,
)
from structural_checks import (
    REGISTER_STATUSES,
)

# The convergence signal's window: TWO consecutive clean passes
# (`references/stage-9-closure.md` 9.1).
STREAK_PASSES = 2

# The sustained-rate baseline. OURS — one measured round — and never a
# trigger on its own: the framing is tightened only when the shelf share
# beside the rate agrees.
SUSTAINED_BASELINE_PCT = 92.0

# The SECOND upheld finding of one class is the class-kill trigger. That
# number is OURS, Tricorder-shaped — no standard supplies it.
CLASS_KILL_THRESHOLD = 2

# Injection rate: LITERATURE reference points, printed as such and never as
# our own measurement — 7% undisciplined, 3.5% disciplined floor — and the
# run of consecutive batches at or above the first one that raises the flag.
INJECTION_HIGH_PCT = 7.0
INJECTION_FLOOR_PCT = 3.5
INJECTION_HIGH_RUN = 2
PERCENT = 100.0

# The cycle from which a re-opened row may no longer ride inside a batch
# ratification act.
SECOND_CYCLE = 2

# Jackknife capture-recapture applies from FOUR lenses up; below that the
# estimate is not printed at all — `n/a: k<4`, never a number.
JACKKNIFE_MIN_LENSES = 4


def listed_date(row: Row) -> date | None:
    """The calendar-valid date an `awaiting-logged-no-action` row was listed."""
    m = LISTED_RE.search(row["terminal"].strip().lower())
    if m is None:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def z3_overdue_lines(rows: list[Row], waiting: list[str], today: date) -> list[str]:
    """Return one line per Z3 row whose wait has outrun the 30-day limit.

    The limit is NOT a new number: it is the nomination limit of the residue
    queue, carried over because both are the same shape — a row parked on an
    act of the owner's that has not happened. Report-only, like every other
    escalation here: it names a fork the orchestrator owes the owner, and
    reaches no exit code, which stays the wait's own (1).
    """
    out: list[str] = []
    for r in rows:
        if r["id"] not in waiting:
            continue
        listed = listed_date(r)
        if listed is None:
            continue
        held = (today - listed).days
        if held <= NOMINATION_MAX_DAYS:
            continue
        out.append(
            f"Z3 CLOSURE OVERDUE: {r['id']} (listed {listed}, {held} days; the "
            f"{NOMINATION_MAX_DAYS}-day limit is the residue queue's own, "
            f"carried over and not a new number) — put it to the owner as its "
            f"own fork: close it, take it out of the batch (the row returns to "
            f"adjudication as an open finding), or set a new date on the "
            f"owner's explicit word. A permanent wait is banned.",
        )
    return out


def severity_line(rows: list[Row], open_ids: set[str]) -> str:
    """Return the severity distribution line (severity x terminal status).

    Severity is cell index 1 in the 7-, 8- and 9-cell schemas alike, so
    this is computed for v1, v2 and v3 ledgers with no schema detection.
    The three canonical classes are always named — a ledger with no blocker
    is a fact worth printing — and any other value found in the cell is
    reported after them under its own name.
    """
    counts: dict[str, list[int]] = {s: [0, 0] for s in SEVERITIES}
    for r in rows:
        key = r["severity"].strip().lower() or "(blank)"
        bucket = counts.setdefault(key, [0, 0])
        bucket[0] += 1
        if r["id"] not in open_ids:
            bucket[1] += 1
    names = list(SEVERITIES) + sorted(k for k in counts if k not in SEVERITIES)
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


def not_adjudicated_lines(rows: list[Row]) -> list[str]:
    """Report the rows whose `verdict` cell is still empty, or [].

    A STATE, not a defect: the finding is transcribed and the adjudicator
    has not reached it. Such a row is non-terminal anyway, so it holds the
    round open through the ordinary open-rows route and this line changes
    no exit code. A ledger with every verdict filled prints nothing here,
    which is what keeps every ledger written before this recount unchanged.
    """
    n = sum(1 for r in rows if not r["verdict"].strip())
    if not n:
        return []
    return [
        (
            f"not adjudicated: {n} rows — the `verdict` cell is empty, which "
            f"is the state before adjudication and not a structural error; "
            f"the security lens's backstop does not read an empty cell"
        ),
    ]


def kill_in_flight_lines(rows: list[Row]) -> list[str]:
    """`kill in flight: <slug> (<id>)` for every OPEN class-kill row.

    The class-kill warning speaks of "a 3rd recurrence with no kill in
    flight", and until now nothing said whether one was in flight or not.
    A row carrying `class-kill:<slug>` IS the gate's ledger row for that
    class; while it is not terminal, the kill is being built and the
    report names it and its id. Report-only, like every other line here.
    """
    out: list[str] = []
    for r in rows:
        if terminal_status(r)[0]:
            continue
        out.extend(
            f"  kill in flight: {slug} ({r['id']})"
            for slug in dict.fromkeys(CLASS_KILL_TAG_RE.findall(r["verdict"]))
        )
    return out


def class_kill_lines(rows: list[Row], prefix: str | None = None) -> list[str]:
    """Return the class-recurrence report, or [] when no row is tagged.

    A ledger with no `class:` and no `class-kill:` tag prints nothing here,
    which is what keeps an untagged ledger recounting exactly as it did
    before. `prefix` is the declared security lens, and it is what tells
    the lens's DEFAULT class apart from a class the adjudicator chose.
    """
    groups = class_groups(rows)
    out: list[str] = []
    if groups:
        body = " | ".join(f"{s} {len(groups[s])}" for s in sorted(groups))
        out.append(f"class recurrences (upheld rows per class tag): {body}")
        kills = kill_groups(rows, prefix)
        for slug in sorted(groups):
            counted = kills.get(slug, [])
            if len(counted) < len(groups[slug]):
                out.append(
                    f"  class-kill count for {slug}: {len(counted)} of "
                    f"{len(groups[slug])} upheld rows — the rest carry the "
                    f"declared security lens's DEFAULT class, which is a "
                    f"signature mode and not a defect class; an adjudicator "
                    f"who means the class itself writes "
                    f"`{CLASS_ORIGIN_ADJUDICATOR}` in the same cell",
                )
            if len(counted) >= CLASS_KILL_THRESHOLD:
                census = f"{slug} ({len(counted)} upheld: {', '.join(counted)})"
                state = kill_row_state(rows, slug)
                if state == "in flight":
                    out.append(
                        f"  CLASS-KILL IN FLIGHT: {census} — the threshold is "
                        f"reached and the kill row for this class is already "
                        f"open; nothing further is due here.",
                    )
                elif state == "done":
                    out.append(
                        f"  CLASS-KILL DONE: {census} — the threshold is "
                        f"reached and the kill row for this class is "
                        f"terminal; nothing further is due here.",
                    )
                else:
                    out.append(
                        f"  CLASS-KILL DUE: {census} — the next step for this "
                        f"class is a mechanical gate or a convention that "
                        f"kills it, logged as its own class-kill ledger row, "
                        f"not one more fix; a 3rd recurrence with no kill in "
                        f"flight escalates to the user. The 2nd-recurrence "
                        f"trigger is OURS, Tricorder-shaped — no standard "
                        f"supplies it.",
                    )
    out.extend(kill_in_flight_lines(rows))
    return out


def injection_lines(rows: list[Row]) -> list[str]:
    """Return the per-batch injection rate, or [] when no row is tagged.

    DENOMINATOR — batch membership: the rows one batch fixed all carry
    that batch's identifier in their `fix` cell (the per-batch commit
    hash, or the snapshot name where no commit sanction exists), grouped
    by literal match. The ledger's "Batch deltas" prose is a historical
    snapshot and is deliberately not parsed. NUMERATOR — the carrier of
    the "finding <- the batch that produced it" link: the `from:<batch>`
    reference inside an `origin:fix-application` tag, and nothing else. A
    tagged row with no readable `from:` is listed as unattributed rather
    than lowering the share in silence.
    """
    tagged = [r for r in rows if FIX_APPLICATION_TAG in r["verdict"]]
    if not tagged:
        return []
    batches: dict[str, list[str]] = {}
    unidentified: list[str] = []
    for r in rows:
        key = batch_key(r["fix"])
        if key in BLANK_CELL:
            if awaits_a_batch(r):
                unidentified.append(r["id"])
            continue
        batches.setdefault(key, []).append(r["id"])
    charged: dict[str, list[str]] = {}
    unattributed: list[str] = []
    for r in tagged:
        m = FROM_TAG_RE.search(r["verdict"])
        if m is None:
            unattributed.append(r["id"])
            continue
        # The SAME normalization on both sides of the join: two different
        # readings of one batch identifier is the divergence that makes a
        # correctly tagged row look orphaned.
        charged.setdefault(batch_key(m.group(1)), []).append(r["id"])
    out = [
        (
            "injection rate (findings caused by a batch's own fix / rows "
            f"that batch fixed; {INJECTION_HIGH_PCT:g}% and "
            f"{INJECTION_FLOOR_PCT:g}% are LITERATURE reference points — "
            "undisciplined and disciplined floor — not our measurement):"
        ),
    ]
    # Batches in first-appearance order, which is the order the run of
    # consecutive high batches is read in.
    run = 0
    for key, ids in batches.items():
        num = len(charged.get(key, []))
        pct = PERCENT * num / len(ids)
        out.append(f"  {key}: {num}/{len(ids)} = {pct:.1f}%")
        run = run + 1 if pct >= INJECTION_HIGH_PCT else 0
        if run >= INJECTION_HIGH_RUN:
            out.append(
                f"  INJECTION RATE HIGH: {key}, {pct:.1f}% — "
                f"{INJECTION_HIGH_RUN} consecutive batches at or above "
                f"{INJECTION_HIGH_PCT:g}%: recommend stopping the batching "
                f"and forking to the user, whose call the stop is. Advisory "
                f"— this metric never stops the round by itself.",
            )
    if unattributed:
        out.append("  INJECTION UNATTRIBUTED: " + ", ".join(unattributed))
    orphans = sorted(k for k in charged if k not in batches)
    if orphans:
        out.append(
            "  injection: no batch in the fix column is named by from:"
            + ", from:".join(orphans),
        )
    if unidentified:
        out.append(
            "  injection rate: n/a (batch not identifiable) for "
            + ", ".join(unidentified),
        )
    return out


def estimate_lines(prefixes: list[str], rows: list[Row]) -> list[str]:
    """Return the residual-defect ESTIMATE block — report-only, always.

    `N-hat = D + ((k-1)/k) * f1`, the Jackknife capture-recapture estimator,
    printed ONLY at `k >= 4` and otherwise as the named `n/a` form. It never
    reaches an exit code and it is not part of any stop rule: it is an
    ADVISORY number, and the caveat printed beside it says whose caution it
    carries.
    """
    k = len(prefixes)
    if k == 0:
        return [
            (
                "residual-defect ESTIMATE: n/a: k not derived from the header "
                "(no `Lenses:` field with machine-readable "
                "` - <PREFIX> | <lens> | <model>` lines) — k is never guessed "
                "from the id prefixes in the table."
            ),
        ]
    if k < JACKKNIFE_MIN_LENSES:
        return [
            (
                f"residual-defect ESTIMATE: n/a: k<4 (k={k}; the Jackknife "
                f"estimator is applied from four lenses up)."
            ),
        ]
    d, f1 = capture_sets(rows, prefixes)
    n_hat = d + ((k - 1) / k) * f1
    return [
        (
            f"residual-defect ESTIMATE (Jackknife capture-recapture): "
            f"N-hat {n_hat:.1f} | D {d} raised | f1 {f1} single-lens | k {k} "
            f"({', '.join(prefixes)})"
        ),
        (
            "  ESTIMATE is ADVISORY, reported and never acted on: it enters no "
            "stop rule and no exit code. Lens diversity does not invalidate it "
            "(the source measured little or no impact on the estimate), but the "
            "caution that remains is OURS and is named as ours: our four field "
            "measurements put the single-lens share at 75-94% and N-hat near "
            "2*D, and they count D as distinct CONFIRMED findings where this "
            "line counts distinct RAISED ones, so comparability is not "
            "established. Treat the number as advice, not as a target."
        ),
    ]


def plateau_line(counts: list[int]) -> list[str]:
    """Return the severity-weighted plateau lines for an ORDERED window.

    `counts` is oldest-first and holds exactly `PLATEAU_WINDOW` entries, so
    the window yields two deltas and the moving average is their mean. The
    caller has already ordered them by `Round-started`; this function never
    reorders and never checks chronology.

    TWO lines, not one. The single line mixed a CURVE — numbers that go up
    or down — with a sentence about the binary signal that actually stops
    the round, and a reader meeting it for the first time read "the curve
    is falling" as "the criterion is met". They are different claims with
    different consequences, so they are different lines: the numbers here,
    and the standing of the signal itself in `stop_criterion_line`.
    """
    deltas = [counts[i + 1] - counts[i] for i in range(len(counts) - 1)]
    average = sum(deltas) / len(deltas)
    return [
        (
            f"severity plateau ({PLATEAU_WINDOW}-round moving average of "
            f"major+blocker deltas): {average:+.1f} | major+blocker per round "
            f"(oldest first): {' -> '.join(str(c) for c in counts)} | deltas "
            f"{', '.join(f'{d:+d}' for d in deltas)}"
        ),
        (
            "  severity plateau is ADVISORY: it is reported beside the binary "
            "verdict-streak signal, never instead of it, and it enters no stop "
            "rule, no gate and no exit code."
        ),
    ]


def stop_criterion_line(pass_rows: list[PassRow]) -> str:
    """The standing of the binary convergence signal, as ONE line.

    The signal is stage 9's: TWO CONSECUTIVE verification passes with zero
    major and zero NOT LANDED. What this line reports is what the passes
    table makes machine-readable — the NOT-LANDED count, the number of new
    findings and the severity that count is written with.

    SEVERITY-AWARE, which is the rule as the skill states it: a pass whose
    new findings are all MINOR still satisfies "zero major/blocker" and is
    counted clean. It used to be counted dirty, and the line then printed
    "not met — pass 1: 1 new findings" over a round the same script had
    already called closable. A count whose severity the cell does not name
    stays dirty: an unread severity is never read as minor, exactly as an
    unreadable verdicts cell is never read as a clean pass. The
    qualification clause (where a row was ever PARTIAL or NOT LANDED, one
    of the two passes must have closed such a row) is the adjudicator's to
    apply, not a cell any table carries. Report-only, like every line
    around it: it enters no exit code.
    """
    head = "stop criterion (verdict streak): "
    if len(pass_rows) < STREAK_PASSES:
        return (
            f"{head}not met — {len(pass_rows)} verification "
            f"pass(es) recorded, the signal needs {STREAK_PASSES} "
            f"consecutive clean ones; report-only, no exit code"
        )
    reasons: list[str] = []
    for row in pass_rows[-STREAK_PASSES:]:
        cell = row["verdicts"] or ""
        nl = not_landed(cell)
        if nl is None:
            reasons.append(
                f"pass {row['ordinal']}: verdicts cell not machine-readable "
                f"({cell.strip() or 'empty'!s})",
            )
        elif nl:
            reasons.append(f"pass {row['ordinal']}: {nl} NOT LANDED")
        if row["new"] is None:
            reasons.append(
                f"pass {row['ordinal']}: new-findings cell not machine-readable",
            )
        elif row["new"]:
            severity = new_findings_severity(row["new_text"] or "")
            if severity is None:
                reasons.append(
                    f"pass {row['ordinal']}: {row['new']} new findings of "
                    f"unnamed severity",
                )
            elif severity in PLATEAU_SEVERITIES:
                reasons.append(
                    f"pass {row['ordinal']}: {row['new']} new {severity} findings",
                )
    if reasons:
        return f"{head}not met — " + "; ".join(reasons) + "; report-only, no exit code"
    last = ", ".join(r["ordinal"] for r in pass_rows[-STREAK_PASSES:])
    return (
        f"{head}met — passes {last} both clean "
        f"(0 NOT LANDED, 0 new major/blocker findings)"
    )


def sustained_lines(
    prefixes: list[str],
    window: list[tuple[str, list[Row]]],
) -> list[str]:
    """Return the per-lens sustained rate with the shelf share beside it.

    The rate is upheld over RAISED, per declared lens, over the whole
    window — this ledger plus the `--prev` ledgers that parsed — which is
    what makes it SUSTAINED rather than one round's rate. The shelf share
    beside it is the share of that lens's REFUTATIONS carrying a `shelf:`
    tag, and the two are printed together on purpose: a lens below the
    baseline has its framing tightened in the next round, never dropped,
    and that call is PAIRED — the rate alone never triggers it, because
    refutations the contract's shelf closed were cheap to refute rather
    than wrong to raise.

    Report-only in every branch: nothing here reaches an exit code, and a
    figure that cannot be computed is `n/a: <reason>` and never `0`. The
    prefixes come from the header's machine-form `Lenses:` lines — the same
    single source `k` uses — so a header that declares none yields one
    `n/a` line rather than a count guessed off the findings table.
    """
    if not prefixes:
        return [
            (
                "per-lens sustained rate: n/a: no machine-form `Lenses:` lines "
                "in the header — the rate is never counted off the id prefixes "
                "in the findings table, where verification passes write rows too"
            ),
        ]
    rows = [r for _, ledger_rows in window for r in ledger_rows]
    if any(r["criterion"] is None for r in rows):
        return [
            (
                "per-lens sustained rate: n/a: a v1 (7-cell) ledger in the "
                "window has no criterion column, so upheld and refuted cannot "
                "be split"
            ),
        ]
    shelf_in_use = any(shelf_slugs(r) for r in rows)
    out = [
        (
            f"per-lens sustained rate (upheld/raised over the window: this "
            f"ledger and {len(window) - 1} previous), shelf share beside it:"
        ),
    ]
    for prefix in prefixes:
        # A row's prefix is everything before the FINAL `-<n>` (the id
        # contract at the top of this file), which is the same reading
        # `security_lens_errors` and `capture_sets` use. It matters only
        # for a composite id such as `V-CIT-1`, whose prefix is `V-CIT`
        # and never the leading `V`; for every single-segment id the two
        # readings are the same string.
        mine = [r for r in rows if r["id"].rsplit("-", 1)[0] == prefix]
        if not mine:
            out.append(
                f"  {prefix}: n/a: no rows raised under this prefix in the window",
            )
            continue
        upheld = [r for r in mine if is_upheld(r)]
        refuted = [r for r in mine if not is_upheld(r)]
        rate = PERCENT * len(upheld) / len(mine)
        if not shelf_in_use:
            shelf = (
                "shelf n/a: no `shelf:` tag anywhere in the window — the tag "
                "is optional and was never set, which is not a share of zero"
            )
        elif not refuted:
            shelf = "shelf n/a: no refutation for a contract shelf to close"
        else:
            shelved = sum(1 for r in refuted if shelf_slugs(r))
            shelf = (
                f"shelf {shelved}/{len(refuted)} = "
                f"{PERCENT * shelved / len(refuted):.1f}%"
            )
        out.append(
            f"  {prefix}: sustained {len(upheld)}/{len(mine)} = {rate:.1f}% | {shelf}",
        )
        if rate < SUSTAINED_BASELINE_PCT:
            out.append(
                f"  {prefix}: BELOW THE {SUSTAINED_BASELINE_PCT:.0f}% BASELINE "
                f"— that baseline is OURS, one measured round, not a "
                f"literature figure. The next round TIGHTENS this lens's "
                f"framing rather than dropping the lens, and only when the "
                f"shelf share beside this rate agrees: the rate alone is "
                f"never the trigger.",
            )
    return out


def register_lines(
    reg: list[RegisterRow],
    nominated: list[str],
    today: date,
) -> list[str]:
    """Return the register's aggregate and its escalation lines.

    REPORT-ONLY, always: no line here reaches an exit code. The aggregate is
    the anti-normalization measure — accepted risk that nobody re-counts
    stops being felt as risk — and the escalations are what keep a row from
    sitting in the queue forever. What the report canNOT do is drain the
    queue; the docstring's register bullet states that boundary in full.
    """
    counts = dict.fromkeys(REGISTER_STATUSES, 0)
    for r in reg:
        counts[r["status"]] += 1
    body = " | ".join(f"{s} {counts[s]}" for s in REGISTER_STATUSES)
    if reg:
        oldest = min(r["status_date"] for r in reg)
        oldest_row = next(r for r in reg if r["status_date"] == oldest)
        age = f"oldest {(today - oldest).days} days ({oldest}, {oldest_row['rid']})"
    else:
        age = "oldest n/a (empty register)"
    out = [f"rows: {len(reg)} | {body} | {age}"]
    for r in reg:
        held = (today - r["status_date"]).days
        if r["status"] == "nominated" and held > NOMINATION_MAX_DAYS:
            out.append(
                f"NOMINATION OVERDUE: {r['rid']} (nominated "
                f"{r['status_date']}, {held} days; the "
                f"{NOMINATION_MAX_DAYS}-day limit on an UNRATIFIED "
                f"nomination is OURS, no standard supplies it) — put it to "
                f"the owner as its own fork: ratify it, withdraw the "
                f"nomination — set the row's status to `withdrawn <date>`; "
                f"the finding goes back to stage 6 of its round as an open "
                f"finding while its round is open, and enters the next round "
                f"on this object as a re-opened finding once that round is "
                f"closed — or set a new date on the owner's explicit word. "
                f"A permanently `nominated` row is banned.",
            )
        if r["status"] == "ratified" and r["review_by"] < today:
            out.append(
                f"REVIEW-BY EXPIRED: {r['rid']} (review-by {r['review_by']}, "
                f"{(today - r['review_by']).days} days ago) — expiry RE-OPENS "
                f"by default and is never a silent renewal: the row enters "
                f"the next round on this object as a re-opened finding.",
            )
        if r["status"] == "expired-reopened" and r["cycle"] >= SECOND_CYCLE:
            out.append(
                f"SECOND CYCLE — OWNER FORK REQUIRED: {r['rid']} "
                f"(expired-reopened {r['status_date']}, cycle #{r['cycle']}) "
                f"— a second expiry is never carried by a batch ratification "
                f"and never renewed in silence: it needs a FRESH "
                f"justification put to the owner, and until that fork is "
                f"decided the row counts as an open finding of the round.",
            )
    # A `withdrawn` register row accounts for no nomination: a withdrawal
    # sends the finding back to adjudication, so a ledger row still waiting
    # in `awaiting-signature` behind it is named below, not counted as a
    # signature wait in silence.
    missing = [
        i
        for i in nominated
        if not any(
            (r["rid"] == i or r["rid"].endswith("/" + i)) and r["status"] != "withdrawn"
            for r in reg
        )
    ]
    if missing:
        out.append(
            "NOMINATION WITHOUT A REGISTER ROW: "
            + ", ".join(missing)
            + " — every nomination carries one register row (rationale, "
            "compensating control, review-by); ids are matched on the "
            "register's run-qualified form, `<run>/<id>`.",
        )
    out.append(
        "the queue drains only through the owner's ratification cadence and "
        "the escalations above: this report is visibility, not traction, and "
        "the register is append-only in this release.",
    )
    return out


def residue_report(
    ledger_path: str,
    register_arg: str | None,
    nominated: list[str],
) -> tuple[list[str], bool]:
    """Return (the residue-register block, register-is-well-formed).

    The block is produced only when the register is IN PLAY, and it is in
    play under exactly three conditions: `--register` was given, the derived
    file exists, or the ledger carries a nomination that a register must
    account for. Under none of them the block is EMPTY — which is what keeps
    a ledger with no register and no nomination recounting byte for byte as
    it did before residue existed (the compatibility promise).

    The second element is False only for a structurally broken register:
    the caller turns that into exit 2, by the same fail-closed rule as a
    malformed ledger row. Everything else here is report-only.
    """
    path, reason = resolve_register(ledger_path, register_arg)
    exists = path is not None and path.is_file()
    if not (register_arg is not None or exists or nominated):
        return [], True
    if path is None:
        return [f"residue register: n/a ({reason})"], True
    if not exists:
        return [f"residue register: n/a (not found at {path})"], True
    reg_lines, load_error = load(str(path))
    if reg_lines is None:
        return [f"residue register: n/a ({load_error})"], True
    reg, errors = parse_register(reg_lines)
    if errors:
        return (
            [f"residue register: {path}", "RESIDUE REGISTER STRUCTURAL ERRORS:"]
            + ["  " + e for e in errors],
            False,
        )
    today = datetime.now(UTC).date()
    return (
        [f"residue register: {path}"]
        + ["  " + line for line in register_lines(reg, nominated, today)],
        True,
    )


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
