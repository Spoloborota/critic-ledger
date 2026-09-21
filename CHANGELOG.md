# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-09-21

**Honesty notes.** No efficacy figure is claimed; `docs/why-critics.md`
carries the withdrawn figures as provenance, with the newer 91.3 % by lens
beside the 99.4 % it does not confirm, and the measurement the README names
has not been taken.

### Removed

- **The round's own telemetry — span writer, rollup, transcript reader, the
  `observability` option and its three files — is removed in full.** The
  bundled OpenTelemetry receiver stays.
- **The router no longer tells the history of the ledger's row forms.**
  Which older widths stay readable, and the header field that declares a
  ledger's form, are stated by the ledger template and by the recount
  script's own help text.
- **The router no longer repeats what stage 0 records about the
  subagent-model variable;** the stage-0 file states it.

### Added

- **A blinded second look has its own verdict vocabulary,** under the
  `re-check` name.
- **`scripts/ledger_md.py`** (the move of this and the other eight
  executables from `templates/` to `scripts/` is described under Changed) —
  one owner for the ledger's row and header
  grammar, its cell escaping and its atomic region writer. `recount.py` and
  the five modules it is split into (`ledger_model.py`, `statuses.py`,
  `structural_checks.py`, `metrics.py`, `report.py`), `set-cell.py`,
  `transcribe.py`, `validate-report.py` and `deleted-lines.py` all import it
  from the same folder instead of carrying hand-copied duplicates of the row
  schema. It also
  runs as a command: `ledger_md.py new` instantiates a working ledger from
  the template with every authoring comment stripped.
- **An addressable heading grid** through the adjudication, fix, verification
  and closure stages, so a step can be cited by name rather than by scrolling.
- **The receiver's own lines are versioned.** Every appended line now
  carries `"v": 1`.
- **The receiver keeps its own file, and keeps it private.** It rotates the
  file aside at `--rotate-mb` (default 256) between two lines, under the
  same lock as the write, into `<stem>.<UTC stamp>.jsonl` beside the live
  one, and `install` forwards the setting into the service unit; the
  directory is created `0700` and the file `0600`.
- **`install --python <path>`** names the interpreter the service runs, and
  an interpreter that sits under a version-stamped directory is refused
  with that option named, rather than guessed at.
- **`status` prints the file's size and the age of its last line**, and a
  file that did not grow over the sample second is now called `idle`
  rather than `static`.
- **The installed service keeps a log.** Both streams are written beside
  the out file (`StandardOutPath`/`StandardErrorPath` on macOS,
  `StandardOutput=append:`/`StandardError=append:` on Linux), so a crash
  leaves a reason rather than a file that stopped growing.
- **A failed write is answered, not hung up on:** the receiver replies 500,
  prints the reason on stderr and keeps the connection, and a declared body
  larger than 16 MiB is drained and refused with 413 without being stored.
- **A service that crashed is restarted; one that exited cleanly is not** —
  `KeepAlive` in its dictionary form with an explicit `ThrottleInterval` on
  macOS, `Restart=on-failure` with `RestartSec` on Linux. A port that
  cannot be bound is named and exits 3 instead of looping in silence.
- **The recommended environment gained the exporter's diagnostics flag** and
  the three content flags as explicit zeros, so an inherited shell
  environment cannot turn them on.
- **A fourth agent, `critic-ledger:executor`, with its spawn prompt
  `templates/executor-prompt.md`.** It runs, exactly as written, the
  commands a critic hands over in `impl` mode, on a scratch copy made for
  them, the orchestrator's own probe of a finding (6.26), also on a scratch
  copy, and a readiness criterion whose command mutates the live working
  tree. It is blind to the findings, their reasoning and their verdicts,
  writes nothing itself but raw output under the run folder's `probes/`, never
  runs a state-changing git command, and only one executor at a time works
  against any one tree. The router's table of roles gains its row.
- **`scripts/extract_final.py`** writes a subagent's final message verbatim
  from its task transcript — the message of its hand-back call where there
  is one, else its last non-empty assistant text — under one header line,
  and prints only a size line; a transcript holding neither prints
  `no report found`, writes nothing and exits 2. Stage 4 salvages with it
  where the platform keeps such a transcript.
- **`ledger_md.py set-header` and `ledger_md.py add-pass-row`.** The first
  writes one header field — `Ledger state`, `Precedents file`,
  `Contract amendments`, `Exit family` or `Scratchpad not cleaned`, and no
  other name — and refuses `Ledger state: closed` on a ledger that is frozen,
  whose findings table carries rows the parser rejects, or that still has
  open rows, rows awaiting a signature or rows awaiting an act of the owner. The second adds one row to the verification-passes table
  and refuses a row of another width. Both refuse a closed ledger and exit 2
  on a refusal. Stages 2, 6, 7 and 9 now say that these fields are written
  with `set-header`, never by hand, that every verification pass is a row
  added with `add-pass-row`, and that the closed state is the round's last
  header write.
- **A `probes/` folder in the run folder** holds the raw output of the
  executors of critics' commands, one file per command set, under the same
  sanitization caveat and privacy gate as the salvaged reports.
- **The residue register takes a fourth status, `withdrawn <date>`,** for a
  nomination the owner withdraws. The register aggregate prints it,
  `NOMINATION OVERDUE` names that form, and the finding goes back to stage 6
  of its round while that round is open, or enters the next round on the
  same object as a re-opened finding once that round is closed. A row of the
  security/PII class is withdrawn only on the owner's live word given to
  that row alone. Only `expired-reopened` may carry a cycle counter; a
  counter on any other status is a structural error.
- **Stage 2 has its own heading grid** — sections 2.1 to 2.4: scope,
  lenses, scratchpad copy and the round profile — so its steps are cited by
  number like those of stages 6 to 9.
- **Criterion-authoring gets its own rules at adjudication and on the
  readiness scale.** A criterion is scoped to the object's declared paths
  and never to a containing directory; a finding claiming "every" gets a
  completeness check and not a sample of literals; an absence criterion
  names the negation trap and the legitimately-kept quotation before it is
  written; a phrase-presence check against a hard-wrapped object states its
  wrap-tolerant form, the `0`-or-`1` limit that form carries and the `--`
  terminator a dash-leading pattern needs; and no criterion pins an absolute
  line number where the object can grow.
- **A row a fixer reports through `NOTICED OUTSIDE BATCH` is adjudicated
  refute-by-default,** exactly as a lens critic's row, and the stage says so
  instead of leaving it to be inferred.
- **A precedent that narrows a gate after it has fired carries its evidence,**
  and the closing pass's fresh verifier re-derives it from the object's files
  rather than re-running the narrowed gate.
- **A critic's own confirm-or-kill command may be malformed,** and the
  executor's existing correction rule is named as the sanctioned path.
- **The connectedness pass reads the ASSEMBLED downstream text,** not only
  the items that prescribe it — a prompt, a stage file or an agent
  definition is read once in the form it will actually have.
- **A `plan`-mode critic re-derives every claim about a script's or git's
  behavior** instead of taking it from the object's prose: it reads the
  cited code or runs the check read-only, and files `UNVERIFIED` when it
  can do neither. The verifier's mandate states the same obligation, and
  neither scales it down with severity or zone.
- **`spec-delta-candidate`** — a verdict-cell literal for a finding closed
  because the object's own signed text prescribes what it objects to. It
  changes no status and no script reads it; closure prints the tagged rows
  as a question list back to the object's author.

### Changed

- **`transcribe.py --stdout` now prints the nine-cell row that the shipped
  ledger template expects**, with the zone cell carrying the `·` placeholder.
  It used to print the eight-cell form, which a fresh ledger refused as a
  malformed row.
- **A batch or a pass is closed by `set-cell.py` calls chained in one Bash
  call**, by the orchestrator itself.
- **The interpreter recorded in the service unit is no longer resolved**
  through a version-stamped directory: the stable symlink is written, so an
  upgrade of that interpreter no longer leaves the service pointing at a
  deleted file.
- **After a clean exit the receiver's service is not restarted.** It used to
  be restarted whatever had happened, which turned a refused start into a
  loop that repeated for as long as the user was logged in.
- **A fixer may not edit the ledger.** It is an append-only record of what
  happened, written by the scripts and the orchestrator; the fixer role now
  says so in as many words.
- **`set-cell.py --column`** writes the `verdict`, `zone` and `criterion`
  cells. This CORRECTS a sentence in the 0.3.0 notes below, which says the
  columns the adjudicator owns "are deliberately not writable through it":
  they are writable now, through one named flag, and the released entry is
  left as it was written.
- **The copy taken for the critics excludes untracked directories,** listing
  every entry and its class before the copy runs, so a virtual environment or
  a cache can no longer ride along into a review copy.
- **The stopping rule prints its own line.** The convergence block now
  separates the numbers from the advice and states the verdict streak as
  `met | not met` with a reason — and never says `met` on data it could not
  read.
- **The recount says when a defect class is being worked on.** A class with a
  kill row in flight prints `CLASS-KILL IN FLIGHT` or `DONE` instead of a
  false `DUE`.
- **Cells escape a pipe character at the writer,** so a finding whose text
  contains one no longer breaks the row it lives in.
- **A FROZEN ledger now refuses every writer, exactly as a CLOSED one
  does.** `ledger_md.py` holds the two write-refusing states in one
  tuple, and the recount's `ledger_model.py` reads its frozen pattern from
  there instead of a private copy — the exit code and the printed message are unchanged.
- **`scripts/deleted-lines.py` prints the repository it resolved** as its
  first line, `REPO <abs-path>`, before the first `COMMIT` record — a walk run
  from the wrong directory is visible at a glance. A git directory or a bare
  repository that has no working tree is now refused with exit 2, where the
  script used to list deletions there.
- **The nine executable files moved from `skills/critic-ledger/templates/` to
  `skills/critic-ledger/scripts/`;** the six prompt and skeleton templates and
  `templates/otel/` stay where they were, and `recount.py` is split into
  `ledger_model.py`, `statuses.py`, `structural_checks.py`, `metrics.py` and
  `report.py` beside it. The exit codes are unchanged, and so is the printed
  output except in two places: the help text of `recount.py` and the refusal
  `set-cell.py` gives for an id with no row now name the transcriber under
  `scripts/`.
- **A round runs under a profile — F, M or L.** Section 2.4 of stage 2
  defines the three profiles and names, by section, what each sets: whether
  the second verification pass runs by default and how wide it is, when the
  connectedness pass is planned, and how the fix batches are cut. The
  profile is assigned at the close of stage 6 from the recount's upheld
  count, or fixed in advance in the contract's stopping rule, and it is
  written into a new `Profile` line of the ledger header; the contract
  template carries the same field. A profile changes no model, no lens
  already spawned, no severity route and no signature: a NOTICED major or
  blocker keeps its route under every profile (6.22). The second-pass
  threshold of 9.2 now counts confirmed findings — upheld rows as the
  recount prints them — and 9.4 states the second pass under each profile.
  Stage 8 plans the connectedness pass once per round (8.3) — after the
  last fix cycle under profile L, on the user's word under F and M — and
  that pass reads the whole object for contradictions between what the
  fixes changed and what they did not. The README states the profile in one
  sentence.
- **The verification-only run modifier of the round contract is described in
  the router:** it is not a third mode but a round of either mode whose
  stopping rule sets fix batches to zero — stage 7 is skipped, stage 8
  verifies the criteria written at stage 6 against the object as it stands,
  and the ledger's `Mode` line still reads `plan` or `impl`.
- **A fix batch is coherent by zone and by kind of edit** (7.6): it gathers
  findings that edit one file or neighbouring files of one zone of the
  contract's zone map, and it never mixes creating a new artifact with
  editing existing files. The long form of the contract says the same.
- **NOTICED minors close a fix cycle as one tail batch** (7.7), after the
  last planned batch and before the verification pass, instead of one
  micro-batch per wave; a NOTICED major or blocker never waits in the wave.
  Section 7.8 points to the batch cut each profile takes in stage 2.
- **A fixer resumed across many batches is replaced by a fresh agent** at
  the nearest checkpoint — the third batch it would open — carrying a
  compact state summary instead of its inherited history (7.3).
- **The form of a readiness criterion is stated in 6.25.** A criterion that
  carries a number, a literal or a code is a command and its printed
  result, with no pipe inside the literal; its draft is run against the
  object before the row reaches a batch, and the value that run printed is
  written into the finding block handed to the fixer. A criterion pinning a
  rule for later readers names content, never a date, a count or a list.
  The blind re-check of a security/PII ruling receives the ruling and its
  own prompt as separate files or reads (6.15).
- **A critic's finding that depends on a run it did not perform is filed as
  an `UNVERIFIED` hypothesis,** with the exact command whose output confirms
  or kills it, and it is adjudicated on that output. Critics cite by an
  immutable anchor — a section number or an id — where the object has one.
- **A verifier's new finding opens with exactly one line
  `<id> | <severity> | <claim>`,** the row the transcription script reads;
  the verifier's definition and prompt say which forms are transcribed,
  which are named under `SKIPPED LINES`, and which are dropped as prose.
- **The fixer re-reads the whole block around every edited sentence, and it
  never estimates a measured value:** a count, a hash or a set of line
  numbers an edit depends on is measured before the batch and written into
  the finding block, and a block that needs one and lacks it is returned as
  `criterion-unworkable`.
- **The verifier never runs the object** — its build, its entry point or its
  tests — as evidence of its own; the one command it executes is a
  criterion's own command. A criterion that mutates a scratch copy of the
  object may be run by the verifier on a copy made for that run and removed
  after it; the repository itself it never mutates.
- **The read-back of a fix batch re-reads the changed lines of the batch's
  diff** — `git diff` of the uncommitted tree, never whole sections — in
  stage 7 and in the verifier's definition alike.
- **The contract template's stopping rule carries a block of pre-signed
  answers:** ten forks, each answered in advance or left as `ask`, which
  keeps the round stopping for the owner. A row of the security/PII class is
  exempt from every answer that writes a signature literal, and 9.21 takes a
  pre-ratification of nominated minors as the user's act for those rows.
- **`references/templates-and-scripts.md` ends with one table of exit
  codes** for `recount.py`, `set-cell.py`, `transcribe.py` and
  `validate-report.py`, and its `recount.py` entry leaves the contract of
  cell values to the script's own docstring, printed by `recount.py --help`.
- **The router's inventory names `scripts/ledger_md.py` and the five
  modules `recount.py` is cut into,** and the new salvage extractor;
  `cleanup-scratchpad.py` is described there as removing the round's scratch
  copies and nothing else.
- **The router defines the role that drives the stages once,** before its
  table of roles, and says that the stage files' name for that role asserts
  nothing about which actor implements it.
- **Rules the stage files repeated now live in one place, with a pointer
  where they were repeated:** the dispatch of an agent, the fallback where
  no agent registry exists included, lives in the router; how a ledger cell
  is written with `set-cell.py`, and that a spawned agent never writes one,
  in 7.17 and in the script's inventory entry; the blind re-check of a
  security/PII ruling in 6.15; the ban on nominating a blocker in 9.19; the
  wish that is not a criterion, and the cell of a refuted or refused row, in
  6.25; the private-repository gate that 9.20 re-runs, in stage 1; the slug
  alphabet of the `origin:` and `shelf:` tags, in 6.11.
- **The inventory and the stage files no longer describe the same thing
  twice:** what each step of the copy keeps and strips is the copy script's
  entry, how `{round_contract}` is filled is stage 2's rule, the deleted-line
  list handed to the verifier is described by its script's entry and by 8.6,
  and sentences that stage 2, 3 and 5 repeated word for word from the
  inventory stay in the inventory alone.
- **The contract's own candidate lists** — residue carried in, known
  limitations, findings already disposed of — reach a lens only as part of
  the contract, and are never copied into another file the critics read.
- **Stage 8 reads the rework share of the last fix cycle alone** beside the
  share over all the round's batches, and that last-cycle share decides
  whether a later pass re-inspects in full.
- **In `impl` mode the executor of a critic's commands starts as soon as
  that critic's report is salvaged** (6.26), one per arriving report, on a
  scratch copy made for that report's commands; every command is first read
  against the bound of stage 3, and the outputs wait under `probes/` until
  adjudication begins.
- **Commands a critic hands over are run as written** on their scratch copy;
  a command that cannot run as written and whose intent is unambiguous is
  run once more in the corrected form, both outputs kept, and an ambiguous
  one goes back to its finding as `UNVERIFIED`. Critics write every command
  for a POSIX shell with every argument quoted, touching nothing outside the
  scratch copy — no state-changing git, no network, no write elsewhere.
- **A readiness criterion whose level-1 command mutates what it runs against
  has two forms** (the readiness scale). Against a scratch copy the
  verifier runs it on a copy made and discarded for that run. Against the
  live object an executor runs it at the moment 7.18 fixes, and the tree is
  proven left as it was found by a snapshot of its files and index taken
  before and after; on a difference the batch is not committed, the first
  snapshot is restored in a fixed order, and the row returns to
  adjudication as `criterion-unworkable`. No verification pass of stage 8
  runs such a command again.
- **Stage 9 names the closing call of `cleanup-scratchpad.py`** — the dry
  run whose plan is read, then the confirmed call — which removes every
  scratch copy the round made under the scratchpad root; the ledger's
  `Scratchpad not cleaned` field records a refusal, sanitized first, or
  `cleaned <date>`.
- **The run folder's `precedents.md` is created at the first adjudication
  batch,** never before stage 6 and never empty, its first line naming why
  it was opened.
- **A refresh of the installed copy is visible.** The inventory says that
  what changed between two installed copies is the `Unreleased` section of
  this file and the version stamp of the copy's manifest; stage 0 has a
  consumer project re-derive its own carried-over notes against a refreshed
  copy before stage 1; and stage 7 lets the consumer's commit convention
  govern the title of a batch commit, the finding ids in the message being
  the only requirement.
- **The recount's verdict-streak line adds `report-only, no exit code`**
  whenever it prints `not met`.
- **The instruction prose of every header field of the ledger template is
  now inside comments,** as are the explanations under its readiness and
  verification-passes sections, so `ledger_md.py new` writes a blank ledger
  that keeps only the field lines and the two vocabulary blocks — the
  terminal statuses and the named non-terminal waits.
- **The two upper segments of a copy's path are created by the caller**
  (`mkdir -p` on the parent of `--dest`) before `copy-project.sh` runs; the
  script creates only the last segment.
- **Where the round contract's own location is git-ignored,** its text is
  placed byte for byte into the copy as `ROUND-CONTRACT.md` — sanitized
  first, fail-closed, and removed together with the copy — so the pointer
  form of `{round_contract}` stays usable; a contract nobody placed leaves
  the text form.
- **A critic's severity word is one of three literals,** and a skipped
  header line that names a real finding gets its row by the mechanical
  route: one corrected header line, whose claim opens with
  `transcription-note:` and names the salvage's `file:line`, is written into
  a separate file and transcribed — the salvage itself stays verbatim.
- **Stage 6 names the terminal literal of a row nominated into the
  residue,** `accepted-residue user-signed <date>`, which every recount run
  checks.
- **`docs/why-critics.md` and the README say what the counted evidence is:**
  two normative documents, code having since passed through impl rounds
  without a control arm; the premium of a fresh verifier over a continued
  one is unmeasured; and the deleted-line count behind the fix-loss figure
  is the source's ~130.
- **In the heading grid, section numbers 6.29 and 9.28 are retired and stay
  unused;** no stage is renumbered to fill them.
- **A critic's commands are one command per Bash call.** The spawn prompt
  now says so, for the commands a critic hands over and for those it runs
  itself in `plan` mode: a chain stops at the first non-zero exit, and every
  check after it silently does not run.
- **A fixer marks a value it did not execute.** Having no shell, it writes
  `(inferred from code, not executed)` beside any exit code, output or count
  that did not reach it as a value measured before the batch.
- **An instrument the round contract declares for cross-checking a ruling
  names the marker its record's format is recognized by,** or the
  git-history fallback that re-derives the text — so a record that changed
  shape is not read as a ruling that was never there.
- **A survival or completeness list a contract declares is copied from the
  ratified text that defines it,** and names the token shapes it sweeps or
  says which it does not. The contract's long form carries the rule.
- **The orchestrator's own shell bookkeeping is held to the hygiene it
  requires of others** — `printf '%s'` rather than `echo` for generated
  content and dividers, a quoted token where it begins with `=`, a quoted
  array rather than a bare `$VAR` for a list or a command. The platform
  notes say so.

### Fixed

- **Stage 9's two split sentences are rejoined under the heading each began
  in**, `copy-project.sh --help` now states the STEP1/STEP2/STEP3 order and
  the `--run-id` rule, and the instruction prose of eleven ledger-template
  header fields (Ledger state, Lenses, Verifier passes, Zone map, Exit family,
  Previous run, Round contract, Contract amendments, Round-started, Process
  prefixes, Residue register) is now inside comments so `ledger_md.py new`
  strips it; the status vocabulary (Terminal statuses, Named NON-terminal
  waits) stays in the blank by design.
- **The writing scripts no longer fail quietly, and no longer refuse a
  whole file over one line.** `set-cell.py` refuses a value carrying a pipe
  LOUDLY — naming the cell, the position of every pipe and the escaped form
  it deliberately does not apply — where the rejection used to be visible
  only to a later recount. `transcribe.py` now parses per LINE: a header line
  whose severity is not one of `blocker`/`major`/`minor` is listed under
  `SKIPPED LINES` with its location while the well-formed lines of the same
  file are transcribed, and it recognizes three header forms — the table row,
  the same row under a list marker, and a `## <id> — <title>` section whose
  block carries a `Severity:` field. `recount.py`'s convergence signal is
  severity-aware, as the rule it reports always was: new findings a pass
  names as minor leave it clean, major or blocker ones do not, and a count
  whose severity nothing names is never read as minor.
- **An untracked directory is kept out of the copy even when the project also
  carries git-ignored content.** The copy's untracked-content pre-flight used
  to run only where the ignored-content gate had found nothing, so on the
  ordinary repository — which has both — the exclusion set it produces was
  never written and a `.venv/`-class subtree reached the critics one file at
  a time. The pre-flight now runs in either case.
- **The file under `--object-only` is no longer listed as excluded while
  being present in the copy.** Past the untracked loose-file limit the copy's
  record named the object `untracked-volume` although the copy kept it; it is
  now recorded as `untracked-kept`, which is what actually happened.
- **A DIRECTORY under `--object-only` is kept too, and said to be kept.** The
  same false record one level up: an uncommitted folder named as the object
  was recorded `untracked-volume` and put into the exclusion set while the
  file list kept every file inside it. A directory that is the object is now
  recorded `untracked-kept`, and one that is not is excluded exactly as
  before.
- **`transcribe.py` refuses a CLOSED ledger.** It was the one writer of the
  payload that never read `Ledger state:`, so a salvage pointed at a finished
  round appended rows into it and exited 0. It now refuses in one line,
  before anything is written, through the same freeze the cell writer obeys.
- **A cell value carrying DEL is refused like every other control
  character.** The refusal tested the ordinal against the C0 block, and DEL
  sits above it, so the one control character named by no other rule passed
  into a cell of a file kept as evidence.
- **A corrupted compressed body is recorded, not dropped on the floor.** A
  `Content-Encoding: gzip` body whose header is valid but whose compressed
  stream is damaged raises `zlib.error`, which is not an `OSError` and was
  not caught: the receiver answered nothing, tore the connection down and
  wrote no line, while its whole promise is that a body it cannot read is
  still counted, by length and with the encoding it declared. It is now
  answered 200 and recorded like every other unreadable body.
- **The receiver's file is private from the instant it exists.** The mode
  is now carried by the syscall that CREATES the file instead of a `chmod`
  after the first write, so no window remains in which an
  identity-carrying line sits on disk under the umask's wider default; a
  process killed inside that window used to leave the file world-readable
  for good, since nothing looked at the mode of a file that already
  existed. `serve` also narrows an existing file once at startup, taking
  group and world bits off and never adding a bit back.
- **`templates/otel/collector.yaml` stops claiming the two capture paths
  write the same file.** Its header comment said the reader cannot tell
  which of the two wrote a file; they are not identical, and the comment
  now states what each one writes — the bare OTLP envelope from the
  collector, a wrapped envelope from the receiver — and that the reader
  tells them apart by shape.
- **The recount's inventory entry no longer carries its own, looser copy of
  the findings-table header;** the router and the ledger template carried
  the exact one. The entry now points to the template's header.
- **A dangling pointer to a reference file that no longer exists** is
  replaced by the run folder's own precedents file (7.19).
- **The recount's inventory entry no longer counts the script's exit codes
  as two:** its four buckets fall on two of the four exit codes the script
  has, as the new table shows.
- **The phrase that presented the list of load-bearing claims as a gate on
  the lens count is corrected:** the list justifies the count, and nothing
  checks the two against each other (stage 2 and the ledger template).
- **The fourth terminal status in 9.18 is named, `refused-user-signed`,**
  where two different lists could have been meant.
- **The anchoring claim is sourced and scoped.** All four places that said
  a reviewer shown a verdict "changes their mind in about a third of
  cases" now name the measurement (Zheng et al. 2023, arXiv:2306.05685,
  §4.2), say it is a side observation of that study, and state the
  condition it holds under — human labelers who had disagreed with the
  verdict they were then shown.
- **Three tool refusals now name the remedy instead of only the symptom.**
  `recount.py`'s "no ledger rows found" exit says that a ledger read before
  `transcribe.py` has run prints the same thing, and to run `transcribe.py`
  first; the stage-5 reference now says so too. `recount.py --prev` names
  WHICH ledger of the three-round window has no readable `Round-started:`
  header, where the severity-plateau line used to report only that the
  order was underivable. `cleanup-scratchpad.py`'s condition-5 refusal says
  that a copy without a manifest is likely a hand-built one, that the
  script will not clean it, and what to do instead. No exit code and no
  condition changes.
- **`class-origin:adjudicator` now qualifies the `class:` tag it stands
  beside, not every tag in the cell.** A security-lens row carrying both the
  mandatory `class:security-pii` default and a coined defect class the
  adjudicator marked no longer raises `CLASS-KILL DUE: security-pii` — the
  kill counts the marked class alone, which is what stage 6.17 always said.
- **`cleanup-scratchpad.py` names the ledger field the way the template
  spells it.** Its closing guidance line now reads `Scratchpad not cleaned:
  {reason, path}`, the header field of `templates/ledger.md`, where it used
  to print a lower-case phrase of a different shape.

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
