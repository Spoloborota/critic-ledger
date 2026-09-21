Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 8 — Verification

### 8.1 The fresh verifier on every pass

A FRESH verifier on EVERY pass, spawned by the agent-type
identifier `critic-ledger:verifier` (bare `verifier` where unambiguous);
the DEFINITION it dispatches to is
`${CLAUDE_PLUGIN_ROOT}/agents/verifier.md`, and (the dispatch rule,
including the no-registry fallback, is the "Models and effort, by role"
section of the router). Prompted from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/verifier-prompt.md`.
There is no actor choice left: never the critic continued, never the
previous verifier continued, never whoever applied the fixes.

### 8.2 The lens-split verification pass

**One pass MAY be executed by N verifiers instead of one, and that mode
has a name: the `lens-split verification pass`.** Each of the N is a
fresh verifier with its OWN non-overlapping scope of ids, handed to it in
the prompt's `{lens_scope}` placeholder — which ids it judges and which
belong to another verifier of the same pass. The freshness rule above
applies to EVERY one of them by name: none is a critic continued, none is
a verifier of an earlier pass continued, and none is the actor that
applied the fixes. A lens-split pass counts as FULL-SCOPE only when the
union of the N scopes covers every id of the pass with no overlap and no
hole; a split leaving an id unjudged is not a completed pass, whatever
the N verifiers reported. The deterministic deleted-line walk is divided
by that same rule and divided EXPLICITLY, because its volume follows the
batch's FILES and not its ids: each verifier's briefing states in
writing which files' deleted lines it walks, or names the ONE verifier
of the pass that walks them all, and the pass is full-volume only when
the union covers every deleted-line of the batch with no hole.
How many verifiers a pass had is recorded in
the passes table's own column, so the count is readable without the run
folder.
Its canon is self-contained by construction — the ledger plus the
round's verbatim salvages.

### 8.3 One full connectedness pass, planned once

A CONNECTEDNESS pass reads the object WHOLE for contradictions between
what the fixes changed and what they did not — the one thing a per-id
pass is blind to. It is a verification pass with `{lens_scope}` = the
whole object and no per-id list, so its only output is new findings; it
is PLANNED ONCE per round, and the point is fixed HERE for each profile
— the profile itself is defined at stage 2 (2.4) and assigned at the
close of stage 6: after the last fix cycle for profile L, on the user's
word for M and on the user's word for F. Without that word the pass is
not planned at all — the round does not wait for it and nobody is asked.
Residue re-checks by id (9.5) are a different duty and never substitute
for it.

Where the object PRESCRIBES, item by item, text that will later be
ASSEMBLED into one downstream artifact — a prompt, a stage file, an agent
definition — the connectedness pass reads that assembled form once, not
only the items in isolation. A per-item reading is structurally blind to
a contradiction that exists only in the assembled text, and that
blindness is a property of the reading, not of the critic: the items can
each be right and the artifact they compose still contradict itself.

### 8.4 A deduplicated row carries the primary criterion in full

**A deduplicated row reaches the verifier with the PRIMARY row's
criterion substituted IN FULL.** Where a row's criterion cell carries
`=<primary-id>` by the deduplication convention of stage 6, the
orchestrator substitutes the full text of the primary row's criterion
into that row's `{ledger_rows}` block — never the bare reference. The
device is the one already used for the deleted-line list: the verifier
judges ready-made material instead of assembling it. Without it a
verifier holding only the lens that owns the duplicate is briefed with a
stub where its bar should be, and a field verifier reported exactly that
break rather than guessing past it. The rule is not a property of the
split mode — it holds on an unsplit pass too, because the verifier's
canon is self-contained.

### 8.5 The verifier does not see the fixer's justification

**The verifier does not see the fixer's justification, and that is a
rule now rather than an accident.** Its prompt carries NEITHER the
fixer's batch report NOR the fixer's reasoning: the verifier gets the
row's criterion cell, the diffs and the round's verbatim critic salvages,
and derives the verdict itself. That is how the prompt template already
stands — there is no placeholder for a fixer report in it — and writing
it down makes the default a rule, so a later edit cannot break it
silently. The reason is measured elsewhere and holds here: human labelers
shown a verdict they had disagreed with were willing to change their vote
about a third of the time (Zheng et al. 2023, arXiv:2306.05685, §4.2 — a
side observation of that study). Exposure to a verdict moves the reviewer
(anchoring), and a cold-start reviewer gives the higher-value signal.

### 8.6 The mandate

BEFORE spawning it the orchestrator runs the deterministic pre-pass
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/scripts/deleted-lines.py` over the batch commits and substitutes its
output into the prompt's `{deleted_lines}`: the verifier JUDGES a
ready-made deleted-line list instead of assembling one, so the
completeness of the walk stops resting on an agent's attention.
Mandate: per-id LANDED/PARTIAL/NOT with file:line evidence taken from
the CURRENT state of the object and checked against that row's
`criterion` cell — the criterion written at stage 6 is what "landed"
means, not a general impression; PARTIAL and NOT must name exactly what
is missing, and "fixed otherwise than the critic proposed" is recorded
as `LANDED OTHERWISE (<what was actually done>)` in the same cell, never
as a new status. "Do not trust claimed fixes — re-derive": every number
a fix introduces is re-derived from the primary source, and a number
that cannot be re-derived is flagged. Walk EVERY line of the
deleted-line list (an equivalent in the new text or a covering
finding-id is mandatory; a normative line gone without either is a new
fix-loss finding). The ZONE scales the DEPTH of that judgment and nothing
else: `Z1` — every line of the list; `Z2` — the lines carrying
obligations; `Z3` — the adjudicator's call. The deterministic pre-pass
still emits the FULL list in every zone, so what narrows is the verifier's
judgment, never the input it judges. The zone does NOT touch the
fresh-verifier rule: a verifier is new on every pass whatever the zone,
and what a zone buys is paper and closure, never independence. Negative claims carry command+output or they count as
unchecked. New defects get the verifier's own prefix, a severity and
file:line — the verifier neither judges its own findings nor proposes
fixes.
A class-L1 criterion born as a `probe-to-criterion` is re-executed live
by the verifier, never read off the fixer's report — which the verifier
does not have in the first place, so the rule is a reminder of what the
level already means rather than a new obligation.
The readiness scale's two forms of a MUTATING level-1 command leave that
rule whole: a probe-to-criterion whose command mutates what it runs
against is re-executed by the verifier on a scratch copy the
orchestrator made for that run and removes after it, as that scale
states, and a command that would have to mutate the live object never
becomes a probe-to-criterion (6.26 states that rule where a probe
becomes a criterion) — a class-L1 criterion of that kind, whatever its
origin, is judged from the executor's output printed at the moment 7.18
fixes, which that row's `fix` cell carries, and no pass of this stage
spawns an executor.
A claim about a SCRIPT's or GIT's behavior is re-derived like a number:
the verifier reads the code the claim cites or runs the check where
running it is read-only, and never accepts the claim from prose — the
object's, the ledger's or a critic's. A claim it can do neither with
becomes a NEW finding of the verifier's own, whose claim opens with the
literal `UNVERIFIED` after its `<id> | <severity> |` header and names the
check that would have settled it — never a per-id verdict word, which
stays the three this section already fixes. That obligation does not
scale down with severity or zone: those scale how MANY lines are judged,
never whether an executable claim is executed.

### 8.7 Depth by severity

Depth scales with the finding's severity: minors are checked pointwise
against the row's criterion (never closed on the fixer's word — the
re-derive mandate forbids exactly that); majors and blockers require the
verifier to re-derive the result itself instead of accepting a pasted
output; a rework of more than ~5% of the object's material triggers a
FULL re-inspection rather than a sampled one — the share is counted in
LINES by script (changed lines across all the round's batch diffs over
the object's line count at the pin) and taken over the object as a
whole, never per file.
Those changed lines are counted ONLY over files that already existed at the
pin — `git diff --numstat --diff-filter=M` — and never over files the round
created: a copied fixture of some twelve hundred lines once carried the
share to 87.7 % and put every verifier of that round on a full re-inspection
of an object nobody had reworked. What the round ADDED is printed beside the
share as its own line, `added: <n> lines in <k> new files`, so nothing is
hidden by the exclusion; the threshold itself does not move.
Beside the share over all the round's batches the count made for the
pass also reads the share over the LAST fix cycle alone — the batches since the
previous verification pass — and it is the last-cycle share that arms
the full re-inspection of a later pass: history does not inflate it.
Touch-up fixes are verified exactly like primary fixes. Salvage the report
immediately (and re-salvage after any append). The ORCHESTRATOR then
transcribes the verifier's per-id results into the ledger's `verified`
cells — the verifier itself is read-only and writes nothing. Verified
cells: re-fixing an id RESETS its verified cell — terminality only
after the LAST fix is verified.

### 8.8 The verified and terminal cells

**The `verified` and `terminal` cells are written with
`scripts/set-cell.py --column <verified|terminal>` by the
orchestrator through Bash, one call per cell (the act is 7.17 of
references/stage-7-fix-batches.md; the script's contract is
references/templates-and-scripts.md):**
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/scripts/set-cell.py --ledger <ledger> --id <id> --column <verified|terminal> --value "<text>"`,
each call printing its own `OK <id>.<column>` line, the reset of a
verified cell being that same call with an empty `--value`, and a whole
pass being closed as one act of 7.17, carrying both columns of every id of
the pass.
Output: every id in scope has
LANDED/PARTIAL/NOT with evidence, transcribed into the ledger.
