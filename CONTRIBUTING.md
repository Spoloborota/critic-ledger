# Contributing

This project is developed by its author under its own review discipline and does
not actively seek contributions. The file exists so that anyone can verify the
state of the project for themselves and see how changes to it are made. Issues
and pull requests may be read; nothing is promised about them.

## Running the tests

```sh
sh tests/run-regression.sh
uvx pytest tests/unit -q
uvx --from shellcheck-py shellcheck -s sh tests/run-regression.sh \
    skills/critic-ledger/templates/copy-project.sh
COVERAGE_FILE=$(mktemp -d)/data uvx --from coverage --with pytest sh -c '
    coverage run -m pytest tests/unit -q && coverage combine && coverage report'
```

Two test layers, then two checks over them.

- The shell suite: 28 cases against
  `skills/critic-ledger/templates/recount.py` — the script that arbitrates round
  closure — each named with its expected exit code (`e0`/`e1`/`e2`/`e3`); it
  prints `ALL FIXTURES PASS` and exits 0 when green.
- The pytest suite: 218
  characterization tests covering all six template scripts as real CLIs
  (argv, stdout, exit codes, filesystem effects), written against a pinned
  behavior baseline so that any behavioral change fails loudly and must be
  deliberate.
- The third command lints both shell scripts.
- The fourth measures
  coverage of the template scripts — because the suite drives them as
  subprocesses, coverage.py is configured with `patch = ["subprocess"]` in
  `pyproject.toml`, which makes a `coverage combine` step mandatory and wants
  `COVERAGE_FILE` outside the work tree.

CI runs both suites on every push and
pull request across Python 3.11–3.14, plus a lint job (ruff with
`select = ALL` and the documented ignore list in `pyproject.toml`,
`ruff format --check`, `mypy --strict`), the shell lint, the coverage floor,
a `zizmor` audit of the workflow itself, a `lychee` link check over the
published Markdown, a structural validation of the plugin manifest and the
SKILL.md frontmatter portability check.

`tests/regression-transcript-2026-08-09.txt` is a snapshot of one green run,
not an input to the suite and not refreshed per release; run the suites
yourself for the current state.

## How changes to the discipline are made

The discipline itself (`skills/critic-ledger/SKILL.md`, the templates, the
agent definitions) changes only through a critic round run on the proposed
change — the project applies its own procedure to itself. A pull request that
rewords the contract without a round behind it will be asked to go through
one. Mechanical fixes (typos, broken links, portability) are exempt.
