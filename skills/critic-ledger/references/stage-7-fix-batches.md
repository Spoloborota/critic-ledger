Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 7 — Fix batches

The fixer is a SEPARATE subagent, one per batch, spawned
by the agent-type identifier `critic-ledger:fixer` (bare `fixer` where
unambiguous); the DEFINITION it dispatches to is
`${CLAUDE_PLUGIN_ROOT}/agents/fixer.md` (`opus` family, high effort), and
where no agent registry is available it is a general-purpose subagent
carrying that definition's constraints verbatim. Prompted
from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/fixer-prompt.md` — never the main loop that adjudicated,
so stage-8 verification is a different actor STRUCTURALLY and not by
organizational promise. It gets no git at all: with Bash absent from its
tool set the ban is mechanical, and the fixer only edits files.
**Batches run strictly sequentially, never in parallel.** Platform
subagents run in the BACKGROUND by default and report back later, so
sequencing does not happen by itself: the orchestrator MUST spawn the
fixer — and every other write-capable agent — strictly sequentially, and
only after its report has arrived AND the batch is committed
may the next batch start. Between batches the tree is confirmed quiet
with `git status`. Two write-capable agents over one tree is a measured
race, not a style preference: the reader of a file being rewritten under
it reports aggregate numbers it cannot stand behind.
The fixer reads and edits the WORKING TREE of the object's project; the
critics' scratchpad copy is not handed to it. Its edits must land in the
working tree or the orchestrator's post-batch commit is empty, and there
is no overlap in time to protect against — critics run at stage 3, the
fixer at stage 7.
A batch is ≤10 ids of TARGETED edits, coherent BY TARGET FILE: it is
assembled from findings that edit the same file; when one file carries
more than ten,
the batch is cut along that file's sections; findings requiring the very
same edit always go into one batch even when they came from different
lenses. Coherence by lens or by claim topic is NOT used — one lens's
findings are scattered across files, which is exactly what sequential
runs exist to avoid.
The prompt carries, per id: the finding's FULL salvaged text, the
adjudicator's verdict with its reasoning, the row's readiness criterion
word for word, and an explicit ban on changing that criterion — the main
defence against "the agent decided it was good enough".
**A DO-NOT-TOUCH fence in that prompt is traceable to THIS batch's plan.**
Any restriction narrowing where the fixer may edit is legitimate only
where the plan of the same batch carries the collision note it comes from;
a fence with no such note is an error of the ORCHESTRATOR, not a property
of the dependency graph, and it is lifted BEFORE the fixer is spawned —
never after the fixer has returned `criterion-unworkable` against it.
**The fixer's FIRST step on every id is to reproduce the defect in the
CURRENT text** and confirm the finding's premise still holds. Where it
does not — the text does not say what the finding quotes, the place is
gone, an earlier batch already changed it — the fixer does NOT edit and
returns the premise outcome below. A specification instruction can be
wrong and a competent fixer implements it faithfully: two coordinator
instructions in one field round were defective and both were carried out
exactly as written.
Back channel:
the fixer's final report returns exactly one outcome per id — `fixed`,
`criterion-unworkable` with a reason, or `premise-not-found` with a
reason; the orchestrator routes every `criterion-unworkable` AND every
`premise-not-found` id BACK TO STAGE 6, by the same route as a
verifier's new findings, never straight into the next batch.
Re-adjudication either redesigns the fix or the criterion (which by the
general rule RESETS that row's verified cell) or NOMINATES the row into
residue by the route of stage 9.
**Two returns per id, and the second one is not a third fix.** One id
travels the loop "stage 6 → fix batch → stage 7" at most TWICE, and the
two NON-TERMINAL back-channel outcomes count TOGETHER —
`premise-not-found` and `criterion-unworkable` are one counter, not two.
The first return is routine: stage 6 redesigns the fix or the criterion
and the id goes into a later batch. The SECOND return on the SAME id —
the same outcome or the other one, the criterion rewritten in between or
not — never gets a third attempt SILENTLY: the pipeline may not award one
by its own decision, and only the owner's explicit word can (recorded in
the ledger header). By default, meaning without that word, the row either
goes to the owner as a fork or is routed into accepted residue (the
nomination route of stage 9) by the disposition the contract declared.
The counter is kept PER ID, in that row's `verdict` cell as `returned:<n>`
— never against the wording of the criterion, or a redesign of the
criterion would reset it in silence. The reason this limit exists is
ours, reasoned and not measured: the kill criterion watches the
VERIFIER's new-findings curve across passes and cannot see a
fixer-adjudicator oscillation on one id at all, and class-kill catches it
only if the orchestrator recognizes two returns as one cause.
**A BLOCKER is excluded from the nomination half, exactly as at a fired
stop rule.** Nominating a blocker is banned outright (the recount refuses
`awaiting-signature` on a blocker row), so a second return on a blocker
row has exactly ONE route: its own fork to the owner. The owner either
awards the third fix attempt by explicit word (recorded in the ledger
header) or FREEZES the row and carries it into the next round. That word
of the owner's is the act the freeze header is written under: the
orchestrator writes the same literal stage 9 fixes,
`Stop-rule freeze: <ISO-date> | carried-to: <next run id | pending>` —
the date being the date of the owner's word, `carried-to` filled by the
stage-9 rules — and the row takes the same `frozen-carried (stop-rule,
<ISO-date>)` in its `terminal` cell. This holds even when the contract's
stop rule never fired: the freeze here is per-row, but its header field
and its status are the ones already defined, no new literal is coined,
and the row therefore passes the structural check unchanged (a
`frozen-carried` row with no `Stop-rule freeze:` field is a structural
error). Where the field ALREADY stands from an earlier freeze, it is not
rewritten — stage 9's collision rule holds here too: the header keeps the
first date and this row carries its own in its `terminal` cell. An
exhausted blocker has NO silent route.
Where observability is on, that fork is a recorded wait and not only a
header line: the orchestrator opens an `owner-wait-authorization` span
when the question is put to the owner — the third fix attempt here, and
by the same reason the word that continues a round past a fired stop rule
(references/stage-9-closure.md) — and closes it on his word, the outcome
`answered | refused | abandoned`.
**`NOTICED OUTSIDE BATCH` — the fixer's channel for what it saw beside
its work.** The fixer may not fix anything outside its batch, and it is
equally forbidden to swallow what it noticed there. Its report therefore
closes with a block under that exact heading: one entry per observation,
each with `file:line` and what was observed, written under an id prefix
the ORCHESTRATOR fixes at stage 2 alongside the lens prefixes and under
the same id contract. This is a REPORT BLOCK, not a per-id outcome: the
outcome vocabulary of the back channel above is untouched by it, no entry
of the block attaches to an id of the batch, and an empty block is
written as `none` rather than omitted. The block's contents travel to
STAGE 6 as new findings, by the same route a verifier's new findings
take — never straight into the next fix batch, and never into an edit the
fixer makes on its own authority. At that adjudication such a finding —
NOTICED origin, not a blocker, no `origin:fix-application` tag — may take
the fourth nomination occasion of stage 9 (references/stage-9-closure.md)
into the residue register instead of a fix batch.
The BATCH-COMMIT EXECUTOR fixed at stage 2 commits after EVERY batch — ids
in the commit message, the commit hash into the fix cells immediately.
**The `fix` cell is written with the canonical writer, never by hand:**
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/set-cell.py --ledger <ledger> --id <id> --column fix --value "<text>"`,
one call per cell. It addresses the row by id, takes the row width from
the ledger's own header, splits on the raw `|` instead of on `" | "` —
the split that twice lost a row's empty trailing cells in the field —
refuses a value carrying a pipe or a newline, and prints `OK <id>.<column>`
for the write it made, so the twenty silent no-ops of another round
cannot recur: a run that writes nothing exits non-zero.
That executor is the ORCHESTRATOR by default; in `impl` mode it is the
target project's convention, and where that convention is PR mechanics the
fix cell holds the PR LINK and the row stays NON-TERMINAL until the merge;
in DEGRADED mode (no commit sanction, stage 0) it is `none` and the fix
cell references the uncommitted working state. Wherever commits exist they
are mandatory: the stage-8 deleted-line walk runs on them.
**A criterion that requires EXECUTION is executed by the orchestrator,
never by the fixer.** The fixer has no Bash at all, so a criterion of
class L1 of the readiness scale — a suite, a linter, a script, any bar
that is a command and its exit code — is one it structurally cannot
satisfy. Executing it is an obligation of the round, and it falls on the
ORCHESTRATOR or on a subagent named by the same pattern as every other
executor of this skill: the agent-type identifier
`critic-ledger:verifier`, the DEFINITION it dispatches to
`${CLAUDE_PLUGIN_ROOT}/agents/verifier.md`, and where no agent registry
is available a general-purpose subagent carrying that definition's
constraints verbatim. The moment is fixed: BETWEEN the fixer's report and
the batch commit, never after it. What the run produces — the exact
command and its exit code — goes into that row's `fix` cell beside the
commit hash. This is a duty, not an option: a batch carrying a class-L1
criterion that was not executed before the commit is NOT closed by that
commit. The same actor at the same moment performs the batch's READ-BACK
— re-reading the changed region against the post-condition the batch was
spawned under, which is what that word means here and the only sense it
carries in this document. A read-back is the difference between "the edit
is on disk and says what it had to say" as a checked fact and as the
fixer's claim; a field round had to escalate exactly this to an actor
with a shell, because the fixer could not run it.
**Class-kill: the second recurrence stops fixing and builds a gate.**
The recount counts upheld rows per `class:` slug and prints
`CLASS-KILL DUE: <slug>` from two of them. The orchestrator's reaction
is obligatory, not a right: the next step for that class is NOT one
more fix but a mechanical gate — a grep or a script in the round's
toolkit — or a convention in the object that kills the class, and the
gate itself is entered as its OWN ledger row, a `class-kill` finding
with its own id and its own terminal path. Where the criterion of an
ALREADY EXISTING row of this round pins the convention that kills the
class, the class-kill disposition instead closes by reference to that
criterion — no new gate script and no separate row — and an orchestrator
entry naming the DONOR row goes into the ledger. The reaction stays
obligatory: what changes is the form it takes, never the right to skip
it. A third recurrence with no
kill in flight escalates to the user, and the class's fix batches stop.
The "second recurrence" number is OURS, Tricorder-shaped: no standard
supplies it, and it is written here as ours rather than borrowed.
**The kill in flight is PRINTED, not remembered.** The gate's own ledger
row carries `class-kill:<slug>` in its `verdict` cell, naming the class
that gate kills, and while that row is not terminal the recount prints
`kill in flight: <slug> (<id>)` beside the class counts. That is how a
reader sees whether the third recurrence's escalation applies, instead of
taking someone's word for it. It is a state line like the counts around
it and changes no exit code; a ledger carrying no such tag prints nothing
there. The counts themselves read one more marker: a `class:security-pii`
set by the security-lens default is the lens's signature mode and counts
toward no kill unless the same cell carries `class-origin:adjudicator`
(stage 6).
**The gate's executable form: `gates/<K-id>.sh` in the round folder.**
Where the kill is a script rather than a convention, the script is a file
of the round, `gates/<K-id>.sh`, named for the class-kill row it belongs
to and to no other row: this is the FILE FORM of that row, not a second
kind of thing called a gate. A `gates/<K-id>.sh` with no `class-kill:`
row carrying that id is a structural error of the convention — the row
is what makes the script's verdict readable — and so is a second row
claiming the same file. The outcome of running it is written into the
gate row's `verified` cell in the form the closure already reads:
`LANDED — gate <K-id>.sh OK` when the gate passes, and
`NOT LANDED — gate <K-id>.sh FAIL` when it does not. The literals are
not free choices. The recount requires the substring `LANDED` in the
`verified` cell of a `verified-landed` row and refuses `NOT LANDED` or an
empty cell as non-terminal, so a bare `GATE OK` would leave the gate's
own row non-terminal — the round unclosable on the very thing that
killed the class. Both forms above are read by that contract as it
stands, without one edit to it.
**What the gate covers and when it is re-run.** The gate covers ALL
surfaces of the deliverable — the source, the commit bodies, the
documentation, the PR description and the round's own scope contract —
and not only the file the class was first noticed in. It is re-run
AFTER EVERY BATCH, over the artifacts the round itself produced as much
as over the object. An instance of the class produced by a fix of THIS
round counts as a recurrence like any other: the class-kill counter
sees it. All three were observed in field rounds, not reasoned into
existence.
**Stopping the batching disposes of the class's open rows, here and
not later.** When the class's fix batches stop, EVERY ledger row
carrying that `class:<slug>` without a terminal status goes BACK to
stage 6 for RE-adjudication in the light of the gate that was built (or
that is missing) — an obligation of the orchestrator, not a right. Each
such row is then routed by its own severity: a blocker closes only
through the gate or through a fix, and until one exists the row stays
open and the round unclosed; a major is either covered by the gate's
own row and closes with it, or is NOMINATED into residue by the route
of stage 9 — which is where the fresh verifier's look on a major
nominee lives, and where a negative look sends the row back here; a
minor takes the same nomination route. A row whose defect the gate
removed mechanically closes by REFERENCE to the gate, not by one more
hand-made fix — that is what stopping the batching is for. Leaving a
row of the class silently hanging open is banned: it holds a terminal
status, or a nomination waiting in `awaiting-signature`, or an explicit
note that it waits for the gate.
**Injection rate, and what it may and may not do.** The recount also
prints, per batch, the share of `origin:fix-application` findings
charged to that batch over the number of rows the batch fixed — the
rows carrying that same batch identifier in their `fix` cell, matched
literally; the ledger's "Batch deltas" prose is a historical snapshot
and is not read as a membership table. A tagged row with no readable
`from:` is listed separately as unattributed rather than lowering the
share in silence, and a batch identified by neither a hash nor a
snapshot name gets `n/a` rather than an invented denominator. Two
CONSECUTIVE batches at 7% or above print `INJECTION RATE HIGH` with a
recommendation to stop the batching. That literal is deliberately not
the class-kill one and its weight is different: `CLASS-KILL DUE`
obliges the reaction above, while `INJECTION RATE HIGH` is a printed
metric and obliges exactly one thing — put the fork to the user, whose
call the stop is. Printing `CLASS-KILL DUE` off the injection threshold
is banned: one literal, one weight of compulsion. 7% and 3.5% are
literature reference points (undisciplined and disciplined floor),
marked as such in the output and never as our own measurement.
Rewrites are banned; if a fix REQUIRES rewriting the artifact: the
ORCHESTRATOR freezes the ledger by setting
its `Ledger state:` header line to
`FROZEN (superseded-by-rewrite, <date> + reason)` — rows keep their
current statuses, a frozen ledger is never closable (the recount
reports it as a distinct state). The rewritten artifact is a NEW
object and a new full round, and the adjudicated-but-unlanded ids
enter the new round's disposition.
**With observability on**, append one `fixer` span per batch with its
`ids`, the batch's `commit`,
`outcome: fixed:<n>,unworkable:<m>,notfound:<k>`, and
the same tool-result capture as stage 3. All THREE of the fixer's
per-id outcomes are counted there: `notfound:<k>` carries the
`premise-not-found` returns, which without it are the one outcome no
number records. The `flags` of that span are written and not left
empty by default: `respawn` where this batch's fixer was spawned again
after a failed run, `degraded` where its result was accepted knowing
it was partial, `criterion-unworkable` where an id came back with that
outcome. A flag nobody sets is a flag nobody can read afterwards.
Output: batch committed, fix cells
filled.
