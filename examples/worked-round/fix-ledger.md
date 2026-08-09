# Fix-ledger — skill-payload (worked example, created 2026-08-09)

> **Provenance.** This file is a **sanitized derivative of real critic rounds
> run on this repository — not a transcript.** Every row restates a finding
> that was actually raised, adjudicated, fixed and verified here; the wording
> is re-authored in plain English so an outsider can read it, and nothing is
> invented. Eight rows come from the round whose object was this plugin's own
> payload; **two rows are imported from an earlier round on the same
> repository** — `DA-2`, to show a `blocker`-severity row (the later round
> produced none), and `DC-1`, to show the `accepted-residue` status (the later
> round produced none). Commit hashes in the `fix` column and the header's
> `Pin` are **illustrative placeholders**, not hashes from this repository's
> history. The verbatim critic and verifier reports are **not** part of this
> example: salvaged reports stay local and never ship.

- Ledger state: open. (This field records only whether a later rewrite froze
  the ledger; a round that has closed still reads `open` — its closure is the
  recount's verdict, recorded under "Closure" below.)
- Object: full path `<repo>/skills/critic-ledger/SKILL.md` plus
  `<repo>/skills/critic-ledger/templates/` (11 files) | short name:
  skill-payload — the short name is only the run-folder address, the full path
  lives here. Pin: `3f2a91c` (illustrative placeholder). Pin = state at round
  start; verification always runs against the CURRENT head.
- Previous run on this object: an earlier round on the same repository, kept
  in a local, unshipped run folder (it is the source of the two imported rows).
- Mode: plan. The object is a normative document plus the scripts it
  describes; the scripts are reviewed as documented contracts, and read-only
  runs against a scratch copy are allowed.
- Prerequisite (stage 0): git = yes, commit sanction = yes; normal mode.
- Lenses: internal-consistency → `HA` → sonnet → ~20 min; design-fidelity →
  `HB` → sonnet → ~20 min; platform-correctness → `HC` → sonnet → ~20 min;
  script-correctness → `HD` → sonnet → ~20 min. No owner-set lens. Two further
  prefixes are not lenses: `HV` and `HW` are findings raised BY the
  verification passes, and a leading `D` marks the two rows imported from the
  earlier round (whose lens names are not reproduced here).
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
- Closure rule: the round closes only on a programmatic recount
  (`templates/recount.py`) reporting zero non-terminal rows. A row's status
  lives ONLY in its cells; prose never overrides the table. Range rows are
  banned — one id per row. Every row is exactly 8 cells wide; a literal pipe
  inside a cell is escaped as `\|`. The criterion cell must agree with the
  terminal cell. The recount reads ONLY the first findings table.
- Terminal statuses (canonical names — exactly four): `verified-landed` /
  `refuted-with-reason` / `accepted-residue` (with the literal
  `user-signed <date>`) / `refused-user-signed <date>`.

| id | sev | claim (hook; canon = the report) | verdict | criterion | fix | verified | terminal |
|---|---|---|---|---|---|---|---|
| DA-2 | blocker | The closure script did not parse every row it was given: a row with a stray pipe or a wrong cell count was skipped without a word, left out of the totals, and the script still announced the round closable — so a ledger could be declared finished while a real finding sat inside it unread. | confirmed; reproduced on a fixture whose single damaged row disappeared from the count while the exit code stayed 0 | L1 command and exit code — a fixture ledger carrying one unparsable row makes the script exit 2 and print that line's number; a clean fixture still exits 0 | `a1b2c3d` | LANDED (V1) | verified-landed |
| HA-1 | major | The prose asserted that the closure script refuses an owner signature written without a date, but the code looked only for the bare word: a signature with no date at all was accepted and the row counted as finished. An audit trail that cannot say WHEN the owner signed is not an audit trail. | confirmed twice over — the internal-consistency lens and the script lens each reached it independently and each ran its own fixture; the duplicate was merged into this row | L1 command and exit code — fixtures whose signature carries no date exit non-zero; the same fixtures with an ISO date exit 0 | `b2c3d4e` | LANDED (V1) | verified-landed |
| HA-5 | major | The fix-batch stage ordered the orchestrator to commit after every batch, phrased with no exceptions, while the modes table one section earlier already allowed a project's own committer and a review-request link where the commit hash would go. A reader following the stage text would break the table's rule and never notice. | confirmed: an unconditional instruction standing against a table that grants an alternative | L2 deterministic structural check — the fix-batch stage names the committer field chosen at scoping and states that a review link may stand in the fix cell | `c3d4e5f` | LANDED (V1) | verified-landed |
| HB-3 | major | The document was said to have grown two rules — one for merging findings that two lenses raised, one for handling decisions the owner gave mid-round — that appeared in none of the design notes behind it, i.e. to have acquired normative content nobody sanctioned. | refuted with command evidence: reading the file as it stood before the rewrite showed both rules already present, so they are preserved text rather than an addition; a design note's silence does not repeal a rule it never discussed | — | — | — | refuted-with-reason |
| HC-1 | major | For each of the four agent roles the document gave only the path of its definition file and never the identifier the orchestrator must actually pass when spawning it — the one string without which none of the spawn instructions can be executed as written. | confirmed: the real spawn surface is named nowhere in the object | L2 deterministic structural check — every spawn instruction carries the role's agent identifier next to the definition path | `c3d4e5f` | LANDED (V1) | verified-landed |
| HD-3 | major | The script that hands each critic its own copy of the project took a fast path on one platform that dragged the whole version-control history along, whatever the per-lens setting said — and the manifest it wrote then described a copy that did not exist. Critics were reading history nobody had asked to give them. | confirmed on a fixture: the fast path delivered the full history to every copy regardless of the flag | L1 command and exit code — a copy made without the history flag contains no repository metadata and the manifest records the exclusion; with the flag the metadata is present | `d4e5f6a` | LANDED (V1) | verified-landed |
| HD-5 | minor | The report-acceptance script judged whether a finding cited evidence by looking for a filename with a dot or a slash in it, so a finding pointing at an extension-less file at top level was stamped as evidence-free although its evidence was perfectly concrete. | confirmed (minor); a false alarm, not a missed defect | L1 command and exit code — a fixture whose only evidence cites an extension-less file is reported with zero suspicious findings | `e5f6a7b` | LANDED (V1) | verified-landed |
| HV-1 | major | Raised by verification pass 1: for five upheld rows the fix cell had been left empty even though the corresponding batch commits existed and were correctly named, because the hash was copied in by a pattern that stumbled over the escaped pipes inside claim text. The object fixes had landed; the ledger's own record of them had not. | confirmed; the defect is in the ledger's bookkeeping rather than in the object, which makes it exactly the kind of thing only an independent pass finds | L1 command and exit code — a script pass over the ledger reports zero upheld rows with an empty fix cell | `f6a7b8c` | LANDED (V2) | verified-landed |
| HW-1 | minor | Raised by the closing pass: the sentence defining how a merged duplicate row is written did not match the shape the round's own rows actually used, which added a short explanatory tail after the pointer. | confirmed (minor): the same drift between prose and practice, one line wide | L2 deterministic structural check — the merge rule states that the pointer may be followed by a short gloss | `a7b8c9d` | LANDED (V3, mechanical grep by the orchestrator) | verified-landed |
| DC-1 | major | The evidence figures quoted in the public text form a fingerprint: together they identify an unpublished private research document as their source, so anyone holding both could tie this repository to it. | confirmed as a class of risk, with the stakes re-judged at adjudication: the link back to the author is INTENDED — this repository is meant to be attributable — and the figures carry the evidence a reader needs. The residue is the correlation with the private source, which matters only if that document ever leaks; the owner chose to keep the numbers | L2 deterministic structural check — the figures no longer occur in the published text (upheld criterion, deliberately left unsatisfied) | no fix — owner decision on the published figures | n/a: no fix attempted; the row is residue, not a landing | accepted-residue user-signed 2026-08-06 (attribution is intended; re-signed by the owner) |

## Verification passes

| # | pass (scope) | verdicts (L/P/NOT) | new findings | bundled | second-pass-skipped | notes |
|---|---|---|---|---|---|---|
| 1 | full re-inspection of every upheld id by a fresh verifier (the round's rework share sat above the 5% trigger) | 6/0/0 | 1 (HV-1) | no | n/a — the round was above the 20-finding threshold, so a second pass was mandatory | deleted-line walk complete, zero fix-loss |
| 2 | CLOSING pass by a second fresh verifier: HV-1 plus a re-check of a sample of earlier ids | 1/0/0 | 1 (HW-1, minor) | yes | n/a | convergence signal met — passes 1 and 2 both zero-major, zero NOT LANDED |
| 3 | post-convergence micro-batch: HW-1 alone, checked mechanically by grep | 1/0/0 | 0 | yes | n/a | the curve closes at 0 |

New-findings curve by pass: computed by `templates/recount.py` from the table
above — quoted in the closure block below, never hand-counted. Convergence
signal = two consecutive passes with 0 major and 0 NOT LANDED. Kill criterion:
no decay for three consecutive passes → stop and fork to the owner.

## Batch deltas

- Fix batches ran sequentially, each at or under the 10-item limit, each
  committed by the orchestrator with its finding ids in the commit message.
- After the convergence signal the remainder moved to micro-batches with a
  bundled verification pass; bundling preserves the per-id verdicts, and the
  switch is recorded here rather than assumed.

## Inter-round DELTA

The earlier round on this repository is not shipped with the example, so no
executable delta is reproduced here. What a delta says, in one sentence: which
ids became terminal since the previous round, which regressed, which are still
open, and which are new — a change report, never a fresh snapshot. The command
that produces it is shown in `README.md`.

## Disposition of previous rounds

The earlier round closed with no open rows; its one residue row is carried
here as `DC-1` and re-signed by the owner, rather than being silently
inherited.

## Closure

Round closed 2026-08-09 on a programmatic recount — every row terminal, no
row awaiting a signature. Verbatim output of
`python3 ../../skills/critic-ledger/templates/recount.py fix-ledger.md`:

```text
rows: 10 | terminal: 10 | non-terminal: 0
new-findings curve: 1 -> 1 -> 0
ROUND CLOSABLE: zero non-terminal rows.
```

Exit code: 0.
