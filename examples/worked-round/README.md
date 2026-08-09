# How to read `fix-ledger.md`

**The eight columns of a row** (one critic round, ten findings, one file)
- `id` — lens prefix plus a number; the handle every later mention uses.
- `sev` — `blocker` / `major` / `minor`, assigned when the finding is judged.
- `claim` — what the critic asserted, in one self-contained hook.
- `verdict` — the adjudicator's ruling on that claim, with its reason.
- `criterion` — the readiness criterion (below); exactly `—` for refuted rows.
- `fix` — where the fix lives: a commit hash, a review link, or "no fix".
- `verified` — an independent pass's per-id verdict: LANDED / PARTIAL / NOT.
- `terminal` — the status that closes the row; anything else means still open.

## Four terms an outsider will not have
- *Terminal status* — one of exactly four endings: `verified-landed`,
  `refuted-with-reason`, `accepted-residue` (owner-signed and dated),
  `refused-user-signed`. A row without one is open, whatever the prose says.
- *Readiness criterion* — written before the fix is attempted, it says what
  would prove the fix landed, on a seven-level scale: L1 (strongest, a command
  and its exit code) down to L7 (weakest, "it reads better now" — never alone).
- *Verification pass* — a sweep by someone other than the fixer, re-deriving
  each fix instead of trusting it, and giving every id its own verdict.
- *New-findings curve* — how many NEW findings each pass turned up: the
  round's defect curve, and the thing that has to decay toward zero.

## The passes table and the convergence signal
Each pass gets a row: scope, per-id verdicts, new findings, bundling, notes.
The round may close once two consecutive passes come back with zero major
findings and zero NOT LANDED verdicts — the convergence signal. If the curve
fails to decay across three passes, the script warns and the round goes back
to the owner instead.

## Comparing two rounds

```text
python3 ../../skills/critic-ledger/templates/recount.py fix-ledger.md --prev <previous-round>/fix-ledger.md
DELTA vs <previous-round>/fix-ledger.md: newly-terminal ['EA-1'] | regressed [] | still-open [] | new-open ['EB-2']
```

That output line is a **format illustration**; its ids are invented. Full
contract: `../../skills/critic-ledger/SKILL.md`. The earlier round is not
shipped here. This example is a sanitized derivative of real rounds run here,
not a transcript: two rows come from an earlier round here, hashes illustrative.
