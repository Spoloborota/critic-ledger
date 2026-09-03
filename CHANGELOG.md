# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-08-29

A round now opens against a **signed scope contract** and closes over a
**durable register of accepted risk**. Between those two, the release adds the
measurements that say when a round is going in circles — a defect class that
keeps coming back, fixes that cause new findings, a severity curve that has
stopped falling — and the routes that let a round end without pretending every
finding was fixed.

**One thing a default install now does differently:** observability is on out
of the box, and turning it off is one line (see "Changed"). The plugin still
makes no network calls of any kind, and everything it writes is still a local
file you own. It also changes what a ledger LOOKS like: see "Compatibility" at
the end.

**`SKILL.md` is now a router.** The skill file keeps the gate, the contract's
headlines and the ledger row schema, the modes, the role table and a ten-entry
stage index; the procedure itself lives in thirteen `references/*.md` files
next to it, each read at the point of need by an explicit instruction in the
router. The visible consequence: after a context compaction the orchestrator
re-reads the file of the current stage before its next action, and the router
itself stays inside the platform's re-attachment window. Nothing was
rewritten — every moved line is the old line, verbatim, and a gate proves it.

### Added

- **The round contract, and a gate on it.** `templates/round-contract.md` is a
  new skeleton filled and signed BEFORE the first critic is spawned: the
  object's goals, the pre-signed Non-Goals, the zone map, the lens panel, the
  stopping rule, the declared instrument set and the limitations accepted at
  authoring time. For an object longer than **400 lines** the signed contract
  is a gate — no contract, no round; below that the owner may waive it with one
  word, recorded in the ledger header. The threshold is ours and is marked as
  ours. The contract's text goes into every lens prompt identically and
  verbatim, and the ledger header carries the contract's path and its sha at
  the round's start, so a contract edited mid-round is detectable instead of
  silently replacing the one the round ran under. Amendments made inside a
  running round are numbered, dated, one sentence long, and void without the
  owner's signature where they touch a field the owner signed.
- **Zones, and a ninth cell on the row.** The ledger's findings table gains a
  `zone` column, inserted THIRD: `Z1` mechanically checkable contracts, `Z2`
  normative prose, `Z3` informative prose, taken from the contract's zone map
  and filled by the adjudicator at judgment time — never by transcription,
  which leaves a stub there because a zone is a judgment. What a zone changes
  is the paper and the closure route, never the strictness of a check: severity
  is untouched (a blocker in the lightest zone means the zone map was wrong and
  the row is re-zoned), the deterministic deleted-line pre-pass still emits the
  FULL list for every zone, and a verifier is fresh on every pass in every
  zone.
- **Three more terminal statuses, so a round can end honestly.**
  `out-of-scope-by-contract (NG-<n>, signed <date>)` closes a finding whose
  whole claim falls inside a Non-Goal, on the signature given when the
  Non-Goals were authored and with no live signature asked for at that moment.
  `frozen-carried (stop-rule, <date>)` disposes of a row still open when the
  stopping rule fired: terminal for this round, carried into the next one as a
  re-opened finding, and — unlike a superseding freeze — not a bar to closure.
  `logged-no-action` is the disposition of an informative finding the owner
  logged and chose to act on in no way; it exists only in the new schema, only
  on a `Z3` row, and only through a closing act the owner signs off over at
  most ten rows. A row of the security/PII class travels none of these routes
  without a live signature of its own.
- **Two named non-terminal waits.** `awaiting-signature (nominated <date>)` and
  `awaiting-logged-no-action (listed <date>)` are not statuses but named places
  a row waits: counted and printed apart from an open row, still exiting 1, and
  both ageable — past 30 days the recount prints the row as overdue and the
  orchestrator owes the owner a fork. A permanent wait is banned.
- **Managed residue and the residue register.** `templates/residue-register.md`
  is a new, append-only file that lives at the ROOT of the project's run-folder
  directory and outlives every run: one row per finding NOMINATED into residue,
  with its rationale, its compensating control, a mandatory `review-by` date
  and a status that advances `nominated` → `ratified` → `expired-reopened`.
  Nomination is the orchestrator's act, made at machine speed; it becomes
  accepted RISK only when the owner ratifies it, in an act of at most ten rows
  that writes both sides at once. A blocker may never be nominated. The recount
  reads the register with `--register`, prints the aggregate and the deadline
  warnings, and changes no exit code doing so. The register is a durable write
  outside any run folder, so the privacy and sanitization gates that guard a
  salvaged report guard it too, fail-closed.
- **`templates/set-cell.py`** — the canonical writer of a row's `fix`,
  `verified` and `terminal` cells, and the third mechanical step beside the
  recount and the layout script. It writes ONE cell of ONE row per call,
  addressed from the END of the row, so one rule serves all three row widths;
  the columns the adjudicator owns are deliberately not writable through it. It
  exists because the ad-hoc edit it replaces split rows on `" | "`, silently
  lost a row's empty trailing cells, and did so twice in one round.
- **Class-kill: the second recurrence of a defect class stops being a fix.** A
  `class:<slug>` tag inside the `verdict` cell groups upheld findings by defect
  class; at the second upheld row of one class the recount prints `CLASS-KILL
  DUE`, and the next step for that class is a mechanical gate or a convention
  that kills it — logged as its own ledger row — rather than one more fix. A
  third recurrence with no kill in flight escalates to the owner. The
  second-recurrence trigger is ours and is marked as ours.
- **Fix-injection rate.** `origin:fix-application from:<batch>` in the
  `verdict` cell charges a finding to the batch whose fix caused it, and the
  recount prints the rate per batch — findings caused by a batch's own fix over
  the rows that batch fixed. Where the batch cannot be identified the line says
  so instead of inventing a denominator. The reference points printed beside it
  are from the literature and are labelled as such, not as our measurement.
- **The severity-weighted plateau and an advisory residual-defect estimate.**
  Given two `--prev` ledgers the recount prints a three-round moving average of
  the major+blocker delta, ordered by the ledgers' own round-start timestamps
  and never by the order of the arguments — beside the binary convergence
  streak, never instead of it. Separately, from four declared lenses up, it
  prints a Jackknife capture-recapture estimate of the defects still unfound,
  with the caution that the number is ADVISORY: it enters no stop rule and no
  exit code, and our own field measurements are stated as not comparable to it.
  The lens count it uses is read from the header's machine-form `Lenses:` lines
  and from nowhere else — never guessed from the id prefixes in the table.
- **A per-lens sustained rate, with a shelf share beside it.** Over a window of
  ledgers the recount prints each lens's upheld-over-raised rate, and beside it
  the share of that lens's refuted rows closed by a pre-signed contract
  disposition — the new `shelf:<slug>` tag on a refuted row. The two are
  printed together on purpose: a lens whose claims are shelved by the contract
  is not the same as a lens whose claims are wrong, and no lens is judged by
  its sustained rate alone.
- **The lens-split verification pass, and a `verifiers` column to record it.**
  One verification pass may be executed by N fresh verifiers with
  non-overlapping scopes; the passes table's new column is the count, `1`
  stating plainly that the pass was NOT split. A second pass may also be
  narrowed to the new findings of the first plus a connectedness check of what
  their fixes changed — the **residue-scoped second pass** — but only when the
  first pass was full-scope, returned zero NOT LANDED on the round's original
  ids, and an explicit owner signature for the narrowing is written into the
  ledger. The narrowing is a right, not a default: without that signature the
  second pass runs in full, and no other actor may grant it.
- **`NOTICED OUTSIDE BATCH`** — a required block in the fixer's report, and the
  only channel for what the fixer saw beside its assignment. It carries
  observations to the adjudicator as candidate findings; it never authorizes an
  edit outside the batch.
- **A third value for `Ledger state:`.** Beside `open` and `FROZEN` the header
  now takes the literal `closed <ISO-date>`, written at the closing stage on
  the recount that printed `ROUND CLOSABLE`. It records the closure, it does
  not decide it: the value blocks nothing, a closed ledger recounts exactly as
  an open one does, and a round left awaiting a signature keeps `open`.
- **The worked example grew the new material.** `examples/worked-round/` now
  ships the round contract and the residue register beside the ledger, the
  ledger itself carries zones, the closed header state, the new statuses and
  the `verifiers` column, and its how-to-read legend covers them. Everything
  the new schema added there is invented for the example — with one declared
  exception: the register's first row extends the ledger's sanitized `DC-1`
  thread; no other id, path, date, actor name, rationale or compensating
  control comes from any real round.
- **The round now measures where its time actually goes.** Waiting for the
  owner became a measured orchestrator unit rather than a gap: the trace takes
  **owner-wait spans** under a closed reason vocabulary
  (`owner-wait-signature`, `-authorization`, `-fork`, `-amendment`,
  `-ratification`, `-z3-closure`) and a closed outcome vocabulary (`answered`,
  `refused`, `abandoned`). `round-summary.json` gains a **`stages[]`** array —
  one envelope per stage, `max(ended) - min(started)` over the spans already
  written, with no new span invented to produce it — and **four metrics,
  M8–M11**: the union of the spans' intervals as the round's PARALLELISM (M8),
  the ORCHESTRATOR REMAINDER a stage's envelope leaves uncovered (M9), the
  round's own IDLE complement (M10), and the owner's WAIT as an aggregate
  (M11). Every one of them is `n/a: <reason>` where the data does not support
  it, and none of them can fail a round.
- **The summary states the reviewed object's scale.** `round-summary.json`
  carries an `object` field with `lines_at_pin`, `changed_lines` and
  `files_touched` — GIVEN to `rollup.py` as CLI options and never measured by
  it, `null` for each one not given, and not one file name among them.
- **A token total with no breakdown is kept instead of dropped.** Where the
  completed `Agent` tool result reports only an aggregate, the span records it
  with `tokens_source: "agent-tool-result-total"`: the total is carried, the
  four-counter breakdown is absent rather than invented, and a round made
  entirely of such spans is still fully covered.
- **A third counter in the fixer's outcome slot.** Beside `fixed:<n>` and
  `unworkable:<m>` a fixer span may now carry `notfound:<k>`, the count of its
  `premise-not-found` returns, so the batch's three outcomes roll up instead of
  two.
- **`Process prefixes:` — a ledger header field declaring what is NOT a lens.**
  The fixer's `NOTICED OUTSIDE BATCH` channel and a class-kill gate write rows
  under a prefix shaped exactly like a lens's, and no reader could tell them
  apart machine-side; the field names them, keeping them out of the lens count
  `k` by declaration rather than by a guessing filter. The literal `none` and
  an absent field mean the same thing, which is why every ledger written before
  it recounts unchanged. A field present but reading as neither is a structural
  error, not a silent "none".

### Changed

- **`observability` is on by default.** In 0.2.0 the option shipped switched
  off, and a round measured nothing until the user turned it on; the counts it
  produces are worth having on the round that needs them rather than on the
  round after, so the manifest's `"default"` is now `true`. What the flag does
  is unchanged, and so is the privacy invariant it was written under:
  everything it produces is a local file in that round's own folder —
  `trace.jsonl` and `round-summary.json` in `.critic-ledger/<run>/`, plus the
  cross-project `rounds.jsonl` in the plugin's data directory — nothing is sent
  anywhere, there is no endpoint and no upload. Opting out is one line:
  `"observability": false` in `pluginConfigs` in your user `settings.json`, or
  `--config observability=false` at install, or `/plugin` → Configure at any
  time. With it off nothing happens at any stage: no file created, no directory
  created, no number collected.
- **The `.gitignore` entry is no longer written silently on a project's first
  round.** `.critic-ledger/` is still entered into the project's `.gitignore`
  and confirmed before the run folder is created, but on the FIRST run in a
  project the round now states the line to be added and the file, and waits
  for the user's explicit word. The question has exactly two outcomes:
  consent — the entry is written and the round proceeds; refusal OR no answer
  — fail-closed, the round does NOT start and no run folder is created.
  Silence is not consent, and there is no third outcome. Every later
  invocation still checks the entry and restores a missing one.
- **`copy-project.sh` no longer takes its fastest path when the source carries
  git-ignored content** — a user-visible change of behavior. The strict clone
  (step 1) copies everything on disk, so against a project mixed with ignored
  runtime state it would WIDEN what the critics see, unannounced. The script
  now runs a git pre-flight and, where ignored content exists (or where the
  pre-flight itself fails), skips step 1 and builds the copy from the
  git-known file list instead, listing what it excluded and why in the copy's
  manifest. Nothing is narrowed in silence: a critic must know what it never
  saw.
- **The id contract is relaxed.** A finding id's prefix may now be several
  dash-joined, letter-led segments — `V-CIT-1` recounts exactly as `VA-1` does
  — so a verifier's prefix can carry the lens it re-checked. Matching stays
  exact, which is why one prefix never absorbs another's rows.
- **The verifier is not shown the fixer's justification, and never asks for
  it.** Its prompt carries the criterion cells, the diffs and the round's
  verbatim critic salvages — not the fixer's report and not its reasoning — so
  a pass answers "would a fresh critic still file here?" rather than "were the
  edits applied as described?". The verifier also gained one narrow second
  duty, the pre-commit read-back: a single command run against the
  not-yet-committed tree, with no verdicts and no deleted-line walk, which
  exists because the fixer has no shell and cannot execute a command-and-exit-
  code criterion at all.
- **The fixer reproduces the defect before editing** and stops where the
  premise no longer holds, instead of applying a fix to text that has already
  moved. Its outcome vocabulary grew from two values to three: beside `fixed`
  and `criterion-unworkable` a report may now say `premise-not-found`, given
  when the defect is not in the current text and nothing was edited for that
  id. The new value takes the same route as the second one — back to
  adjudication, never straight into the next fix batch — and the two count
  together against that id's limit of returns.
- **A security/PII finding is re-checked independently before the owner
  signs.** The conclusion comes from an actor or a tool OTHER than the one that
  proposed accepting or refusing it, and it is recorded in the register row.
  The owner's own ruling does not cancel the re-check — that is the case the
  re-check exists for — and such a row never rides inside a batch act: it
  reaches the owner one at a time.
- The test suites and the counts CI states for them were re-derived from the
  tree rather than carried forward: the pytest characterization suite is 1051
  tests and the recount regression suite 79 cases, and `CONTRIBUTING.md` now
  prints the command that re-derives each number beside the number itself.
- **The closed-round regression no longer ships with the suite.** Its cases
  drive `trace.py` and `rollup.py` over the run folders of rounds already
  closed on disk; inside `tests/unit/` their fixtures could only be written
  as literals — folder names, per-round statistics — and the cases always
  skipped, because no clone of this tree carries those folders. What the
  published suite gains is self-containment: it tests only what this tree
  contains, it carries no round metadata from anywhere else, and two new
  payload invariants hold it to both.

### Removed

- Four files no longer ship: `SECURITY.md`, `.editorconfig`,
  `tests/COVERAGE-MATRIX-0.2.0.md` and
  `tests/regression-transcript-2026-08-09.txt`. The editor configuration
  configured editors rather than the plugin; the matrix and the transcript
  were point-in-time snapshots of a suite that supersedes them on every run.

### Compatibility

- **A ledger in the new nine-cell schema is not readable by an older recount.**
  Given a v3 table, the 0.2.x script reports `findings header has 9 cells; the
  table must be 7-cell (legacy) or 8-cell (with criterion)` and exits 2. The
  incompatibility is one-way and deliberate: THIS release's recount still reads
  both older widths unchanged — v2 (8 cells, with the readiness criterion) and
  v1 (7 cells, without it) — and no exit code moved for either. A ledger
  declares its width in the header's `Row schema:` field, and a declaration
  that contradicts the table's own header is a structural error rather than a
  guess.

## [0.2.1] - 2026-08-27

- **The Dependabot configuration no longer ships in the published tree.**
  Dependency-upgrade pull requests are raised in the development repository
  instead.
- **Comments in the CI workflow were reworded** to describe the current
  release process.

## [0.2.0] - 2026-08-11

Optional, off-by-default measurement of a round's own cost, plus the behavioral
fixes a characterization pass found in the shipped scripts.

**Nothing here changes what a default install does.** The measurement is behind
a flag that ships `false`; with it off no new file is written and no new code
path runs. The plugin still makes no network calls of any kind.

### Added

- **An `observability` option, off by default.** Declared as `userConfig` in
  `.claude-plugin/plugin.json` (`boolean`, `"default": false`) and read by the
  skill through `${user_config.observability}`; anything other than the exact
  literal `true` means off, including an unsubstituted placeholder. Set it
  without a dialog at install time —
  `claude plugin install … --config observability=true` — or later through
  `/plugin configure`.
- Two reference scripts under `skills/critic-ledger/templates/`: `trace.py`,
  which appends and validates one span per unit of work into that round's
  `.critic-ledger/<run>/trace.jsonl`, and `rollup.py`, which turns that trace
  plus the fix-ledger into a `round-summary.json` beside the ledger, five
  efficiency metrics, and an identifier-free one-line-per-round projection
  appended to `~/.claude/plugins/data/critic-ledger-*/rounds.jsonl`. Local files
  only; no field of either artifact carries free text, every metric that cannot
  be computed reports `n/a: <reason>` instead of a number, and `trace.py` is the
  one script here that never fails closed — a broken trace never fails a round.
- `skills/critic-ledger/SKILL.md`: an "Observability (optional, default off)"
  section carrying the flag read, the privacy invariant and the `n/a` rule, plus
  one instruction per round stage on what that stage records.
- `recount.py`: a severity distribution over the findings table; `started` /
  `ended` columns on the verification-passes table with a time-indexed defect
  curve; an optional `--trace <trace.jsonl>` summary line. Existing v1 ledgers
  keep recounting unchanged, and no exit code moved.
- The ledger template's v2 header lines, the passes table's `started` / `ended`
  cells, the round's verifier-prefix beside the lens prefixes on the `Lenses:`
  bullet, and a paragraph stating that the trace, not the ledger, is the machine
  copy.
- README: a rewritten Privacy section that lists both new artifacts' **complete**
  field lists — including the two identifiers a "counts only" file would
  otherwise hide, `agent_id` and `id_prefix` — says that the cross-project
  rollup accumulates across projects until deleted, and names deleting each file
  as its complete opt-out.
- Test coverage for all of the above: the shell regression suite goes from 28 to
  38 cases, the pytest characterization suite from 230 to 526 tests.

### Changed

- The skill no longer sets `disable-model-invocation`, so a plain prose request
  can start a round. The Gate section and the description's "explicit user
  request" requirement remain the guard; the change is recorded rather than
  silent because it widens what can trigger an expensive procedure.
- The four agent definitions demote their model self-report to a **fallback**:
  the platform-resolved model is the source of record where one is available,
  and a self-reported model is labelled as such.
- `recount.py` invoked with no argument now exits 2 with a usage line instead of
  a traceback; `-h` / `--help` still print the docstring on stdout and exit 0.

### Fixed

Found by a characterization pass over the shipped scripts and closed under this
project's own fix-ledger discipline:

- Uniform help across `recount.py`, `check-frontmatter.py` and `transcribe.py`:
  `-h` / `--help` print the docstring on stdout, exit 0, and win over any other
  argument. `validate-report.py -h` likewise exits 0 rather than 2.
- `recount.py`: an unreadable ledger exits 2 with a named diagnostic instead of
  raising; `--prev` without a following path is a usage error; a machine
  signature date must be a calendar-valid ISO date, so `2026-02-31` no longer
  passes as a signature.
- `recount.py`: a malformed `ended` timestamp in the passes table is reported by
  name and the time axis suppressed for that run — never silently, and with no
  change to the exit code.
- `cleanup-scratchpad.py`: the size-mismatch note fires when either side is
  zero, and `--older-than-hours` is echoed back without a spurious trailing
  `.0`.
- `check-frontmatter.py`: repeating `--strict-portable` is idempotent.
- `deleted-lines.py`: because `--paths` is greedy, a command that put commits
  after it now gets a diagnostic naming the tokens `--paths` swallowed.
- `validate-report.py`: docstring-bounds detection no longer depends on line
  width, and multi-item diagnostics use consistent separators.

### Release housekeeping

Internal CI tooling was synchronized with this release ahead of publication;
no user-facing behavior changed.

BACKFLOW-ACK: .github/workflows/tests.yml public=8323da866a031d600129412f31e514cd04c82569 dev=4eade4cb5e42fd1dbbe8fdb3064afcae3b8bf8ee

## [0.1.0] - 2026-08-10

Initial public release.

**Honesty notes.** The README's headline effectiveness figures predate the
current actor allocation (fixes used to be applied by the judging session; they
are now applied by a separate fixer subagent) and carry that caveat in place.
The exception is the single-round 70% data point, which was measured under the
shipped allocation — one round, n=10, not a headline figure. The cost/time
instrument those re-measurements were waiting on **shipped in 0.2.0** — the
optional `observability` flag and its trace/rollup scripts — but the
re-measurement itself **has not been taken**, and neither has the automated
evals suite been built. Until both exist, the headline figures stay caveated
exactly as they are.

### Added

- The `critic-ledger` skill: adversarial critic rounds on a plan or an
  implementation, driven to closure through a fix-ledger — parallel read-only
  critics under derived non-overlapping lenses, refute-by-default adjudication
  with a readiness criterion per finding, targeted fix batches applied by a
  separate fixer subagent, independent per-finding verification by a fresh
  verifier on every pass, a measured convergence signal, and programmatic
  closure by a recount script.
- Four subagent role definitions (`agents/`): plan-critic, impl-critic, fixer
  (no shell access by construction), verifier.
- Seven reference scripts (`skills/critic-ledger/templates/`): ledger
  recount, mechanical findings layout, report acceptance, project copying for
  critics, scratchpad cleanup, deleted-line pre-pass, frontmatter portability
  check — plus the ledger and prompt templates.
- A sanitized worked example (`examples/worked-round/`) derived from real
  rounds run on this repository, with a how-to-read legend.
- A 28-case regression suite for the recount script (`tests/`), run by CI.
- A 218-case pytest characterization suite (`tests/unit/`) pinning the CLI
  behavior of all six template scripts — argv, stdout, exit codes and
  filesystem effects — run by CI across Python 3.11–3.14.
- Strict static tooling, pinned in CI: ruff (`select = ALL` with a documented
  ignore list in `pyproject.toml`) plus `ruff format`, `mypy --strict` with
  opt-in error codes beyond strict, `shellcheck` over both shell scripts in
  POSIX `sh` dialect, and an informational run of the `ty` type checker; the
  scripts carry PEP 723 inline metadata and full type annotations, floor
  Python 3.11.
- A subprocess-aware coverage gate over the template scripts: the
  characterization suite runs them as real subprocesses, so coverage.py is
  configured with `patch = ["subprocess"]` and a `fail_under` floor, and CI
  publishes the coverage table to the job summary.
- A hardened CI workflow: every action pinned to a full commit SHA with its
  release tag in a trailing comment, least-privilege `permissions` at the
  workflow level, `persist-credentials: false` on every checkout, a `zizmor`
  audit of the workflow itself, and a Dependabot configuration that keeps the
  SHA pins maintainable.
- A `lychee` link check over the published Markdown, run in CI.
- `SECURITY.md`: scope of the shipped code, private vulnerability reporting,
  and what a reporter can expect from a solo-maintained project.
- `docs/why-critics.md`: the discipline's origin story, the defect-to-rule
  provenance, and the proven/not-proven ledger.
