Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 8 — Verification

A FRESH verifier on EVERY pass, spawned by the agent-type
identifier `critic-ledger:verifier` (bare `verifier` where unambiguous);
the DEFINITION it dispatches to is
`${CLAUDE_PLUGIN_ROOT}/agents/verifier.md`, and where no agent registry is
available it is a general-purpose subagent carrying that definition's
constraints verbatim. Prompted from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/verifier-prompt.md`.
There is no actor choice left: never the critic continued, never the
previous verifier continued, never whoever applied the fixes.
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
**The verifier does not see the fixer's justification, and that is a
rule now rather than an accident.** Its prompt carries NEITHER the
fixer's batch report NOR the fixer's reasoning: the verifier gets the
row's criterion cell, the diffs and the round's verbatim critic salvages,
and derives the verdict itself. That is how the prompt template already
stands — there is no placeholder for a fixer report in it — and writing
it down makes the default a rule, so a later edit cannot break it
silently. The reason is measured elsewhere and holds here: a reviewer
shown someone else's verdict changes their mind in about a third of
cases (anchoring), and a cold-start reviewer gives the higher-value
signal.
BEFORE spawning it the orchestrator runs the deterministic pre-pass
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/deleted-lines.py` over the batch commits and substitutes its
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
Depth scales with the finding's severity: minors are checked pointwise
against the row's criterion (never closed on the fixer's word — the
re-derive mandate forbids exactly that); majors and blockers require the
verifier to re-derive the result itself instead of accepting a pasted
output; a rework of more than ~5% of the object's material triggers a
FULL re-inspection rather than a sampled one — the share is counted in
LINES by script (changed lines across all the round's batch diffs over
the object's line count at the pin) and taken over the object as a
whole, never per file.
Touch-up fixes are verified exactly like primary fixes. Salvage the report
immediately (and re-salvage after any append). The ORCHESTRATOR then
transcribes the verifier's per-id results into the ledger's `verified`
cells — the verifier itself is read-only and writes nothing. Verified
cells: re-fixing an id RESETS its verified cell — terminality only
after the LAST fix is verified.
**The `verified` and `terminal` cells are written with the same canonical
writer as the `fix` cell of stage 7**, never by hand:
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/set-cell.py --ledger <ledger> --id <id> --column <verified|terminal> --value "<text>"`,
one call per cell, each printing its own `OK <id>.<column>` line — a
transcription that reports success while changing nothing is what this
closes, and the reset of a verified cell is that same call with an empty
`--value`.
**With observability on**, append one `script` span for that
`deleted-lines.py` run and one `verifier` span PER VERIFIER AGENT —
each carrying the pass ordinal in `unit` (`P<n>`), the pass's
verifier-prefix in `id_prefix`, its own `ids`,
`outcome: L:<n>,P:<n>,NOT:<n>,new:<n>`, and `flags:["bundled"]` where it
applies, with the same tool-result capture as stage 3 — then copy the
pass's aggregated `started`/`ended` (earliest open, latest close across
its spans) into the passes table's two trailing columns.
That span's other flags are written on the same terms and not left
empty by default: `respawn` where this verifier was spawned again after
a failed run, `degraded` where its result was accepted knowing it was
partial. The ORCHESTRATOR sets the flag at the moment it decides the
respawn or accepts the partial result — afterwards nothing in the trace
tells a pass that ran twice from one that ran once.
Output: every id in scope has
LANDED/PARTIAL/NOT with evidence, transcribed into the ledger.
