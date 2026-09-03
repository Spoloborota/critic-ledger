Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

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
  `{round_contract}`, `{project_rules}`. `{round_contract}` carries the
  round contract's own text and is substituted into EVERY lens's prompt
  identically and verbatim — never re-told or angled for one lens.
  Under the two conditions stage 2 sets, that text may instead be a
  pointer to the contract's path inside the critics' own copy; identical
  for every lens either way.
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
  reasoning, and the row's readiness criterion word for word; the
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
  the deterministic deleted-line list of the batch diff (produced by
  `templates/deleted-lines.py`) — the verifier JUDGES that list instead
  of assembling it. There is deliberately NO placeholder for the fixer's
  report or its reasoning: the verifier is not shown the justification of
  the actor whose work it checks.
- `templates/recount.py` — the reference recount script: the contract of
  ledger cell values (which rows count as terminal), fail-closed row
  parsing (a malformed row is a structural error, never a silent drop),
  the programmatic count of open/closed rows, the new-findings curve with
  the kill-criterion warning, the `--prev` inter-round delta, and the
  FROZEN-ledger state. The row it parses is the NINE-cell one (`id |
  severity | zone | claim | verdict | readiness criterion | fix | verified |
  terminal`); rows of the older eight- and seven-cell schemas stay countable
  — the script accepts exactly 7, 8 or 9 cells and addresses `criterion`,
  `fix`, `verified` and `terminal` from the END of the row, so no branch is
  needed for any of them, and `criterion` is the fourth cell from the end at
  8 and 9 alike. The header's optional `Row schema: v1 | v2 | v3` declares
  which form the table takes; a declaration that contradicts the table, a
  second one, or a value outside that vocabulary is a structural error, and
  its absence changes nothing at all.
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
  each apart from an open row: four buckets, still two exit codes, one
  state line per run, and exit 0 still meaning every row is terminal. Past
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
- `templates/trace.py` — the round's span writer and validator, used only
  when observability is on: `append` writes one record (an `open` at a
  unit's start, the complete `span` at its close) into the run folder's
  `trace.jsonl`, `validate` re-checks a whole file against the schema and
  reports report-only defects. Every field is an enumeration or an
  anchored, length-bounded pattern and a value that fails is REFUSED
  rather than written. It is the one script here that must never fail
  closed: its exit code is always 0, and a failure produces one
  diagnostic line from a closed error-class vocabulary that never echoes
  what it could not read.
- `templates/rollup.py` — the stage-9 rollup, used only when
  observability is on: it reads `trace.jsonl` plus the ledger and writes
  `round-summary.json` beside the ledger together with a human table,
  computing the round's cost and confirmation metrics with a per-metric
  `n/a: <reason>` wherever an input is missing — never a `0` and never a
  silent omission. `--rounds <path>` additionally appends ONE
  identifier-free projection line to the cross-project rollup; no
  observability condition ever reaches its exit code. The two stopping
  metrics reach `round-summary.json` through that same mechanism and as
  measurements only — `RDE`, the advisory residual-defect estimate off the
  header's declared lens count, and `SWP`, the severity-weighted plateau
  over the window `--prev` supplies (repeatable up to two, unreadable or
  absent giving the metric its named `n/a` and never an exit code). No
  prose crosses into the summary: the estimate's caveat lives in this text
  and in the recount's own report, where a reader of the number sees it.
- `templates/copy-project.sh` — makes the scratchpad copy the critics
  read: a copy-on-write clone in STRICT mode — run only when git reports
  no ignored content under the project root — falling back to the
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
  empty cell is what keeps a fresh row non-terminal). The row's WIDTH is the
  target ledger's, taken from its `Row schema:` field or, absent that, from
  the findings header's own cell count; a field and a header that disagree,
  or neither readable, stop the run with nothing written rather than emit a
  row of a foreign width. In the nine-cell schema the filled cells are named
  rather than counted — the `zone` cell carries the stub `·`, because a zone
  is the adjudicator's judgment against the zone map and transcription stays
  literal copying. Parsing is
  fail-closed, a duplicate id is a structural error, and the write is
  all-or-nothing.
- `templates/set-cell.py` — the canonical writer of a row's `fix`,
  `verified` and `terminal` cells: one call writes ONE cell of ONE row,
  addressed by id in the first findings table (`--ledger`, `--id`,
  `--column`, `--value`). The row width is the LEDGER'S, derived the same
  way `transcribe.py` derives it, and the cell is addressed from the END of
  the row, so v1, v2 and v3 rows are written by one rule; rows are split on
  the raw `|` with `\|` read as an escaped literal and never on `" | "`,
  the split that silently dropped a row's empty trailing cells in the
  field. A value carrying a pipe, a newline or any other control character
  is refused, the write is all-or-nothing, and every write prints
  `OK <id>.<column>` while a run that writes nothing exits non-zero — a
  silent no-op is not one of the outcomes. `zone`, `verdict` and
  `criterion` belong to adjudication and are deliberately not writable
  here.
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
