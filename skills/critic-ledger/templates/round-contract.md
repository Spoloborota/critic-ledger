# Round contract — {object-slug}

<!-- The scope contract of ONE round, filled and SIGNED before the first
     critic is spawned. Copy this file beside the object under review, fill
     every section, get the owner's signature on the two blocks marked
     "OWNER SIGNS", and only then spawn. The ledger header carries this
     file's path and its sha at the round's start, so that a contract
     edited mid-round is detectable instead of silently replacing the one
     the round actually ran under.

     WHY THIS EXISTS. Scope, strictness and acceptance used to be decided
     AFTER the findings arrived, so every finding turned up with equal
     standing and was litigated one by one to a terminal status. The
     working counter-example is a round that declared "one round, two
     batches, one verification, then STOP; residuals go to the follow-up
     chapter" and closed 26 of 26 findings in a day.

     HOW LONG IT MAY TAKE. A contract that takes more than HALF AN HOUR to
     fill is too elaborate — that limit is OURS, no standard supplies it.
     The point is to decide three things in advance (scope, strictness,
     acceptance), not to produce a document.

     WHEN IT IS MANDATORY. For an object longer than 400 LINES the signed
     contract is a GATE: no contract, no round. That threshold is OURS and
     is marked as ours — it is not borrowed from any standard, and the
     owner may move it with one word, recorded in the ledger header. For a
     shorter object the owner may waive the contract with one word, and the
     waiver goes in the ledger header too; for a small object the contract
     may also live as a section pasted straight into the ledger header
     rather than as a file.

     WHERE IT GOES DURING THE ROUND. The text of this contract is
     substituted into the prompt of EVERY lens, identically and verbatim —
     never re-told, shortened or angled for one lens. A lens judging a
     claim against a different scope than its neighbours is the failure
     this file exists to stop. -->

## 1. Object and round id

- **Object:** `{path}` at `{sha or date}`, `{n}` lines.
- **Round id:** `{run-folder id}` · **Coordinator:** `{who}` ·
  **Date opened:** `{ISO date}`
- **Mode:** `{plan | impl}`.

## 2. Goals — what this object is FOR

Three to six bullets. Each names a property a reviewer may legitimately hold
this object to. A claim that traces to none of them is out of scope by
construction, and that is what makes section 3 enforceable rather than
decorative.

- {goal 1}
- {goal 2}
- {goal 3}

## 3. Non-Goals — pre-signed dispositions (OWNER SIGNS)

Write each one as a DISPOSITION, not as prose. "We are not doing X here" is a
rule somebody still has to apply; the form below is a gate the adjudicator
executes without coming back for a signature:

> **NG-{n}.** A finding whose claim is `{what}` routes to
> `out-of-scope-by-contract`. Reason: `{why}`

At adjudication such a finding's `terminal` cell is filled with the complete
literal `out-of-scope-by-contract (NG-{n}, signed {ISO date})`, where the date
is the date of the signature BELOW — not the date of the adjudication. No live
signature is asked for at that moment: it was given here.

**Blank is not an option.** An empty Non-Goals section means the round will
litigate everything, which is the defect this contract exists to stop.

**One class is exempt from the pre-signature.** A finding marked
`class:security-pii` may NOT be closed by a Non-Goal on this signature alone:
that class needs the owner's live word for BOTH of its outcomes, so its row
carries `user-signed {date}` beside the contract literal or it is not closed
at all. The recount enforces this as a structural error.

**Owner signature:** `{name, ISO date}` — unsigned means the round has not
opened.

## 4. Zone map

A table covering EVERY section of the object with the review depth that
section gets. Three zones, and these are their names — the ledger's `zone`
cell and the recount read these literals and no others:

- **Z1** — mechanically checkable contracts: scripts, acceptance blocks,
  anything a command can decide.
- **Z2** — normative prose: obligations a later actor must obey.
- **Z3** — informative prose: rationale, history, examples.

A zone table that does not partition the object is a defect of the
contract, not of the round. Severity is untouched by this axis — a blocker in
the lightest zone means the zone tag was wrong, not that the process is
bypassed.

| Section (lines) | Zone | Review contract for it |
|---|---|---|
| {section} | {Z1 \| Z2 \| Z3} | {what is checked, and how deeply} |

**What a zone changes is the paper and the closure route, never the
strictness of a check.** Z1 and Z2 run the existing pipeline unchanged. A Z3
row may close through `logged-no-action` — the disposition of an informative
finding the owner logs and acts on in no way — in a batch the owner signs off
in one act of at most ten rows; no row outside Z3 may take that status, and a
`class:security-pii` row never travels inside such an act. The deleted-line
walk narrows in JUDGMENT depth only (Z1: every line of the list; Z2: the lines
carrying obligations; Z3: the adjudicator's call) — the deterministic pre-pass
still emits the FULL list for every zone. And the fresh-verifier rule is NOT
relaxed for any zone: a verifier is new on every pass regardless of where the
finding sits. The mechanical consequences of the zone are stated once, in
`templates/ledger.md` (the `zone` cell and the `logged-no-action` status), and
are not restated here.

## 5. Lenses and panel

One row per lens: what it looks for, the model it runs on, and one line on why
it does not overlap its neighbours. **Four or more lenses** if the round's
residual-defect estimate is to be computed at all; with fewer, state here
explicitly that it will not be computed, so that its absence later is not read
as a lost number.

| Lens prefix | What it looks for | Model | Non-overlap with |
|---|---|---|---|
| {PREFIX} | {hypothesis it attacks} | {family} | {the neighbouring lens} |

- **Residual-defect estimate:** {will be computed (k = n ≥ 4) | will NOT be
  computed, k = n < 4}.
- **Security lens:** `{PREFIX | none}`. Declaring one here has a mechanical
  consequence and is not a label: every finding that lens raises gets the
  class `security-pii` BY DEFAULT at adjudication — the adjudicator marks it
  without deciding the question again — and the same prefix goes into the
  ledger header's `Security lens:` field, where the recount reads it. Removing
  the default takes a written reason in the row itself,
  `declassed:security-pii — {reason}`; silence does not remove it.
- **A check that ran outside this panel twice is a lens, not a habit.** A
  check performed as a post-closure step or a manual run in TWO consecutive
  rounds is declared a lens of the panel from the second time on, instead of
  being repeated by hand for a third. It then enters the NEXT round as one of
  its load-bearing hypotheses on ordinary terms: it takes a slot under the
  ceiling of seven and counts against the hard budget of twelve simultaneous
  agents. It gets no exemption from either — if the hypotheses are already
  seven or the budget is spent, the next round's panel is rebuilt around it.

## 6. Stopping rule (OWNER SIGNS)

- **Rounds:** {n}. **Fix batches:** {n}. **Verification passes:** {n}.
- **Profile:** {auto | F | M | L}. `auto` = assigned at stage 6 by the
  thresholds of references/stage-2-scope-and-lenses.md 2.4; a fixed value is
  the owner's and stage 6 records it as given.
- **What happens to whatever is still open when the rule fires:** {nomination
  into the residue register | freeze and carry into the next round}. Name ONE
  of the two; "we will see" is not a disposition. Whichever is named here also
  governs the open rows when the KILL CRITERION fires — the two stop events
  route their leftovers the same way.
- **Blockers are the exception, always.** A blocker still open when the rule
  fires can take only ONE of the two dispositions — the freeze — because a
  blocker is categorically non-nominable. And it does not take it
  automatically: EVERY such blocker goes to the owner as its own fork, either
  to continue the round past the fired rule on the owner's explicit word or to
  be frozen and carried. A silently frozen blocker is as banned as silently
  continuing.
- **Exit family admissible:** {clean-streak | residual-risk | either}. A round
  closed through the freeze is always the residual-risk family and never the
  clean-streak one.
- **Clean-pass qualification in force:** {yes | no} — whether a verification
  pass has to meet the round's own quality bar before it counts toward the
  streak. The skill's own qualification applies whatever is written here and
  is not waivable by this field: where any row of the round was ever PARTIAL
  or NOT LANDED, the pair of clean passes counts only if at least one of them
  closed such a row, and that round has no right to the one-pass shortcut of
  the soft 20-findings threshold either.

An answer written here is the owner's signature on that fork; the
orchestrator transcribes it into the ledger where the stage text asks for a
signature and never manufactures one out of silence. The security/PII
class (§3) is exempt from every answer here that writes a signature
literal — the ratification of nominated minors and the default sign for a minor of the
last permitted pass: a row marked `class:security-pii` needs the owner's
live word for BOTH of its outcomes, so a pre-signed disposition does not
reach it, and such a row carries its own live `user-signed <date>` or stays
open.

- **Pre-signed answers** (each `{answer | ask}`; `ask` keeps today's
  behaviour — the round stops and puts the fork to the owner):
  - a blocker found in the round — fixed in the round / ask;
  - a design fork at a structural impossibility of the edit — freeze and
    carry / fork-research first / ask;
  - ratification of minors nominated into residue — pre-ratified by this
    signature with the literal `accepted-residue user-signed <date>` / ask;
  - exit family when the stop rule fires — as named above;
  - the residue-scoped second pass — granted by this signature (9.6) / not
    granted;
  - a blind re-check that disagrees with a security/PII ruling — `ask`, and
    no other answer is offered: such a re-check is put to the owner AS a
    disagreement, never smoothed into the ruling, and a signature given
    before the round does not stand in for that word;
  - `INJECTION RATE HIGH` — continue the other batches and list to the owner
    at closure / stop;
  - the kill criterion firing — the disposition named above / ask;
  - one micro-batch beyond the batch limit for a trivially fixable minor of
    the last pass — allowed / not;
  - the default sign for a minor of the last permitted pass that is a DoD
    literal of a closed package or a line of the round's own text — in
    force / struck.

**Owner signature:** `{name, ISO date}`

## 7. Residue register carried in

Rows on this object still awaiting a signature or ratified with a review date,
with their ages. If there are none, state `none` together with the command
that established it — an unproven "nothing carried in" is not a finding of
nothing, it is a check nobody ran.

## 8. Declared instrument set

The scripts that will compute this round's arithmetic and run its gates, by
path. Anything counted by hand is declared a defect here, in advance, so that
a hand-counted number later is a breach of the contract rather than a matter
of taste.

- {path of the recount script}
- {paths of the round's own gates}

Where an instrument named here cross-checks a ruling, a citation or a count
against a live record, the entry also names the version or format marker by
which that record is recognized, so a record that has changed shape is read
as changed and not as a ruling that was never there; where the record
carries no such marker, the entry names instead the git-history fallback
that re-derives the same text from the commit that carried it.

## 9. Known limitations accepted at authoring time

What this round knowingly will NOT catch, written down so that its absence is
not later mistaken for coverage.

- {limitation}

## Amendments

An amendment is a change to this contract made INSIDE the running round. It is
numbered, dated and one sentence long, it is recorded BOTH here and in the
ledger header's `Contract amendments:` field, and an unnumbered amendment does
not take effect at all.

An amendment touching a field the OWNER signed — the Non-Goals, the stopping
rule, the privacy-gate answer, the models — carries the owner's signature in
the same machine form as residue does, `user-signed {ISO date}`, and is void
without it.

| # | Date | What it changes | Owner signature (only if a signed field is touched) |
|---|---|---|---|
| Amendment {n} | {ISO date} | {one sentence} | {user-signed {ISO date} \| not required} |
