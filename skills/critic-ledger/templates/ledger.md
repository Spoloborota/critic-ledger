# Fix-ledger — {object-slug} (run {run-folder}, created {date})

<!-- The file name is always fix-ledger.md; it lives inside the run folder
     {run-folder} = .critic-ledger/{YYYY-MM-DD-HHMMSS-object-slug}/,
     which carries the uniqueness. There is no round number: a repeat round
     on the same object is a new run folder, linked by the "Previous run"
     field below. -->

<!-- Mandatory header fields. Fill every line; delete none. -->

<!-- THE MACHINE COPY IS THE TRACE, NOT THIS FILE. With observability on,
     the ledger gains exactly three header lines below plus two trailing
     columns on the verification-passes table — a human-readable summary
     and nothing more. Every per-span number (assigned and observed model,
     tokens, wall-clock, agent ids, per-id tags) lives in
     {run-folder}/trace.jsonl and is read from there by templates/rollup.py;
     it is never copied back into these cells, and no column is added here
     to hold it. There is deliberately NO lens table and no token column: a
     second machine-readable copy of the same facts is a second source of
     truth, and the one that drifts is always the hand-maintained one. This
     file measures QUALITY — what was found, what was fixed, what was
     verified; the trace measures COST. With observability off, nothing
     here changes except the two words that say so. -->
- Ledger state: {open | closed <ISO-date> | FROZEN (superseded-by-rewrite,
  date + reason)}.
  Freezing is the ORCHESTRATOR's header write; rows keep their statuses; a
  frozen ledger is never closable. Closing is its other one: the literal
  `Ledger state: closed <ISO-date>` replaces `open` at stage 9, on the
  recount that printed `ROUND CLOSABLE`. That value blocks nothing — it
  carries no `frozen`, so a closed ledger recounts exactly as an open one
  does — and a round left awaiting a signature keeps `open`.
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
  {normal | DEGRADED} mode; subagent-model: {set <value> | set
  <non-model-value> | unset}.
- Round contract: {path of the signed contract file} sha {sha of that file at
  the round's start} | none — object under the 400-line gate, owner waived it
  on {date}. The contract is a DURABLE file beside the object, from
  templates/round-contract.md, and it is signed BEFORE the first critic is
  spawned: an object longer than 400 lines cannot open a round without it.
  For a small object the contract may be a section pasted into this header
  instead of a file, and this field then says so. Both the path and the sha
  live here because a contract edited mid-round is otherwise indetectable —
  a re-read of the file months later would show something the round never saw.
- Contract amendments: {none | Amendment {n}: {ISO date} — {one sentence on
  what it changes}, one entry per amendment}. An amendment made INSIDE the
  round is
  numbered, dated and one sentence long, and it is written HERE: an
  unnumbered amendment does not take effect. An amendment touching a field
  the owner signed (Non-Goals, the stopping rule, the privacy-gate answer,
  the models) carries the owner's signature in the same machine form as
  residue — `user-signed {ISO date}` — and is void without it.
- Round-started: {ISO-8601 UTC | n/a} — when stage 1 created this file. It
  is also what puts a round in TIME for the severity-weighted plateau: given
  two `--prev` ledgers the recount orders the window by this field alone and
  never by the order of its arguments, so a round that leaves it `n/a`
  cannot take part in a plateau.
- Observability: {on | off}. One word, decided at stage 0 from the flag and
  written here at stage 1(c) with the rest of the header, so that a reader
  of an old ledger can tell whether the absence of numbers means "off" or
  "lost". Never left blank.
- Trace: {trace.jsonl | none (observability off)}.
- Lenses:
  - {PREFIX} | {lens name} | {model}
  - {PREFIX} | {lens name} | {model}
  These dashed lines directly under the field, one per lens and NOTHING
  between them, are its MACHINE part: `{PREFIX} | {lens name} | {model}`,
  the prefix letter-led, capitals and digits only (`[A-Z][A-Z0-9]{0,3}`,
  the recount id contract). templates/recount.py reads `k` — the lens count
  of the residual-defect estimate — from this run and from NOWHERE else,
  and it stops at the first line that does not take the shape. So
  everything softer goes BELOW the run, in prose like this: the timebox per
  lens, `owner-set` for a lens the owner asked for, a note on a lens
  dropped because a respawn failed, and with observability on the model
  that was actually OBSERVED rather than the one assigned.
- Verifier passes: {verifier-prefix stem | n/a}. Stage 2 fixes ONE stem for
  the round, under the recount's own id contract and distinct
  from every one of the lens prefixes, and records it HERE — never among
  the `Lenses:` lines, which are counted. Verifier prefixes live by the same id contract
  as lens prefixes, which is exactly why `k` is never a count of the
  distinct prefixes in the findings table: that count would grow with every
  verification pass. Pass n's verifier-prefix is that stem followed by the
  pass ordinal — stem `V` gives `V1`, `V2`, … — and a defect a verifier
  raises during pass n is a finding like any other: its own row, under
  `V<n>`. Prefix matching is exact, the recount's own id contract
  `^{prefix}-\d+$`, so `V1` never absorbs `V12`'s rows and a one-letter
  stem never absorbs a two-letter lens's.
  The stem MAY BE COMPOSITE — `V-CIT`, the lens carried inside the
  verifier's own ids so that a reader of the row sees which lens the pass
  re-checked; the recount's id contract accepts a prefix of dash-joined
  letter-led segments, so `V-CIT-1` recounts like any other id and the pass
  ordinal is appended to a composite stem exactly as to a simple one
  (`V-CIT` gives `V-CIT1`, `V-CIT2`, …). The two forms differ: `V-CIT-1` is
  a finding id — a prefix plus its number, which is why it recounts like any
  other id — while `V-CIT1` is pass 1's prefix and not an id itself, and
  that pass's findings are `V-CIT1-1`, `V-CIT1-2`, …, the `V-CIT1-<n>`
  shape. A composite stem is still a stem:
  it is written in THIS field, in the header beside the `Lenses:` prefixes
  and never among them, and it must stay DISTINCT from every one of them —
  `V-CIT` beside a lens `CIT` is fine, `V-CIT` beside a lens `V-CIT` is
  not.
- Process prefixes: none
  Replace `none` on the line above — and nothing else on it, the whole
  remainder of that line is the field's value — with the prefixes of the
  rows a PROCESS writes rather than a lens, comma-separated and in the same
  alphabet as the `Lenses:` prefixes (`[A-Z][A-Z0-9]{0,3}`): the
  `NOTICED OUTSIDE BATCH` prefix stage 2 fixed alongside the lens ones, and
  the prefix a class-kill gate's own row takes. Leave the literal `none`
  where the round declared neither. Without this field those rows are
  machine-INDISTINGUISHABLE from a lens's: they carry an id of exactly the
  same shape. Like `Verifier passes:` it is a declaration of what is NOT a
  lens — it is read by templates/recount.py through its own pattern, it
  never joins the `Lenses:` run, it never enters `k`, and every prefix it
  names must stay DISTINCT from every lens prefix.
- Security lens: none
  Replace `none` on the line above — and nothing else on it, the whole
  remainder of that line is the field's value — with the PREFIX of the lens
  the contract declared the round's security lens (same alphabet as the
  `Lenses:` prefixes, `[A-Z][A-Z0-9]{0,3}`), or leave the literal `none`
  when the contract declared no such lens. The field is the machine backstop against
  a class mark nobody set: every findings row whose id carries that prefix
  must hold either `class:security-pii` in its `verdict` cell or the written
  removal of the default, `declassed:security-pii — {reason}` with a
  non-empty reason. A row with neither is a structural error of the recount.
  The value is `none` rather than a `{placeholder}` on purpose: this field
  arms a gate, and templates/recount.py refuses a value it cannot read, so an
  unfilled placeholder would fail every round that has no security lens at all.
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
- Row schema: v3
  The value is the WHOLE remainder of the line above, exactly as with
  `Security lens:` below, and it must be one of `v1` / `v2` / `v3` — the
  form the findings table takes, declared once so that
  templates/recount.py, templates/transcribe.py and the verifier know what
  they parse without counting cells first: `v1` = 7 cells, `v2` = 8 (the
  readiness criterion added), `v3` = 9 (the zone column added third). This
  skeleton ships v3, so leave the value as it stands unless you are
  continuing an older ledger. The field must name the width the table's own
  header actually has — a declaration contradicting the table is a structural
  error of the recount, a second such line is one too, and everything softer
  belongs on these continuation lines, never on the field's own.
- Zone map: {path of the round contract § "Zone map" | the table itself, when
  the object was under the 400-line gate and the contract was pasted into
  this header}. Written by the ORCHESTRATOR at stage 2, from the contract the
  owner signed: it assigns every section of the object one of `Z1`
  (mechanically checkable contracts — scripts, acceptance blocks), `Z2`
  (normative prose — obligations for a later actor) or `Z3` (informative
  prose — rationale, history, examples), and it is the source the `zone` cell
  of every row below is filled from. The map's own rules — it must cover the
  object WHOLE, and a table that does not partition it is a defect of the
  CONTRACT rather than of the round — live in templates/round-contract.md § 4
  and are not restated here; this field only says where the map for THIS
  round is.
- Closure rule: the round closes only on a programmatic recount
  (templates/recount.py) reporting zero non-terminal rows. A row's status
  lives ONLY in its cells; prose never overrides the table. Range rows are
  banned — one id per row. Every row is exactly as wide as THIS table's own
  header — 9 cells in the v3 schema this skeleton ships (`id | sev | zone |
  claim | verdict | criterion | fix | verified | terminal`); any other width
  is a structural error, and mixing widths inside one table is banned. Two
  older forms stay readable and are still recounted: `v2`, the same row
  without `zone` (8 cells), and `v1`, the v2 row without `criterion` (7).
  The zone column was inserted THIRD on purpose — `criterion`, `fix`,
  `verified` and `terminal` are addressed from the END of the row, so the
  three schemas are read without branching, and `criterion` is the fourth
  cell from the end at 8 and 9 cells alike. A literal pipe inside any cell MUST be
  escaped as `\|` (the recount fails closed on malformed rows). The
  criterion cell must agree with the terminal cell: a `verified-landed` row
  carries a non-empty criterion that is not a dash, a `refuted-with-reason`
  or `refused-user-signed` row carries exactly the em-dash `—` — either
  violation is a structural error, not a warning. The recount reads ONLY
  this first findings table (up to the next heading) — appendix tables of
  the same shape are not part of the round count.
- The `zone` cell (v3 only): `Z1`, `Z2` or `Z3`, taken from the zone map
  above for the section of the object the finding lands in. It is filled by
  the ADJUDICATOR at stage 6, never by transcription — templates/transcribe.py
  leaves the stub `·` there, because transcription is literal copying and a
  zone is a judgment; a zone the adjudicator finds genuinely disputable is
  his call and is recorded in `{run-folder}/precedents.md`. What the zone
  changes is the PAPER and the CLOSURE ROUTE, never the strictness of any
  check: severity is not renamed or lowered by it (a blocker found in `Z3`
  means the zone MAP was wrong — the row is re-zoned, with the ruling written
  to precedents.md, and the process is not bypassed), the deterministic
  deleted-line pre-pass still emits the FULL list for every zone, and the
  fresh-verifier rule holds on every pass in every zone. `Z1` and `Z2` run the
  existing pipeline unchanged. The one mechanical consequence is the terminal
  status `logged-no-action` below, which no row outside `Z3` may take.
- Terminal statuses (canonical names — exactly seven): `verified-landed` /
  `refuted-with-reason` / `accepted-residue` / `refused-user-signed` /
  `out-of-scope-by-contract` / `frozen-carried` / `logged-no-action`. The
  residue cell must contain the literal `user-signed {date}`, where `{date}`
  is a calendar-valid ISO date (`9999-99-99` is rejected).
  `refused-user-signed` is the owner's REFUSAL to fix a CONFIRMED finding
  (its home is the security/PII class, marked as such at adjudication, never
  retroactively): terminal only with the literal `refused-user-signed {date}`
  (a calendar-valid ISO date there too)
  in the terminal cell — a bare `refused` stays non-terminal, silence is not
  a signature. "Fixed otherwise than the critic proposed" is NOT a fifth
  status: it lives in the `verified` cell as the literal
  `LANDED OTHERWISE (<what was actually done>)` and the row closes with the
  ordinary `verified-landed`; without a non-empty description in the
  parentheses the outcome is "partial" and the row stays open.
  `out-of-scope-by-contract` is the disposition the round's SCOPE CONTRACT
  pre-signed: a finding whose whole claim is covered by a declared Non-Goal
  takes it with NO live signature, because the owner signed when the
  Non-Goals were authored. It is terminal only under the complete literal
  `out-of-scope-by-contract (NG-{n}, signed {ISO date})` — the Non-Goal named
  and the contract's own signing date in the cell. ONE exception, and it is a
  structural error rather than a status: a row marked `class:security-pii`
  may not take this route without a live `user-signed {date}` in the same
  cell, because that class needs the owner's word for BOTH of its outcomes
  and a signature given in advance does not cover it.
  `frozen-carried` is the disposition of a row still open when the contract's
  STOP RULE fired: literal `frozen-carried (stop-rule, {ISO date})`, the date
  being that row's own freeze, no live signature (the owner signed the
  stopping rule before the round opened). It is terminal FOR THIS ROUND and
  it does NOT block closability — that is the whole difference from
  `superseded-by-rewrite`, which makes a ledger permanently unclosable and is
  therefore no legitimate exit from a stop rule. Every `frozen-carried` row
  is carried into the next round on this object as a re-opened finding: the
  freeze closes the round, not the finding.
  `logged-no-action` is the disposition of an INFORMATIVE finding the owner
  logged and chose to act on in no way. It exists only in the v3 schema and
  only on a row whose `zone` is `Z3`: the status is reached through a closing
  batch the owner signs off in ONE act — at most ten rows per act, the same
  limit residue ratification uses — and the zone is what says the finding is
  informative at all. `logged-no-action` in a 7- or 8-cell row (which has no
  `zone` cell to check the condition against) and `logged-no-action` at any
  zone other than `Z3` are both structural errors of the recount, not
  undefined cases. The security/PII exception above applies here word for
  word: a row marked `class:security-pii` never travels inside a batch act,
  and the status without a live `user-signed {date}` in the same cell is a
  structural error.
  If the ledger
  is kept in another language, map aliases to these names here, once — and
  normalize them to the canonical names before the closing recount: the
  recount accepts only these seven.
- Named NON-terminal waits — not a fifth and sixth status but named places a
  row WAITS, counted and printed apart from an open row while still exiting
  1: `awaiting-signature (nominated {date})` is a residue NOMINEE queued for
  the owner's ratification — the date is calendar-valid and mandatory, the
  value may never sit on a `blocker` row (the recount rejects that
  combination as a structural error), and the row keeps the readiness
  criterion written at adjudication exactly as a ratified residue does;
  `awaiting-logged-no-action (listed {date})` is a `Z3` row picked into a
  closing batch and waiting for the owner's own act, the date being the day
  it was listed. A round with no open row but with
  either queue non-empty is NOT closed: the recount names the state
  (`ROUND AWAITING RATIFICATION` first, `ROUND AWAITING Z3 CLOSURE` when
  only that queue remains) and exits 1. The `listed` date is what makes that
  second wait ageable: past 30 days — not a new number, the residue queue's
  own nomination limit carried over — the recount prints the row under
  `Z3 CLOSURE OVERDUE` and the orchestrator owes the owner a fork of its own
  (close it, take it out of the batch and return it to adjudication as an
  open finding, or set a new date on the owner's explicit word). A permanent
  wait is banned here exactly as a permanent nomination is. A cell with no
  readable date still counts in the queue — it is the owner's act that drains
  it either way — but the recount reports it as unageable rather than passing
  it over. Because the status that CLOSES this wait exists only in the v3
  schema, the wait itself belongs on a `Z3` row of a v3 ledger: putting it on
  a v1/v2 row parks the row in a queue no status of that schema can drain.
- Exit family: {clean-streak | residual-risk | residual-risk close (stop-rule
  freeze)}. Which of the two legitimate exits closed this round — the streak
  of clean verification passes, or a close over residue that the owner has
  RATIFIED. Both are legitimate closures, not a success and a failure; the
  field exists so that a later reader does not have to guess which one this
  was. A round closed through the stop rule's freeze is a FORM of the second
  family and says so in the value above; it is never the first, because a
  round that stopped on its rule did not earn a streak of clean passes.
- The stop rule's freeze, when it fires, adds ONE header line here, written
  by the ORCHESTRATOR at the moment of the freeze and never as part of this
  skeleton: `Stop-rule freeze: {ISO date} | carried-to: {id of the next run
  folder | pending}`. That line is ONE per ledger and is written ONCE, by
  whichever freeze occasion came FIRST — the contract's stop rule firing, or
  the one-off freeze of an exhausted blocker. A second occasion does not
  rewrite it: the header keeps the first date, and every later frozen row
  carries its OWN date in its `terminal` cell, which is where "when was THIS
  row frozen" lives. A second such line in the header, a line that does not
  take the shape above, a `frozen-carried` row with no such line at all, and
  `carried-to: pending` still standing when the round closes are all
  structural errors of the recount — an overwrite is never a silent
  replacement and a carry to nowhere is never a carry. At closure the recount
  prints `FROZEN CARRIED: {n} rows → {carried-to}`.
- Residue register: {path of the project's .critic-ledger/residue-register.md
  | none — nothing nominated in this project yet}. The register lives OUTSIDE
  this run folder on purpose: it outlives any one run. Its skeleton is
  templates/residue-register.md.
- Residue carried in: {n rows, oldest {age} | none}. Quoted from the
  recount's register aggregate — the same rule as every other count here,
  never hand-computed.

<!-- Verdict-cell tags. Optional tags live inside the `verdict` cell and
     are read by templates/recount.py: `class:<slug>` — the defect class a
     finding belongs to — `origin:fix-application from:<batch>` — a
     finding whose substance is a defect in applying an earlier fix, plus the
     batch whose fix it was — and `shelf:<slug>` on a REFUTED row, naming the
     pre-signed contract disposition that closed the claim wholly, which the
     recount counts into the shelf share printed beside the per-lens
     sustained rate. Two more serve the class-kill count:
     `class-origin:adjudicator`, written beside a `class:` tag to say the
     class is the adjudicator's own judgment and not the security lens's
     DEFAULT — only then does the row count toward a class-kill — and
     `class-kill:<slug>` on the gate's OWN ledger row, naming the class that
     gate kills, which the recount prints as `kill in flight: <slug> (<id>)`
     while that row is not terminal. Their alphabet, their boundary and the
     point at which each becomes mandatory are stage 6 of the skill
     (references/stage-6-adjudication.md) and, for the class-kill row,
     stage 7 (references/stage-7-fix-batches.md); they are not restated here.
     A `class:` or `shelf:` that attempts a slug and produces
     none readable is a structural error of the recount, not a guess at where
     the slug ends; either of them followed straight away by a space, a `|`
     or the end of the cell is prose and is ignored.
     ONE slug is RESERVED and carries no other meaning: `class:security-pii`
     is the security/PII class, and every check keyed on that class reads
     that literal alone — `class:security`, `class:pii` and `class:sec-pii`
     are different classes and none of them is it. One more literal lives in
     the same cell and is not a tag but the written removal of a default:
     `declassed:security-pii — <reason>`, which the adjudicator writes when a
     finding of the declared security lens is NOT of that class. The reason
     is free prose and may not be empty.
     AN EMPTY `verdict` CELL IS A STATE, NOT A DEFECT: the state "not
     adjudicated", which a fresh stage-5 layout carries by construction. It
     is exempt from that default, and the recount reports it as
     `not adjudicated: <n> rows` — the rows are non-terminal anyway, so the
     round stays unclosable on their account. The exemption is EXACTLY the
     empty case: a FILLED cell that says nothing about the class is the
     structural error it always was. -->

| id | sev | zone | claim (hook; canon = the report) | verdict | criterion | fix | verified | terminal |
|---|---|---|---|---|---|---|---|---|

## Readiness criterion (the `criterion` cell)

<!-- Written by the ADJUDICATOR, BEFORE any fix is attempted; the fixer
     may not change it. -->

- Record it as the scale level plus a short name, then the criterion
  itself: `L2 structural check — the removed wording no longer occurs in
  {file}`. Levels 1-7, see references/readiness-scale.md for the full
  scale.
- Pick the level by the ladder, not by feel; when in doubt take the LOWER
  level — an honest weak criterion beats a strong one nobody can satisfy.
- A criterion the fixer could satisfy by editing the very file that
  defines the check (test, scoring script, rubric) is invalid.
- "Improve it", "polish it", "make it clearer" are rejected at
  adjudication — these are not criteria.
- A criterion that turns out to be unsatisfiable becomes an
  `accepted-residue` with a one-line reason and the owner's signature —
  never a silent pass, never rewritten after the fact into an executable
  form it cannot honestly take. It gets there by the nomination route: the
  row waits in `awaiting-signature` with its register entry until the owner
  ratifies it.
- Refuted and refused rows carry exactly `—` here (deliberately not
  needed, as opposed to forgotten); an empty cell is banned for every row.

## Verification passes

<!-- The carrier of the convergence signal and of the kill criterion. -->

| # | pass (scope) | verdicts (L/P/NOT) | new findings | bundled | second-pass-skipped | notes | verifiers | started | ended |
|---|---|---|---|---|---|---|---|---|---|

New-findings curve by pass: computed by templates/recount.py from the
table above — quote the script's output here, do not hand-compute.
Convergence signal = two consecutive passes with 0 major and 0 NOT
LANDED. Kill criterion: no decay for three consecutive passes → stop,
fork to the user (the recount prints the warning). Beside that binary
streak — never instead of it — the recount prints the severity-weighted
plateau when it is given two `--prev` ledgers, and the advisory
residual-defect ESTIMATE whenever the header declares four lenses or
more. Both are reported numbers: neither enters the stop rule.

`bundled` = yes when the pass covered several micro-batches at once —
the regime the remainder moves to after the convergence signal; bundling
preserves PER-ID verdicts, and the switch is recorded in the round delta.
`second-pass-skipped` = yes when the round stayed under the soft
threshold of 20 findings and the second pass was skipped by default. The
threshold buys tokens, not correctness: the owner may ask for the pass
anyway, and from 20 findings up it is mandatory.

`verifiers` = how many verifiers the pass had: `1` for an ordinary pass and
`N` for a `lens-split verification pass` — one pass executed by N fresh
verifiers, each with its own non-overlapping scope of ids. The cell is a
COUNT and nothing more; which ids went to which verifier is the run folder's
record, not a ledger cell. It is written for every pass, because `1` is the
statement that the pass was NOT split, and the count is what makes a
too-small union of scopes visible at a glance. The column is inserted before
`started` / `ended` and is read by nobody mechanically: the recount finds
every column it needs BY NAME, and a column it does not know it ignores by
construction.

`started` / `ended` = the pass's own ISO-8601 UTC timestamps at seconds
resolution (`2026-08-11T10:16:04Z`), filled only when observability is on.
They are APPENDED as the last two columns and never inserted: the recount
finds `new findings` by column name and falls back to cell index 3, so a
v1 table without these two and a v2 table with them count identically, the
kill criterion keeps working on both, and an older recount reading a newer
table simply ignores the extra cells. Omit them entirely for a round that
ran with observability off — absence is not an error, and the recount then
says only that there is no time axis. A timestamp that is present but
unparseable is reported by name with the time axis suppressed; it never
changes the exit code, because a cost measurement must not be able to fail
a round on quality.

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
