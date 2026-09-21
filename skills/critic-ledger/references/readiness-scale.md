Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Readiness criteria — the seven-level scale

Every upheld finding carries a readiness criterion in its `criterion` cell,
written by whoever adjudicated it (stage 6), before any fix is attempted,
and never touched by the fixer. The levels run from the least forgeable to
the most forgeable; each names the artifact that carries the proof.

| # | Level | How it is gamed | What carries the proof | Example |
|---|---|---|---|---|
| 1 | Command and exit code | the fixer edits the checking file itself, or substitutes the scoring function | the verifier re-runs the command written in the cell itself; the checking file is inside the deleted-line walk | a markup/link linter, a test suite or an analyzer exits 0 |
| 2 | Deterministic structural check | the letter is satisfied while the substance is hollowed out (the list items come out empty) | a search pattern narrow enough to fail on a stub, plus one sampled substantive check | "the removed wording no longer occurs in {file}"; "no `TODO` marks left in the changed files" |
| 3 | Threshold on a measurement | narrowing the measured sample; picking the lucky run | the verifier measures it itself; neither the measuring script nor its inputs belong to the fixer | "unsupported evaluative adjectives 12 → 0, counted by script"; "coverage ≥ 80%"; "p95 < 200 ms on fixture X" |
| 4 | Cross-check against an external artifact | the reference points where something else is said, or stops resolving at all | the verifier consults the source itself and puts the matched quote into the ledger row | "the claim now cites a source that really contains the quoted text"; "the called interface exists and returns the described shape" |
| 5 | Structured resolution over a fixed vocabulary | a plausible but tangential edit NEXT TO the flagged place | the row must carry exact "before"/"after" quotes for THAT id, or the specific diff hunk answering THAT claim | one outcome per finding: landed / landed otherwise (described) / rejected with reason |
| 6 | Rubric with worked examples | bias toward verbosity, toward one's own text, toward position in the list | the judge is not the actor who fixed it, and the rubric's examples are written BEFORE the fix, at adjudication | "the section's terminology agrees with the glossary", with three conforming and three non-conforming examples |
| 7 | Naked judgment — the fixer's word | forged completely | nothing; level 7 NEVER closes a finding on its own | "it reads better now"; "the code is cleaner" |

Rules of use:

- **Pick the level by the LADDER, not by feel.** Ask in order and stop at
  the first "yes": (1) is there a command whose output or exit code
  DIFFERS before and after the fix? → level 1; (2) is "fixed" expressible
  as the presence or absence of a concrete string in the object? → level 2;
  (3) otherwise a before/after quote pair plus one sentence of reasoning.
- **A level-1 command that MUTATES what it runs against has two forms.**
  Against a scratch COPY of the object —
  never the repository — the verifier runs it itself: a mutation-tested
  guard, a renamed placeholder, a fixture rewritten in the copy. That copy
  is made for the run by the ORCHESTRATOR, with `scripts/copy-project.sh`,
  at `<scratchpad root>/critic-copies/<object-slug>/<copy-id>` with
  `--run-id <copy-id>` — the orchestrator creating the parent of that path
  first, because the script refuses a `--dest` whose parent does not exist
  and creates only the last segment — and handed to the verifier by path;
  the reverted state is proven by the copy being DISCARDED, not by an
  undo: the orchestrator removes it after the run with
  `scripts/cleanup-scratchpad.py --root <scratchpad root> --manifest <that copy's manifest> --confirm`,
  after the same call without `--confirm` has printed the plan — without
  it the script deletes nothing — and the closing call of stage 9 removes
  any such copy still standing. Against the LIVE object it is run by an
  executor spawned for that command, at the moment 7.18 fixes — one
  executor at a time against any one tree, never beside the fixer or
  another executor on it, and a verification pass of stage 8 never runs it
  again; the verifier judges from that executor's printed output, and the
  `verified` cell names which half the verifier ran live and which it
  judged from the executor's output. The command leaves the live object as
  it found it, and the reverted state is proven by the snapshot of the
  tree 7.18 defines, taken by the orchestrator before the command runs
  and again after the executor returns, the two printing the same bytes —
  not by the executor's word; the batch is never committed over a
  difference, and 7.18 names what the orchestrator does on one.
- **When in doubt, take the LOWER level, never the higher one.** An honest
  weak criterion beats a strong one nobody can satisfy: an unsatisfiable
  criterion turns into an argument at verification, a weak one merely into
  less convincing proof.
- **A level-1 criterion is frozen against a recorded self-baseline.**
  Before freezing it, the orchestrator runs the command ONCE against the
  PRE-FIX state; where it already fails for reasons unrelated to the
  finding, the criterion is written against that recorded baseline —
  "exits 0, or does not regress from the recorded baseline exit `<n>`" —
  and never as a bare "exits 0" no fix of this finding could reach. The
  baseline is recorded AT adjudication, before the fix, so the rule that a
  criterion never changes after adjudication is untouched. That first run
  is the probe named `probe-to-criterion` in
  references/stage-6-adjudication.md and repeated in
  references/stage-8-verification.md. The carve-out is SECURITY: for a
  finding of class `class:security-pii` — the security lens's own rows
  included — the baseline form does NOT apply, its criterion stays
  "exits 0", and a security command that already fails is a finding of the
  round in its own right rather than a baseline.
- A dispute over which level applies is settled by the ADJUDICATOR — not
  the fixer, not the verifier — and settled BEFORE the fix is attempted.
- **Level 7 never closes a finding alone.** It may take part only alongside
  at least one objective artifact: a quote pair, a named diff hunk, or a
  structural check.
- A criterion the fixer could satisfy by editing the very file that defines
  the check (the test, the scoring script, the rubric) is INVALID — the
  check and the checked never sit in one pair of hands.
- **A criterion never pins an absolute line number** where the object can
  grow between batches. A later batch that lengthens the file above the
  range moves the place, and the criterion then reads a section that
  cannot show the fix however correct the fix is — a defect of the
  ROUND's paper, not of the object. The anchor is CONTENT: a heading, a
  row shape, a literal the region itself carries, selected by `awk` or
  `sed` keyed on it. One already frozen that way is redesigned by the
  re-adjudication route, its `verified` cell reset and the row re-verified
  on the next pass.
- For prose, the absence of an executable check is normal and not a defect
  of the procedure: the criterion is then an exact before/after quote pair
  plus one sentence of reasoning, all inside the ledger row.
- What adjudication rejects as a mere wish instead of a criterion, and
  what an absence criterion — the level-2 example above is one — names
  before it is written, are both ruled in 6.25 of
  references/stage-6-adjudication.md.
- A criterion that turns out to be unsatisfiable becomes an
  `accepted-residue` with a one-line reason and the user's signature —
  never a silent pass, and never rewritten after the fact into an
  executable form it cannot honestly take. It reaches that status by the
  nomination route of 9.19 of references/stage-9-closure.md. A criterion
  that proved a poor choice is a NEW finding on the next pass, not a
  silent pass.
- Record it as the level plus a short name, then the criterion itself:
  `L2 structural check — the removed wording no longer occurs in {file}`.
  What the cell of a refuted or refused row holds is ruled in 6.25 of
  references/stage-6-adjudication.md.
