---
name: critic-ledger
description: >-
  Run an adversarial critic round on a plan or an implementation and drive
  every finding to a terminal status through a fix-ledger: parallel read-only
  critics, refute-by-default adjudication, targeted fix batches, independent
  per-finding verification, convergence signal, programmatic closure. This is
  an expensive multi-agent procedure. Use ONLY on explicit user request.
disable-model-invocation: true
argument-hint: "plan <path> | impl <path|commit-range>"
---

# critic-ledger — critic rounds with a fix-ledger discipline

## Gate (read first)

Run this skill ONLY when the user explicitly asked for a critic round /
fix-ledger cycle. Never self-trigger it because the description "seems to
fit". If the object to review was not named, STOP and ask for it.

## The contract (self-contained; the whole discipline in one place)

1. **Critics are strictly read-only.** They never edit or write files and
   never run any state-changing git command (checkout/add/stash/restore/
   reset/commit). They observe and report. Read-only commands (grep, counts,
   `git log/show/diff`) are allowed and — for factual claims — required.
2. **Maximum flaws, ZERO solutions.** A critic enumerates as many real or
   potential defects as possible under its assigned lens, each as an atomic
   finding (one finding = one defect) with concrete evidence (file:line,
   exact quote, or command+output). Critics never propose fixes, never
   adjudicate their own findings. Positive confirmations ("checked,
   clean") are NOT findings and take no severity — they belong in the
   report's coverage statement.
3. **Adjudication belongs to the orchestrator (main loop), never to
   critics.** Default to refuting each finding (refute-by-default); verify
   security/PII refutations by hand — refuters have been wrong. The user
   owns all "ship it / acceptable / ignore" calls.
4. **Every finding reaches a terminal status through a fix-ledger** — a
   durable file, not chat prose, with one EIGHT-cell row per finding, under
   the header exactly as the ledger template ships it:
   `id | sev | claim (hook; canon = the report) | verdict | criterion | fix | verified | terminal`
   — where `sev` is the severity and `criterion` is the READINESS criterion.
   That cell is filled
   at adjudication, before any fix is attempted, off the seven-level scale
   below. Range rows are banned (one id per row). Ledger arithmetic
   (counts, deltas, closure) is computed by script, never by hand.
5. **Fixes are targeted batches, ≤10 ids each**, applied by a SEPARATE
   fixer subagent — never the main loop that adjudicated — run strictly
   sequentially and with no git access at all. A batch is coherent BY
   TARGET FILE: it is assembled from findings that edit the same file (a
   file with more than ten is cut along its sections), not by lens and not
   by claim topic. The ORCHESTRATOR commits after every batch, with the
   finding ids in the commit message and the commit hash written into the
   fix cells immediately. Never "fix" a document by wholesale rewrite —
   rewrites silently drop both fixed and unrelated content; a rewrite is a
   new artifact requiring a fresh round.
6. **Verification is a separate pass by a FRESH actor on EVERY pass** —
   never a continuation of the critic, never a continuation of the previous
   verifier, and structurally never the fixer, since the fixer is a
   subagent of its own. The mandate is "do not trust claimed fixes —
   re-derive". Per-id verdicts LANDED / PARTIAL / NOT LANDED — plus
   `LANDED OTHERWISE (<what was actually done>)` for a fix that closes the
   finding by another route — with file:line evidence, each checked against
   that row's readiness criterion and not against a general impression. For
   mechanically checkable items a deterministic grep/script beats LLM
   judgment.
7. **Terminal statuses — FOUR**: `verified-landed` / `refuted-with-reason`
   / `accepted-residue` / `refused-user-signed`. The fourth exists only for
   findings marked as the security/PII class when they were ruled on; for
   those a refusal is terminal too. Both `accepted-residue` and
   `refused-user-signed` require the user's explicit signature in machine
   form (`user-signed <date>` / `refused-user-signed <date>`) — silence is
   not a status. The round closes only when a programmatic recount reports
   zero non-terminal rows.

Severity taxonomy (same for this file and all prompts): **blocker** = the
object is unfit for its purpose or a fix would cause irreversible harm;
**major** = a fact/contract distortion that manifests in a realistic usage
scenario; **minor** = a local defect with no influence on decisions.

## Readiness criteria — the seven-level scale

Every upheld finding carries a readiness criterion in its `criterion` cell,
written by whoever adjudicated it (stage 6), before any fix is attempted,
and never touched by the fixer. The levels run from the least forgeable to
the most forgeable; each names the artifact that carries the proof.

| # | Level | How it is gamed | What carries the proof | Example |
|---|---|---|---|---|
| 1 | Command and exit code | the fixer edits the checking file itself, or substitutes the scoring function | the verifier re-runs the command written in the cell itself; the checking file is inside the deleted-line walk | a markup/link linter, a test suite or an analyzer exits 0 |
| 2 | Deterministic structural check | the letter is satisfied while the substance is hollowed out (the list items come out empty) | a search pattern narrow enough to fail on a stub, plus one sampled substantive check | "the removed wording no longer occurs in {file}"; "no `TODO` marks left in the changed files" |
| 3 | Threshold on a measurement | narrowing the measured sample; picking the lucky run | the verifier measures it itself; neither the measuring script nor its inputs belong to the fixer | "unsupported evaluative adjectives 12 → 0, counted by script"; "coverage ≥ 80%"; "p95 < 200 ms on fixture X" |
| 4 | Cross-check against an external artifact | the reference points where something else is said, or stops resolving at all | the verifier consults the source itself and puts the matched quote into the ledger row | "the claim now cites a source that really contains the quoted text"; "the called interface exists and returns the described shape" |
| 5 | Structured resolution over a fixed vocabulary | a plausible but tangential edit NEXT TO the flagged place | the row must carry exact "before"/"after" quotes for THAT id, or the specific diff hunk answering THAT claim | one outcome per finding: landed / landed otherwise (described) / rejected with reason |
| 6 | Rubric with worked examples | bias toward verbosity, toward one's own text, toward position in the list | the judge is not the actor who fixed it, and the rubric's examples are written BEFORE the fix, at adjudication | "the section's terminology agrees with the glossary", with three conforming and three non-conforming examples |
| 7 | Naked judgment — the fixer's word | forged completely | nothing; level 7 NEVER closes a finding on its own | "it reads better now"; "the code is cleaner" |

Rules of use:

- **Pick the level by the LADDER, not by feel.** Ask in order and stop at
  the first "yes": (1) is there a command whose output or exit code
  DIFFERS before and after the fix? → level 1; (2) is "fixed" expressible
  as the presence or absence of a concrete string in the object? → level 2;
  (3) otherwise a before/after quote pair plus one sentence of reasoning.
- **When in doubt, take the LOWER level, never the higher one.** An honest
  weak criterion beats a strong one nobody can satisfy: an unsatisfiable
  criterion turns into an argument at verification, a weak one merely into
  less convincing proof.
- A dispute over which level applies is settled by the ADJUDICATOR — not
  the fixer, not the verifier — and settled BEFORE the fix is attempted.
- **Level 7 never closes a finding alone.** It may take part only alongside
  at least one objective artifact: a quote pair, a named diff hunk, or a
  structural check.
- A criterion the fixer could satisfy by editing the very file that defines
  the check (the test, the scoring script, the rubric) is INVALID — the
  check and the checked never sit in one pair of hands.
- For prose, the absence of an executable check is normal and not a defect
  of the procedure: the criterion is then an exact before/after quote pair
  plus one sentence of reasoning, all inside the ledger row.
- "Improve it / polish it / make it clearer" is not a criterion and is
  rejected right at adjudication.
- A criterion that turns out to be unsatisfiable becomes an
  `accepted-residue` with a one-line reason and the user's signature —
  never a silent pass, and never rewritten after the fact into an
  executable form it cannot honestly take. A criterion that proved a poor
  choice is a NEW finding on the next pass, not a silent pass.
- Record it as the level plus a short name, then the criterion itself:
  `L2 structural check — the removed wording no longer occurs in {file}`. A
  refuted or refused row carries exactly the em-dash `—`; an empty cell is
  allowed to nobody.

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
| Example lenses (EXAMPLES, not a default count — the count comes from the load-bearing-hypothesis rule at stage 2) | data validity / design completeness / integration-ecosystem | code correctness / design regression / empirics ("run it and prove it") |
| Execution | read-only commands (greps/counts) are MANDATORY for factual claims; running the object is not required | runs/tests are NOT executed by the critic: the critic formulates commands, the orchestrator or a separate agent executes them on a scratchpad COPY of the object. No spawn surface enforces isolation — the guarantee is organizational, and that is stated honestly. The sandbox isolates EXECUTION; reading the object's files is never restricted |
| Fix verification | textual re-derivation + greps | deterministic where possible: tests/linters/scripts BEAT LLM judgment |
| Typical scope | a whole document | a diff/module; a whole repository is out of scope for one invocation |
| Deleted-line scan (verification) | EVERY deleted line of the diff | normative/contract lines; refactoring deletions are adjudicated, not auto-counted as fix-loss |
| Rewrite-ban scope | the whole artifact | the module/file under fix; refactoring wider than the batch = a rewrite = a new round |
| Who commits batches | the orchestrator | per the target project's convention (PR workflow etc.); the commit executor is fixed at stage 2. With PR mechanics the fix cell holds the PR link and `verified` is set only after merge — the row is non-terminal until then |
| Ledger address | default (below), slug from the object | same; for a commit range, slug from the range |
| Large object | by sections, one ledger | split into sub-objects along module boundaries, one round each; the split is fixed at stage 2 |

Common to BOTH modes: do NOT use git-worktree isolation when the review
targets uncommitted changes — the worktree does not contain them, so the
review would examine the wrong thing. When execution isolation is needed,
redirect HOME/tmp instead.

**Artifact address and privacy.** The round's artifacts live INSIDE the
project under review, in a per-run folder:

```
.critic-ledger/
  2026-01-15-101502-auth-plan/
    fix-ledger.md      fixed name; the run folder carries the uniqueness
    precedents.md      created by the ORCHESTRATOR at the first repeated
                       ruling, never in advance; an empty one never exists
    critics/           verbatim critic reports
    verify/            verbatim verifier reports
```

Seconds are part of the folder name on purpose: two rounds on the same
object inside one minute would otherwise share a directory and mix two
runs' ledgers and manifests. If the name is taken even so, the round
refuses and names the occupied path instead of writing over it; colons are
absent deliberately (they break paths on Windows). The short object name is
at most 32 characters, lowercased, every non-alphanumeric replaced by a
hyphen — the object's FULL path stays in the ledger header, the short name
is only an address. The folder is created at the round's first step (stage
1), entered into the project's `.gitignore` BEFORE it is created, and its
creation is announced to the user on the first run in this project. Project
conventions for durable artifacts, if any, are senior to this default;
register the directory in the project's local index if one exists. Runs
already made under the older `<repo>/critic-rounds/<object-slug>/` address
stay where they are and are not migrated; the new address governs new runs.

BEFORE the first salvage, confirm the repository is private — and the check
has a MECHANISM, not just a requirement: list the remotes; zero remotes
means local and private; a non-empty list means asking the user with that
list shown, because a remote's privacy cannot be established from the
working tree. The gate is fail-closed: no answer, a command that did not
run, or output that did not parse all count as "not private". Verbatim
critic reports never enter a public/shared repository — keep them in a local
unversioned holding with an explicit "not durable" note instead. Salvage
into any repo is subject to the project's leak/PII sanitization discipline,
fail-closed: if the project declares a sanitization pass and it cannot be
run, the salvage stays out of the repo.

**Models and effort, by role.** The plugin carries an agent definition per
role in `${CLAUDE_PLUGIN_ROOT}/agents/`, and the `Definition` column below
gives each one's full path. (`${CLAUDE_PLUGIN_ROOT}` is substituted by the
platform with the plugin's install directory; every intra-plugin path below
uses it.) Spawning goes by the AGENT-TYPE IDENTIFIER, not by the path:
`critic-ledger:critic-plan`, `critic-ledger:critic-impl`,
`critic-ledger:fixer`, `critic-ledger:verifier` — the bare name
(`fixer`, `verifier`, …) works where it is unambiguous. The definition file
is what the agent IS; the identifier is the dispatch handle passed to the
spawn tool. If the platform's agent registry is unavailable (the plugin is
not installed as a plugin), spawn a general-purpose subagent instead and
embed that definition's constraints VERBATIM in its prompt. A model is named
as a FAMILY CLASS, never as a pinned model id — ids go stale, families do
not.

| Role | Who it is | Model | Effort | Definition |
|---|---|---|---|---|
| Orchestrator | the main session, not an agent | the session's | the session's | — |
| Critic, `plan` mode | subagent, one per lens | `sonnet` | high | `${CLAUDE_PLUGIN_ROOT}/agents/critic-plan.md` |
| Critic, `impl` mode | subagent, one per lens | `sonnet` | high | `${CLAUDE_PLUGIN_ROOT}/agents/critic-impl.md` |
| Fixer | subagent, one per batch | `opus` | high | `${CLAUDE_PLUGIN_ROOT}/agents/fixer.md` |
| Verifier | subagent, fresh on EVERY pass | `sonnet` | high | `${CLAUDE_PLUGIN_ROOT}/agents/verifier.md` |

Transcription of findings into ledger rows is a SCRIPT, not an agent
(`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/transcribe.py`), so it has no row here. Escalation above these
defaults happens only on the user's explicit word; offer it as ONE line
with its cost, never as a full decision-fork presentation.

**Warning — `CLAUDE_CODE_SUBAGENT_MODEL`.** This environment variable
stands FIRST in the platform's subagent-model resolution order, above the
spawn call and above the agent definition, so when it is set the whole
per-role allocation collapses silently into a single model. The
orchestrator writes the ACTUALLY applied models into the ledger header, not
the assigned ones, and flags the divergence there whenever the two differ.

**Platform reality — the agents' "orchestrator-only" rule is not enforced.**
Agent definitions have no `disable-model-invocation` equivalent (that field
exists for skills, and this skill uses it): nothing at the platform level
stops a session from auto-delegating to a `critic-ledger` agent by
description match outside a round. The only guard is the description text of
each definition. This residual risk is ACCEPTED and stated here rather than
papered over — exactly like the fixer's no-git guarantee, which is mechanical
(Bash absent from the tool set) where this one is not.

## Stage machine

0. **Prerequisite.** Two conditions, and they are NOT symmetric.
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
   `none (degraded)`. Output: a prerequisite line in the ledger header.
1. **Run folder.** Explicit sub-steps, in this order:
   **(a) Ignore-list BEFORE the folder.** `.critic-ledger/` is entered
   into the project's `.gitignore` and the entry confirmed BEFORE the run
   folder is created — otherwise a window exists in which artifacts already
   sit in the tree and no rule covers them. If the entry cannot be made,
   the round does not start. This is checked on EVERY invocation, not only
   the first: a branch switch, a stash, a foreign commit or a regenerated
   `.gitignore` can drop it; a missing entry is restored and the user told.
   The ignore rule is a DEFAULT a project may override — a project that
   deliberately versions its rounds as evidence (this plugin's own
   repository does) keeps them versioned, and what is checked instead is
   that the folder sits in that project's publication-exclusion list.
   **(b) Create the run folder** at the address fixed above
   (`.critic-ledger/<YYYY-MM-DD-HHMMSS-object>/`), with its `critics/`
   and `verify/` subdirectories, and, on the FIRST run in this project,
   tell the user plainly that the folder was created and ignored.
   **(c) Blank ledger** `fix-ledger.md` from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/ledger.md`, created
   in the run folder HERE — before any critic is spawned.
   Output: the run folder in place with its `critics/` and `verify/`
   subdirectories, the ignore entry confirmed, and a blank ledger inside it.
2. **Scope and lenses.** Explicit sub-steps, in this order:
   **(a) Scope.** The orchestrator fixes: the object (paths/commits), mode,
   an id prefix for EACH lens (assigned here, not by critics; letter-led,
   letters and digits only — the recount script's id contract depends on
   it), the models per the role table above (escalation only on the user's
   explicit word, offered as one line with price), the batch-commit
   executor (impl: per project convention), and a timebox per lens. Object
   pin = the state at round start; verification always runs against the
   CURRENT head — third-party edits mid-round produce new findings via
   stage 6, they do not break the round.
   **(b) Lenses — non-overlapping, and their count DERIVED, never
   assumed.** It equals the number of the object's independent LOAD-BEARING
   hypotheses: a claim whose falsity makes the object unfit (a safety invariant, a
   compatibility promise, a cost estimate, a rollback plan, a correctness
   claim about a transformation). **Floor 2, ceiling 7.** The object's SIZE
   drives a lens's DEPTH ("read it whole, not by sampling"), never the
   count. A critical hypothesis does NOT get a second lens of its own: it
   gets 2–3 repeated independent passes over the same hypothesis, and a
   finding counts only when at least two passes agree. The list of
   load-bearing hypotheses is written into the ledger header as the
   justification of the count — a count without the list is invalid — and
   is SHOWN to the user before any critic is spawned; the user may strike
   an item or add one, and that edit IS the mechanism for a user-supplied
   lens, which is added on top of the derived count and MARKED in the
   header as owner-given. Silence counts as consent: the list is already in
   the header and visible. Each lens declares HERE whether it needs the git
   history in its copy. **Hard budget: at most 12 simultaneous agents** —
   lenses plus repeated passes plus the owner's lens — checked BEFORE any
   spawn; over budget, cut the number of hypotheses getting repeated passes
   or run the round in waves, never overrun silently. The actual sum goes
   into the ledger header.
   **(c) Scratchpad copy.** `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/copy-project.sh` makes the copy the
   critics read — they work on the COPY, not on the working tree. Strict
   reflink clone first, then the git-known file list (the history is copied
   only for the lenses that declared they need it), then an object-only
   narrowing; symlinks are copied AS LINKS, secret-class files are stripped
   at every step, and every omission is an `EXCLUDED:` line that goes into
   the ledger header — a critic that does not know what it never saw writes
   a lying coverage statement. One copy per critic when reflink works, one
   shared copy otherwise; with a shared copy the history is available to
   every lens and that fact is recorded in the header rather than papered
   over. The number of simultaneous clones of a private tree equals the
   agent sum, not the lens count.
   Output: a ledger file with a filled header and the critics' copies made.
3. **Critic round.** Parallel spawn of one critic per lens, by the agent-type
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
   failure is recorded in the ledger header as a dropped lens. Output: N
   reports accepted by the criteria.
4. **Immediate salvage.** Each report is preserved verbatim in a durable
   file before any other work — and again after EVERY append to a report
   or salvage file, within the same batch (a single-shot salvage loses
   late appends). Address: critic reports go into the run folder's
   `critics/` subdirectory, verifier reports (stage 8) into `verify/`, one
   file per lens and per pass. The sanitization caveat and the privacy gate
   above apply. Mechanism: critics are read-only, so the
   ORCHESTRATOR salvages by reprinting the agent's final message verbatim
   (not the raw transcript file). Critics run in parallel and their reports
   arrive out of order, in separate messages: EACH report is salvaged on
   ITS OWN arrival, singly, before anything else is done with it — waiting
   for the others is banned, and adjudication does not begin until the last
   expected report is saved or its lens is declared dropped. Salvage verify:
   the id set in the salvage equals the id set in the report. The reprint
   cost is acknowledged and accepted — it buys the durability guarantee.
   Output: one salvage file per lens under `critics/`.
5. **Mechanical layout.** Mechanical transcription comes first, before any
   judging:
   `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/transcribe.py` lays the salvaged findings out into the ledger
   skeleton — one finding, one row, with the `id`/`severity`/`claim` cells
   produced by LITERAL COPY of the finding's header line and the rest left
   empty. It is copying, not paraphrase, so the information loss is zero,
   and it fails CLOSED: a line that looks like a finding but does not parse
   stops the transcription with a structural error instead of being
   silently skipped. The main loop then fills only `verdict` and
   `criterion`, at stage 6 and never here. Output: a ledger skeleton with
   one row per finding, the `id`/`severity`/`claim` cells filled by literal
   copy and every other cell empty.
6. **Adjudication.** Main loop, never a subagent — a subagent has neither
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
   **Precedents file**: repeated rulings are written to
   `{run-folder}/precedents.md` so the ninth batch does not judge against
   the first one's grain and a resumed session can pick the round up. The
   ORCHESTRATOR creates it at the FIRST repeated ruling, never in advance;
   it stays terse — the repeated rulings and their reasoning only, never
   raw finding text, which is always addressable by id on disk. Limit: 200
   lines or 25 KB, checked on every append; reaching it is the signal to
   MERGE repeats into one precedent, never to drop the tail silently.
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
   Cross-lens duplicates are deduplicated here via the "=id" convention:
   the verdict references the primary id, one fix, every id keeps its row;
   a duplicate row's criterion cell carries `=<primary-id>`, optionally
   followed by a short gloss (never a bare dash — the recount's
   consistency check reserves the dash for refuted rows).
   **Every upheld finding gets its readiness criterion HERE, before any fix
   is attempted**, written by whoever adjudicated: the scale level plus the
   criterion itself in the row's `criterion` cell, the level picked off the
   ladder and the LOWER level taken whenever in doubt. A refuted or refused
   row carries exactly the em-dash `—`; an empty cell is allowed to nobody.
   "Improve it / polish it / make it clearer" is not a criterion and is
   rejected right here, and a criterion the fixer could satisfy by editing
   the very file that defines the check is invalid.
   Zero-confirmed branch (everything refuted or nothing found): skip
   stages 7–8 and the loop-and-convergence part of stage 9, go straight to
   its closure part. Output: every id has a verdict and a
   non-empty criterion cell.
7. **Fix batches.** The fixer is a SEPARATE subagent, one per batch, spawned
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
   fixer in the FOREGROUND — `run_in_background: false` on the spawn call, or
   the platform's equivalent "wait for the result in this call" — never as a
   background task; only after its report has arrived AND the batch is
   committed may the next batch start. Without that parameter the requirement
   is a wish, not a guarantee.
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
   defence against "the agent decided it was good enough". Back channel:
   the fixer's final report returns exactly one outcome per id, `fixed` or
   `criterion-unworkable` with a reason; the orchestrator routes every
   `criterion-unworkable` id BACK TO STAGE 6, by the same route as a
   verifier's new findings, never straight into the next batch.
   Re-adjudication either redesigns the fix or the criterion (which by the
   general rule RESETS that row's verified cell) or takes the row into
   accepted residue under the user's signature.
   The BATCH-COMMIT EXECUTOR fixed at stage 2 commits after EVERY batch — ids
   in the commit message, the commit hash into the fix cells immediately.
   That executor is the ORCHESTRATOR by default; in `impl` mode it is the
   target project's convention, and where that convention is PR mechanics the
   fix cell holds the PR LINK and the row stays NON-TERMINAL until the merge;
   in DEGRADED mode (no commit sanction, stage 0) it is `none` and the fix
   cell references the uncommitted working state. Wherever commits exist they
   are mandatory: the stage-8 deleted-line walk runs on them.
   Rewrites are banned; if a fix REQUIRES rewriting the artifact: the
   ORCHESTRATOR freezes the ledger by setting
   its `Ledger state:` header line to
   `FROZEN (superseded-by-rewrite, <date> + reason)` — rows keep their
   current statuses, a frozen ledger is never closable (the recount
   reports it as a distinct state). The rewritten artifact is a NEW
   object and a new full round, and the adjudicated-but-unlanded ids
   enter the new round's disposition. Output: batch committed, fix cells
   filled.
8. **Verification.** A FRESH verifier on EVERY pass, spawned by the agent-type
   identifier `critic-ledger:verifier` (bare `verifier` where unambiguous);
   the DEFINITION it dispatches to is
   `${CLAUDE_PLUGIN_ROOT}/agents/verifier.md`, and where no agent registry is
   available it is a general-purpose subagent carrying that definition's
   constraints verbatim. Prompted from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/verifier-prompt.md`.
   There is no actor choice left: never the critic continued, never the
   previous verifier continued, never whoever applied the fixes.
   Its canon is self-contained by construction — the ledger plus the
   round's verbatim salvages.
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
   fix-loss finding). Negative claims carry command+output or they count as
   unchecked. New defects get the verifier's own prefix, a severity and
   file:line — the verifier neither judges its own findings nor proposes
   fixes.
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
   after the LAST fix is verified. Output: every id in scope has
   LANDED/PARTIAL/NOT with evidence, transcribed into the ledger.
9. **Loop, convergence and closure.** Two parts, in this order.
   **Loop and convergence.** NEW verifier findings never go straight into
   fix batches: repeat stages 6–8 — every new finding is adjudicated
   first. Loop until the convergence signal: two consecutive verification
   passes with zero major and zero NOT LANDED. After the signal, proceed
   in micro-batches with BUNDLED verification passes (bundling preserves
   per-id verdicts); the regime switch is recorded in the round delta and
   is subject to the user's veto. **Soft threshold of 20 findings:**
   under 20 findings in a round the SECOND clean pass is skipped by
   default and is still run on the user's word; from 20 findings up it is
   mandatory. The threshold buys tokens, not correctness — a small
   round's second pass mostly costs money, and whatever it invents goes
   through adjudication and dies there under refute-by-default.
   Mechanically checkable items may be verified by script/grep at ANY
   point of the loop — this allowance is NOT gated on the convergence
   signal: for such items a deterministic check beats LLM judgment. The
   orchestrator declares an item "mechanical" when the check can be
   expressed as a grep/script over the artifact, and that script AND its
   fixtures are salvaged next to the ledger so any later actor can re-run
   them. Verifier freshness is a
   MEASURED rule and it governs EVERY pass, not only the closing one: a
   fresh session scores F1 28.6% against 24.6% for a check run inside the
   session that produced the work (p=0.008; external research on verifier
   independence, 2026-08-08). The closing pass being run by a fresh
   (non-continuation) verifier is therefore that general rule's special
   case, not a separate precaution.
   Kill criterion: if the new-findings curve does not decay for three
   consecutive passes → stop, fork to the user (the object likely needs a
   rewrite = a new round, not an endless loop). A row that stays PARTIAL
   for two consecutive passes escalates back to stage 6 for
   re-adjudication (the fix design itself is suspect) or to a user fork;
   PARTIAL is never terminal, so closure still gates such rows. Output:
   two consecutive clean passes, or a kill stop.
   **Closure.** Programmatic terminality recount (script, never by hand):
   zero non-terminal rows — FOUR terminal statuses, `verified-landed` /
   `refuted-with-reason` / `accepted-residue` / `refused-user-signed`.
   The fourth exists only for findings the adjudicator marked as the
   security/PII class when it ruled on them (the class is never assigned
   retroactively): for those a REFUSAL is terminal as well, and both the
   refusal and an accepted residue are terminal only under the user's
   explicit signature — a plain `refuted-with-reason` never closes such a
   finding. Terminal cells are flipped by the ORCHESTRATOR only, per this
   taxonomy, after the verifier's result is transcribed. The signature
   has a MACHINE form, otherwise the rule is indistinguishable from its
   absence: an accepted-residue cell must contain the literal
   `user-signed <date>` and a refusal cell the literal
   `refused-user-signed <date>` — the recount enforces both. If the user
   is unavailable for the residue signature, a legitimate session outcome
   is "round awaiting signature": everything verified, only the rows
   waiting for the user are non-terminal, closure comes with their word.
   Write the final round delta and, when needed, a disposition of previous
   rounds' findings by a separate delegation ("not re-opened by a fresh
   full pass = superseded").
   Re-entry: the next round on the same object is a NEW RUN DIRECTORY,
   `.critic-ledger/<YYYY-MM-DD-HHMMSS-object>/` with its own
   `fix-ledger.md` — the directory carries the uniqueness, there is no
   round number and no numbered ledger name; the link back is the ledger
   header field "Previous run", pointing at the previous run directory
   for this object. Open/residue rows of the previous one are disposed
   in the new round's appendix. Output: a programmatic "0 non-terminal"
   report OR an explicit "awaiting signature" status with the list of
   waiting rows.

## Templates

Every file listed below is addressed from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/` — the paths in this section are given relative to that directory. The stage instructions above always carry the full substituted path; the names below are descriptive labels.

- `templates/ledger.md` — the ledger skeleton: mandatory header fields,
  the row schema, the verification-passes table + new-findings curve (the
  carrier of the convergence signal and the kill criterion), per-batch
  delta sections (delta snapshots are marked historical; the current count
  lives in one place — the table), the inter-round DELTA report, the
  disposition appendix.
- `templates/critic-prompt.md` — the stage-3 contract with placeholders
  `{object}`, `{lens}`, `{id_prefix}`, `{mode}`, `{timebox}`,
  `{project_rules}`, including the mode-conditional execution rule (plan:
  run read-only commands yourself; impl: formulate commands, never
  execute the object).
  `{project_rules}` is a MANDATE to read the target project's own agent
  rules (CLAUDE.md) and leak discipline — not a context dump; if the
  project has none, work by this prompt's contract alone.
- `templates/fixer-prompt.md` — the stage-7 contract for the fix-batch
  subagent, with placeholders `{batch_id}`, `{object_path}`,
  `{findings}`, `{project_rules}`. `{findings}` carries, per id, the
  finding's FULL salvaged text, the adjudicator's verdict with its
  reasoning, and the row's readiness criterion word for word; the
  criterion is fixed and the fixer may never touch it or the file that
  evaluates it. The fixer edits the working tree, gets no git at all, and
  returns exactly one outcome per id — `fixed` or `criterion-unworkable`
  with a reason.
- `templates/verifier-prompt.md` — the stage-8 mandate with placeholders
  `{ledger_rows}`, `{object_path}`, `{batch_commits}`, `{prior_verdicts}`,
  `{salvage_path}`, `{deleted_lines}`, `{new_findings_prefix}`. Canon
  files = the ledger + the round's salvages; `{deleted_lines}` carries
  the deterministic deleted-line list of the batch diff (produced by
  `templates/deleted-lines.py`) — the verifier JUDGES that list instead
  of assembling it.
- `templates/recount.py` — the reference recount script: the contract of
  ledger cell values (which rows count as terminal), fail-closed row
  parsing (a malformed row is a structural error, never a silent drop),
  the programmatic count of open/closed rows, the new-findings curve with
  the kill-criterion warning, the `--prev` inter-round delta, and the
  FROZEN-ledger state. The row it parses is the EIGHT-cell one (`id |
  severity | claim | verdict | readiness criterion | fix | verified |
  terminal`); rows of the older seven-cell schema stay countable — the
  script accepts exactly 7 or exactly 8 cells and addresses `verified`
  and `terminal` from the END of the row, so no branch is needed.
  `LANDED OTHERWISE (<what was actually done>)` in the `verified` cell is
  terminal only with a non-empty description in the parentheses. Criterion
  consistency is checked too: an upheld finding's criterion cell is
  non-empty, a refuted one's holds the literal `—`; an empty cell is
  allowed to nobody. Closure runs through it, never through manual
  counting.
- `templates/copy-project.sh` — makes the scratchpad copy the critics
  read: a copy-on-write clone in STRICT mode, falling back to the
  git-known file list and then to an object-only narrowing, printing
  every omission as an `EXCLUDED:` line. Symlinks are copied AS LINKS and
  secret-class files (`.env*`, `*.pem`, `id_*`, …) are stripped on every
  step; the run directory also gets the cleanup manifest.
- `templates/validate-report.py` — the deterministic half of report
  acceptance: it checks the two mechanically complete traits — the lens's
  id prefix on every finding and the severity literal — and reports
  everything softer (no file:line, missing header fields, no coverage
  statement) as a MARK. It never rejects a report; "re-run this lens"
  stays the orchestrator's call.
- `templates/transcribe.py` — mechanical transcription of the salvaged
  reports into ledger rows before adjudication: one finding = one row,
  with the id/severity/claim cells produced by LITERAL COPY of the
  finding's header line and the remaining cells left empty on purpose (an
  empty cell is what keeps a fresh row non-terminal). Parsing is
  fail-closed, a duplicate id is a structural error, and the write is
  all-or-nothing.
- `templates/cleanup-scratchpad.py` — removes the critics' copies and
  nothing else, by the LANGUAGE (an open directory descriptor; no shell,
  no `rm`), with the path taken from the run manifest rather than from an
  argument or a variable. Dry by default — it prints the plan and each
  condition's verdict — and deletes only on a second `--confirm` call;
  any refusal is a ledger line, never a crash.
- `templates/deleted-lines.py` — the deterministic deleted-line pre-pass
  for verification: given the batch commits (or a `--range`), it lists
  every deleted line as `<old-path>:<old-lineno>: <text>` and marks
  renames, binaries and whole-file deletions. It neither classifies nor
  filters — every listed line is a CANDIDATE the verifier judges, which
  takes the last manual step out of the deleted-line mandate.
- `templates/check-frontmatter.py` — inventories a SKILL.md's frontmatter
  against the portable Agent Skills specification (exactly six top-level
  fields), listing platform extensions AS extensions rather than errors
  and naming anything else as a probable typo. Fail-closed on an
  unterminated block or a duplicate key; `--strict-portable` turns the
  extensions into a failure too.

## Why this discipline (measured; self-reported counters, grade C)

Derived from live remediation rounds on normative planning documents in
the author's private projects: bulk "fix on the spot" from critic
summaries fully landed ~47% of findings; itemized ledger batches with
independent per-item verification converged to ~100% (0 NOT LANDED across
150+ fixes). In a 525-finding historical mining, 16.6% of ALL critic work
was catching defects of prior fix APPLICATION. Fix-loss went 1 → 0 after
the deleted-line mandate; the new-defects curve decayed to zero; bundled
post-signal verification passes cost ×2.7–8.5 less than the full mandate.

**Caveat on the numbers.** All of the above was measured under the
PREVIOUS actor allocation, in which fixes were applied by the
orchestrator's main loop and not by a subagent. The allocation this skill
now prescribes is therefore NOT directly comparable: a later round under
the mixed allocation saw 70% of the verifier's findings target fix
application, against the 16.6% published above. The counters stand as the
reason the discipline exists; they are due for a re-measurement under the
current allocation after release.
