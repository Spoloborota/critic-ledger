# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

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
