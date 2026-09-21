# Round contract — skill-payload (worked example)

> **Everything below is INVENTED for this example.** The object, the goals,
> the Non-Goals, the zone map, the lens table, the stopping rule, the names
> and every date are written to illustrate the shape of a signed contract.
> Nothing here is carried over from a real round. The template this file is
> filled from is `../../skills/critic-ledger/templates/round-contract.md`,
> which carries the rules; this file carries only one round's answers.
>
> A contract is filled and SIGNED **before the first critic is spawned**, and
> for an object longer than 400 lines it is a gate: no contract, no round.
> Its text is substituted into the prompt of every lens identically and
> verbatim, so that no two lenses judge a claim against a different scope.
> The ledger beside this file records this file's path and its sha at the
> round's start, which is what makes a mid-round edit detectable.

## 1. Object and round id

- **Object:** `<repo>/skills/critic-ledger/SKILL.md` plus
  `<repo>/skills/critic-ledger/templates/` (11 files) at `3f2a91c`
  (illustrative placeholder), 2,140 lines. Of the 11, the nine scripts now
  live under `<repo>/skills/critic-ledger/scripts/`; the two ledger and
  prompt skeletons stay under `templates/`.
- **Round id:** `<run-folder>` (short name `skill-payload`) ·
  **Coordinator:** the orchestrating session · **Date opened:** `2026-08-08`
- **Mode:** `plan`. The object is a normative document plus the scripts it
  describes; the scripts are reviewed as documented contracts, and read-only
  runs against a scratch copy are allowed.

## 2. Goals — what this object is FOR

- The staged procedure is executable as written by someone who has never run
  it, with no step that presumes the author's memory.
- The row schema, the closure script and the templates agree with one another
  cell for cell.
- Every agent role the document names can actually be spawned the way the
  document says it is spawned.
- Each shipped script does what the document claims it does, at the exit codes
  the document quotes.

## 3. Non-Goals — pre-signed dispositions (OWNER SIGNS)

> **NG-1.** A finding whose claim is `the skill should expose a
> machine-readable index of its own agents, commands or stages for a host
> application to consume` routes to `out-of-scope-by-contract`. Reason: the
> object is a procedure for humans and subagents to execute, and no host
> integration is planned in this release; an index would be a second source of
> truth over the same facts.

> **NG-2.** A finding whose claim is `the documented cost or duration figures
> should be re-measured` routes to `out-of-scope-by-contract`. Reason: the
> instrument that would produce the measurement ships in this same release and
> has not yet been run for a single round; a re-measurement demanded now would
> be a number invented to satisfy a review.

A finding marked `class:security-pii` may NOT be closed on this signature
alone: that class needs the owner's live word for both of its outcomes, so its
row carries `user-signed <date>` beside the contract literal or it is not
closed at all.

**Owner signature:** `owner, 2026-08-08` — unsigned means the round has not
opened.

## 4. Zone map

| Section (lines) | Zone | Review contract for it |
|---|---|---|
| `SKILL.md` stages 0-9, the executable procedure (1-980) | Z2 | Every obligation is read as an instruction a later actor must obey: who acts, when, and what makes the step done. |
| `SKILL.md` acceptance blocks and quoted exit codes (981-1180) | Z1 | Checked against the scripts by running them; a quoted exit code that the script does not return is a defect, not a wording matter. |
| `SKILL.md` rationale, history and worked narrative (1181-1420) | Z3 | Read for honesty and for claims that contradict the normative sections; informative by construction. |
| `templates/` scripts, all nine, now under `scripts/` (1421-2010) | Z1 | Read as contracts and exercised read-only against a scratch copy: argv, stdout, exit codes, filesystem effects. |
| `templates/` ledger and prompt skeletons, two files (2011-2140) | Z2 | The obligations they place on whoever fills them, and their agreement with the recount's own parsing. |

The table covers the object whole; a zone table that does not partition the
object is a defect of this contract rather than of the round. Severity is
untouched by this axis — a blocker in the lightest zone means the zone was
wrong, and the row is re-zoned with the ruling written to the round's
precedents file.

## 5. Lenses and panel

| Lens prefix | What it looks for | Model | Non-overlap with |
|---|---|---|---|
| `HA` | internal contradictions between two places in the same object | sonnet | takes no position on whether a rule is well designed, only on whether two statements of it agree |
| `HB` | drift between the object and the design notes behind it | sonnet | judges provenance, never platform mechanics |
| `HC` | whether every instruction can be executed on the real platform surface | sonnet | judges executability, never the object's internal agreement |
| `HD` | whether each shipped script does what the prose claims | sonnet | reads code and runs it read-only; the prose lenses do neither |

- **Residual-defect estimate:** will be computed (k = 4).
- **Security lens:** `none`. No lens of this panel attacks a security or PII
  hypothesis, so no row of this round carries the `security-pii` class by
  default, and the ledger header's `Security lens:` field reads `none`.
- A check that ran outside this panel twice is a lens, not a habit: the
  frontmatter portability check was run by hand in the two previous rounds on
  this object and enters the NEXT round as a declared lens.

## 6. Stopping rule (OWNER SIGNS)

- **Rounds:** 1. **Fix batches:** 3. **Verification passes:** 3.
- **What happens to whatever is still open when the rule fires:** nomination
  into the residue register. Blockers are the exception, always: a blocker
  still open when the rule fires can only be frozen and carried, and never
  automatically — each one goes to the owner as its own fork.
- **Exit family admissible:** either.
- **Clean-pass qualification in force:** yes.

**Owner signature:** `owner, 2026-08-08`

## 7. Residue register carried in

One row, from the earlier round on this object: the accepted risk recorded as
`DC-1` in `residue-register.md` beside this file, ratified `2026-08-06` with a
review date of `2026-09-05`. Established by running the recount against the
register, not by reading the register by eye.

## 8. Declared instrument set

- `../../skills/critic-ledger/scripts/recount.py` — every count and every
  closure verdict of this round.
- `../../skills/critic-ledger/scripts/transcribe.py` — the mechanical layout
  of findings into ledger rows.
- `../../skills/critic-ledger/scripts/set-cell.py` — every write to a row's
  `fix`, `verified` and `terminal` cells.
- `../../skills/critic-ledger/scripts/deleted-lines.py` — the deterministic
  deleted-line pre-pass before each verification pass.

Anything counted by hand is a breach of this contract, declared in advance so
that it is not later a matter of taste.

## 9. Known limitations accepted at authoring time

- No lens attacks the object's PERFORMANCE claims; a round that cannot measure
  cost cannot falsify a cost figure, and NG-2 says so.
- The scripts are exercised read-only against a scratch copy, so a defect that
  only appears when writing into a real project is out of this round's reach.
- The panel reads the object as it stands at the pin; a third party editing it
  mid-round produces new findings through adjudication and is not a hole in
  the contract.

## Amendments

None. No change was made to this contract inside the running round, and the
ledger header's `Contract amendments:` field says the same. An amendment made
inside a round is numbered, dated and one sentence long, is recorded in both
places, and takes effect only if it is numbered; one touching a field the
owner signed carries `user-signed <ISO date>` and is void without it.

| # | Date | What it changes | Owner signature (only if a signed field is touched) |
|---|---|---|---|
| - | - | none | - |
