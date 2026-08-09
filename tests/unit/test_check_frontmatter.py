"""Characterization tests for check-frontmatter.py.

The script inventories the top-level fields of a SKILL.md frontmatter block
and classifies them as portable, platform extension or unknown. Exit codes:
0 = no unknown fields (and, under --strict-portable, no extensions either),
1 = unknown fields (or extensions under --strict-portable), 2 = unreadable
file, structurally broken frontmatter, or a usage error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SCRIPT = "check-frontmatter.py"


def skill(tmp_path: Path, text: str, name: str = "SKILL.md") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


MINIMAL = "---\nname: demo\ndescription: a demo skill\n---\n\n# Body\n"


# --- happy paths -----------------------------------------------------------

def test_portable_only_header_is_ok(run, tmp_path):
    res = run(SCRIPT, skill(tmp_path, MINIMAL))
    assert res.returncode == 0, res.stdout
    assert "portable: name, description" in res.stdout
    assert "platform-extensions: (none)" in res.stdout
    assert "unknown: (none)" in res.stdout
    assert "portable=2 extensions=0 unknown=0" in res.stdout
    assert res.stdout.rstrip().endswith("OK: no unknown fields.")


def test_field_count_line_names_the_path(run, tmp_path):
    path = skill(tmp_path, MINIMAL)
    res = run(SCRIPT, path)
    assert f"frontmatter of {path}: 2 top-level field(s)" in res.stdout


def test_all_six_portable_fields_are_recognized(run, tmp_path):
    text = ("---\n"
            "name: demo\n"
            "description: a demo skill\n"
            "license: MIT\n"
            "compatibility: any\n"
            "metadata:\n"
            "  version: 1\n"
            "allowed-tools: Read\n"
            "---\n")
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 0, res.stdout
    assert "portable=6 extensions=0 unknown=0" in res.stdout
    assert ("portable: name, description, license, compatibility, metadata, "
            "allowed-tools" in res.stdout)


def test_indented_lines_are_continuations_not_keys(run, tmp_path):
    text = ("---\n"
            "name: demo\n"
            "description: >-\n"
            "  a long description whose continuation\n"
            "  looks: like a key but is indented\n"
            "---\n")
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 0, res.stdout
    assert "portable=2 extensions=0 unknown=0" in res.stdout


def test_opening_delimiter_tolerates_trailing_whitespace(run, tmp_path):
    res = run(SCRIPT, skill(tmp_path, "---   \nname: demo\n---\n"))
    assert res.returncode == 0, res.stdout
    assert "portable=1 extensions=0 unknown=0" in res.stdout


# --- platform extensions ---------------------------------------------------

def test_platform_extension_is_listed_but_not_an_error(run, tmp_path):
    text = "---\nname: demo\ndescription: d\nmodel: sonnet\n---\n"
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 0, res.stdout
    assert "platform-extensions: model" in res.stdout
    assert "NOT PORTABLE AS IS — platform extensions present:" in res.stdout
    assert "  model: model the skill's own session runs on" in res.stdout
    assert "portable=2 extensions=1 unknown=0" in res.stdout


def test_strict_portable_turns_extensions_into_failure(run, tmp_path):
    text = "---\nname: demo\ndescription: d\nmodel: sonnet\neffort: low\n---\n"
    res = run(SCRIPT, skill(tmp_path, text), "--strict-portable")
    assert res.returncode == 1, res.stdout
    assert ("--strict-portable: 2 platform extension(s) — the header does not "
            "carry over to other harnesses as is." in res.stdout)


def test_strict_portable_on_a_clean_header(run, tmp_path):
    res = run(SCRIPT, skill(tmp_path, MINIMAL), "--strict-portable")
    assert res.returncode == 0, res.stdout
    assert res.stdout.rstrip().endswith("OK: no unknown fields. Portable as is.")


def test_strict_portable_flag_position_is_free(run, tmp_path):
    res = run(SCRIPT, "--strict-portable", skill(tmp_path, MINIMAL))
    assert res.returncode == 0, res.stdout


# --- unknown fields --------------------------------------------------------

def test_unknown_field_is_reported_and_fails(run, tmp_path):
    text = "---\nname: demo\ndescription: d\nallowed_tools: Read\n---\n"
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 1, res.stdout
    assert "unknown: allowed_tools" in res.stdout
    assert "UNKNOWN FIELDS — neither in the portable six nor a known" in res.stdout
    assert "  allowed_tools" in res.stdout


def test_unknown_field_wins_over_strict_portable_extensions(run, tmp_path):
    text = "---\nname: demo\ndescriptions: typo\nmodel: sonnet\n---\n"
    res = run(SCRIPT, skill(tmp_path, text), "--strict-portable")
    assert res.returncode == 1, res.stdout
    assert "NOT PORTABLE AS IS" in res.stdout
    assert "UNKNOWN FIELDS" in res.stdout
    # The unknown-field branch returns first, so the --strict-portable line
    # never appears when both conditions hold.
    assert "--strict-portable:" not in res.stdout


def test_quoted_keys_are_not_recognized_as_portable(run, tmp_path):
    """Documented parsing limit: a quoted key counts as an unknown field."""
    text = '---\n"name": demo\ndescription: d\n---\n'
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 1, res.stdout
    assert 'unknown: "name"' in res.stdout


# --- informational note ----------------------------------------------------

def test_missing_required_fields_are_a_note_not_an_error(run, tmp_path):
    text = "---\nlicense: MIT\n---\n"
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 0, res.stdout
    assert ("note (not an error here): the spec's required field(s) name, "
            "description are absent" in res.stdout)


# --- no frontmatter --------------------------------------------------------

def test_file_without_frontmatter_is_not_an_error(run, tmp_path):
    path = skill(tmp_path, "# Just a document\n\nProse.\n")
    res = run(SCRIPT, path)
    assert res.returncode == 0, res.stdout
    assert res.stdout.startswith(f"NO FRONTMATTER: {path} does not start with")


def test_empty_file_has_no_frontmatter(run, tmp_path):
    res = run(SCRIPT, skill(tmp_path, ""))
    assert res.returncode == 0, res.stdout
    assert "NO FRONTMATTER" in res.stdout


def test_delimiter_further_down_is_a_horizontal_rule(run, tmp_path):
    text = "# Title\n\n---\nname: not-a-header\n---\n"
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 0, res.stdout
    assert "NO FRONTMATTER" in res.stdout


# --- structural errors -----------------------------------------------------

def test_unclosed_frontmatter_is_a_structural_error(run, tmp_path):
    text = "---\nname: demo\ndescription: d\n\n# Body without a closing rule\n"
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith(
        "STRUCTURAL ERROR — no verdict is trustworthy until fixed:")
    assert "is never closed by a '---' line" in res.stdout


def test_duplicate_key_is_a_structural_error(run, tmp_path):
    text = "---\nname: demo\ndescription: d\nname: again\n---\n"
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith(
        "STRUCTURAL ERRORS — no verdict is trustworthy until fixed:")
    assert ("line 4: DUPLICATE top-level key 'name' (first seen on line 2) "
            "— ambiguous" in res.stdout)


def test_duplicate_check_runs_before_classification(run, tmp_path):
    """A duplicate unknown key exits 2, not 1: structure gates the verdict."""
    text = "---\ntypo: a\ntypo: b\n---\n"
    res = run(SCRIPT, skill(tmp_path, text))
    assert res.returncode == 2, res.stdout
    assert "unknown:" not in res.stdout


# --- argument and IO errors ------------------------------------------------

@pytest.mark.parametrize("argv", [
    (),
    ("a.md", "b.md"),
])
def test_wrong_argument_count_prints_usage(run, argv):
    res = run(SCRIPT, *argv)
    assert res.returncode == 2, res.stdout
    assert "Usage:  check-frontmatter.py <SKILL.md> [--strict-portable]" in res.stdout


def test_repeated_strict_flag_is_a_usage_error(run, tmp_path):
    """Only one occurrence is removed from argv, so the second stays a path."""
    res = run(SCRIPT, "--strict-portable", skill(tmp_path, MINIMAL),
              "--strict-portable")
    assert res.returncode == 2, res.stdout
    assert "Usage:  check-frontmatter.py" in res.stdout


def test_missing_file_is_reported(run, tmp_path):
    missing = tmp_path / "absent.md"
    res = run(SCRIPT, missing)
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith(f"cannot read {missing}: ")


def test_directory_argument_is_reported(run, tmp_path):
    res = run(SCRIPT, tmp_path)
    assert res.returncode == 2, res.stdout
    assert "cannot read" in res.stdout


def test_non_utf8_file_is_reported(run, tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_bytes(b"---\nname: \xff\xfe\n---\n")
    res = run(SCRIPT, path)
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith(f"cannot decode {path} as UTF-8: ")
