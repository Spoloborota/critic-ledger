Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 9 — Loop, convergence and closure

Two parts, in this order.

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
is subject to the user's veto. **Soft threshold of 20 findings:**
under 20 findings in a round the SECOND clean pass is skipped by
default and is still run on the user's word; from 20 findings up it is
mandatory. The threshold buys tokens, not correctness — a small
round's second pass mostly costs money, and whatever it invents goes
through adjudication and dies there under refute-by-default.
**The qualification is SENIOR to that threshold.** A round in which any
row was ever PARTIAL or NOT LANDED has no right to the one-pass
shortcut, however few findings it holds: it owes the pair of clean
passes, and the qualification above applies to that pair. The shortcut
survives only for the round that was clean from its first pass — the one
the plain convergence rule already suffices for. Without this sentence
the qualification would be bypassed in silence, because in a small round
the pair it inspects would simply not exist.
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
three returns the binary rule above: skipped under 20 findings, run in
full from 20 up. **The narrowing is a right, not a default** — without
the owner's signature in the ledger the second pass is executed in full,
and no other actor may grant the narrowing. The threshold itself is not
softened by this mode: it is what decides whether a second pass is owed
at all, and the mode only decides the scope of one that is.
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
Kill criterion: if the new-findings curve does not decay for three
consecutive passes → stop, fork to the user (the object likely needs a
rewrite = a new round, not an endless loop). A row that stays PARTIAL
for two consecutive passes escalates back to stage 6 for
re-adjudication (the fix design itself is suspect) or to a user fork;
PARTIAL is never terminal, so closure still gates such rows. Output:
two consecutive clean passes, or a kill stop.
**The contract's STOP RULE is executed here, and silence after it fires
is banned.** The rule was written and signed before the first critic
(stage 0) and copied into the ledger header at stage 2: so many rounds,
so many fix batches, so many verification passes, and a named disposition
for whatever is still open when it fires. When it fires, every open row is
routed by THAT disposition — nomination into the residue register, or the
freeze below — and the round stops. Continuing past a fired stop rule is
allowed only on the owner's explicit word, recorded in the ledger header;
quietly carrying on is not a judgment call, it is the failure the rule
exists to prevent. Where observability is on, that word is also asked for
inside a span: the orchestrator opens `owner-wait-authorization`
(`references/stage-7-fix-batches.md`, which names this occasion beside the
third fix attempt) when the question is put to the owner, and closes it on
his word, the outcome `answered | refused | abandoned`.
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
why a fired kill criterion is one of the three recognized occasions for
nomination named below.
**The stop rule's freeze is its own mechanism, and it is NOT
`superseded-by-rewrite`.** That older literal —
`FROZEN (superseded-by-rewrite, <date> + reason)` in `Ledger state:` — is
for "the object was rewritten whole" and by its own definition makes the
ledger NEVER closable, which is no legitimate exit from a stop rule. The
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
**An open BLOCKER at a fired stop rule: freeze plus an owner fork, never
nomination.** Nominating a blocker is banned outright (the recount refuses
`awaiting-signature` on a blocker row), so of the two contractual
dispositions exactly one is open to it — `frozen-carried` — and a contract
declaring "nomination" does not lift that ban. Nor is the freeze issued
automatically: for EVERY blocker still open the orchestrator puts its own
fork to the owner — continue the round past the fired rule on the owner's
explicit word (recorded in the header), or freeze the row and carry it
into the next round. A silently frozen blocker is banned exactly as
silently continuing is. Where observability is on, that fork is a recorded
wait and not only a header line: the orchestrator opens the
`owner-wait-authorization` span of `references/stage-7-fix-batches.md` —
the continue-past-a-fired-stop-rule occasion that sentence names, and this
is where it fires — when the question is put to the owner, and closes it
on his word, the outcome `answered | refused | abandoned`.
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
**Closure.** Programmatic terminality recount (script, never by hand):
zero non-terminal rows — SEVEN terminal statuses, `verified-landed` /
`refuted-with-reason` / `accepted-residue` / `refused-user-signed` /
`logged-no-action` / `out-of-scope-by-contract` / `frozen-carried`, the
last two being the contract's own, described in `references/contract-long-form.md` and recognized only
under their complete literal.
**`ROUND CLOSABLE` is what moves the header into the closed state.** On
the report that prints it — the fourth bucket of the exit contract, zero
non-terminal rows, exit 0 — the ORCHESTRATOR writes
`Ledger state: closed <ISO-date>` into the ledger header, replacing
`open`; the date is a calendar-valid ISO date, the date that report was
obtained. A round that ended in any of the other three buckets does not
touch the field — "awaiting signature" is not closed — and the field is
never set by hand ahead of the recount that sanctions it. The recount
needs no change to read it: `closed` carries no `frozen`, so a closed
ledger recounts exactly as an open one does, and the freeze literal
remains the only value that makes a ledger unclosable.
The fourth exists only for findings the adjudicator marked as the
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
Where observability is on, that wait is recorded rather than merely
lived through: the orchestrator opens an `owner-wait-signature` span when
the signature for a terminal cell is asked for and closes it on the
user's word, the outcome `answered | refused | abandoned`.
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
**The register is durable and lives outside the run folder** —
`.critic-ledger/residue-register.md`, from the skeleton
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/residue-register.md`,
one row per nominee: `run-qualified id | severity | claim-hook |
rationale | compensating-control | review-by | status | origin-run`. Its
cell contract, its deadlines and the privacy gates that govern writing
to it live in that template and are not restated here. Two of them
decide whether a nomination happens at all, so they are named here as
well: the FIRST write to the register in a given project is preceded by
the same private-repository confirmation, with the same fail-closed
rule, as the first salvage — no confirmation, no write, and the finding
stays open — and the free text of `rationale` and
`compensating-control` passes the same leak/PII sanitization discipline
as a salvaged report.
**Ratification is the user's act, in batches of at most ten**, on the
user's own cadence; ten is not a new number but the batch limit this
discipline already uses. The WHOLE queue is shown before the act, not
only the ten being signed. After it the orchestrator writes both sides —
`accepted-residue user-signed <date>` into each ledger row's terminal
cell and `ratified <date>` into each register row. No row is ratified by
silence. A row of the security/PII class never rides inside that act: it
reaches the user ONE AT A TIME, carrying the conclusion of an
independent re-check made by an actor or a tool OTHER than the one that
proposed accepting it, and that conclusion is recorded in its register
row. Without its own word from the user such a row stays nominated even
when the act covered the rest of the queue. The same one-at-a-time rule
holds whenever such a row's compensating control is the literal
`none — direct risk accepted`: a bare acceptance of security risk never
travels inside a batch.
Where observability is on, the queue's wait for that act is an
`owner-wait-ratification` span, opened when the queue is put in front of
the user and closed on the act, the outcome
`answered | refused | abandoned`. A row that reaches the user one at a
time is asked for one at a time, so its wait is a span of its own.
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
Where observability is on, the state the recount prints as
`ROUND AWAITING Z3 CLOSURE` has a record of its own: the orchestrator
opens an `owner-wait-z3-closure` span when the batch is put in front of
the owner and closes it on his act, the outcome
`answered | refused | abandoned`.
**The wait has a limit, and it is not a new number.** Thirty days from the
`listed` date — the residue queue's own nomination limit, carried over —
after which the recount prints the row under `Z3 CLOSURE OVERDUE` and the
orchestrator owes the owner a fork of its own: close it, take it out of
the batch (the row returns to stage 6 as an open finding), or set a new
date on the owner's explicit word. A permanent wait is banned here as
categorically as a permanent `nominated` is.
**That independent re-check is owed by every security/PII ruling put up
for signature, refutations included, and its conclusion is attached
BEFORE the owner signs.** It is armed at stage 6 with the class mark and
made by an actor or a tool other than the one that ruled — a fresh
read-only `sonnet`-class agent, or a deterministic check — working
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
rather than as residue.
**The aggregate is printed at every closing** — how many rows, how many
of them nominated / ratified / expired, and the age of the oldest. That
is anti-normalization: accepted risk nobody re-counts stops being felt
as risk. Its honest boundary belongs here too, because a printed report
is easy to mistake for a mechanism. The report is VISIBILITY, NOT
TRACTION, and nothing here promises the queue shrinks. Exactly two
efforts shrink it, both outside the script: the user's ratification
cadence, and the escalation forks above. The register is append-only in
this release — no archiving, no deletion of rows — so without a cadence
it grows monotonically, and the only counterweights are the printed age
of the oldest row and those mandatory forks. That is a deliberate limit,
not an oversight: a queue that drained itself would be residue accepting
itself.
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
the round goes into the ledger header's `Exit family:` line — and a round
closed through the stop rule's freeze writes there the form of family (b)
that names it, `residual-risk close (stop-rule freeze)`, never (a).
Write the final round delta and, when needed, a disposition of previous
rounds' findings by a separate delegation ("not re-opened by a fresh
full pass = superseded").
When observability is ON the delta also
carries a COST line, and that line is a transfer of numbers already
computed rather than a new measurement: once the rollup below has
written `round-summary.json`, the orchestrator quotes out of it the
round's `wallclock_s`, its `totals.tokens` and the count of batches and
passes the same file records — no script, no schema and no instrument
changes for it. A `null` is quoted as an honest `n/a` with its reason
and never as a zero: on the order documented right here the summary is
built BEFORE the round span `s1.00` closes, so `wallclock_s` is
legitimately `null` and the line then reads `wallclock_s: n/a: summary
built before s1.00 close`. The line also carries the rollup's own
limitation in the rollup's own words —
`orchestrator: n/a (not separable)` — so that a cost line covering the
spawned units alone is not read as the round's whole cost.
With observability off the round
delta is written exactly as it is today.
**With observability on**, run
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/rollup.py` over
the ledger and the round's `trace.jsonl` to write `round-summary.json`
beside the ledger, giving it the same two `--prev` ledgers the closing
recount was given so that the plateau reaches the summary as well, and
`--rounds <path>` only where the
cross-project rollup is in use — the script shells out to nothing and so
cannot resolve `${CLAUDE_PLUGIN_DATA}/rounds.jsonl` itself, and what it
appends there is ONE line, the identifier-free projection of that
summary and never the summary itself — and only AFTER that line append
the closure span carrying the recount's numbers and then the round span
`s1.00`'s `kind: "span"` close record, the last line the round writes.
**The object's SCALE is measured here and passed in.** The rollup shells
out to nothing, so it cannot measure the size of what the round reviewed
or of what the round changed: this stage measures both with
`git diff --numstat` and hands the script three counts —
`--lines-at-pin <n>`, `--changed-lines <n>` and `--files-touched <n>`.
Only numbers cross; no path and no file name does, which is what keeps a
field about the object from naming it. The path scope is the object paths
the scope contract declared, and what every diff excludes is the round's
OWN run folder — that one folder, `.critic-ledger/<run>/`, and never the
`.critic-ledger/` tree above it. A round that counted its own records as
work on the object would be measuring itself; but a path under
`.critic-ledger/` that the scope contract itself declared as an object
path — the durable residue register is the standing case — is part of the
object and stays IN the measurement, which a tree-wide exclude would drop
in silence. The commands, by mode:
- **`plan`** — the object is those paths AT THE PIN, the state at the
  round's start. `--lines-at-pin` is the SUM over the object paths of
  `git show <pin>:<path> | wc -l` — the sum alone is passed, never the
  per-path numbers and never a path. `--changed-lines` (the sum of
  `added+deleted`) and `--files-touched` (the number of files) come from
  `git diff --numstat <pin>..HEAD -- <object paths> ':(exclude).critic-ledger/<run>/'`,
  where `HEAD` is the state at this stage.
- **`impl`** — the object is a RANGE `A..B`, and `B` plays the pin's
  role. `--lines-at-pin` is the `added+deleted` of the range ITSELF,
  `git diff --numstat A..B -- <object paths> ':(exclude).critic-ledger/<run>/'`
  — the size of what was under review; the round's own work is counted
  from `B` forward,
  `git diff --numstat B..HEAD -- <object paths> ':(exclude).critic-ledger/<run>/'`,
  which gives `--changed-lines` and `--files-touched`.
A count that was not measured is simply not passed: the field is then
`null`, which reads as unmeasured, and never `0`, which would claim a
round that changed nothing.
Re-entry: the next round on the same object is a NEW RUN DIRECTORY,
`.critic-ledger/<YYYY-MM-DD-HHMMSS-object>/` with its own
`fix-ledger.md` — the directory carries the uniqueness, there is no
round number and no numbered ledger name; the link back is the ledger
header field "Previous run", pointing at the previous run directory
for this object. Open/residue rows of the previous one are disposed
in the new round's appendix. Output: a programmatic "0 non-terminal"
report OR an explicit "awaiting signature" status with the list of
waiting rows.
