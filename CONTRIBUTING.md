# Contributing

This project is developed by its author under its own review discipline and does
not actively seek contributions. The file exists so that anyone can verify the
state of the project for themselves and see how changes to it are made. Issues
and pull requests may be read; nothing is promised about them.

## Running the tests

```sh
sh tests/run-regression.sh
uvx pytest==9.1.1 tests/unit -q
uvx --from shellcheck-py shellcheck -s sh tests/run-regression.sh \
    skills/critic-ledger/templates/copy-project.sh
COVERAGE_FILE=$(mktemp -d)/data uvx --from coverage==7.15.4 \
    --with pytest==9.1.1 sh -c '
    coverage run -m pytest tests/unit -q && coverage combine && coverage report'
```

Two test layers, then two checks over them.

- The shell suite: 79 cases against
  `skills/critic-ledger/templates/recount.py` — the script that arbitrates round
  closure — each named with its expected exit code (`e0`/`e1`/`e2`/`e3`); it
  prints `ALL FIXTURES PASS` and exits 0 when green. The count is re-derived,
  never taken on trust —
  `grep -oE '\bc[0-9]{2}\b' tests/run-regression.sh | sort -u | wc -l`.
- The pytest suite: characterization tests covering all ten template
  scripts as real CLIs —
  the nine Python ones plus `copy-project.sh`, driven through `sh`
  (argv, stdout, exit codes, filesystem effects), written against a pinned
  behavior baseline so that any behavioral change fails loudly and must be
  deliberate. No count is quoted here; it is derived the same way —
  `uvx pytest==9.1.1 tests/unit -q --collect-only` prints it, on the same
  pin CI runs — so the number read is the number the suite has.
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

## How changes to the discipline are made

The discipline itself (`skills/critic-ledger/SKILL.md`, its `references/`
files, the templates, the agent definitions) changes only through a critic
round run on the proposed change — the project applies its own procedure to
itself. A pull request that rewords the contract without a round behind it
will be asked to go through one. Mechanical fixes (typos, broken links,
portability) are exempt.
