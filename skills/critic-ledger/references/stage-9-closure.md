Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 9 — Loop, convergence and closure

Two parts, in this order.

### 9.1 Loop and convergence

**Loop and convergence.** NEW verifier findings never go straight into
fix batches: repeat stages 6–8 — every new finding is adjudicated
first. Loop until the convergence signal: two consecutive verification
passes with zero major and zero NOT LANDED.
**The pair is QUALIFIED where the round ever had a marked row.** If ANY
row of this round was at any point PARTIAL or NOT LANDED, the two clean
passes count only when at least one of them CLOSED such a row —
agreement is cheapest exactly where it is weakest. A round that was clean
from its first pass (no row was ever PARTIAL or NOT LANDED) converges by
the plain rule above: qualifying it would make convergence unreachable
for the ideal round.
**"Closed" is not "closed by the pass's own hands."** A marked row leaves
the qualification's account through ANY terminal outcome, not only
through a fix landing inside one of the two passes: a row that was once
PARTIAL or NOT LANDED and that stage-6 re-adjudication closed — by
refutation, or by going into accepted residue under the owner's signature
— counts as closed here too. Put the other way round, and it is the same
rule: the qualification looks only at rows still OPEN at the time of the
pass, since a closed row has nothing left to close. Without this the
qualification creates a second unreachability of its own — every marked
row leaves by the adjudication route, no pass ever "closes" one, and the
signal never fires.
After the signal, proceed
in micro-batches with BUNDLED verification passes (bundling preserves
per-id verdicts); the regime switch is recorded in the round delta and
is subject to the user's veto.
Every verification pass is one row of the ledger's `Verification passes`
table, added with `scripts/ledger_md.py add-pass-row`.

### 9.2 The soft threshold of twenty findings

**Soft threshold of 20 findings:**
under 20 CONFIRMED findings — upheld rows as the recount prints them, the same count the profile is assigned from (stage 2) — the SECOND clean pass is skipped by
default and is still run on the user's word; from 20 CONFIRMED findings up it is
mandatory. The threshold buys tokens, not correctness — a small
round's second pass mostly costs money, and whatever it invents goes
through adjudication and dies there under refute-by-default.
9.2 decides WHETHER the second pass runs by default; 9.4 decides its
SCOPE under the round's profile; the two share the number and nothing
else.

### 9.3 The qualification is senior to that threshold

**The qualification is SENIOR to that threshold.** A round in which any
row was ever PARTIAL or NOT LANDED has no right to the one-pass
shortcut, however few findings it holds: it owes the pair of clean
passes, and the qualification above applies to that pair. The shortcut
survives only for the round that was clean from its first pass — the one
the plain convergence rule already suffices for. Without this sentence
the qualification would be bypassed in silence, because in a small round
the pair it inspects would simply not exist.

### 9.4 The second pass under a round profile

F: the second pass is skipped by default (9.2) and runs on the user's
word. M: skipped by default and run on the user's word (9.2); a pass so
run may be narrowed residue-scoped under the three conditions of 9.5,
whose (c) is the owner's signature (9.6). L: the second pass is
mandatory (9.2) and full-scope in 8.2's sense, unless the three
conditions of 9.5 hold and the owner's signature grants the narrowing
(9.6) — no profile withdraws that right. The connectedness pass is 8.3's
own, and that section fixes when it is planned under each profile. The
qualification of 9.3 is senior to every line of this section.

### 9.5 The residue-scoped second pass

**A third mode exists, and it has a name: the `residue-scoped second
pass`.** The threshold above knows only two — skip the second pass, or
repeat it whole — and where pass 1 was a fan-out of lens verifiers,
repeating it whole doubles the cost of the entire verification. The
second pass MAY instead be narrowed to the NEW findings of pass 1 plus a
targeted connectedness check of what their fixes changed, but only when
all THREE conditions hold at once: (a) pass 1 was full-scope in the
sense of stage 8 — on a lens-split pass, the union of the scopes covered
every id with no overlap and no hole; (b) pass 1 returned 0 NOT LANDED
on the round's ORIGINAL ids; (c) an explicit OWNER signature exists for
this round, written into the ledger verbatim. Absence of any one of the
three returns the binary rule above: skipped under 20 CONFIRMED findings, run in
full from 20 up.

### 9.6 Who may grant the narrowing

**The narrowing is a right, not a default** — without
the owner's signature in the ledger the second pass is executed in full,
and no other actor may grant the narrowing. The threshold itself is not
softened by this mode: it is what decides whether a second pass is owed
at all, and the mode only decides the scope of one that is.

### 9.7 Full scope, mechanical checks and verifier freshness

Condition (a) takes stage 8's sense of full-scope WHOLE: on a lens-split
pass the deleted-line walk is divided by the same explicit rule as the
ids, so a pass whose walk left a hole is not full-scope here either.
Mechanically checkable items may be verified by script/grep at ANY
point of the loop — this allowance is NOT gated on the convergence
signal: for such items a deterministic check beats LLM judgment. The
orchestrator declares an item "mechanical" when the check can be
expressed as a grep/script over the artifact, and that script AND its
fixtures are salvaged next to the ledger so any later actor can re-run
them. Verifier freshness is a
MEASURED rule and it governs EVERY pass, not only the closing one: a
fresh session scores F1 28.6% against 24.6% for a check run inside the
session that produced the work (p=0.008; external research on verifier
independence, 2026-08-08). The closing pass being run by a fresh
(non-continuation) verifier is therefore that general rule's special
case, not a separate precaution.
A precedent of 6.4 of references/stage-6-adjudication.md that narrowed or
re-aimed a gate after it had fired is named to that fresh verifier in its
spawn prompt by the orchestrator and RE-DERIVED from the object's own
files: re-running the narrowed gate confirms the narrowing and never the
ground it was narrowed on.

### 9.8 The kill criterion

Kill criterion: if the new-findings curve does not decay for three
consecutive passes → stop, fork to the user (the object likely needs a
rewrite = a new round, not an endless loop). A row that stays PARTIAL
for two consecutive passes escalates back to stage 6 for
re-adjudication (the fix design itself is suspect) or to a user fork;
PARTIAL is never terminal, so closure still gates such rows. Output:
two consecutive clean passes, or a kill stop.

### 9.9 What the contract's autonomy section decides here

### 9.10 The contract's stop rule

**The contract's STOP RULE is executed here, and silence after it fires
is banned.** The rule was written and signed before the first critic
(stage 0) and copied into the ledger header at stage 2: so many rounds,
so many fix batches, so many verification passes, and a named disposition
for whatever is still open when it fires. When it fires, every open row is
routed by THAT disposition — nomination into the residue register, or the
freeze below — and the round stops. Continuing past a fired stop rule is
allowed only on the owner's explicit word, recorded in the ledger header;
quietly carrying on is not a judgment call, it is the failure the rule
exists to prevent.

### 9.11 Three stop events, and the earlier condition rules

**Three stop events live in this stage, and the EARLIER condition
rules.** They are the contract's stop rule, the kill criterion above (the
new-findings curve failing to decay for three passes) and the convergence
signal (the streak of clean passes). The round is stopped by whichever
event's condition was met FIRST; the second does not override it
afterwards. Where both conditions turn out to have been met on the SAME
run of this stage, the contract's stop rule is senior — it carries the
owner's signature from before the round opened. The ROUTING of open rows
is identical either way: a fired kill criterion routes them by the same
disposition the contract declared, and the owner fork the kill criterion
demands anyway ACCOMPANIES that routing rather than replacing it. That is
why a fired kill criterion is one of the four recognized occasions for
nomination named below. An answer the round contract carries in advance
for a fired kill criterion (`templates/round-contract.md`) is the user's
word on that fork and is followed as such: the fork is then already
answered.

### 9.12 The stop rule's freeze is its own mechanism

**The stop rule's freeze is its own mechanism, and it is NOT
`superseded-by-rewrite`.** That older literal —
`FROZEN (superseded-by-rewrite, <date> + reason)` in `Ledger state:` — is
for "the object was rewritten whole" and by its own definition makes the
ledger NEVER closable, which is no legitimate exit from a stop rule. A
ledger in that state is refused by every writer exactly as a CLOSED one
is — `recount.py` prints `LEDGER IS FROZEN (superseded by a rewrite) —
not closable:` and exits 3 — so the freeze below is the only freeze that
still closes. The
freeze here works like this:
- **Header line:** `Stop-rule freeze: <date> | carried-to: <id of the next
  run folder | pending>`, written by the ORCHESTRATOR at the moment of the
  freeze.
- **Row disposition:** every open row sent into the freeze gets
  `frozen-carried (stop-rule, <date>)` in its `terminal` cell. It is
  terminal FOR THIS ROUND, it is neither accepted risk nor a wait for a
  signature — the signature was given under the contract's stopping rule —
  and the date is that row's own freeze date.
- **What the recount does:** `frozen-carried` counts as terminal like any
  other status, so a freeze does NOT block closability — that is the whole
  difference from `superseded-by-rewrite`. At closure the recount prints
  `FROZEN CARRIED: <n> rows → <carried-to>`. A `frozen-carried` row with
  no `Stop-rule freeze:` line in the header, and a `carried-to: pending`
  still standing when the round closes, are structural errors, not a quiet
  transfer into nowhere.
- **The carry is obligatory:** every `frozen-carried` row enters the
  disposition of the NEXT round on this object as a re-opened finding,
  exactly as an expired `review-by` does. The freeze closes the round, not
  the finding.
- **Exit family:** the freeze is a form of the residual-risk close, and
  the header's `Exit family:` reads
  `residual-risk close (stop-rule freeze)`. A round closed through a
  freeze is NEVER of the clean-streak family.

### 9.13 The freeze field is one per ledger

**The freeze field is ONE per ledger and is written ONCE.** It has two
independent writers — the stop rule firing here, and the one-off freeze of
an exhausted blocker — so the collision rule is fixed rather than left to
whoever writes second: (1) the field is set by the FIRST freeze occasion,
whichever it was; (2) a later occasion does not rewrite it — the header
keeps the first date, and each later frozen row carries its OWN date in
its `terminal` cell, which is where "when was THIS row frozen" lives;
(3) `carried-to` follows the rules above and may not still read `pending`
when the round closes; (4) an attempt to overwrite the existing field with
another date or another `carried-to` is a structural error of the recount,
never a silent replacement.

### 9.14 An open blocker at a fired stop rule

**An open BLOCKER at a fired stop rule: freeze plus an owner fork, never
nomination.** Nominating a blocker is banned outright (9.19), so of the
two contractual dispositions exactly one is open to it —
`frozen-carried` — and a contract declaring "nomination" does not lift
that ban. Nor is the freeze issued
automatically: for EVERY blocker still open the orchestrator puts its own
fork to the owner — continue the round past the fired rule on the owner's
explicit word (recorded in the header), or freeze the row and carry it
into the next round. A silently frozen blocker is banned exactly as
silently continuing is.

### 9.15 Two stopping metrics computed by the script

**Two stopping metrics are computed by the script, not argued — and
they sit BESIDE that binary streak, never in place of it.** The flow
had no way to SEE diminishing returns, only to feel them; these give
the round eyes, and nothing more. Neither enters a stop rule, a gate or
an exit code.
(i) The RESIDUAL-DEFECT ESTIMATE, Jackknife capture-recapture over the
per-lens finding sets: `N-hat = D + ((k-1)/k) * f1`, `D` the distinct
findings the lenses RAISED (before adjudication, cross-lens duplicates
collapsed by the `=<primary-id>` convention), `f1` those raised by
exactly one lens, `k` the lens count declared at stage 2(a). It is
printed only from `k >= 4` — the estimator's own applicability
condition — and below that the recount says `n/a: k<4` rather than
computing a number outside the condition.
**The caveat travels with the number, and its two halves have different
owners.** Lens diversity does not invalidate it: the source measured
little or no impact on the estimation results, so this flow does not
claim that disjoint lenses inflate the number. The caution that
remains is OURS and is labelled as ours — we hold four field
measurements of our own in which the single-lens share ran 75-94% and
`N-hat` came out near `2*D`, but those count `D` as distinct CONFIRMED
findings where the estimate counts distinct RAISED ones, and
comparability between the two denominators is not established. So the
number is ADVISORY: quote it, do not act on it, and never let it stand
in for the streak or for a verification pass. Replacing the estimator
with another formula is a later release and the user's decision, not an
orchestrator's.
(ii) The SEVERITY-WEIGHTED PLATEAU: the moving average of the
major+blocker deltas over a window of three ledgers — this round and
two previous ones, given as two `--prev` paths. The recount does not
take the argument order on trust: it reads each ledger's own
`Round-started:` field, orders the window by it, notes a re-ordering
with `prev order: reordered by Round-started`, and where that field is
missing, unreadable or the same in both, computes nothing and says so.
One `--prev` still gives exactly the delta it always gave.

### 9.16 The per-lens sustained rate travels in a pair

**The PER-LENS SUSTAINED RATE travels with the inter-round delta, and it
is read in a PAIR.** With `--prev` the recount also prints, per declared
lens, the share of that lens's raised findings that were upheld across
the window, and BESIDE it the share of that lens's refutations closed by
the contract's shelf (the `shelf:` tag of stage 6). A lens sustained
below the baseline of 92% — OUR number, one measured round, not a
literature figure — gets its framing TIGHTENED in the next round; it is
never dropped for a low rate. That tightening is NEVER decided on the
sustained rate alone: the condition is PAIRED, and the shelf share
standing beside the rate is its second half. This is a deliberate change
from the rule's earlier single-value form, in which the rate by itself
triggered the tightening — the field case that changed it is a lens whose
confirmations ran at a third, whose every refutation was closed by the
contract shelf, and which produced the round's two most valuable extra
fixes. Cheap to refute is not the same as wrong to raise, and the metric
may not punish the round's best lens. Like the two metrics above it, the
pair is report-only: it enters no stop rule, no gate and no exit code.

### 9.17 Closure

**Closure.** Programmatic terminality recount (script, never by hand):
zero non-terminal rows — SEVEN terminal statuses, `verified-landed` /
`refuted-with-reason` / `accepted-residue` / `refused-user-signed` /
`logged-no-action` / `out-of-scope-by-contract` / `frozen-carried`, the
last two being the contract's own, described in `references/contract-long-form.md` and recognized only
under their complete literal.

The closing report also PRINTS every row whose `verdict` cell carries
`spec-delta-candidate` (6.19) — id and claim, nothing more — as a
question list back to the object's author. No script reads that tag, so
the orchestrator obtains the list by grep over the ledger and pastes it;
an empty list is printed as `spec-delta-candidate: none`, so a reader can
tell "nothing was routed back" from "nobody looked". The list is a report
and not a gate: it changes no status, and closure neither waits for it to
be answered nor refuses on its account.

After the closing recount the critics' copies — and every other scratch
copy the round made with the copy script under that root, a criterion's
copy of the readiness scale included — are removed by
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/scripts/cleanup-scratchpad.py --root <scratchpad root> --confirm`
— the same root stage 2 handed to the copy script — after the same call
WITHOUT `--confirm` has run first as the dry run whose plan is read
before confirming, and by nothing else. Only where a call REFUSES does
the ledger header's `Scratchpad not cleaned` field record it, and then as
ONE line — the refusal's reason and the path it named — because the
header writer takes one line only; the dry-run plan that refused call
printed is kept beside the ledger, in the run folder's
`scratchpad-cleanup-plan.txt`, never inside the field. The path and the
plan are both absolute and carry the machine's scratchpad root, and the
header and the run folder may be versioned as evidence, so both pass the
project's leak/PII sanitization discipline of stage 1 first, fail-closed,
before either is written. A clean closure writes `cleaned <date>` in the
field instead; a copy already removed after its
run was removed by the same script; the run folder is never its target.
That field is written with `scripts/ledger_md.py set-header`, never by hand.

### 9.18 ROUND CLOSABLE

**`ROUND CLOSABLE` is what moves the header into the closed state.** On
the report that prints it — the fourth bucket of the exit contract, zero
non-terminal rows, exit 0 — the ORCHESTRATOR writes
`Ledger state: closed <ISO-date>` into the ledger header — written with
`scripts/ledger_md.py set-header`, never by hand, which refuses the value
on a frozen ledger, on one whose findings table carries rows the parser
rejects, and on one that still has open or waiting rows —
replacing
`open`; the date is a calendar-valid ISO date, the date that report was
obtained. A round that ended in any of the other three buckets does not
touch the field — "awaiting signature" is not closed — and the field is
never set by hand ahead of the recount that sanctions it. The recount
needs no change to read it: `closed` carries no `frozen`, so a closed
ledger recounts exactly as an open one does, and the freeze literal
remains the only value that makes a ledger unclosable.
`Ledger state: closed` is the round's LAST header write: the
`Scratchpad not cleaned` field of 9.17 and the `Exit family` field of
9.27 are written before it, because the header writer refuses every
field of a closed ledger.
The fourth terminal status of the list above, `refused-user-signed`,
exists only for findings the adjudicator marked as the
security/PII class when it ruled on them (the class is never assigned
retroactively): for those a REFUSAL is terminal as well, and both the
refusal and an accepted residue are terminal only under the user's
explicit signature — a plain `refuted-with-reason` never closes such a
finding. Terminal cells are flipped by the ORCHESTRATOR only, per this
taxonomy, after the verifier's result is transcribed. The signature
has a MACHINE form, otherwise the rule is indistinguishable from its
absence: an accepted-residue cell must contain the literal
`user-signed <date>` and a refusal cell the literal
`refused-user-signed <date>`, each with a calendar-valid ISO date —
the recount enforces both. If the user
is unavailable for the residue signature, a legitimate session outcome
is "round awaiting signature": everything verified, only the rows
waiting for the user are non-terminal, closure comes with their word.
Transcribing into that machine form is a right that never travels alone,
and its two halves are ONE rule: the orchestrator MAY render the owner's
human phrase into the machine literal — `user-signed <date>`, or
`refused-user-signed <date>` for a refusal — while the cell, or the
disposition note it points at, MUST carry
the phrase verbatim beside the `user-signed` literal
it was rendered into, in the owner's own words and in quotes.
The recount's `SIGNED_DATE_RE` reads the literal and nothing else, so a
licence to transcribe granted without the duty to quote would legalise a
signature manufactured out of silence, which no closed ledger of this
repository carries.

### 9.19 Residue is nominated at machine speed

**Residue is nominated at machine speed and ratified in batches.**
Nominating a row into residue is an act of the ORCHESTRATOR and waits
for nobody: it sets that row's terminal cell to
`awaiting-signature (nominated <date>)` and writes the row's entry in
the register below. There are exactly FOUR recognized occasions for it
— closing the round here, a stop rule firing, a kill criterion firing,
the third routing that class's open rows by the disposition its own
contract declared, and a finding of NOTICED origin at the very
adjudication that upholds it: one that is NOT a blocker and does NOT
carry `origin:fix-application`, on an object no larger than the scope
contract's line threshold (references/stage-0-prerequisites.md), may be
nominated there instead of entering a fix batch, and the residue
register is its only route. Blockers are categorically non-nominable and the
recount refuses the combination outright. A nominee of the MAJOR class
gets ONE look from a FRESH verifier (never a continuation) before it is
queued, and that look can BLOCK the queueing: where the verifier
concludes the finding is not residual risk — it is trivially fixable, it
is really a blocker, or its premise does not hold — the nomination is
NOT made. The row returns to stage 6 as an open finding with the look's
conclusion attached and takes an ordinary route from there. The
orchestrator may not queue a nominee over a negative look. The
conclusion is kept either way: in the register row when it was positive,
in the ledger's `verdict` cell when it was negative, because a finding
that was never nominated has no register row to keep it in.
Withdrawing a nomination takes the owner's word, and the orchestrator
records it as `withdrawn <date>` in the register row; a row of the
security/PII class leaves `nominated` that way only on the owner's live
word given to that row alone — never by a pre-signed answer, never
inside a batch act — and until that word it stays nominated and keeps
being printed as overdue.

### 9.20 The register is durable and lives outside the run folder

**The register is durable and lives outside the run folder** —
`.critic-ledger/residue-register.md`, from the skeleton
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/residue-register.md`,
one row per nominee: `run-qualified id | severity | claim-hook |
rationale | compensating-control | review-by | status | origin-run`. Its
cell contract, its deadlines and the privacy gates that govern writing
to it live in that template and are not restated here. Two of them
decide whether a nomination happens at all, so they are named here as
well: the FIRST write to the register in a given project is preceded by
the private-repository gate of stage 1, re-run before the first
register write — no confirmation, no write, and the finding
stays open — and the free text of `rationale` and
`compensating-control` passes the same leak/PII sanitization discipline
as a salvaged report.

### 9.21 Ratification

**Ratification is the user's act, in batches of at most ten**, on the
user's own cadence; ten is not a new number but the batch limit this
discipline already uses. The WHOLE queue is shown before the act, not
only the ten being signed. After it the orchestrator writes both sides —
`accepted-residue user-signed <date>` into each ledger row's terminal
cell and `ratified <date>` into each register row. No row is ratified by
silence. A row of the security/PII class never rides inside that act: it
reaches the user ONE AT A TIME — a `class:security-pii` ruling is
re-checked blind by another actor before the owner signs (6.15) —
carrying that re-check's conclusion, which is recorded in its register
row. Without its own word from the user such a row stays nominated even
when the act covered the rest of the queue. The same one-at-a-time rule
holds whenever such a row's compensating control is the literal
`none — direct risk accepted`: a bare acceptance of security risk never
travels inside a batch.
Where the round contract's stopping rule pre-ratifies the minors
nominated into residue, that signed answer is the user's act for those
minor rows, given before any queue existed — the batch limit and the
showing of the queue above bind the acts made on the queue, not that
answer — and both sides named above are written from it, dated with the
contract's signature; a row of the security/PII class never rides on
it, and the one-at-a-time rule above, its bare-acceptance case included,
stands for such a row untouched.

### 9.22 The Z3 closing act

**The Z3 CLOSING ACT is the same shape, on the same limit.** The rows the
adjudicator routed to `logged-no-action` — informative findings the owner
logs and acts on in no way — are closed in batches of at most ten, one act
of the owner per batch, exactly as ratification above; the whole queue is
shown before the act. Until that act each row carries the named
non-terminal `awaiting-logged-no-action (listed <date>)`, and the round is
NOT closed while one stands. After the act the orchestrator writes
`logged-no-action` into the row's terminal cell; a row whose `zone` is not
`Z3`, and any such row in a ledger of the older seven- or eight-cell
schema, is a structural error of the recount rather than a closure. A
`class:security-pii` row never rides inside this act either — it reaches
the owner one at a time, with the independent re-check's conclusion, and
its terminal cell carries its own `user-signed <date>`.

### 9.23 The wait has a limit

**The wait has a limit, and it is not a new number.** Thirty days from the
`listed` date — the residue queue's own nomination limit, carried over —
after which the recount prints the row under `Z3 CLOSURE OVERDUE` and the
orchestrator owes the owner a fork of its own: close it, take it out of
the batch (the row returns to stage 6 as an open finding), or set a new
date on the owner's explicit word. A permanent wait is banned here as
categorically as a permanent `nominated` is.

### 9.24 The independent re-check

**That independent re-check is owed by every security/PII ruling put up
for signature, refutations included, and its conclusion is attached
BEFORE the owner signs.** It is armed at stage 6 with the class mark: a
`class:security-pii` ruling is re-checked blind by another actor before
the owner signs (6.15) — here the owner is not asked to sign until its
conclusion stands beside the request — the re-checker working
BLIND: the original finding, the object and the class mark, never the
ruling's rationale, which it may see only after its own conclusion is
recorded. The conclusion goes in front of the owner together with the
request, and is recorded in the row (in the register row too, where the
finding was nominated). Where the ruling was the OWNER's own
pre-adjudication, the re-check is still made, by an actor other than
him: this is the case it exists for, since without it the owner signs
his own decision with no independent word beneath it. A re-check that
disagrees reaches him AS a disagreement. This closes the 0.2.0 hole of a
signature with nobody's independent re-check under it.

### 9.25 Expiry re-opens a finding

**Expiry re-opens; a second cycle goes to the user.** The recount
compares the register against the current date on EVERY run and prints
what has run out: a nomination left unratified past its limit, a
ratified row whose `review-by` has passed, a row expiring a second time.
The first two oblige the orchestrator to raise a fork; the third is
stronger — a second expiry, and equally a re-nomination of a finding
that has already been re-opened once, is never carried by the batch act
and never renewed in silence. It goes to the user as its own fork with a
FRESH justification (what changed since the first acceptance, why the
risk is accepted again, what compensating control appeared), and until
that fork is decided the row counts as an open finding of the round
rather than as residue. A withdrawal whose round is still open returns
the row to that round's stage 6 as an open finding; where that round is
already closed — and a closed round is never re-opened — the finding
enters the next round on this object as a re-opened finding, entered at
that round's stage 6 by its orchestrator, the route an expired row
takes, and the orchestrator recording `withdrawn <date>` names that
destination to the owner in the same act.

### 9.26 The aggregate printed at every closing

**The aggregate is printed at every closing** — how many rows, how many
of them `nominated` / `ratified` / `expired-reopened` / `withdrawn` (the
buckets under the literals the recount prints), and the age of the
oldest. That is anti-normalization: accepted risk nobody re-counts
stops being felt as risk. Its honest boundary belongs here too,
because a printed report
is easy to mistake for a mechanism. The report is VISIBILITY, NOT
TRACTION, and nothing here promises the queue shrinks. Exactly two
efforts shrink it, both outside the script: the user's ratification
cadence, and the escalation forks above. The register is append-only in
this release — no archiving, no deletion of rows — so without a cadence
it grows monotonically, and the only counterweights are the printed age
of the oldest row and those mandatory forks. That is a deliberate limit,
not an oversight: a queue that drained itself would be residue accepting
itself.

### 9.27 Two exit families

**Two exit families, both legitimate closures.** (a) the CLEAN-STREAK
close — the streak of clean verification passes above. (b) the
RESIDUAL-RISK close — a stop rule fired, everything unresolved was
nominated, the register was updated, the aggregate was printed, AND the
whole queue of nominees has been ratified by the user, AND the queue of
rows waiting for an act of the user's own (`awaiting-logged-no-action`)
is empty. Both waits must be empty, and they are read in that order:
neither a nomination nor putting a row into the closing batch is itself
a closure. While one `awaiting-signature` row stands, the round is
awaiting ratification — the recount prints `ROUND AWAITING RATIFICATION`
and exits 1; while the signature queue is empty but one
`awaiting-logged-no-action` row stands, the round is awaiting that
closing act — `ROUND AWAITING Z3 CLOSURE`, exit 1 again. The (b) close
arrives exactly when the last row of both queues has had its own, which
is exactly when the recount prints `ROUND CLOSABLE`. Which family closed
the round goes into the ledger header's `Exit family:` line, written with
`scripts/ledger_md.py set-header`, never by hand — and a round
closed through the stop rule's freeze writes there the form of family (b)
that names it, `residual-risk close (stop-rule freeze)`, never (a).
Write the final round delta and, when needed, a disposition of previous
rounds' findings by a separate delegation ("not re-opened by a fresh
full pass = superseded").

### 9.29 Re-entry

Re-entry: the next round on the same object is a NEW RUN DIRECTORY,
`.critic-ledger/<YYYY-MM-DD-HHMMSS-object>/` with its own
`fix-ledger.md` — the directory carries the uniqueness, there is no
round number and no numbered ledger name; the link back is the ledger
header field "Previous run", pointing at the previous run directory
for this object. Open/residue rows of the previous one are disposed
in the new round's appendix. Output: a programmatic "0 non-terminal"
report OR an explicit "awaiting signature" status with the list of
waiting rows.
