Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 3 — Critic round

Parallel spawn of one critic per lens, by the agent-type
identifier (bare name where unambiguous): `plan` mode
`critic-ledger:critic-plan`, `impl` mode `critic-ledger:critic-impl`.
The DEFINITIONS those identifiers dispatch to are
`${CLAUDE_PLUGIN_ROOT}/agents/critic-plan.md` and `${CLAUDE_PLUGIN_ROOT}/agents/critic-impl.md`;
where no agent registry is available, spawn a general-purpose subagent and
embed the definition's constraints verbatim. Critics are
prompted from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/critic-prompt.md`, with the object addressed
inside the scratchpad COPY made at stage 2. The contract elements are
mandatory: strict read-only + no mutating git; maximum defects, zero
solutions; atomic findings with the lens id prefix and severity; every
negative claim carries command+output; a coverage statement naming what
was NOT inspected when the timebox ran out; the final message IS the raw
report.
Report acceptance is a HYBRID, never a pure script and never pure
impression. `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/validate-report.py` checks deterministically the
two mechanically complete traits — the lens's id prefix on every finding
and the severity literal — and merely MARKS everything softer (a finding
without `file:line`, missing header fields, no coverage statement),
because the evidence rule's second branch, an exact quote, is not
mechanically checkable. The trait "no solutions proposed" is entirely
the orchestrator's judgment. The script NEVER rejects a report by
itself: the verdict "re-run this lens" is the orchestrator's call, or one
false positive burns a whole critic run. A report that fails acceptance
causes ONE respawn of the lens with a tightened contract; a second
failure is recorded in the ledger header as a dropped lens.
An agent that died on a server error has no report: fragments are never
salvaged, the stage is respawned with a fresh actor, and one line of fact
goes into the ledger. That is not the acceptance path above — there is
nothing to accept or reject — and the respawn is not the lens's one
tightened re-run either.
**With observability on**, open one `critic` span per lens at its spawn
and close it at report acceptance, recording that spawn's own
`usage`/`totalTokens`/`resolvedModel`/`agentId` from the tool result and
`outcome: findings:<n>` — a re-spawned lens carries `flags:["respawn"]`,
a dropped one `outcome:"dropped"`.
Output: N reports accepted by the criteria.

## Stage 4 — Immediate salvage

Each report is preserved verbatim in a durable
file before any other work — and again after EVERY append to a report
or salvage file, within the same batch (a single-shot salvage loses
late appends). Address: critic reports go into the run folder's
`critics/` subdirectory, verifier reports (stage 8) into `verify/`, one
file per lens and per pass. The sanitization caveat and the privacy gate
in `references/stage-1-run-folder.md` apply. Mechanism: critics are read-only, so the
ORCHESTRATOR salvages by reprinting the agent's final message verbatim
(not the raw transcript file). Critics run in parallel and their reports
arrive out of order, in separate messages: EACH report is salvaged on
ITS OWN arrival, singly, before anything else is done with it — waiting
for the others is banned, and adjudication does not begin until the last
expected report is saved or its lens is declared dropped. Salvage verify:
the id set in the salvage equals the id set in the report. The reprint
cost is acknowledged and accepted — it buys the durability guarantee.
**The environment does not get a veto over verbatimness.** Verbatim
salvage outranks local formatting and lint hooks: where the environment
physically prevents writing the text, writing past the hook is part of
the stage, not improvisation — except a hook that blocks on CONTENT (a
secret or credential scanner), which is never written past: its block is
raised as a finding of the round.
**With observability on**, append one `orchestrator` span per salvage
write — `unit: "salvage"`, `outcome: "salvaged"`, `tokens: null` —
several salvages in a round sharing that unit and told apart by their
`span` seq; it is never a `script` span, because salvage is an
orchestrator action and there is no salvage script to name in one.
Output: one salvage file per lens under `critics/`.

## Stage 5 — Mechanical layout

Mechanical transcription comes first, before any
judging:
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/transcribe.py` lays the salvaged findings out into the ledger
skeleton — one finding, one row, with the `id`/`severity`/`claim` cells
produced by LITERAL COPY of the finding's header line and the rest left
empty. It is copying, not paraphrase, so the information loss is zero,
and it fails CLOSED: a line that looks like a finding but does not parse
stops the transcription with a structural error instead of being
silently skipped. The main loop then fills only `zone`, `verdict` and
`criterion`, at stage 6 and never here.
**The row form is the LEDGER'S, and transcription reads it rather than
assuming it.** The script takes the width from the header's `Row schema:`
field, or from the findings header's own cell count where that field is
absent, and refuses to write anything at all when the two disagree or
neither is readable — a row of a foreign width is a structural error of
the recount, so emitting none is the safer failure. In the nine-cell (v3)
schema the filled cells are NAMED rather than counted — `id`, `sev` and
`claim` carry the literal copy and `zone` carries the stub `·`, since the
zone comes between `sev` and `claim` and the filled cells are no longer a
contiguous prefix. The stub is deliberate: a zone is a judgment against
the zone map, and transcription stays literal copying.
**With observability on**, append one `script` span for that
`transcribe.py` run.
Output: a ledger skeleton with
one row per finding, the `id`/`severity`/`claim` cells filled by literal
copy and every other cell empty, `zone` carrying the stub `·`.
