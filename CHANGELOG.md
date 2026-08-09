# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.1.0] - 2026-08-10

Initial public release.

**Honesty notes.** The README's headline effectiveness figures predate the
current actor allocation (fixes used to be applied by the judging session; they
are now applied by a separate fixer subagent) and carry that caveat in place.
The exception is the single-round 70% data point, which was measured under the
shipped allocation — one round, n=10, not a headline figure. Re-measurement of
the headline figures under the shipped allocation, plus an automated evals
suite, is planned for a subsequent release together with cost/time telemetry.

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
