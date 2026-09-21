Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 0 — Prerequisite

Three conditions, and they are NOT symmetric.

**git is MANDATORY.** The object must be under git — the deleted-line
walk at stage 8 runs on batch commits, and pins are commit hashes. A
project without git has no degraded branch any more: the round REFUSES
to start, says why, and names the remedy (`git init` in the object's
project, a first commit, then re-run). Silently proceeding on content
snapshots is not offered.
**Commit sanction is the one that may be missing.** Confirm the
orchestrator may commit in this repository (the user's word or a
standing project rule). No sanction → DEGRADED mode, declared in the
ledger header: pins are commit hashes, fixes stay uncommitted, fix cells
reference before/after snapshot pairs, diffs run against the uncommitted
working state, and the ledger's "Batch-commit executor" field reads
`none (degraded)`.
**Those snapshots are named for their batch and live INSIDE the run
folder — nowhere else.** The path is written here literally:
`.critic-ledger/<run>/fix-batch-<n>-{before,after}/`, one pair per batch,
never reused and never overwritten (a second batch writing over the
first one's backup once made that batch's deleted-line walk impossible).
The project root and any place outside `.critic-ledger/<run>/` are
BANNED, and the reason is mechanical rather than tidiness: the ignore
entry of stage 1(a) and a project's publication-exclusion list both key
on the `.critic-ledger/` prefix, while a name like `fix-batch-3-before/`
is caught by neither — a snapshot written at the root would ride into a
public release copy uncaught.
**The SCOPE CONTRACT is the third condition, and above 400 lines it is a
GATE.** Three decisions — scope, strictness, acceptance — used to be taken
AFTER the findings arrived, so every finding turned up with equal standing
and was litigated one by one to a terminal status. So: for an object longer
than **400 lines** a contract carrying BOTH owner signatures (Non-Goals,
stopping rule) exists before the FIRST spawn, or the round does not open.
That threshold is OURS — no standard supplies it — and the owner moves it
with one word, recorded in the ledger header. Below the threshold the owner
may waive the contract with one word, and the waiver goes in the header
too. The contract is a DURABLE file beside the object, from
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/round-contract.md`,
by the reviewed project's own convention for documents; the ledger header
carries its PATH and its SHA, so that a contract edited mid-round is
detectable instead of silently replacing the one the round ran under. For a
small object the contract may instead be a section pasted straight into the
ledger header. Filling it is capped at HALF AN HOUR — our limit, marked as
ours: a contract that takes longer is too elaborate, since the point is to
decide three things in advance and not to produce a document. What is
decided here is checked at stage 2, executed at stage 6 and stage 9, and
put in front of every critic at stage 3.
**The subagent-model environment is READ here, not assumed.** Before the
FIRST spawn the orchestrator reads `CLAUDE_CODE_SUBAGENT_MODEL`
(`printf '%s' "$CLAUDE_CODE_SUBAGENT_MODEL"` — an ordinary environment
read, not a platform extension) and records the answer in the ledger
header's existing `- Prerequisite (stage 0):` line as `subagent-model: set
<value>` or `subagent-model: unset`. The value itself is written only
when it passes an anchored model-name shape check — latin letters,
digits, hyphen and dot, 64 characters at most; anything else is recorded
as the fixed literal `subagent-model: set <non-model-value>`, without
the value. This is a RECORD, not a gate: the round continues either way,
and no stop condition is created by it. What it makes visible is the
collapse the router warns about — a variable that stands above the spawn
call silently flattens the per-role allocation, so the header must show
the models that ACTUALLY applied.
After a refresh of the installed copy the consumer project's own
carried-over notes — a companion checklist, a contract skeleton, script
addresses — are re-derived against the copy before stage 1: nothing in the
skill re-derives them for it.

Output: a prerequisite line in the ledger header.
