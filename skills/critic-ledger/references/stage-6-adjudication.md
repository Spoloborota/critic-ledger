Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 6 — Adjudication

Main loop, never a subagent — a subagent has neither
the project's context nor the user's earlier rulings.
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
**What is read**: the FULL block of the finding — claim, evidence,
command and its output — never the header line alone; a header is not
enough to judge on. Blocks are read POINTWISE: locate the finding in the
salvage file by its id, then read the narrow fragment, not the whole
file. Findings may reference each other, and the adjudicator MUST pull a
cross-referenced block even when it lies OUTSIDE the current batch. If
the session was compacted, re-read the reports from disk before
continuing.
**Re-grounding has one more FIRST action, and it is an instruction rather
than a consequence of anything else.** After a compaction and at the
start of a new session the orchestrator checks the round's `trace.jsonl`
for an owner-wait span left open and closes it with the outcome the
owner's word gave — `answered`, `refused` or `abandoned`. Its `started`
is copied off the disk record by `templates/trace.py` itself, so the
duration of the wait survives the gap instead of restarting with the
session. Where the owner's word has still not come the span STAYS open:
that is the honest "the wait continues" and not a lost record. Left open
after the word HAS come, it is the opposite — an `open` with no close
reads as a round interrupted, and a round that survived a compaction
becomes indistinguishable in the trace from one that was abandoned.
**Precedents file**: repeated rulings are written to
`{run-folder}/precedents.md` so the ninth batch does not judge against
the first one's grain and a resumed session can pick the round up. The
ORCHESTRATOR creates it at the FIRST repeated ruling, never in advance;
it stays terse — the repeated rulings and their reasoning only, never
raw finding text, which is always addressable by id on disk. Limit: 200
lines or 25 KB, checked on every append; reaching it is the signal to
MERGE repeats into one precedent, never to drop the tail silently.
Before adjudicating a new refutation the orchestrator checks the run's own
`precedents.md`: the file is an INPUT document of the round, not only an
output. Reading it costs one narrow read and is what keeps the ninth
batch's refutation on the grain of the first one's.
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
User decisions given in chat are encoded as
pre-adjudication with a mark; a conflict between a pre-adjudication and
a blocker finding → re-present to the user, never silently pick.
A design fork goes to the owner: it is never closed by an adjudication
verdict. Adjudication rules on whether a claim holds, not on which of two
legitimate designs the object should have.
Where observability is on, every fork put to the owner before an
adjudication — and equally the escalation the recount demands with
`OWNER FORK REQUIRED` — is a recorded wait: the orchestrator opens an
`owner-wait-fork` span at the moment the question is put and closes it on
the owner's word, the outcome `answered | refused | abandoned`.
**The owner's own ruling does not cancel the independent re-check —
it is the case the re-check exists for.** Where a pre-adjudication
refutes or accepts a finding of the security/PII class, the ruling actor
OF RECORD is the owner, so the re-check is made by an actor other than
him and is still attached to the signature request before he signs.
Otherwise the owner signs his own decision and nothing independent stands
under that signature at all.
Cross-lens duplicates are deduplicated here via the "=id" convention:
the verdict references the primary id, one fix, every id keeps its row;
a duplicate row's criterion cell carries `=<primary-id>`, optionally
followed by a short gloss (never a bare dash — the recount's
consistency check reserves the dash for refuted rows).
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
**The security/PII class mark is ONE fixed literal, and it lives in the
ledger.** That literal is `class:security-pii` in the `verdict` cell,
read by the same anchoring as every other class tag. It goes in the
LEDGER — which always exists — and not only in an observability span,
which is optional and switchable off. Here the tag is stricter than the
general rule above: the adjudicator sets it on EVERY finding of the
security/PII class, from the FIRST one and regardless of recurrence,
because every check keyed on this class reads that literal and nothing
else. `class:security`, `class:pii` and `class:sec-pii` are different
classes and none of them counts as the mark; the slug `security-pii` is
reserved for this class and carries no other meaning.
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
after that conclusion is recorded. The reason is the verifier's at stage
8: a reviewer shown someone else's verdict changes their mind in about a
third of cases, and a security checkpoint is the last place to spend that
third. The conclusion travels with the signature request and is written
into the row (and into the register row where the finding was nominated);
a re-check that disagrees is put to the owner AS a disagreement, never
smoothed into the ruling.
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
**An empty `verdict` cell is a STATE, not a defect.** A stage-5 layout
carries findings rows whose verdict cells are still blank; that state is
"not adjudicated", it is exempt from the backstop, and the recount reports
it as `not adjudicated: <n> rows` instead of refusing to recount. The rows
are non-terminal anyway, so the round stays unclosable on their account and
the exit code is the ordinary one for open rows. The relaxation is EXACTLY
the empty case: a FILLED cell that was written and left the class out is the
structural error it always was — a judgment made, not a judgment pending.
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
**The ZONE cell is filled here, from the map and not by feel.** Every row
gets its `zone` — `Z1`, `Z2` or `Z3` — off the ledger header's zone map
(stage 2), for the section of the object the finding lands in, replacing
the `·` transcription left. A genuinely disputable zone is the
adjudicator's call and the ruling goes into `{run-folder}/precedents.md`
like any other repeated ruling.
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
**A finding caused by an earlier fix is tagged where the metric can
read it** — in the ledger, which always exists, and not only in an
observability span, which is optional. A verifier finding whose
substance is a defect in APPLYING an earlier fix gets
`origin:fix-application from:<batch>` in its `verdict` cell, where
`<batch>` is the identifier of the batch whose fix was applied
defectively: the value of that row's `fix` cell (the per-batch commit
hash), or the batch's snapshot-path name in DEGRADED mode. Without the
`from:` reference the injection metric of `references/stage-7-fix-batches.md` has no numerator, so the
adjudicator writes it HERE, taking it from the row whose fix it has
just ruled defective; the same alphabet and terminator as `class:`
apply, widened to 40 characters. A tag whose `from:` cannot be read
counts as unattributed and is never charged to the latest batch by
guess.
**A refutation the contract itself closed may say so — the `shelf:`
tag.** Refuting a finding whose claim a pre-signed disposition of the
round contract closes WHOLLY, the adjudicator MAY tag the `verdict` cell
`shelf:<slug>`, the slug naming that disposition (`shelf:ng-2`). It is
OPTIONAL, it changes no status, and its whole purpose is arithmetic: the
recount prints the share of a lens's refutations that carry it beside
that lens's sustained rate at stage 9, so that a lens is never judged by
the rate alone. Alphabet, boundary and prose rule are the `class:` tag's,
unchanged — `[a-z0-9-]`, 1-32 characters, ended by the first character
outside that alphabet, and a `shelf:` followed straight away by a space,
a `|` or the end of the cell is ordinary prose. It is set on a REFUTED
row: a shelf closes a claim, it does not uphold one.
**Every upheld finding gets its readiness criterion HERE, before any fix
is attempted**, written by whoever adjudicated: the scale level plus the
criterion itself in the row's `criterion` cell, the level picked off the
ladder and the LOWER level taken whenever in doubt. A refuted or refused
row carries exactly the em-dash `—`; an empty cell is allowed to nobody.
"Improve it / polish it / make it clearer" is not a criterion and is
rejected right here, and a criterion the fixer could satisfy by editing
the very file that defines the check is invalid.
**One route to a criterion has a name, because it recurs.** The
orchestrator's own probe run before adjudication is named
`probe-to-criterion`: the probe becomes a class-L1 criterion, and the
verifier re-executes it live. Nothing new is built for it — the command
the orchestrator already ran to test the claim is written into the
`criterion` cell as the level-1 criterion it is.
Zero-confirmed branch (everything refuted or nothing found): skip
stages 7–8 and the loop-and-convergence part of stage 9, go straight to
its closure part.
**With observability on**, append one `orchestrator` span per
adjudication batch with its `ids`, its `id_tags` — this is where
`fix-application` and `security-pii` are set, at ruling time and never
retroactively — and `outcome: upheld:<n>,refuted:<m>`.
Output: every id has a verdict and a
non-empty criterion cell.
