# Why this discipline

The reasoning behind the plugin: the failure it was derived from, what was
observed, what is honestly unproven, and which defect forced which rule. The
*mechanics* live in
[`../skills/critic-ledger/SKILL.md`](../skills/critic-ledger/SKILL.md).

> **These numbers are provenance, not efficacy evidence.** They are the
> observations the rules below were derived from — what was seen while the
> discipline was being built, on the author's own documents, under the
> PREVIOUS actor allocation (fixes applied by the judging session, not by a
> separate fixer subagent). n = 2 on the counted pair, one object class,
> self-reported counters with no external arbiter. They are recorded so each
> rule can be traced to the defect that forced it, not offered as a measure
> of how well the shipped discipline works. No external benchmark of it
> exists; the README quotes no figures, and collecting that evidence is
> planned rather than done.

All measurements below are **self-reported counters from the author's private
research — confidence grade C** (the scale: A — an external controlled study;
B — an internal controlled comparison; C — self-reported counters, no external
arbiter): no control group beyond the one A/B described, counting done by the
project that benefited. One figure is not such a counter, flagged in section 4:
verifier independence (F1 28.6% against 24.6%) is external published research.

## 1. The symptom: findings that never converge

The pattern repeated in two independent workstreams. Critics review a document
in parallel; the orchestrator adjudicates and fixes on the spot, usually by bulk
rewrite. The next round finds fixes never applied, fixes applied partially,
defects the fixing introduced, and unrelated passages lost in the rewrite. The
count does not decay toward zero, and "fixed" stops carrying information. Across
eight critic runs over one execution plan, the share of findings that were
defects of a *previous fix's application* rose round over round: 20% at round
four, 48% at six, 83% at a mini-round auditing fixes. While that stayed an
impression there was nothing to treat; on 2026-08-04 it became numbers.

## 2. The measurement that forced the ledger: ~47% against ~100%

Two remediation mechanics, compared in one session with the same critic models:

- **A — fix on the spot.** The document was rewritten in bulk from the critics'
  *summaries*; 117 findings claimed across three lenses. A verification round
  returned **56 fully landed / 40 partial / 23 not landed — about 47% full
  application**, plus 31 new findings.

  The verdict counts sum to **119**, not the
  **117** claimed, and the gap is evidence, not a typo to paper over: in that
  same session two critics found errors in their *own* earlier reports — one lens
  had understated its count, putting the aggregate at **121** — so the self-tally
  was unreliable in both directions.

  The headline survives either denominator
  (56/117 ≈ 48%, 56/119 ≈ 47%); the numbers stand as recorded.
- **B — the itemized fix batch.** A numbered list of items, each with an address
  and a readiness criterion, then an independent pass giving every item a LANDED
  / PARTIAL / NOT LANDED verdict with file and line. Convergence to **~100%
  within at most two iterations, in all four cases** (rounds of 10, 15, 18, 4).

Four details of B became the discipline's skeleton: an imperative *list* with a
criterion per item; targeted edits, never a rewrite; the applier never verifies;
adjudication reads the critics' **full reports**, not A's summaries.

## 3. The historical layer: 16.6% of all critic work

The second layer is retrospective: a read-only agent classified **every**
itemized finding of seven plan-forming critic rounds as a new defect, fix-loss
(a prior fix overwritten or dropped), fix-incomplete (partial, or not on every
surface), fix-introduced (the fix created it) or meta (a counting error).

**Result: 525 findings, of which fix-loss + fix-incomplete + fix-introduced =
87, about 16.6%** — a sixth of all that critic work went into catching defects
of *applying* prior fixes rather than into new problems.

The author's own notes
attached the limit to it: rounds six and seven were *deliberately* hunting for
under-application, and how much lay uncaught earlier is unknown, so 16.6% is a
lower bound.

Five cases were confirmed by git archaeology, one of which settles
whether this really happens: a fix claimed a README repair and the diff of the
commit it named was **empty**; the change landed two commits later, under a
message announcing that it finally had. A resolution claimed without
verification is not a hypothesis; it is a documented event.

**Where this disease is already treated.** Five domains that close findings
under a regulator or a machine gate — medical-device CAPA, checklist science and
code review among them — yield seven recurring elements the procedure is
assembled from: a state machine per finding; verification as a separate
mandatory step; verification by a *different* role; a ledger that cannot
silently lose an item; a mechanical gate over a narrative summary; deferred
re-verification; an itemized checklist over memory.

The sharpest data point is
the WHO surgical checklist trial — Haynes et al., *A Surgical Safety Checklist
to Reduce Morbidity and Mortality in a Global Population*, NEJM 2009
([doi:10.1056/NEJMsa0810119](https://doi.org/10.1056/NEJMsa0810119)) — mortality
1.5% to 0.8%, complications 11.0% to 7.0%: the effect came not from the list but
from phase-by-phase itemization read out by a *different* role.

## 4. What was observed, and what is not shown

Keeping these two columns apart is the point. The five closed rounds, all grade C:

- **first live run** (a meta-plan with a three-rewrite history; curve
  20 → 9 → 3 → 4 → 1 → 3 → 0 → 0 → 0 → 1) — 165 ids, 165 terminal — 164
  verified-landed, 1 refuted, 0 residue; 21 fix batches; **0 NOT LANDED across
  150+** verified fixes
- **the plugin's own spec** (a normative spec; curve 5 minor → 1 minor → 0) — 94
  rows, all closed-verified; 12 batches; fix-loss 0 across all 12 deleted-line
  scans
- **dogfood on the skill** (this plugin's skill document and templates; curve
  1 → 0 → 8 → 0) — 32 rows, 32 terminal; 2 blockers; 1 row signed as accepted
  residue
- **first field application** (summary documents from the author's private
  research; curve 2 → 1 → 0 → 1 → 0) — 17 rows, 17 terminal, all verified-landed
- **the design round behind the 70% figure** (this plugin's seven design
  documents; curve 3 → 2 → 2 → 1 → 1 → 1 → 0) — 66 rows, 66 terminal — 63
  verified-landed, 3 refuted, 0 residue; 12 batches; 6 verification passes run
  by 8 fresh verifiers, none of whom applied a fix; **0 NOT LANDED**

### Observed, within grade C (self-reported counters, no external arbiter):

- ~47% against ~100% application completeness — an A/B in one session, same
  critics, four cases on the B side.
- 16.6% of critic work spent catching prior-fix application defects over 525
  classified findings; single-document trend 8% → 20% → 48% → 83%; read by its
  own authors as a lower bound.
- Decaying defect curves on the five closed rounds (the list above).
- Fix-loss 1→0 after the deleted-line mandate: the single occurrence predates
  the mandate, none after it across roughly 129 deleted lines.
- Micro-batch economics of ×2.7–8.5 relative to the full verification mandate.
- Critic accuracy around 99.4% — one refuted finding out of 165 — while the
  discipline bites the critics too: verifiers found errors in their own reports.

**The one figure here that is not self-reported.** A review run by a fresh
session scores F1 **28.6%** against **24.6%** for a review run inside the
session that produced the work (**p = 0.008**), and reviewing a second time
inside the same session does not close the gap. Source: Song, *Cross-Context
Review: Improving LLM Output Quality by Separating Production and Review
Sessions* ([arXiv:2603.12123](https://arxiv.org/abs/2603.12123)), 30 artifacts
and 150 injected errors. This is **external published research**, the only
measurement here with an outside arbiter, taken on a review task of its own,
not on this discipline's rounds. The rule "every verification pass is run by a
fresh verifier" rests on it.

### Not shown — and flagged as unproven in the primary sources themselves:

- **n = 2, and both points are the same object class.** The counted pair is the
  first live run (a meta-plan) and the dogfood round (this plugin's skill
  document and templates): the second widened n but not the class, both being
  normative documents. Folding in the list's later rounds would raise n and
  leave the class exactly where it is — and the class is the caveat.
- **Verifiers are of the same model family as the critics and the fixer.**
  Self-preference — judges scoring their own family higher — is documented,
  grade A: Panickssery et al., *LLM Evaluators Recognize and Favor Their Own
  Generations*, NeurIPS 2024
  ([arXiv:2404.13076](https://arxiv.org/abs/2404.13076)). Mitigated by the
  "re-derive" mandate and deterministic checks; cross-family verification is
  unsolved and remains a high-stakes option.
- **The cost of verifier freshness is unmeasured here — the effect is not.** The
  F1 result above is external research, and the skill states freshness as a
  MEASURED rule for every pass, the closing one included. Unmeasured is the
  price: the live run's closing was still done by continuations, so what a fresh
  verifier per pass costs in tokens and time is unknown here.
- **Residual dogfood circularity.** An independent trace audit — a fresh agent
  *without* the skill, reading the ledger, the reports and the commits against
  the skill's contract — reduces the self-checking but cannot remove it: whether
  the critic and verifier spawns were genuinely independent is an assertion in a
  report header, not something a read-only audit derives.
- **Defects caught on the tool itself**, which gets no privilege: the two
  closure-script blockers (see section 6), and a fix batch that carried 12 identifiers
  against a contractual limit of 10, recorded as a durable deviation.

## 5. 16.6% against 70%, reconciled

A later round — five lenses over seven design documents of this plugin — raised
66 findings, 56 from the critics and 10 from the verification passes; **7 of
those 10 targeted fix application** rather than the object, i.e. 70%:

- **16.6%** = 87 / 525. Numerator: findings classed fix-loss, fix-incomplete or
  fix-introduced. Denominator: all itemized findings of seven critic rounds on
  normative documents in the author's private research. Measured 2026-08-04,
  retrospectively, by a read-only agent, under the old actor allocation.
- **70%** = 7 / 10. Numerator: verification-pass findings targeting fix
  application. Denominator: all findings that round's verification passes
  raised. Population: one round, on this plugin's own design documents. Measured
  2026-08-08, inside the round as it ran, under the new actor allocation.

**Comparability verdict: they are not directly comparable.** Different
numerators, denominators, populations, allocations — neither number revises the
other, and n=10 carries no weight against a 525-finding corpus. They share only
direction: remediation defects are a large share of what a later pass finds.

**The actor-allocation change, in one sentence:** fixes used to be applied by
the session that judged the findings; the shipped design moves fixing into a
separate subagent. Both figures — the 16.6% corpus and the ~47%/~100% A/B —
were taken under the old allocation and are not yet re-measured under the
shipped one.

## 6. Delta provenance: which defect forced which rule

Each rule is stated with the defect that forced it. The discipline grew by
targeted insertions, never by rewriting its own text — rewrites lose content.

1. **The verifier walks every DELETED line of each fix batch's diff.** Forced by
   a batch that removed a neighbouring normative block along with the line it
   was editing; after the mandate, fix-loss went 1→0 across ~129 deleted lines.
2. **Critic reports are salvaged verbatim immediately, and again after every
   append, inside the same batch.** Forced by a recurring durable-storage
   blocker: a single-shot salvage loses whatever the agent appends later.
   Sanitization is fail-closed and checked before the first salvage: leak
   discipline not run, the salvage stays in a local unversioned holding.
3. **A negative claim in a verdict or a fix requires a command and its output.**
   Forced by an orchestrator's false "not found": without evidence the claim is
   "not checked", not "absent".
4. **Ledger arithmetic is computed by script; a round closes only on a
   programmatic recount.** Forced by three manual counting errors in one run,
   against none observed from the script.
5. **Convergence signal: two consecutive clean passes; the remainder then runs
   in bundled micro-batches keeping per-id verdicts, and the CLOSING pass goes
   to a fresh verifier.** Forced by the cost of the full mandate on a shrinking
   remainder; validated on 58 findings, at ×2.7–8.5 lower cost (see section 4).
6. **The closure script parses fail-closed.** A critic pointed out that the rule
   demanded script-computed arithmetic while none shipped — a norm with no
   carrier. The script then proved to drop rows silently, and the worse case
   **reproduced live** mid-adjudication: two verdict cells held a literal pipe,
   the script counted 21 rows instead of 23 and called the round closable. The
   gate lied about the very table recording the finding that it lies.
7. **Critics never execute anything against the working tree.** The spec had
   demanded sandboxed execution while the spawn surface offers no isolation.
   Critics now formulate commands, execution happens elsewhere against a
   scratchpad copy, and the admission is written into the plugin: there is no
   enforced isolation, the guarantee is organizational.

Two commitments come from the same path rather than from one defect. Without
version control or commit sanction the round still runs, in a **degraded mode
that states its weaker audit guarantee instead of disguising it**. And before
publication a **deterministic grep gate** runs alongside a read-only red-team
agent over the working tree *and* the full history, told to play a motivated
OSINT researcher — an audit is worth as much as it tries.

## 7. What this does not solve

The permanent limit: **the discipline does not decide when to call critics.**
That stays with the user, or a project's standing order. It answers "how do I
drive what was found to completion", not "is this artifact worth a round" — the
second question is human, which is also why every "good enough", "ignore it" and
"accept as residue" call belongs to the user by contract, and why silence is
never a status.
