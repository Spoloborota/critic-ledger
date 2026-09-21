Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 3 — Critic round

Parallel spawn of one critic per lens, by the agent-type
identifier (bare name where unambiguous): `plan` mode
`critic-ledger:critic-plan`, `impl` mode `critic-ledger:critic-impl`.
The DEFINITIONS those identifiers dispatch to are
`${CLAUDE_PLUGIN_ROOT}/agents/critic-plan.md` and `${CLAUDE_PLUGIN_ROOT}/agents/critic-impl.md`;
(the dispatch rule, including the no-registry fallback, is the
"Models and effort, by role" section of the router). Critics are
prompted from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/critic-prompt.md`, with the object addressed
inside the scratchpad COPY made at stage 2. The contract elements are
mandatory: strict read-only + no mutating git; maximum defects, zero
solutions; atomic findings with the lens id prefix and severity; every
negative claim carries command+output; a coverage statement naming what
was NOT inspected when the timebox ran out; the final message IS the raw
report.
In `impl` mode, commands a critic hands over are run by an EXECUTOR (the
orchestrator or the `critic-ledger:executor` agent, 6.26) AS WRITTEN, on the
scratch copy made for that report's commands (6.26); where the command as
written cannot run and the critic's intent is unambiguous, it is run ONCE
more in the corrected form, and BOTH outputs are kept under `probes/`, the
correction named. A command whose intent is ambiguous is returned to the
critic's finding as `UNVERIFIED` (the form of the critic's mandate), never
guessed. The executor's shell is not the critic's: no command may rely on
word-splitting of an unquoted variable or on any zsh/bash difference — a
command that does is corrected under the same rule. A handed-over command
touches nothing outside the scratch copy it is run on — no state-changing
git, no network, no write to the repository or to any other path; a
command that would need more is not run and goes back to its finding as
`UNVERIFIED`, the reason named.
Report acceptance is a HYBRID, never a pure script and never pure
impression. `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/scripts/validate-report.py` checks deterministically the
two mechanically complete traits — the lens's id prefix on every finding
and the severity literal — and merely MARKS everything softer (a finding
without `file:line`, missing header fields, no coverage statement),
because the evidence rule's second branch, an exact quote, is not
mechanically checkable. The trait "no solutions proposed" is entirely
the orchestrator's judgment.
The verdict "re-run this lens" is the orchestrator's call even where the
script finds problems — a false positive of the script would otherwise
burn a whole critic run. A report that fails acceptance
causes ONE respawn of the lens with a tightened contract; a second
failure is recorded in the ledger header as a dropped lens.
An agent that died on a server error has no report: fragments are never
salvaged, the stage is respawned with a fresh actor, and one line of fact
goes into the ledger. That is not the acceptance path above — there is
nothing to accept or reject — and the respawn is not the lens's one
tightened re-run either.
Output: N reports accepted by the criteria.

## Stage 4 — Immediate salvage

Each report is preserved verbatim in a durable
file before any other work — and again after EVERY append to a report
or salvage file, within the same batch (a single-shot salvage loses
late appends). Address: critic reports go into the run folder's
`critics/` subdirectory, verifier reports (stage 8) into `verify/`, one
file per lens and per pass. The sanitization caveat and the privacy gate
in `references/stage-1-run-folder.md` apply. Mechanism: critics are read-only, so the
ORCHESTRATOR salvages by writing the agent's final message verbatim —
with `scripts/extract_final.py` from the subagent's task transcript where
the platform keeps one, else by reprinting it — never the raw transcript
file. The extractor reads the subagent's task TRANSCRIPT, never the
indented hand-back the harness shows the orchestrator: an indented or
HTML-escaped copy is not verbatim, and a salvage made from it fails the
id-set check by construction where a `|` or a `<` was escaped.
**Reprinting is the fallback, and it is the dangerous one.** A report that
quotes escape-sequence TEXT — a backslash followed by `u2028`, `u2029`,
`n`, `t` or any `uXXXX` — has that text written as the CHARACTER it names
when the salvage is re-typed instead of copied byte for byte, and U+2028
and U+2029 are invisible to a reader and line terminators to some
parsers. A reprinted salvage that had to quote such text is therefore
checked for the literal substring afterwards — `grep -c 'u2028'
<salvage>` — and fewer hits than the report itself shows is the
substitution, repaired by restoring the escape TEXT.
Critics run in parallel and their reports
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
Output: one salvage file per lens under `critics/`.

## Stage 5 — Mechanical layout

Mechanical transcription comes first, before any
judging:
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/scripts/transcribe.py` lays the salvaged findings out into the ledger
skeleton — one finding, one row. It is copying, not paraphrase, so the
information loss is zero, and it follows a per-line rule: a line that looks like a finding but
does not parse is SKIPPED and named with its `file:line` under
`SKIPPED LINES`, while the file's well-formed lines are transcribed. A
duplicate id and a wrong row width remain structural errors (exit 2): a
wrong width writes nothing, a duplicate writes every row that is not one.
The main loop then fills only `zone`, `verdict` and `criterion`, at stage
6 and never here.
Running `scripts/recount.py` before this point is not a tooling failure:
a ledger whose rows are not transcribed yet has none, so the recount
exits 2 with `no ledger rows found` exactly as it would on a broken
table. The remedy is the sequence, not a repair — run
`scripts/transcribe.py` first and recount after it.
A SKIPPED line that names a REAL finding is not repaired in the salvage —
the salvage stays verbatim. The orchestrator CREATES the row by the
mechanical route instead: it writes ONE corrected header line — the
critic's id, the severity literal the critic plainly meant, and a claim
opening with `transcription-note:` that names the salvage's `file:line`
and the words the critic actually used — into a separate file, never into
the salvage, and runs `scripts/transcribe.py --ledger` over that file,
which appends the row to the findings table like any other.
`scripts/set-cell.py` creates no row: it writes only cells of a row that
already exists, so the new row takes its adjudication cells at stage 6
through it like every other row. An intent that is not plain is not
guessed: the line stays skipped and the lens is asked.
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
Output: a ledger skeleton with
one row per finding, the `id`/`severity`/`claim` cells filled by literal
copy and every other cell empty, `zone` carrying the stub `·`.
