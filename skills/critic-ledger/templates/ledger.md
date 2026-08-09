# Fix-ledger — {object-slug} (run {run-folder}, created {date})

<!-- The file name is always fix-ledger.md; it lives inside the run folder
     {run-folder} = .critic-ledger/{YYYY-MM-DD-HHMMSS-object-slug}/,
     which carries the uniqueness. There is no round number: a repeat round
     on the same object is a new run folder, linked by the "Previous run"
     field below. -->

<!-- Mandatory header fields. Fill every line; delete none. -->
- Ledger state: {open | FROZEN (superseded-by-rewrite, date + reason)}.
  Freezing is the ORCHESTRATOR's single header write; rows keep their
  statuses; a frozen ledger is never closable.
- Object: full path {absolute paths or commit range} | short name
  {object-slug} — the short name is only the run-folder address, the full
  path lives here. Pin: {commit hash} — git is mandatory, so the pin is
  always a commit hash, DEGRADED mode included (degraded = git is present
  but the commit sanction is missing, so the fixes stay uncommitted).
  Pin = state at round start; verification always runs against the CURRENT
  head — third-party mid-round edits produce new findings via adjudication,
  they do not break the round.
- Previous run on this object: {path of the previous run folder | none}.
  This link is the only tie between runs — there is no round number to
  continue.
- Mode: {plan | impl}.
- Prerequisite (stage 0): git = {yes/no}, commit sanction = {yes/no};
  {normal | DEGRADED} mode.
- Lenses: {lens → id-prefix → model → timebox, one line per lens; mark a
  lens the owner asked for as `owner-set`; prefixes are letter-led, letters
  and digits only (recount id contract); note a dropped lens here if a
  respawn failed}.
- Load-bearing claims of the object (why this many lenses): {one line per
  claim whose falsity would make the object unfit}. The lens count equals
  the length of this list — a count without the list is invalid; `owner-set`
  lenses come ON TOP of it.
- Git history requested by: {lenses that declared they need it | none};
  copy is {per-critic | shared for the round}. With a shared copy the
  history one lens asked for is readable by all — accepted knowingly, not
  hidden.
- Excluded from the critics' copy: {classes of files withheld — env and
  secret patterns always, plus whatever was dropped for size when the copy
  had to be narrowed}. A critic must know what it never saw, or its
  coverage statement lies; silent narrowing is banned.
- Concurrent critics: {actual sum = lenses + repeat passes on critical
  claims + owner-set lenses} against the hard budget of 12, checked BEFORE
  spawning. The same number is the count of simultaneous clones of the
  private tree.
- Batch-commit executor: {orchestrator | project convention (name it) |
  none (degraded)}.
- Salvages: {paths of the verbatim report files, under {run-folder}/critics/
  and {run-folder}/verify/}. Privacy confirmed for this repository BEFORE
  the first salvage: {yes | local unversioned holding used instead}.
- Precedents file: {{run-folder}/precedents.md | not created yet — no
  repeated adjudication ruling}. Created and kept by the ORCHESTRATOR only,
  at the first repeated ruling, never in advance.
- Scratchpad not cleaned: {reason, path | cleaned {date}}. Any refusal of
  the cleanup script is a record, not an error — the directory stays and the
  reason lands here; paste the dry-run output that named what was to be
  deleted.
- Closure rule: the round closes only on a programmatic recount
  (templates/recount.py) reporting zero non-terminal rows. A row's status
  lives ONLY in its cells; prose never overrides the table. Range rows are
  banned — one id per row. Every row is exactly as wide as THIS table's own
  header — 8 cells (`id | sev | claim | verdict | criterion | fix |
  verified | terminal`); any other width is a structural error, and mixing
  widths inside one table is banned. A literal pipe inside any cell MUST be
  escaped as `\|` (the recount fails closed on malformed rows). The
  criterion cell must agree with the terminal cell: a `verified-landed` row
  carries a non-empty criterion that is not a dash, a `refuted-with-reason`
  or `refused-user-signed` row carries exactly the em-dash `—` — either
  violation is a structural error, not a warning. The recount reads ONLY
  this first findings table (up to the next heading) — appendix tables of
  the same shape are not part of the round count.
- Terminal statuses (canonical names — exactly four): `verified-landed` /
  `refuted-with-reason` / `accepted-residue` / `refused-user-signed`. The
  residue cell must contain the literal `user-signed {date}`.
  `refused-user-signed` is the owner's REFUSAL to fix a CONFIRMED finding
  (its home is the security/PII class, marked as such at adjudication, never
  retroactively): terminal only with the literal `refused-user-signed {date}`
  in the terminal cell — a bare `refused` stays non-terminal, silence is not
  a signature. "Fixed otherwise than the critic proposed" is NOT a fifth
  status: it lives in the `verified` cell as the literal
  `LANDED OTHERWISE (<what was actually done>)` and the row closes with the
  ordinary `verified-landed`; without a non-empty description in the
  parentheses the outcome is "partial" and the row stays open. If the ledger
  is kept in another language, map aliases to these names here, once — and
  normalize them to the canonical names before the closing recount: the
  recount accepts only these four.

| id | sev | claim (hook; canon = the report) | verdict | criterion | fix | verified | terminal |
|---|---|---|---|---|---|---|---|

## Readiness criterion (the `criterion` cell)

<!-- Written by the ADJUDICATOR, BEFORE any fix is attempted; the fixer
     may not change it. -->

- Record it as the scale level plus a short name, then the criterion
  itself: `L2 structural check — the removed wording no longer occurs in
  {file}`. Levels 1-7, see SKILL.md for the full scale.
- Pick the level by the ladder, not by feel; when in doubt take the LOWER
  level — an honest weak criterion beats a strong one nobody can satisfy.
- A criterion the fixer could satisfy by editing the very file that
  defines the check (test, scoring script, rubric) is invalid.
- "Improve it", "polish it", "make it clearer" are rejected at
  adjudication — these are not criteria.
- A criterion that turns out to be unsatisfiable becomes an
  `accepted-residue` with a one-line reason and the owner's signature —
  never a silent pass, never rewritten after the fact into an executable
  form it cannot honestly take.
- Refuted and refused rows carry exactly `—` here (deliberately not
  needed, as opposed to forgotten); an empty cell is banned for every row.

## Verification passes

<!-- The carrier of the convergence signal and of the kill criterion. -->

| # | pass (scope) | verdicts (L/P/NOT) | new findings | bundled | second-pass-skipped | notes |
|---|---|---|---|---|---|---|

New-findings curve by pass: computed by templates/recount.py from the
table above — quote the script's output here, do not hand-compute.
Convergence signal = two consecutive passes with 0 major and 0 NOT
LANDED. Kill criterion: no decay for three consecutive passes → stop,
fork to the user (the recount prints the warning).

`bundled` = yes when the pass covered several micro-batches at once —
the regime the remainder moves to after the convergence signal; bundling
preserves PER-ID verdicts, and the switch is recorded in the round delta.
`second-pass-skipped` = yes when the round stayed under the soft
threshold of 20 findings and the second pass was skipped by default. The
threshold buys tokens, not correctness: the owner may ask for the pass
anyway, and from 20 findings up it is mandatory.

## Batch deltas

<!-- One dated subsection per fix batch. Delta snapshots are HISTORICAL
     records; the current count lives in one place only — the table above,
     recounted by script. -->

## Inter-round DELTA

<!-- When a previous round exists: newly landed / regressed / still open —
     a delta, not a snapshot. -->

## Disposition of previous rounds

<!-- Open/residue rows of the previous ledger, disposed here: inherited /
     superseded ("not re-opened by a fresh full pass = superseded"). -->
