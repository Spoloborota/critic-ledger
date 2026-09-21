Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

What changed between two installed copies is the `[Unreleased]` section of
`CHANGELOG.md` at the root of the installed copy and the version stamp of the copy's
`.claude-plugin/plugin.json`; nothing in the router repeats it.

## Templates

Every file listed below is addressed from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/` — the paths in this section are given relative to that directory. The stage files `references/stage-*.md` always carry the full substituted path; the names below are descriptive labels.

- `templates/ledger.md` — the ledger skeleton: mandatory header fields,
  the row schema — nine cells in the v3 form it ships, declared in the
  header's own `Row schema:` field, with the seven- and eight-cell forms
  still readable — the `Zone map:` field the round's zones are taken from,
  the verification-passes table + new-findings curve (the
  carrier of the convergence signal and the kill criterion), per-batch
  delta sections (delta snapshots are marked historical; the current count
  lives in one place — the table), the inter-round DELTA report, the
  disposition appendix.
- `templates/residue-register.md` — the skeleton of the DURABLE residue
  register, the one artifact of a round that does not live in the run
  folder: it is copied to `.critic-ledger/residue-register.md`, beside the
  run folders, because it outlives every one of them. It carries the row
  contract (`run-qualified id | severity | claim-hook | rationale |
  compensating-control | review-by | status | origin-run`, blockers barred
  and no blank `rationale` or `compensating-control`), the two privacy
  gates that govern the first write to it, the three deadlines the recount
  reports on, and the ratification rules — batches of ten, the whole queue
  shown before the act, security/PII rows signed one at a time.
- `templates/round-contract.md` — the SCOPE CONTRACT of one round, filled
  and signed BEFORE the first critic is spawned and copied beside the object
  under review: object and round id, three-to-six Goals, Non-Goals written
  as pre-signed dispositions (`a finding whose claim is X routes to
  `out-of-scope-by-contract`, reason Y` — owner signs), the zone map, the
  lens panel with its security-lens declaration, the stopping rule (owner
  signs), the residue carried in, the declared instrument set, the known
  limitations, and the Amendments table. Above 400 lines of object it is a
  gate — no contract, no round — and filling it is capped at half an hour;
  both numbers are OURS and are marked as ours in the file. Its path and sha
  live in the ledger header, and its text is substituted verbatim into every
  lens's prompt.
- `templates/critic-prompt.md` — the stage-3 contract with placeholders
  `{object}`, `{lens}`, `{id_prefix}`, `{mode}`, `{timebox}`,
  `{round_contract}`, `{project_rules}`. `{round_contract}` is filled by
  the rule of stage 2 (a) in `references/stage-2-scope-and-lenses.md`.
  It includes the mode-conditional execution rule (plan:
  run read-only commands yourself; impl: formulate commands, never
  execute the object).
  `{project_rules}` is a MANDATE to read the target project's own agent
  rules (CLAUDE.md) and leak discipline — not a context dump; if the
  project has none, work by this prompt's contract alone.
- `templates/fixer-prompt.md` — the stage-7 contract for the fix-batch
  subagent, with placeholders `{batch_id}`, `{object_path}`,
  `{findings}`, `{project_rules}`, `{noticed_prefix}`. `{noticed_prefix}`
  is the id prefix of the `NOTICED OUTSIDE BATCH` report block, fixed at
  stage 2 alongside the lens prefixes and under the same id contract; the
  block is a report block and not a fourth per-id outcome, and its entries
  route to stage 6. `{findings}` carries, per id, the
  finding's FULL salvaged text, the adjudicator's verdict with its
  reasoning, the row's readiness criterion word for word, and, as a
  fourth element wherever the edit's correctness depends on one, the
  measured value the orchestrator computed before the batch; the
  criterion is fixed and the fixer may never touch it or the file that
  evaluates it. The fixer reproduces the defect in the current text before
  it edits anything, edits the working tree, gets no git at all, and
  returns exactly one outcome per id — `fixed`, `criterion-unworkable`
  with a reason, or `premise-not-found` with a reason, the last two both
  routing the id back to stage 6 and counting together against that id's
  two-return limit.
- `templates/verifier-prompt.md` — the stage-8 mandate with placeholders
  `{ledger_rows}`, `{object_path}`, `{batch_commits}`, `{prior_verdicts}`,
  `{salvage_path}`, `{deleted_lines}`, `{lens_scope}`,
  `{new_findings_prefix}`. `{lens_scope}` names the ids this verifier
  judges and the ids another verifier of the same pass judges — the
  placeholder the `lens-split verification pass` is carried by; on an
  unsplit pass it reads `all ids of this pass`. A row deduplicated by the
  `=<primary-id>` convention arrives inside `{ledger_rows}` with the
  primary row's criterion substituted in full, never as the bare
  reference. Canon
  files = the ledger + the round's salvages; `{deleted_lines}` carries
  the deterministic deleted-line list of the batch diff. There is
  deliberately NO placeholder for the fixer's
  report or its reasoning: the verifier is not shown the justification of
  the actor whose work it checks.
- `templates/executor-prompt.md` — the spawn prompt of the executor, the
  agent that runs a critic's handed-over commands on their scratch copy in
  `impl` mode, the orchestrator's own probe of a finding on a scratch copy
  (6.26), or a criterion's command that mutates the live object, with
  placeholders `{commands}`, `{object_path}`, `{probes_dir}`,
  `{run_as_written_rule}`. `{run_as_written_rule}` carries the stage-3 rule
  on running a handed-over command as written, word for word, so the
  prompt states it as text rather than as a pointer. Like the verifier's,
  it deliberately has NO placeholder for the findings, their reasoning or
  their verdicts: the executor runs commands blind to the adjudication.
- `scripts/recount.py` — the reference recount script: the contract of
  ledger cell values (which rows count as terminal), fail-closed row
  parsing (a malformed row is a structural error, never a silent drop),
  the programmatic count of open/closed rows, the new-findings curve with
  the kill-criterion warning, the `--prev` inter-round delta, and the
  FROZEN-ledger state. The CURRENT row it parses is the NINE-cell row exactly as
  `templates/ledger.md` ships its header; the contract of cell values is
  the module's own docstring, printed by `recount.py --help`; this entry
  describes the call, the buckets and the exit codes. The header's
  optional `Row schema: v1 | v2 | v3` declares which form the table takes;
  a declaration that contradicts the table, a second one, or a value
  outside that vocabulary is a structural error, and its absence changes
  nothing at all.
  `LANDED OTHERWISE (<what was actually done>)` in the `verified` cell is
  terminal only with a non-empty description in the parentheses. Criterion
  consistency is checked too: an upheld finding's criterion cell is
  non-empty, a refuted one's holds the literal `—`; an empty cell is
  allowed to nobody. It also reads the three tags the adjudicator may put in
  a `verdict` cell: `class:<slug>` gives the count of upheld rows per
  defect class and the `CLASS-KILL DUE` warning from the second one,
  `origin:fix-application from:<batch>` gives the per-batch injection rate
  with its advisory `INJECTION RATE HIGH`, and the optional `shelf:<slug>`
  on a refuted row gives the shelf share printed beside the per-lens
  sustained rate under `--prev`; a malformed `class:` or `shelf:` slug is a
  structural error, and every one of those reports is printed only when the
  tag it reads is present, so a ledger carrying none of them recounts
  exactly as it did before. It also knows the two NAMED non-terminal waits — a residue
  nominee's `awaiting-signature (nominated <date>)`, which may never sit on
  a blocker row, and `awaiting-logged-no-action (listed <date>)` — counting
  and printing
  each apart from an open row: four buckets over two of the four exit codes
  (table below), one state line per run, and exit 0 still meaning every row
  is terminal. Past
  the 30-day limit — the nomination limit carried over, not a new number —
  a listed row is printed under `Z3 CLOSURE OVERDUE`, report-only and
  reaching no exit code. The ZONE cell is read for exactly one rule: the
  terminal status `logged-no-action` is accepted at zone `Z3` alone and only
  in the nine-cell schema where that cell exists, and it does not reach a
  `class:security-pii` row without a live `user-signed <date>` — the other
  two combinations are structural errors, not undefined cases.
  `--register <path>` points it at the residue register, and without the
  flag it derives that path from the layout (`.critic-ledger/` beside the
  run folder); the register's aggregate, its expiry escalations and the
  nominations no register row accounts for are printed report-only, never
  reaching an exit code, while a malformed register is a structural error
  like any other. The block appears only when a register is in play, so a
  ledger with neither register nor nomination recounts byte for byte as
  before. It also computes the round's two STOPPING METRICS, both
  report-only and both outside every exit code: the residual-defect
  ESTIMATE (Jackknife, `N-hat = D + ((k-1)/k) * f1`), whose `k` comes from
  the header's machine-form `Lenses:` lines and never from the id prefixes
  in the table, printed from `k >= 4` and otherwise as `n/a: k<4` or
  `n/a: k not derived from the header`, always carrying the caveat that
  names which half of the caution is ours; and the severity-weighted
  plateau.
  It knows the round CONTRACT's two terminal statuses and the two header
  fields they lean on: `out-of-scope-by-contract (NG-<n>, signed <date>)`
  and `frozen-carried (stop-rule, <date>)` are terminal only under their
  COMPLETE literal, `class:security-pii` on an out-of-scope row without a
  live `user-signed <date>` is a structural error, a `frozen-carried` row
  needs the header's single `Stop-rule freeze:` line (two such lines, a
  malformed one, or `carried-to: pending` at closure are structural errors),
  and at closure it prints `FROZEN CARRIED: <n> rows → <carried-to>`. The
  header's `Security lens: <PREFIX> | none` arms the class backstop: a row
  of that lens carrying neither `class:security-pii` nor
  `declassed:security-pii — <reason>` with a non-empty reason is a
  structural error. Every one of these is silent on a ledger that declares
  neither field and uses neither status, which is what keeps older ledgers
  recounting unchanged. For the severity-weighted
  plateau `--prev` is REPEATABLE up to two paths — one gives the
  0.2.0 delta unchanged, two add the moving average over a window ordered
  by each ledger's own `Round-started` field rather than by argument
  position, and a third `--prev` is a usage error. Any `--prev` also prints
  the PER-LENS SUSTAINED RATE over that window with the SHELF SHARE beside
  it, report-only and `n/a: <reason>` wherever a figure cannot be computed
  — never `0`. Closure runs through it,
  never through manual counting.
- `scripts/ledger_model.py` — the ledger as `recount.py` reads it: the
  findings rows, the verification-passes table, the residue register and
  the header fields, each read once and handed back, never printed.
- `scripts/statuses.py` — which row statuses are terminal and which are
  the named waits, with the literals each of them is recognized by.
- `scripts/structural_checks.py` — the checks that turn a malformed row,
  header field or register row into a structural error.
- `scripts/metrics.py` — the counts the report is built from: defect
  classes, class kills, batches, capture sets and the plateau.
- `scripts/report.py` — the lines of the recount's report, handed back to
  `recount.py`, which alone prints them and decides their order.
- `scripts/copy-project.sh` — makes the scratchpad copy the critics
  read: a copy-on-write clone in STRICT mode — run only when git reports
  no ignored content under the project root — falling back to the
  git-known file list and then to an object-only narrowing, printing
  every omission as an `EXCLUDED:` line. A second, untracked-content
  pre-flight runs on every tree: an untracked directory, or more than five
  untracked loose files, blocks the strict clone too, and whatever that
  pre-flight names EXCLUDED is left out of steps 2-3 as well as of the
  clone (unless it is the object under review, which is kept and recorded
  as kept). Symlinks are copied AS LINKS and
  secret-class files (`.env*`, `*.pem`, `id_*`, …) are stripped on every
  step; the run directory also gets the cleanup manifest.
- `scripts/validate-report.py` — the deterministic half of report
  acceptance: it checks the two mechanically complete traits — the lens's
  id prefix on every finding and the severity literal — and reports
  everything softer (no file:line, missing header fields, no coverage
  statement) as a MARK. It never rejects a report; "re-run this lens"
  stays the orchestrator's call.
- `scripts/extract_final.py` — the stage-4 salvage extractor:
  `extract_final.py --src <task transcript> --dst <salvage file> --header
  "<text>"` reads a subagent's task transcript, one JSON record per line,
  and writes the agent's final message verbatim — the message of its
  `SubagentHandback` call where there is one, else its last non-empty
  assistant text — under the one header line
  `<!-- <text> Source: <source kind>. -->`, printing only a size line
  `OK <dst> <source kind> <n> chars <m> lines`. Where the transcript holds
  several `SubagentHandback` calls, the LAST one wins, so a resumed agent's
  earlier hand-back is not in the output. An existing `--dst` is replaced
  — by an atomic replace, never written through a link — and the size line
  then ends with the notice `(replaced an existing file)`; a write that
  fails prints one line, leaves `--dst` as it was and exits 2. A transcript
  that holds neither a hand-back nor any assistant text prints
  `no report found`, writes nothing and exits 2. The task
  transcript lives where the platform keeps it, in the session store under
  the user's home directory — a machine-local path that no artifact of the
  round quotes; the extractor only reads it, writes nothing to `--dst` but
  the extracted final message under its one header line, and never copies
  the transcript file anywhere. That header line is the caller's `--header`
  text followed by the source kind, and the extractor writes the text as
  given: the caller never puts a path into `--header` — the transcript's
  least of all — and the extractor adds none.
- `scripts/transcribe.py` — mechanical transcription of the salvaged
  reports into ledger rows before adjudication: one finding = one row,
  with the id/severity/claim cells produced by LITERAL COPY of the
  finding's header line and the remaining cells left empty on purpose (an
  empty cell is what keeps a fresh row non-terminal). The row's WIDTH is the
  target ledger's, taken from its `Row schema:` field or, absent that, from
  the findings header's own cell count; a field and a header that disagree,
  or neither readable, stop the run with nothing written rather than emit a
  row of a foreign width. In the nine-cell schema the filled cells are named
  rather than counted — the `zone` cell carries the stub `·`, because a zone
  is the adjudicator's judgment against the zone map and transcription stays
  literal copying. Parsing is fail-closed for the row WIDTH and for a
  duplicate id; a header line that does not parse is instead skipped
  per line and reported, and the write is all-or-nothing.
- `scripts/set-cell.py` — the canonical writer of one already-decided
  cell of a row: `fix`, `verified` and `terminal`, the three the fix and
  verification stages own, plus `zone`, `verdict` and `criterion`, the
  adjudicator's three. One call writes ONE cell of ONE row,
  addressed by id in the first findings table (`--ledger`, `--id`,
  `--column`, `--value`). The row width is the LEDGER'S, derived the same
  way `transcribe.py` derives it, and the cell is addressed from the END of
  the row, so v1, v2 and v3 rows are written by one rule; rows are split on
  the raw `|` with `\|` read as an escaped literal and never on `" | "`,
  the split that silently dropped a row's empty trailing cells in the
  field. A value carrying a pipe, a newline or any other control character
  is refused, the write is all-or-nothing, and every write prints
  `OK <id>.<column>` while a run that writes nothing exits non-zero — a
  silent no-op is not one of the outcomes. A cell the row's schema does not
  have is refused rather than invented, and a CLOSED round is refused in one
  line: its ledger is finished evidence. The adjudicator's three cells were
  edited by hand until this script learned them, which left the one class of
  write in a round with neither atomicity nor a grammar check.
- `scripts/ledger_md.py` — the ONE owner of the ledger's markdown
  grammar, and a MODULE first of all: it carries
  three commands. `ledger_md.py new --template <ledger.md> --out
  <fix-ledger.md>` is what stage 1 uses to instantiate a round's blank ledger
  WITHOUT the template's instruction comments (it refuses an `--out` that
  already exists rather than overwriting it). `ledger_md.py set-header
  --ledger <fix-ledger.md> --field <name> --value <text>` writes ONE header
  field as its `- <name>: <value>` line and prints `OK header.<name>`; it
  writes only `Ledger state`, `Precedents file`, `Contract amendments`,
  `Exit family` and `Scratchpad not cleaned`, and refuses every other name,
  and a listed name the header does not carry, in one line with nothing
  written. It also refuses `Ledger state: closed …` on a FROZEN ledger, on
  one whose findings table carries rows the parser rejects, and on one with
  open rows, rows awaiting a signature or rows awaiting an act of the owner
  — the reason is the first of these, in the order the recount decides them
  — with the line `REFUSED: Ledger state:
  closed written before the ledger is ROUND CLOSABLE — <reason>; …`. It
  checks nothing else: every other structural error (a duplicate row id, a
  `Row schema` mismatch, a pending carry-over and the like) is the
  recount's, whose `ROUND CLOSABLE` 9.18 requires first, before this write.
  `ledger_md.py add-pass-row --ledger <fix-ledger.md> --cells
  "<c1>|…|<c8>"` adds one row under the verification-passes table, exactly
  as wide as that table's header (a `\|` in `--cells` stays one escaped
  cell), and prints `OK pass.<#>`; a row of another width is refused with
  nothing written. Both writers exit 2 on a refusal.
  `recount.py`, `set-cell.py`,
  `transcribe.py`, `validate-report.py`, `deleted-lines.py` and
  `extract_final.py` — plus the
  five modules `recount.py` imports — all IMPORT it from their own directory
  (the payload ships loose files, so the import is resolved by the
  importing script's path, never by an installed package — a copy of any of
  those scripts without this file beside it does not run, and `recount.py`
  runs only with its five modules and `ledger_md.py` beside it). It owns the row
  grammar (the three schemas, the raw-`|` split with `\|` as an escaped
  literal, the addressing of every cell), the header-field grammar (a named
  field is read once and TWO of it is a structural error, the rule that had
  been enforced for `Process prefixes:` and silently missing for `Security
  lens:` while the two were parsed by two hand-written patterns), the
  escaping, the atomic patcher (a temporary file created exclusively, an
  atomic replace, and no temporary file left behind by a failed write), the
  writers of a header field and of one cell, and the refusal every writer
  owes a CLOSED round. Its existence is the answer to four hand-made copies
  of one grammar, one of which had already drifted into reading a row the
  other three refuse.
- `scripts/cleanup-scratchpad.py` — removes the round's scratch copies —
  the critics', an executor's, a criterion's — and nothing else, by the
  LANGUAGE (an open directory descriptor; no shell,
  no `rm`), with the path taken from the run manifest rather than from an
  argument or a variable. Dry by default — it prints the plan and each
  condition's verdict — and deletes only on a second `--confirm` call;
  any refusal is a ledger line, never a crash.
- `scripts/deleted-lines.py` — the deterministic deleted-line pre-pass
  for verification: given the batch commits (or a `--range`), it prints
  `REPO <abs-path>` (the repository's top level) as its first line, before
  the first `COMMIT` record, then lists every deleted line as
  `<old-path>:<old-lineno>: <text>` and marks renames, binaries and
  whole-file deletions. It neither classifies nor
  filters — every listed line is a CANDIDATE the verifier judges, which
  takes the last manual step out of the deleted-line mandate.
- `scripts/check-frontmatter.py` — inventories a SKILL.md's frontmatter
  against the portable Agent Skills specification (exactly six top-level
  fields), listing platform extensions AS extensions rather than errors
  and naming anything else as a probable typo. Fail-closed on an
  unterminated block or a duplicate key; `--strict-portable` turns the
  extensions into a failure too.

| script | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `recount.py` | closable | not closable (awaiting ratification, awaiting Z3 closure, open rows) | structural error | frozen ledger |
| `set-cell.py` | written | — | refused (structure, closed round, no write) | — |
| `transcribe.py` | done | — | structural (duplicate id, foreign width) | — |
| `validate-report.py` | accepted | problems found | structural | — |
| `ledger_md.py` | written (the blank ledger, the header field or the pass row) | — | refused, nothing written (a writer's refusal, including the refusal of `Ledger state: closed`) | — |
| `extract_final.py` | written | — | no report found, usage error, or the salvage file cannot be written (nothing written) | — |
