Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 6 — Adjudication

Main loop, never a subagent — a subagent has neither
the project's context nor the user's earlier rulings.

### 6.1 Batches inside a lens

**Batches of at most 10, nested inside a lens.** After every batch the
verdicts are appended to the ledger on disk immediately. A batch NEVER
crosses a lens boundary: a lens is taken whole — its report header and
coverage statement are read ONCE per lens, separately from the finding
blocks, otherwise what the critic never touched stays unknown — and only
then its findings are cut into batches (a lens with 15–20 findings gives
two). Ten is a CEILING against instruction-count degradation, not a
packing quota: an underfilled batch is free, mixing two lenses' context
is not, and small lenses are never merged into one batch. Order: inside
a lens the findings are sorted blockers → majors → minors BEFORE the
cut, and lenses are taken in descending order of their worst finding's
severity. That is how "blockers first" survives — as an ordering rule
inside "lens → batches", with no separate sweep: every blocker is judged
as early as possible without re-reading headers, and an early stop (a
freeze for a rewrite) arrives before effort is spent on minors. The
batch size exists because instruction-following degrades with the NUMBER
of simultaneous tasks, not because the context window fills up.

### 6.2 What is read

**What is read**: the FULL block of the finding — claim, evidence,
command and its output — never the header line alone; a header is not
enough to judge on. Blocks are read POINTWISE: locate the finding in the
salvage file by its id, then read the narrow fragment, not the whole
file. Findings may reference each other, and the adjudicator MUST pull a
cross-referenced block even when it lies OUTSIDE the current batch. If
the session was compacted, re-read the reports from disk before
continuing.

### 6.3 Re-grounding after a compaction

**Re-grounding has one more FIRST action, and it is an instruction rather
than a consequence of anything else.** After a compaction and at the
start of a new session the orchestrator restores from the LEDGER what the
round is waiting for from the owner, and records the outcome his word
gave — `answered`, `refused` or `abandoned` — in the row that names the
wait. Where the owner's word has still not come the wait STAYS recorded
as open: that is the honest "the wait continues" and not a lost record.
Left unrecorded after the word HAS come, a round that survived a
compaction becomes indistinguishable from one that was abandoned.

### 6.4 The precedents file

**Precedents file**: repeated rulings are written to
`{run-folder}/precedents.md` so the ninth batch does not judge against
the first one's grain and a resumed session can pick the round up. The
ORCHESTRATOR creates it at the FIRST adjudication batch — the first line
of the file names why it was opened (a repeated ruling, or the record of
6.13 that no class matched) — never before stage 6 and never empty;
it stays terse — the repeated rulings, the records of 6.13 and their
reasoning only, never raw finding text, which is always addressable by id
on disk. Limit: 200 lines or 25 KB, checked on every append; reaching it is
the signal to MERGE repeats into one precedent, never to drop the tail
silently.
In the same step the ledger header's `Precedents file:` field is set to the
file's path, written with `scripts/ledger_md.py set-header`, never by hand.
Before adjudicating a new refutation the orchestrator checks the run's own
`precedents.md`: the file is an INPUT document of the round, not only an
output. Reading it costs one narrow read and is what keeps the ninth
batch's refutation on the grain of the first one's.
A precedent that NARROWS or re-aims a gate AFTER that gate has fired
carries, in the same act that writes it, the exact grep or `file:line`
evidence for the ground it states: an asserted collision, an asserted
duplicate, an asserted overlap is not a ground until it has been
re-derived from the object's own files. The rule is kept strict here
because this file is the part that could launder a wrong call, and a
narrowing justified by a fact nobody measured is that call.
Where the precedent written here IS the convention that kills a defect
class — the donor convention the class-kill disposition of
`references/stage-7-fix-batches.md` closes by reference to — the explicit
`class-kill:<slug>` row of the ledger is written in the same step, in the
same act as the precedent and never left for later. The recount reads
the LEDGER and not this file, so a donor convention recorded here alone
leaves the class printed as still due, and the kill that is actually in
flight stays invisible to every reader of the counts.

### 6.5 Verdicts are refute-by-default

Verdicts: from the FULL reports (never from summaries),
refute-by-default; verdicts go into the ledger row by row (one id per
row, ranges banned); a finding of the security/PII class is MARKED as
such here, when it is ruled on and never retroactively, and BOTH of its
outcomes — "accept as is" and "refuse" — need the user's signature to
become terminal (the old "re-check security/PII refutations by hand" is
gone: the same actor re-checking its own refusal was self-verification,
not added rigour); minors may be batch-verdicted but every id keeps its
row — the batch of 10 is a unit of READING and does not forbid one
verdict covering several minors.
A row of NOTICED origin — what a fixer reports through the
`NOTICED OUTSIDE BATCH` block of 7.15 of
references/stage-7-fix-batches.md — is adjudicated under this same
refute-by-default rule, exactly as a lens critic's row. That a FIXER
raised it is not vetting and earns it no exemption: it is upheld from its
own evidence or refuted, like every other id.
The `verdict` cell is written with `scripts/set-cell.py --column verdict` by
the orchestrator through Bash, one call per row (the act is 7.17 of
references/stage-7-fix-batches.md; the script's contract is
references/templates-and-scripts.md).

### 6.6 User decisions given in chat

User decisions given in chat are encoded as
pre-adjudication with a mark; a conflict between a pre-adjudication and
a blocker finding → re-present to the user, never silently pick.

### 6.7 A design fork goes to the owner

A design fork goes to the owner: it is never closed by an adjudication
verdict. Adjudication rules on whether a claim holds, not on which of two
legitimate designs the object should have.

### 6.8 The fork is a recorded wait

Every fork put to the owner before an adjudication — and equally the
escalation the recount demands with `OWNER FORK REQUIRED` — is a recorded
wait: the question put to the owner and the outcome his word gave are
written into the row's ledger cells and its disposition note, so the wait
is readable from the ledger itself.

### 6.9 The independent re-check of a security/PII ruling

A `class:security-pii` ruling is re-checked blind by another actor before
the owner signs (6.15) — where the pre-adjudication is the owner's own, the
ruling actor of record is the owner, so the re-check is made by an actor
other than him.

### 6.10 Cross-lens duplicates — the "=id" convention

Cross-lens duplicates are deduplicated here via the "=id" convention:
the verdict references the primary id, one fix, every id keeps its row;
a duplicate row's criterion cell carries `=<primary-id>`, optionally
followed by a short gloss (never a bare dash — the recount's
consistency check reserves the dash for refuted rows).

### 6.11 Class tags and the recurrence check

**Class tags, and the recurrence check that makes them appear.**
Upholding a finding, the adjudicator MAY tag its `verdict` cell
`class:<slug>`, naming the defect CLASS by judgment — no taxonomy is
prescribed. The tag is MANDATORY from the SECOND finding the
adjudicator itself reads as a recurrence: same root cause, same shape
of evidence. The slug is free in MEANING but not in alphabet, or it
could not be lifted back out of the prose: `[a-z0-9-]`, 1-32
characters, ended by the first character outside that alphabet (a
space, a comma, a dot, a `|`, the end of the cell). Capitals, spaces,
dots, slashes and underscores are banned, and a `class:` written any
other way — `class:Foo`, `class:.x`, a slug past 32 characters — is a
structural error of the recount rather than a guess at where the slug
stops. A `class:` followed straight away by a space, a `|` or the end
of the cell is ordinary PROSE, not a botched tag: it is ignored and
groups nothing, because a tag never attaches its slug across
whitespace and because ledgers written before this tag existed carry
such sentences and must keep recounting unchanged. Grouping is by
EXACT slug: nothing is normalized, so one class keeps one literal.

### 6.12 The staleness sweep before fix batches

**Before the FIRST fix batch the object is swept for staleness, ONCE and
mechanically.** Counters, labels and citations inside the object rot as
the object is edited: a `path:line` citation that has moved, a count that
states a number the object no longer has, a label naming a section that
was renamed. None of that is a critic's find — no lens is asked to
recount the object — so it reaches the round only if the orchestrator
looks for it deliberately. The sweep is ONE mechanical probe run by the
orchestrator through Bash — a `grep` over the object's counters, its
labels and its `path:line` citations — and it is run BEFORE the first
batch is formed, not after the fixes have moved the same lines again.
Its findings enter the ledger as NOTICED rows in ONE wave, each carrying
the probe command in its `criterion` cell, and are batched afterwards by
the ordinary rules of stage 7; nothing is repaired inside the sweep
itself, which is a reading step and not an editing one. A sweep that
finds nothing is still recorded as having been run, as one line in
`{run-folder}/precedents.md`, so that a later reader can tell a clean
object from a skipped step.

### 6.13 The trigger's honest boundary

**The trigger's honest boundary.** There is no mechanical detector of
recurrence here — no text similarity, no claim hash — and this release
does not undertake to build one, so class-kill works exactly as far as
the adjudicator's discipline with the tag goes: a tag never set means
the trigger never fires and the whole mechanism stays silently unused.
That is admitted, not masked. The compensation is procedural, not
scripted: in EVERY adjudication batch, before the batch is closed, the
orchestrator compares each upheld finding's root cause and evidence
shape against `{run-folder}/precedents.md` and against the `class:`
slugs already in the ledger; a match obliges the SAME slug (a new one
is never coined), and no match is recorded in `precedents.md` as a line
saying the check was made. The step is manual and stays manual; skipping
it is a defect of adjudication, visible as the missing record.

### 6.14 The security/PII class mark — one fixed literal

**The security/PII class mark is ONE fixed literal, and it lives in the
ledger.** That literal is `class:security-pii` in the `verdict` cell,
read by the same anchoring as every other class tag. It goes in the
LEDGER, which always exists. Here the tag is stricter than the
general rule above: the adjudicator sets it on EVERY finding of the
security/PII class, from the FIRST one and regardless of recurrence,
because every check keyed on this class reads that literal and nothing
else. `class:security`, `class:pii` and `class:sec-pii` are different
classes and none of them counts as the mark; the slug `security-pii` is
reserved for this class and carries no other meaning.

### 6.15 The re-checker is blinded

**Marking the class here ARMS an independent re-check, and the re-checker
is blinded.** Before a ruling on a `class:security-pii` row — a
REFUTATION exactly as much as an acceptance — is put in front of the
owner for signature at stage 9, it is re-checked by an actor or a tool
OTHER than the one that ruled: a fresh read-only `sonnet`-class agent, or
a deterministic check where the claim is mechanical. This is not the old
same-actor re-check that was dropped as self-verification; the whole
content of the rule is the difference in actor. The re-checker gets the
critic's ORIGINAL finding verbatim from the salvage, the object, and the
row's class mark — and NOT the rationale of whoever ruled. It reaches its
own conclusion first; the ruling's reasoning may be shown to it only
after that conclusion is recorded. The ruling and the re-checker's prompt
reach it as SEPARATE files or reads, never as one file with a conditional
section. The reason is the verifier's at stage
8: human labelers shown a verdict they had disagreed with were willing to
change their vote about a third of the time (Zheng et al. 2023,
arXiv:2306.05685, §4.2 — a side observation of that study); exposure to a
verdict moves the reviewer, and a security checkpoint is the last place
to spend that third. The conclusion travels with the signature request and is written
into the row (and into the register row where the finding was nominated);
a re-check that disagrees is put to the owner AS a disagreement, never
smoothed into the ruling.

### 6.16 The backstop against a mark nobody set

**The backstop against a mark nobody set.** The checks below see only the
row where the mark IS written; a finding never classed at all is
invisible to them by construction, and classing is a judgment made once
and never retroactively. So the mark has a machine-checkable DEFAULT: a
finding raised by the lens the contract declared the SECURITY LENS (stage
2(b), carried in the header's `Security lens:` field) is of the
security/PII class by default — the adjudicator writes
`class:security-pii` on it without deciding the question again. Removing
the default is allowed and takes writing, in that same row's `verdict`
cell: `declassed:security-pii — <reason>`, the reason free prose and never
empty. A row of the security lens carrying neither the class nor a
reasoned declass, and a `declassed:` with an empty reason, are structural
errors of the recount. Completeness is NOT claimed: a security-relevant
finding can come from another lens and marking it stays the adjudicator's
judgment — a known limitation of this release. What is closed is the main
path around every gate this class has, not every path.

### 6.17 The default is not a recurrence

**The default is not a recurrence, and the difference is written.** Because
the backstop puts `class:security-pii` on EVERY row of the declared security
lens, that slug there names the lens's signature mode and not a defect class
that recurred; a class whose every member carries the default counts toward
no class-kill of stage 7. Where the adjudicator means the CLASS itself, it
says so in the same `verdict` cell — `class-origin:adjudicator` beside the
tag — and only those rows are counted for the kill. The marker changes
nothing else: an explicit `class:security-pii` arms every check keyed on
that class exactly as before, and the recount's census line still counts
every tag.

### 6.18 An empty verdict cell is a state

**An empty `verdict` cell is a STATE, not a defect.** A stage-5 layout
carries findings rows whose verdict cells are still blank; that state is
"not adjudicated", it is exempt from the backstop, and the recount reports
it as `not adjudicated: <n> rows` instead of refusing to recount. The rows
are non-terminal anyway, so the round stays unclosable on their account and
the exit code is the ordinary one for open rows. The relaxation is EXACTLY
the empty case: a FILLED cell that was written and left the class out is the
structural error it always was — a judgment made, not a judgment pending.

### 6.19 The contract's terminal status

**The contract's own terminal status is assigned here.** A finding whose
claim is WHOLLY covered by a declared Non-Goal takes
`out-of-scope-by-contract (NG-<n>, signed <date>)` — the Non-Goal named,
and the date being the date the CONTRACT was signed, not today's. No live
signature is asked for: it was given when the Non-Goals were authored.
"Wholly" is the whole test — a finding that merely touches a Non-Goal is
adjudicated normally. ONE exception: a row marked `class:security-pii`
never leaves through a Non-Goal on the pre-signature alone. That class
needs the owner's live word for BOTH of its outcomes, so such a row
carries `user-signed <date>` of its own beside the contract literal or it
is not closed at all, and the recount treats the combination without a
live signature as a structural error.
A row nominated into the residue takes its terminal form at stage 9, and
the form is a LITERAL — `accepted-residue user-signed <date>` — so a row
written here with the bare word is caught by every recount run;
9.21 owns the ratification and this line only names the literal.

A row closed BECAUSE THE OBJECT'S OWN SIGNED TEXT PRESCRIBES what the
finding objects to — and not merely because a Non-Goal declines the
topic — carries one more literal in its `verdict` cell,
`spec-delta-candidate`, beside whatever terminal status it took:
`refuted-with-reason` as much as
`out-of-scope-by-contract`. The finding is disposed of for THIS round and
the tag changes no status, blocks no closure and is read by no script;
what it buys is that the closure prints the question back to the object's
author (9.17) instead of losing it. It is not the `shelf:` tag of 6.24 —
a shelf names a pre-signed disposition that declined the topic, this
names the object's own prescription of the behavior objected to.

### 6.20 The zone cell is filled here

**The ZONE cell is filled here, from the map and not by feel.** Every row
gets its `zone` — `Z1`, `Z2` or `Z3` — off the ledger header's zone map
(stage 2), for the section of the object the finding lands in, replacing
the `·` transcription left. A genuinely disputable zone is the
adjudicator's call and the ruling goes into `{run-folder}/precedents.md`
like any other repeated ruling.
The cell is written with `scripts/set-cell.py --column zone` by the
orchestrator through Bash, one call per row (the act is 7.17 of
references/stage-7-fix-batches.md; the script's contract is
references/templates-and-scripts.md).

### 6.21 What a zone changes — paper and closure route

**What a zone changes is the PAPER and the CLOSURE ROUTE, never the
strictness of a check.** `Z1` and `Z2` run the existing pipeline
unchanged. Severity is neither renamed nor lowered by a zone: a BLOCKER
found in `Z3` means the zone MAP was wrong — the row is re-zoned, the
ruling is written to precedents.md, and the process is not walked around.
The one route a zone opens is `logged-no-action` for a `Z3` row: the
finding is logged, no action is taken on it, and it closes in a batch the
owner signs off in ONE act — the mechanism is stage 9's, alongside the
ratification batch it is modelled on. Putting the row into that batch is
not itself the closure: until the owner's act the row carries the named
non-terminal `awaiting-logged-no-action (listed <date>)`. And the
security/PII exception above holds here WORD FOR WORD — a row marked
`class:security-pii` never travels inside the batch act, so
`logged-no-action` on such a row without its own live `user-signed <date>`
is a structural error of the recount, exactly as it is under
`out-of-scope-by-contract`.

### 6.22 A NOTICED finding's severity gate under a profile

Under ANY profile a NOTICED finding ruled major or blocker keeps the route
its severity gives it, and no profile shortens it: an upheld major is
never left to the tail wave of 7.7 — it enters the next fix batch, unless
one of the two routes this process already opens takes it instead, the
`logged-no-action` of 6.21 for a `Z3` row or the fourth occasion of
references/stage-9-closure.md 9.19, each on its own conditions and
neither of them a profile's doing. An upheld blocker takes the blocker
route of 7.14, and neither of those two routes is open to it. What a
profile compresses is the number of passes and batches (the profile's
thresholds are stated at stage 2), never the route of a major or a
blocker.

### 6.23 A finding caused by an earlier fix

**A finding caused by an earlier fix is tagged where the metric can
read it** — in the ledger, which always exists. A verifier finding whose
substance is a defect in APPLYING an earlier fix gets
`origin:fix-application from:<batch>` in its `verdict` cell, where
`<batch>` is the identifier of the batch whose fix was applied
defectively: the value of that row's `fix` cell (the per-batch commit
hash), or the batch's snapshot-path name in DEGRADED mode. Without the
`from:` reference the injection metric of `references/stage-7-fix-batches.md` has no numerator, so the
adjudicator writes it HERE, taking it from the row whose fix it has
just ruled defective; the `origin:` tag takes the slug alphabet and
terminator of 6.11, widened to 40 characters. A tag whose `from:` cannot be read
counts as unattributed and is never charged to the latest batch by
guess.

### 6.24 A refutation the contract closed — the shelf tag

**A refutation the contract itself closed may say so — the `shelf:`
tag.** Refuting a finding whose claim a pre-signed disposition of the
round contract closes WHOLLY, the adjudicator MAY tag the `verdict` cell
`shelf:<slug>`, the slug naming that disposition (`shelf:ng-2`). It is
OPTIONAL, it changes no status, and its whole purpose is arithmetic: the
recount prints the share of a lens's refutations that carry it beside
that lens's sustained rate at stage 9, so that a lens is never judged by
the rate alone. Alphabet, boundary and prose rule are the `class:` tag's
of 6.11, unchanged. It is set on a REFUTED
row: a shelf closes a claim, it does not uphold one.

### 6.25 The readiness criterion

**Every upheld finding gets its readiness criterion HERE, before any fix
is attempted**, written by whoever adjudicated: the scale level plus the
criterion itself in the row's `criterion` cell, the level picked off the
ladder and the LOWER level taken whenever in doubt. A refuted or refused
row carries exactly the em-dash `—`; an empty cell is allowed to nobody.
"Improve it / polish it / make it clearer" is not a criterion and is
rejected right here, and a criterion the fixer could satisfy by editing
the very file that defines the check is invalid.
A criterion is SCOPED to the object's own declared paths and never to a
containing directory: a grep or a count aimed at the directory measures
text no fix of this round may touch, and its target then cannot be
reached however complete the fix. Where the FINDING's own claim carries a
universal quantifier — "every", "all" — the criterion is a mechanical
completeness check over the whole matching set, never a list of literals
the adjudicator sampled: the sample is satisfied, the finding closes, and
the rest of the set stays defective.
The cell is written with `scripts/set-cell.py --column criterion` by
the orchestrator through Bash, one call per row (the act is 7.17 of
references/stage-7-fix-batches.md; the script's contract is
references/templates-and-scripts.md).

The FORM of a criterion that carries a number, a literal or a code is a
command and its printed result — `grep -cF '<literal>' <file>` → `<n>`,
an exit code, a count — with no pipe inside the literal: a pipe is never
escaped as `\|` there, because the cell writer of 7.17 refuses any
pipe, so such a literal is rephrased; the DRAFT criterion is run against
the real text of the object BEFORE the row is handed to a batch, and a
draft that prints the wrong number is rewritten here, not discovered by
the fixer (this is a check of the draft, distinct from 6.26 where the
probe itself becomes the criterion). A criterion pinning a rule for later
readers is written in its KILLING form — a rule that names content, never
a date, a count of occurrences or a list that rots.
Against a hard-wrapped prose object the default form of a phrase-presence
check is WRAP-TOLERANT, because the object's own line breaks split a
phrase that a plain `grep` then reports absent:
`tr -s '\n ' ' ' < <file> | grep -cF '<literal>'` → `1`, the squeeze
load-bearing because `tr '\n' ' '` alone leaves the indent spaces
standing at the wrap point. Two limits of that form are named here rather
than rediscovered by the next round that needs them. First, the collapse
makes the whole file ONE line, so `grep -c` after it prints only `0` or
`1` and can never say "twice": a criterion asserting N occurrences counts
occurrences instead —
`tr -s '\n ' ' ' < <file> | grep -oF '<literal>' | wc -l | tr -d ' '` →
`<n>`, the last filter there because BSD `wc` pads its count.
Second, a pattern that itself begins with a dash needs the argument
terminator before it, or grep reads it as an option it does not have —
`grep -cF -- '--agent-receipt' <file>` → `1`.
Such a command carries a shell pipe and the cell writer of 7.17 refuses
one, so it is recorded the way 9.7 of references/stage-9-closure.md rules
a mechanical check — the command saved as a script beside the ledger —
and the `criterion` cell names that script and the result it must print.
Where the criterion carries a number or a code, the value that draft run
printed is written into the row's finding block handed to the fixer: it is
the input of the fixer's measured edit (step 3b of
`templates/fixer-prompt.md`), which never estimates such a value.
An ABSENCE criterion — "X no longer occurs", "the wording is gone" —
names its two failure modes before it is written, because each of them
leaves the fix landed and the check red. The NEGATION trap: a corrected
object that restates the claim as "is not X" still carries X, and a bare
substring search matches inside the negation. The KEPT quotation: X may
legitimately survive elsewhere in the object — a historical note, a dated
figure, a quoted owner ruling — and a criterion banning the string
outright then contradicts the fix it is checking. So the check is written
against the OPERATIVE place, anchored to the structural region that
excludes explanatory and historical text, and never as a bare absence of
the string over the whole object.

### 6.26 probe-to-criterion

**One route to a criterion has a name, because it recurs.** The
orchestrator's own probe run before adjudication is named
`probe-to-criterion`: the probe becomes a class-L1 criterion, and the
verifier re-executes it live. Nothing new is built for it — the command
the orchestrator already ran to test the claim is written into the
`criterion` cell as the level-1 criterion it is.
Where the confirm-or-kill of such a probe is EXECUTED by a spawn rather
than by the orchestrator itself, that spawn is the `critic-ledger:executor`
agent. In either mode, a probe whose command would have to mutate the
live object never becomes a probe-to-criterion: a class-L1 criterion of
that kind is run by an executor at the moment 7.18 fixes, as the readiness
scale states.

In `impl` mode the executor of a critic's confirm-or-kill commands starts
as soon as that critic's report is salvaged — spawned at that moment where
it is an agent — while other critics may still be running, and is never
held until the last report: one executor per arriving report, its output
attached to the findings it belongs to.
Between the salvage and the run stands the
orchestrator's READ of every command in the report against the bound of
stage 3: a command that would touch anything outside its scratch copy is
not run and goes back to its finding as `UNVERIFIED`, the reason named.
A critic's command may also be MALFORMED in itself — an argument the
object's own grammar requires and the critic left out — and what such a
command then prints is a fact about the REPORT, not about the object. No
input grammar is declared for an object anywhere in this plugin, and none
is owed: the sanctioned path is the executor's own correction rule of
`${CLAUDE_PLUGIN_ROOT}/agents/executor.md`, which runs the corrected form
once, keeps both outputs and NAMES the correction, with the
criterion-command exception that same rule states.
Running those commands is not adjudication: the stage-4 rule that
adjudication does not begin until the last expected report is saved
stands, and the outputs wait under `probes/` until it begins. Each
executor runs on a scratch copy made for its report's commands, never on
the copy the critics are reading — one executor at a time against any one
tree. That copy is made by the ORCHESTRATOR, with
`scripts/copy-project.sh`, at
`<scratchpad root>/critic-copies/<object-slug>/<copy-id>` with
`--run-id <copy-id>` — the
orchestrator creating the parent of that path first, because the script
refuses a `--dest` whose parent does not exist and creates only the last
segment — and handed to the executor by path; the
orchestrator removes it after the executor returns with
`scripts/cleanup-scratchpad.py --root <scratchpad root> --manifest <that copy's manifest> --confirm`,
after the same call without `--confirm` has printed the plan — without it
the script deletes nothing — and the closing call of stage 9 removes any
such copy still standing; where the executor is a spawned agent, the
executor never makes or removes it.

### 6.27 Zero-confirmed branch

Zero-confirmed branch (everything refuted or nothing found): skip
stages 7–8 and the loop-and-convergence part of stage 9, go straight to
its closure part.

### 6.28 A design fork needs fork-research first

### 6.30 Output

The round's profile is ASSIGNED at the close of this stage by the rule of
2.4 of references/stage-2-scope-and-lenses.md and written into the ledger
header's `- Profile:` line.

Output: every id has a verdict and a
non-empty criterion cell.
