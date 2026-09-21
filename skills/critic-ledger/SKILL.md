---
name: critic-ledger
description: >-
  Run an adversarial critic round on a plan or an implementation and drive
  every finding to a terminal status through a fix-ledger: parallel read-only
  critics, refute-by-default adjudication, targeted fix batches, independent
  per-finding verification, convergence signal, programmatic closure. This is
  an expensive multi-agent procedure. Use ONLY on explicit user request.
argument-hint: "plan <path> | impl <path|commit-range>"
---

# critic-ledger — critic rounds with a fix-ledger discipline

## Gate (read first)

Run this skill ONLY when the user explicitly asked for a critic round /
fix-ledger cycle. Never self-trigger it because the description "seems to
fit". If the object to review was not named, STOP and ask for it.

## The contract (self-contained; the whole discipline in one place)

This section is the canon of the discipline; its long form — principles 1–3 and 5–7 in full — is `references/contract-long-form.md`, and every restatement of a rule inside the `references/` files is subordinate to this section.

1. **Critics are strictly read-only.**
2. **Maximum flaws, ZERO solutions.**
3. **Adjudication belongs to the orchestrator (main loop), never to critics.**
4. **Every finding reaches a terminal status through a fix-ledger** — a
   durable file, not chat prose, with one NINE-cell row per finding, under
   the header exactly as the ledger template ships it:
   `id | sev | zone | claim (hook; canon = the report) | verdict | criterion | fix | verified | terminal`
   — where `sev` is the severity, `zone` is the review zone the round
   contract's zone map assigned to that part of the object, and `criterion`
   is the READINESS criterion. The last two cells are filled
   at adjudication, before any fix is attempted, the criterion off the
   seven-level scale of `references/readiness-scale.md`. Range rows are
   banned (one id per row). Ledger arithmetic
   (counts, deltas, closure) is computed by script, never by hand, and so is
   the WRITING of the three cells the fix and verification stages own:
   `fix`, `verified` and `terminal` are set with `scripts/set-cell.py`
   (stages 7 and 8), and a cell edited by hand is a defect of the same class
   as a count made by hand.
5. **Fixes are targeted batches, ≤10 ids each**, applied by a SEPARATE fixer subagent — never the main loop that adjudicated — run strictly sequentially and with no git access at all.
6. **Verification is a separate pass by a FRESH actor on EVERY pass** — never a continuation of the critic, never a continuation of the previous verifier, and structurally never the fixer.
7. **SEVEN terminal statuses**: `verified-landed` / `refuted-with-reason` / `accepted-residue` / `refused-user-signed` / `out-of-scope-by-contract` / `frozen-carried` / `logged-no-action`.

Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/contract-long-form.md` before ruling on anything these principles govern; the headlines above are pointers, not the rule.

Severity taxonomy (same for this file and all prompts): **blocker** = the
object is unfit for its purpose or a fix would cause irreversible harm;
**major** = a fact/contract distortion that manifests in a realistic usage
scenario; **minor** = a local defect with no influence on decisions.

## References

Each file below is addressed from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/`; one line per file, path then description.

- `references/readiness-scale.md` — the seven-level readiness scale, the ladder rules and the record form of a criterion
- `references/platform-notes.md` — the accepted residual risk: the agents' "orchestrator-only" rule is not enforced by the platform
- `references/observability.md` — the bundled OpenTelemetry receiver: install, liveness, and the privacy invariant
- `references/stage-0-prerequisites.md` — stage 0: the three preconditions (git, private repository, a named object)
- `references/stage-1-run-folder.md` — stage 1: the run folder, its address and privacy rules, the ignore list
- `references/stage-2-scope-and-lenses.md` — stage 2: object, mode, scope contract, lenses, the ledger header
- `references/stages-3-5-critics-salvage-layout.md` — stages 3–5: the critic spawn, verbatim salvage, mechanical transcription into the ledger
- `references/stage-6-adjudication.md` — stage 6: refute-by-default adjudication, readiness criteria, class tags, the security/PII re-check
- `references/stage-7-fix-batches.md` — stage 7: fixer batches, the back channel, the class-kill gate, commits and fix cells
- `references/stage-8-verification.md` — stage 8: the fresh verifier, deleted-line walk, verified cells
- `references/stage-9-closure.md` — stage 9: the loop, the convergence signal, residue nomination and ratification, programmatic closure
- `references/templates-and-scripts.md` — the full description of every template and script under `templates/` and `scripts/`
- `references/contract-long-form.md` — principles 1–3 and 5–7 of the contract in full

Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/platform-notes.md` before the first agent spawn.

## Modes and scope

`/critic-ledger plan <path>` — object is a normative document (spec,
plan, README-contract, rule). `/critic-ledger impl <path|commit-range>`
— object is an implementation (code+tests, configs, scripts).

Invocation arguments as passed: `$ARGUMENTS`

The mode is read from those arguments: the leading word `plan` or `impl`
if present, otherwise inferred from the argument TEXT; when ambiguous,
default to `plan`; when no object is given, stop and ask.

The skill covers exactly these two object classes. Routing rule: if the
target project already has a specialized validation pipeline with its own
convergence contract for this object class (e.g. a dedicated CV-validation
loop with PASS gates), that pipeline is senior — do not run this skill on
such objects.

Key mode differences (non-exhaustive; anything unnamed is common):

| Aspect | plan | impl |
|---|---|---|
| Example lenses (EXAMPLES, not a default count — the count comes from the load-bearing-hypothesis rule at stage 2) | data validity / design completeness / integration-ecosystem / security | code correctness / design regression / empirics ("run it and prove it") / security |
| Execution | read-only commands (greps/counts) are MANDATORY for factual claims; running the object is not required | runs/tests are NOT executed by the critic: the critic formulates commands, the orchestrator or the `critic-ledger:executor` agent executes them on a scratchpad COPY of the object. No spawn surface enforces isolation — the guarantee is organizational, and that is stated honestly. The sandbox isolates EXECUTION; reading the object's files is never restricted |
| Fix verification | textual re-derivation + greps | deterministic where possible: tests/linters/scripts BEAT LLM judgment |
| Typical scope | a whole document | a diff/module; a whole repository is out of scope for one invocation |
| Deleted-line scan (verification) | EVERY deleted line of the diff | normative/contract lines; refactoring deletions are adjudicated, not auto-counted as fix-loss |
| Rewrite-ban scope | the whole artifact | the module/file under fix; refactoring wider than the batch = a rewrite = a new round |
| Who commits batches | the orchestrator | per the target project's convention (PR workflow etc.); the commit executor is fixed at stage 2. With PR mechanics the fix cell holds the PR link and `verified` is set only after merge — the row is non-terminal until then |
| Ledger address | default (`references/stage-1-run-folder.md`), slug from the object | same; for a commit range, slug from the range |
| Large object | by sections, one ledger | split into sub-objects along module boundaries, one round each; the split is fixed at stage 2 |

Common to BOTH modes: do NOT use git-worktree isolation when the review
targets uncommitted changes — the worktree does not contain them, so the
review would examine the wrong thing. When execution isolation is needed,
redirect HOME/tmp instead.

A VERIFY-ONLY run is not a third mode: it is a round of either mode whose
contract's stopping rule sets fix batches to 0 — stage 7 is skipped, stage 8
verifies the criteria written at stage 6 against the object as it stands,
and the ledger's `- Mode:` still reads `plan` or `impl`. The header's free
prose may name it; no field does.

**Models and effort, by role.** The plugin carries an agent definition per
role in `${CLAUDE_PLUGIN_ROOT}/agents/`, and the `Definition` column below
gives each one's full path. (`${CLAUDE_PLUGIN_ROOT}` is substituted by the
platform with the plugin's install directory; every intra-plugin path in this router and its `references/` files
uses it.) Spawning goes by the AGENT-TYPE IDENTIFIER, not by the path:
`critic-ledger:critic-plan`, `critic-ledger:critic-impl`,
`critic-ledger:fixer`, `critic-ledger:verifier`, `critic-ledger:executor` — the bare name
(`fixer`, `verifier`, …) works where it is unambiguous. The definition file
is what the agent IS; the identifier is the dispatch handle passed to the
spawn tool. If the platform's agent registry is unavailable (the plugin is
not installed as a plugin), spawn a general-purpose subagent instead and
embed that definition's constraints VERBATIM in its prompt. A model is named
as a FAMILY CLASS, never as a pinned model id — ids go stale, families do
not. **Orchestrator** — the ROLE that drives this skill's stages: it spawns
every other actor, adjudicates and writes the ledger (its model and effort
are the row below); wherever a stage file says "the orchestrator", it means
this role and asserts nothing about which actor implements it.

| Role | Who it is | Model | Effort | Definition |
|---|---|---|---|---|
| Orchestrator | the main session, not an agent | the session's | the session's | — |
| Critic, `plan` mode | subagent, one per lens | `sonnet` | high | `${CLAUDE_PLUGIN_ROOT}/agents/critic-plan.md` |
| Critic, `impl` mode | subagent, one per lens | `sonnet` | high | `${CLAUDE_PLUGIN_ROOT}/agents/critic-impl.md` |
| Fixer | subagent, one per batch | `opus` | high | `${CLAUDE_PLUGIN_ROOT}/agents/fixer.md` |
| Verifier | subagent, fresh on EVERY pass | `sonnet` | high | `${CLAUDE_PLUGIN_ROOT}/agents/verifier.md` |
| Executor | subagent, one per arriving report in `impl` mode, per own probe (6.26) or per live criterion | `sonnet` | medium | `${CLAUDE_PLUGIN_ROOT}/agents/executor.md` |

Transcription of findings into ledger rows is a SCRIPT, not an agent
(`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/scripts/transcribe.py`), so it has no row here. Escalation above these
defaults happens only on the user's explicit word; offer it as ONE line
with its cost, never as a full decision-fork presentation.

**Warning — `CLAUDE_CODE_SUBAGENT_MODEL`.** This environment variable
stands FIRST in the platform's subagent-model resolution order, above the
spawn call and above the agent definition, so when it is set the whole
per-role allocation collapses silently into a single model. The
orchestrator writes the ACTUALLY applied models into the ledger header, not
the assigned ones, and flags the divergence there whenever the two differ.

## Stage machine

Only the first part of this router survives a context compaction; after a compaction the orchestrator re-reads the file of the CURRENT stage — the `references/` file its index entry names — before any further action, and re-reads this router in full when it cannot tell which stage it is in.

- **Stage 0 — Prerequisite.** Output: a prerequisite line in the ledger header.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stage-0-prerequisites.md` now and follow it.
- **Stage 1 — Run folder.** Output: the run folder in place with its `critics/` and `verify/` subdirectories, the ignore entry confirmed, and a blank ledger inside it.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stage-1-run-folder.md` now and follow it.
- **Stage 2 — Scope and lenses.** Output: a ledger file with a filled header and the critics' copies made.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stage-2-scope-and-lenses.md` now and follow it.
- **Stage 3 — Critic round.** Output: N reports accepted by the criteria.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stages-3-5-critics-salvage-layout.md` now and follow it.
- **Stage 4 — Immediate salvage.** Output: one salvage file per lens under `critics/`.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stages-3-5-critics-salvage-layout.md` now and follow it.
- **Stage 5 — Mechanical layout.** Output: a ledger skeleton with one row per finding, the `id`/`severity`/`claim` cells filled by literal copy and every other cell empty, `zone` carrying the stub `·`.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stages-3-5-critics-salvage-layout.md` now and follow it.
- **Stage 6 — Adjudication.** Output: every id has a verdict and a non-empty criterion cell.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stage-6-adjudication.md` now and follow it.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/readiness-scale.md` now and follow it.
- **Stage 7 — Fix batches.** Output: batch committed, fix cells filled.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stage-7-fix-batches.md` now and follow it.
- **Stage 8 — Verification.** Output: every id in scope has LANDED/PARTIAL/NOT with evidence, transcribed into the ledger.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stage-8-verification.md` now and follow it.
- **Stage 9 — Loop, convergence and closure.** Output: a programmatic "0 non-terminal" report OR an explicit "awaiting signature" status with the list of waiting rows.
  Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/stage-9-closure.md` now and follow it.

## Templates and scripts

Every file below is addressed from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/`; the paths are relative to that directory. Each template is self-documented; the descriptions here are labels, the full text is in `references/templates-and-scripts.md`.

- `templates/ledger.md` — the ledger skeleton: mandatory header fields, the row schema
- `templates/residue-register.md` — the skeleton of the DURABLE residue register
- `templates/round-contract.md` — the SCOPE CONTRACT of one round, filled and signed BEFORE the first critic is spawned
- `templates/critic-prompt.md` — the stage-3 contract with placeholders
- `templates/fixer-prompt.md` — the stage-7 contract for the fix-batch subagent
- `templates/verifier-prompt.md` — the stage-8 mandate with placeholders
- `scripts/recount.py` — the reference recount script: the contract of ledger cell values
- `scripts/ledger_md.py` — the one owner of the ledger's markdown grammar; `ledger_md.py new` writes a round's blank ledger
- `scripts/ledger_model.py`, `statuses.py`, `structural_checks.py`, `metrics.py`, `report.py` — the five modules `recount.py` is cut into; never called directly
- `scripts/copy-project.sh` — makes the scratchpad copy the critics read
- `scripts/validate-report.py` — the deterministic half of report acceptance
- `scripts/extract_final.py` — writes a subagent's final message verbatim from its task transcript
- `scripts/transcribe.py` — mechanical transcription of the salvaged reports into ledger rows before adjudication
- `scripts/set-cell.py` — the canonical writer of a row's `fix`, `verified` and `terminal` cells
- `scripts/cleanup-scratchpad.py` — removes the round's scratch copies and nothing else
- `scripts/deleted-lines.py` — the deterministic deleted-line pre-pass for verification
- `scripts/check-frontmatter.py` — inventories a SKILL.md's frontmatter against the portable Agent Skills specification

Read `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/references/templates-and-scripts.md` before the first script call and follow it.

## Why this discipline

The reasoning behind these rules, the numbers and what is honestly unproven live in `${CLAUDE_PLUGIN_ROOT}/docs/why-critics.md`; this file carries only the mechanics.
