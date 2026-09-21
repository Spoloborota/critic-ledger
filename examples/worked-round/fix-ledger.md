# Fix-ledger — skill-payload (worked example, created 2026-08-09)

> **Provenance.** This file is a **sanitized derivative of real critic rounds
> run on this repository — not a transcript.** Every row restates a finding
> that was actually raised, adjudicated, fixed and verified here, except
> `DC-1` (below); the wording is re-authored in plain English so an outsider
> can read it. Eight rows come from the round whose object was this plugin's
> own payload; **one row is imported from an earlier round on the same
> repository** — `DA-2`, to show a `blocker`-severity row (the later round
> produced none). Commit hashes in the `fix` column and the header's
> `Pin` are **illustrative placeholders**, not hashes from this repository's
> history. The verbatim critic and verifier reports are **not** part of this
> example: salvaged reports stay local and never ship.
>
> **The v3 material is INVENTED, not sanitized.** The zone of every row, the
> `DC-1` row (chosen to show the `accepted-residue` status, which the later
> round produced none of), the rows `HB-6` and `HC-4`, the round contract
> beside this file, every cell of the residue register beside it and the
> header fields the v3 schema added were all written FOR this example. No
> id, path, date, actor name, rationale or compensating control in any of
> them is carried over from a real round: a register row is free text about
> an accepted risk, and free text is exactly what an example may not borrow.

- Ledger state: closed 2026-08-09. (The field takes one of three values —
  `open`, `closed <ISO-date>`, or `FROZEN` after a superseding rewrite. It was
  `open` for the whole round; the literal `closed` replaced it at the last
  stage, on the recount that printed `ROUND CLOSABLE` and is quoted verbatim
  under "Closure" below. `closed` blocks nothing: it carries no freeze, so this
  ledger still recounts exactly as it did while open.)
- Object: full path `<repo>/skills/critic-ledger/SKILL.md` plus
  `<repo>/skills/critic-ledger/templates/` (11 files; the nine scripts now
  live under `<repo>/skills/critic-ledger/scripts/`, the two skeletons stay
  under `templates/`) | short name:
  skill-payload — the short name is only the run-folder address, the full path
  lives here. Pin: `3f2a91c` (illustrative placeholder). Pin = state at round
  start; verification always runs against the CURRENT head.
- Previous run on this object: an earlier round on the same repository, kept
  in a local, unshipped run folder (it is the source of the two imported rows).
- Mode: plan. The object is a normative document plus the scripts it
  describes; the scripts are reviewed as documented contracts, and read-only
  runs against a scratch copy are allowed.
- Prerequisite (stage 0): git = yes, commit sanction = yes; normal mode.
- Lenses:
  - HA | internal-consistency | sonnet
  - HB | design-fidelity | sonnet
  - HC | platform-correctness | sonnet
  - HD | script-correctness | sonnet
  The four dashed lines above are the field's MACHINE part, one per lens and
  nothing between them; the recount reads the lens count `k` from them and from
  nowhere else. Everything softer belongs here, below the run: ~20 min timebox
  per lens, no owner-set lens. Two further prefixes are not lenses and are
  deliberately absent from the run above — `HV` and `HW` are findings raised BY
  the verification passes — and a leading `D` marks the two rows imported from
  the earlier round (whose lens names are not reproduced here).
- Verifier passes: `HV` is the stem this round fixed for its verification
  passes; `HW` is the closing pass's. Verifier prefixes are never counted among
  the lenses, which is why `k` is 4 and not 6.
- Process prefixes: none
  No row of this round was written by a PROCESS rather than by a lens or a
  verification pass — the fixer's `NOTICED OUTSIDE BATCH` block came back
  empty in every batch and no class-kill gate was built — so the field
  keeps its literal. Like `Verifier passes:` above it declares what is NOT
  a lens, and it takes no part in `k`.
- Security lens: none
- Round contract: `round-contract.md` beside this file, sha `7ad91f4`
  (illustrative placeholder), signed before the first critic was spawned. The
  object is far over the 400-line gate, so the round could not open without it.
- Contract amendments: none.
- Round-started: 2026-08-09T09:00:00Z.
- Load-bearing claims of the object (why this many lenses): (1) the staged
  procedure is executable as written by someone who has never run it; (2) the
  row schema, the closure script and the templates agree with one another;
  (3) every agent role can actually be spawned the way the document says;
  (4) each shipped script does what the document claims it does.
- Git history requested by: no lens; the copy is shared for the round.
- Excluded from the critics' copy: secret-class files per the copy script's
  default patterns (none were present in this repository).
- Concurrent critics: 4 against the hard budget of 12, checked BEFORE spawning.
- Batch-commit executor: orchestrator.
- Salvages: `<run-folder>/critics/` and `<run-folder>/verify/`. **Not included
  in this example** — verbatim reports are local artifacts and never ship.
  Privacy confirmed for this repository BEFORE the first salvage: yes.
- Precedents file: not created — no repeated adjudication ruling arose.
- Scratchpad not cleaned: cleaned 2026-08-09 by the cleanup script with
  `--confirm` (two honest refusals on the way, both resolved by naming the
  root and the run id explicitly; deleted=1 refused=0).
- Row schema: v3
- Zone map: `round-contract.md` § 4 "Zone map" beside this file. It partitions
  the object whole; the `zone` cell of every row below is filled from it by the
  ADJUDICATOR, never by transcription.
- Residue register: `residue-register.md` beside this file. In a real project
  it lives at the root of the project's own run-folder directory, OUTSIDE any
  one run, because it outlives every run; it is shipped next to this ledger
  only so the example is readable in one place.
- Residue carried in: 1 row, oldest 3 days at the round's start — the register
  row this object inherited from the earlier round. The register's own
  aggregate covers the whole PROJECT and is printed by the recount under
  `--register`, never hand-counted here.
- Exit family: residual-risk — the round closed over one ratified residue row,
  not on a streak of clean passes alone. Both exits are legitimate closures.
- Closure rule: the round closes only on a programmatic recount
  (`scripts/recount.py`) reporting zero non-terminal rows. A row's status
  lives ONLY in its cells; prose never overrides the table. Range rows are
  banned — one id per row. Every row is exactly 9 cells wide, the width of the
  v3 schema this ledger declares (`zone` inserted third); a literal pipe inside
  a cell is escaped as `\|`. The criterion cell must agree with the terminal
  cell. The recount reads ONLY the first findings table.
- Terminal statuses (canonical names — exactly seven): `verified-landed` /
  `refuted-with-reason` / `accepted-residue` (with the literal
  `user-signed <date>`) / `refused-user-signed <date>` /
  `out-of-scope-by-contract (NG-<n>, signed <date>)` /
  `frozen-carried (stop-rule, <date>)` / `logged-no-action`. The last is the
  one status the zone gates: only a `Z3` row may take it, and only through a
  closing batch the owner signs off in one act. `frozen-carried` did not arise
  here — this round's stopping rule never fired.
- Named NON-terminal waits: `awaiting-signature (nominated <date>)` for a
  residue NOMINEE queued for the owner's ratification, and
  `awaiting-logged-no-action (listed <date>)` for a `Z3` row waiting in a
  closing batch. Neither is a status; each is a place a row WAITS, counted
  apart from an open row and still exiting 1. `DC-1` below sat in the first of
  them for three days — see the register's `nominated` and `ratified` dates —
  and `HB-6` sat in the second for one.

| id | sev | zone | claim (hook; canon = the report) | verdict | criterion | fix | verified | terminal |
|---|---|---|---|---|---|---|---|---|
| DA-2 | blocker | Z1 | The closure script did not parse every row it was given: a row with a stray pipe or a wrong cell count was skipped without a word, left out of the totals, and the script still announced the round closable — so a ledger could be declared finished while a real finding sat inside it unread. | confirmed; reproduced on a fixture whose single damaged row disappeared from the count while the exit code stayed 0 | L1 command and exit code — a fixture ledger carrying one unparsable row makes the script exit 2 and print that line's number; a clean fixture still exits 0 | `a1b2c3d` | LANDED (V1) | verified-landed |
| HA-1 | major | Z1 | The prose asserted that the closure script refuses an owner signature written without a date, but the code looked only for the bare word: a signature with no date at all was accepted and the row counted as finished. An audit trail that cannot say WHEN the owner signed is not an audit trail. | confirmed twice over — the internal-consistency lens and the script lens each reached it independently and each ran its own fixture; the duplicate was merged into this row | L1 command and exit code — fixtures whose signature carries no date exit non-zero; the same fixtures with an ISO date exit 0 | `b2c3d4e` | LANDED (V1) | verified-landed |
| HA-5 | major | Z2 | The fix-batch stage ordered the orchestrator to commit after every batch, phrased with no exceptions, while the modes table one section earlier already allowed a project's own committer and a review-request link where the commit hash would go. A reader following the stage text would break the table's rule and never notice. | confirmed: an unconditional instruction standing against a table that grants an alternative | L2 deterministic structural check — the fix-batch stage names the committer field chosen at scoping and states that a review link may stand in the fix cell | `c3d4e5f` | LANDED (V1) | verified-landed |
| HB-3 | major | Z2 | The document was said to have grown two rules — one for merging findings that two lenses raised, one for handling decisions the owner gave mid-round — that appeared in none of the design notes behind it, i.e. to have acquired normative content nobody sanctioned. | refuted with command evidence: reading the file as it stood before the rewrite showed both rules already present, so they are preserved text rather than an addition; a design note's silence does not repeal a rule it never discussed | — | — | — | refuted-with-reason |
| HC-1 | major | Z2 | For each of the four agent roles the document gave only the path of its definition file and never the identifier the orchestrator must actually pass when spawning it — the one string without which none of the spawn instructions can be executed as written. | confirmed: the real spawn surface is named nowhere in the object | L2 deterministic structural check — every spawn instruction carries the role's agent identifier next to the definition path | `c3d4e5f` | LANDED (V1) | verified-landed |
| HD-3 | major | Z1 | The script that hands each critic its own copy of the project took a fast path on one platform that dragged the whole version-control history along, whatever the per-lens setting said — and the manifest it wrote then described a copy that did not exist. Critics were reading history nobody had asked to give them. | confirmed on a fixture: the fast path delivered the full history to every copy regardless of the flag | L1 command and exit code — a copy made without the history flag contains no repository metadata and the manifest records the exclusion; with the flag the metadata is present | `d4e5f6a` | LANDED (V1) | verified-landed |
| HD-5 | minor | Z1 | The report-acceptance script judged whether a finding cited evidence by looking for a filename with a dot or a slash in it, so a finding pointing at an extension-less file at top level was stamped as evidence-free although its evidence was perfectly concrete. | confirmed (minor); a false alarm, not a missed defect | L1 command and exit code — a fixture whose only evidence cites an extension-less file is reported with zero suspicious findings | `e5f6a7b` | LANDED (V1) | verified-landed |
| HV-1 | major | Z1 | Raised by verification pass 1: for five upheld rows the fix cell had been left empty even though the corresponding batch commits existed and were correctly named, because the hash was copied in by a pattern that stumbled over the escaped pipes inside claim text. The object fixes had landed; the ledger's own record of them had not. | confirmed; the defect is in the ledger's bookkeeping rather than in the object, which makes it exactly the kind of thing only an independent pass finds | L1 command and exit code — a script pass over the ledger reports zero upheld rows with an empty fix cell | `f6a7b8c` | LANDED (V2) | verified-landed |
| HW-1 | minor | Z2 | Raised by the closing pass: the sentence defining how a merged duplicate row is written did not match the shape the round's own rows actually used, which added a short explanatory tail after the pointer. | confirmed (minor): the same drift between prose and practice, one line wide | L2 deterministic structural check — the merge rule states that the pointer may be followed by a short gloss | `a7b8c9d` | LANDED (V3, mechanical grep by the orchestrator) | verified-landed |
| DC-1 | major | Z3 | A shipped README table quotes throughput numbers measured on the author's own hardware: together they could be cross-referenced against unpublished benchmark logs, so anyone holding both could tie this repository to them. | confirmed as a class of risk, with the stakes re-judged at adjudication: the link back to the author is INTENDED — this repository is meant to be attributable — and the numbers carry the evidence a reader needs. The residue is the correlation with the private logs, which matters only if those logs ever leak; the owner chose to keep the numbers | L2 deterministic structural check — the numbers no longer occur in the published text (upheld criterion, deliberately left unsatisfied) | no fix — owner decision on the published numbers | n/a: no fix attempted; the row is residue, not a landing | accepted-residue user-signed 2026-08-06 (attribution is intended; re-signed by the owner) |
| HB-6 | minor | Z3 | The origin-story document tells the discipline's history in an order that does not match the order the rules were actually adopted, so a reader reconstructing WHY a rule exists from that narrative gets the sequence wrong. | confirmed as written, and confirmed as informative: the section carries no obligation for any later actor, and no check anywhere reads it. The owner read the finding and chose to act on it in no way — the story is a story | L7 reading — recorded for the record; no bar was set, because no action was taken | no fix — informative finding, logged | n/a: no fix attempted; the row was logged, not landed | logged-no-action |
| HC-4 | major | Z2 | The skill should ship a machine-readable index of every agent identifier it spawns, so that a host application could enumerate the roles without parsing prose. | confirmed as a real gap and disposed of without a live signature: the whole claim falls inside Non-Goal NG-1 of this round's contract, which the owner signed before the first critic was spawned. Nothing here is refuted — the work is out of scope, which is a different thing and says so | n/a — the claim falls whole inside a pre-signed Non-Goal, so no readiness bar was set for it | no fix — pre-signed Non-Goal | n/a: no fix attempted; the disposition is the contract's | out-of-scope-by-contract (NG-1, signed 2026-08-08) |

## Verification passes

| # | pass (scope) | verdicts (L/P/NOT) | new findings | bundled | second-pass-skipped | notes | verifiers |
|---|---|---|---|---|---|---|---|
| 1 | full re-inspection of every upheld id, split by lens across four fresh verifiers whose scopes covered every id with no overlap and no hole (the round's rework share sat above the 5% trigger) | 6/0/0 | 1 (HV-1) | no | n/a — the round was above the 20-finding threshold, so a second pass was mandatory | a lens-split verification pass; deleted-line walk complete for every zone, zero fix-loss | 4 |
| 2 | CLOSING pass by a fifth fresh verifier: HV-1 plus a re-check of a sample of earlier ids | 1/0/0 | 1 (HW-1, minor) | yes | n/a | convergence signal met — passes 1 and 2 both zero-major, zero NOT LANDED. Not narrowed to the residue: no owner signature for a residue-scoped second pass exists in this ledger, and without it the pass is run in full | 1 |
| 3 | post-convergence micro-batch: HW-1 alone, checked mechanically by grep | 1/0/0 | 0 | yes | n/a | the curve closes at 0 | 1 |

New-findings curve by pass: computed by `scripts/recount.py` from the table
above — quoted in the closure block below, never hand-counted. Convergence
signal = two consecutive passes with 0 major and 0 NOT LANDED. Kill criterion:
no decay for three consecutive passes → stop and fork to the owner.

## Batch deltas

- Fix batches ran sequentially, each at or under the 10-item limit, each
  committed by the orchestrator with its finding ids in the commit message.
- After the convergence signal the remainder moved to micro-batches with a
  bundled verification pass; bundling preserves the per-id verdicts, and the
  switch is recorded here rather than assumed.
- The fixer reproduced each defect in the CURRENT text before editing and
  stopped where a premise no longer held; what it noticed BESIDE its batch went
  into its report's `NOTICED OUTSIDE BATCH` block, never into an edit, and
  reached the adjudicator as new candidate findings rather than as silent work.
- The verifiers were not shown the fixer's report or its reasoning — only the
  criterion cells, the diffs and the round's verbatim critic salvages — so each
  pass answered "would a fresh critic still file here?" rather than "were the
  edits applied as described?".
- `HB-6` and `HC-4` were closed without a fix batch at all: `HC-4` by the
  contract's Non-Goal NG-1, pre-signed before the round opened, and `HB-6` by
  the owner's own act over a batch of `Z3` rows he chose to act on in no way.

## Inter-round DELTA

The earlier round on this repository is not shipped with the example, so no
executable delta is reproduced here. What a delta says, in one sentence: which
ids became terminal since the previous round, which regressed, which are still
open, and which are new — a change report, never a fresh snapshot. The command
that produces it is shown in `README.md`.

## Disposition of previous rounds

The earlier round closed with no open rows; its one residue row is carried
here as `DC-1` and re-signed by the owner, rather than being silently
inherited. The durable side of that acceptance is the register beside this
file: `DC-1` was NOMINATED by the orchestrator, sat in `awaiting-signature`
while the ledger stayed open, and became accepted risk only when the owner
ratified it — an act that writes both sides at once, `ratified 2026-08-06`
into the register's `status` cell and `accepted-residue user-signed 2026-08-06`
into the row's `terminal` cell. Nothing is ratified by silence, and a register
row is never deleted: the register is append-only and outlives every run
folder.

## Closure

Round closed 2026-08-09 on a programmatic recount — every row terminal, no row
awaiting a signature, and no row waiting on the owner's Z3 closing act. Only
then was `Ledger state:` moved from `open` to `closed 2026-08-09` in the header
above: the field records the closure, it does not decide it. Verbatim output of
`python3 ../../skills/critic-ledger/scripts/recount.py fix-ledger.md`:

```text
rows: 12 | terminal: 12 | non-terminal: 0
severity distribution (terminal/rows): blocker 1/1 | major 8/8 | minor 3/3
upheld/refuted: 11 upheld, 1 refuted
residual-defect ESTIMATE (Jackknife capture-recapture): N-hat 14.0 | D 8 raised | f1 8 single-lens | k 4 (HA, HB, HC, HD)
  ESTIMATE is ADVISORY, reported and never acted on: it enters no stop rule and no exit code. Lens diversity does not invalidate it (the source measured little or no impact on the estimate), but the caution that remains is OURS and is named as ours: our four field measurements put the single-lens share at 75-94% and N-hat near 2*D, and they count D as distinct CONFIRMED findings where this line counts distinct RAISED ones, so comparability is not established. Treat the number as advice, not as a target.
new-findings curve: 1 -> 1 -> 0
  time axis: n/a (no started/ended columns — v1 passes table)
ROUND CLOSABLE: zero non-terminal rows.
```

Exit code: 0.

The residual-defect estimate is printed because the header declares four
lenses; it is advisory and enters no stop rule and no exit code.

The register beside this file is passed with `--register residue-register.md`,
which adds an aggregate over the accepted risk of the whole project. That block
is deliberately NOT quoted here: its ages and its overdue warnings are computed
against the day the command runs, so a transcript of them would be stale by the
time anyone read it. Run it to see it.
