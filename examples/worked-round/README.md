# How to read this example

Three files, and they are read in this order:

- `round-contract.md` — the scope contract, filled and SIGNED before the first
  critic was spawned. It decides three things in advance: what the object is
  FOR, what is out of scope (the Non-Goals, which the owner signs once and
  which then close findings without coming back for a signature), and when the
  round stops. For an object over 400 lines it is a gate — no contract, no
  round — and it carries the zone map the ledger's `zone` cells are filled
  from.
- `fix-ledger.md` — the round itself: every finding, its judgment, its
  readiness criterion, its fix, its independent verification and the status
  that closed it.
- `residue-register.md` — the risk the project decided to CARRY rather than
  fix. It outlives every round, which is why a real one never lives inside a
  run folder; it sits here only so the example reads in one place.

**The nine columns of a row** (one critic round, twelve findings, one file)
- `id` — lens prefix plus a number; the handle every later mention uses.
- `sev` — `blocker` / `major` / `minor`, assigned when the finding is judged.
- `zone` — `Z1` / `Z2` / `Z3`, taken from the contract's zone map for the
  section the finding lands in, and filled by the adjudicator. It changes the
  paper and the closure route, never the strictness of any check.
- `claim` — what the critic asserted, in one self-contained hook.
- `verdict` — the adjudicator's ruling on that claim, with its reason.
- `criterion` — the readiness criterion (below); exactly `—` for refuted rows.
- `fix` — where the fix lives: a commit hash, a review link, or "no fix".
- `verified` — an independent pass's per-id verdict: LANDED / PARTIAL / NOT.
- `terminal` — the status that closes the row; anything else means still open.

## Five terms an outsider will not have
- *Terminal status* — one of exactly seven endings: `verified-landed`,
  `refuted-with-reason`, `accepted-residue` (owner-signed and dated),
  `refused-user-signed`, `out-of-scope-by-contract` (the Non-Goal named and the
  contract's own signing date), `frozen-carried` (the stopping rule fired; the
  row is carried into the next round on this object) and `logged-no-action`
  (an informative `Z3` finding the owner logged and chose to act on in no way).
  A row without one is open, whatever the prose says. Two named places a row
  WAITS — `awaiting-signature` and `awaiting-logged-no-action` — are not
  statuses: they are counted apart from an open row and still leave the round
  unclosed.
- *Residue* — a defect the round chose to carry. The orchestrator NOMINATES it
  at machine speed; it becomes accepted risk only when the owner ratifies it,
  in an act of at most ten rows that writes both the ledger row and the
  register row. A row of the security/PII class never rides inside that act:
  it reaches the owner one at a time, carrying the conclusion of a re-check
  made by someone other than whoever proposed accepting it.
- *Readiness criterion* — written before the fix is attempted, it says what
  would prove the fix landed, on a seven-level scale: L1 (strongest, a command
  and its exit code) down to L7 (weakest, "it reads better now" — never alone).
- *Verification pass* — a sweep by someone other than the fixer, re-deriving
  each fix instead of trusting it, and giving every id its own verdict.
- *New-findings curve* — how many NEW findings each pass turned up: the
  round's defect curve, and the thing that has to decay toward zero.

## The passes table and the convergence signal
Each pass gets a row: scope, per-id verdicts, new findings, bundling, notes,
and how many verifiers the pass had. That last count is `1` for an ordinary
pass and `N` for a *lens-split verification pass* — one pass executed by N
fresh verifiers, each with its own non-overlapping scope of ids, as pass 1 of
this round was. A second pass may be narrowed to the new findings of the first
plus a connectedness check of what their fixes changed — the
*residue-scoped second pass* — but only on an explicit owner signature written
into the ledger; without it the pass is run in full, as here.
The round may close once two consecutive passes come back with zero major
findings and zero NOT LANDED verdicts — the convergence signal. If the curve
fails to decay across three passes, the script warns and the round goes back
to the owner instead.

## Comparing two rounds

```text
python3 ../../skills/critic-ledger/scripts/recount.py fix-ledger.md --prev <previous-round>/fix-ledger.md
DELTA vs <previous-round>/fix-ledger.md: newly-terminal ['EA-1'] | regressed [] | still-open [] | new-open ['EB-2']
```

That output line is a **format illustration**; its ids are invented. Full
contract: `../../skills/critic-ledger/SKILL.md`. The earlier round is not
shipped here. This example is a sanitized derivative of real rounds run here,
not a transcript: two rows come from an earlier round here, hashes illustrative.
Everything the newer row schema added — every `zone`, the rows `HB-6` and
`HC-4`, the whole contract and the register's second row — is INVENTED for
this example and carried over from no real round at all; the register's first
row deliberately extends the ledger's sanitized `DC-1` thread.

## One more thing the recount reads

```text
python3 ../../skills/critic-ledger/scripts/recount.py fix-ledger.md --register residue-register.md
```

Given the register it prints an aggregate over the project's accepted risk —
how many rows are nominated, ratified and expired, and the age of the oldest —
plus the deadline warnings: a nomination left unratified past 30 days, and a
`review-by` date that has passed and re-opens the row by default. None of them
changes the exit code: they are obligations on the orchestrator, not gates on
the script. Their numbers are computed against the day you run it, which is why
the ledger's own "Closure" block does not quote them.
