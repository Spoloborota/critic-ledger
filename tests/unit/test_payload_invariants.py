"""Invariants over the shipped payload read as FILES rather than as CLIs.

Everything else in `tests/unit/` drives a script through a subprocess and
pins its observable behavior. Three claims of the 0.2.0 observability work
are not behavior of any single script but properties of the payload as a
whole, and this module is where they are enforced:

* **No network primitive exists in the payload.** The gate is one command
  over `templates/*.py`, so it is checked over the whole directory here.
  `test_trace.py` and `test_rollup.py` already assert it on their own
  script; neither of them can fail when a network import appears in a
  third file.
* **No shell-out that could reach a network.** The constraint names three
  scripts (`trace.py`, `rollup.py`, `recount.py`) and exempts the two that
  legitimately shell out today (`copy-project.sh`, and `deleted-lines.py`
  via git). `recount.py` is the one of the three that had no such
  assertion anywhere.
* **The SKILL.md stage sentences.** Every stage of the stage machine
  carries an observability instruction; the skill spells them out as ten
  `**With observability on**` sentences, one per stage 0-9. A stage that
  silently loses its sentence is a hole in the trace that no script-level
  test can see.

All three read the shipped files from `scripts_dir` / the repository root,
so they hold for a copy of the payload (`CRITIC_LEDGER_SCRIPTS_DIR`)
exactly as they hold for the tree the suite lives in.
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO_ROOT

# The network gate's own token list, verbatim. The bare words `curl`,
# `wget` and `http` are deliberately NOT here: `validate-report.py`
# mentions them as text about commands, and a gate that flagged text
# would be switched off within a week.
NETWORK_TOKENS = (
    "urllib",
    "requests",
    "socket",
    "ftplib",
    "smtplib",
    "http.client",
)

# The three scripts under the no-subprocess constraint.
NO_SUBPROCESS_SCRIPTS = ("trace.py", "rollup.py", "recount.py")

# The two exempted by name, so this file records the exemption
# instead of leaving it as an unexplained absence.
SHELL_OUT_EXEMPT = ("deleted-lines.py",)

SKILL_MD = REPO_ROOT / "skills" / "critic-ledger" / "SKILL.md"
OBSERVABILITY_MARKER = "**With observability on**"
STAGE_MACHINE_HEADING = "## Stage machine"
STAGE_START_RE = re.compile(r"^(\d+)\. \*\*")


# --- the network gate over the whole payload -------------------------------


def test_no_template_script_imports_a_network_primitive(scripts_dir):
    """The network gate over `templates/*.py`, as one sweep."""
    offenders = []
    for path in sorted(scripts_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        offenders += [
            f"{path.name}: {token}" for token in NETWORK_TOKENS if token in text
        ]
    assert offenders == []


def test_the_gate_covers_every_python_file_that_ships(scripts_dir):
    """The gate is only worth its exit code if it sees the whole directory.

    A new script added to `templates/` without a test of its own is still
    read by the sweep above; this pins that the sweep is not silently
    matching nothing, and that it reaches the three named scripts.
    """
    seen = {path.name for path in scripts_dir.glob("*.py")}
    assert seen >= {
        "check-frontmatter.py",
        "cleanup-scratchpad.py",
        "deleted-lines.py",
        "recount.py",
        "rollup.py",
        "trace.py",
        "transcribe.py",
        "validate-report.py",
    }


# --- no shell-out from the three named scripts -----------------------------


@pytest.mark.parametrize("script", NO_SUBPROCESS_SCRIPTS)
def test_the_named_scripts_contain_no_subprocess_at_all(scripts_dir, script):
    """A normative constraint on two, a preserved property of the third."""
    text = (scripts_dir / script).read_text(encoding="utf-8")
    assert "subprocess" not in text
    for shell_exec in ("os.system", "os.popen", "os.execv", "os.spawn"):
        assert shell_exec not in text, shell_exec


@pytest.mark.parametrize("script", SHELL_OUT_EXEMPT)
def test_the_exempt_script_still_shells_out_only_through_a_fixed_argv(
    scripts_dir, script
):
    """The exemption is for git through a list argv, never through a shell."""
    text = (scripts_dir / script).read_text(encoding="utf-8")
    assert "import subprocess" in text
    assert "shell=True" not in text


# --- SKILL.md: one observability sentence per stage -------------------------


def stage_blocks() -> list[tuple[int, list[str]]]:
    """The stage machine, split into (stage number, its lines)."""
    lines = SKILL_MD.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line == STAGE_MACHINE_HEADING)
    end = next(
        (
            i
            for i, line in enumerate(lines[start + 1 :], start + 1)
            if line.startswith("## ")
        ),
        len(lines),
    )
    blocks: list[tuple[int, list[str]]] = []
    for i in range(start + 1, end):
        match = STAGE_START_RE.match(lines[i])
        if match:
            # The stage's own opening line belongs to its body: a marker
            # written there must count for that stage, not vanish.
            blocks.append((int(match.group(1)), [lines[i]]))
        elif blocks:
            blocks[-1][1].append(lines[i])
    return blocks


def test_the_stage_machine_has_ten_stages_numbered_zero_through_nine():
    """Stages 0-9, in order, with nothing renumbered or dropped."""
    assert [number for number, _ in stage_blocks()] == list(range(10))


def test_every_stage_carries_exactly_one_observability_sentence():
    """BDF5 T3: ten markers, one per stage — not ten anywhere in the file."""
    per_stage = {
        number: sum(line.count(OBSERVABILITY_MARKER) for line in body)
        for number, body in stage_blocks()
    }
    assert per_stage == dict.fromkeys(range(10), 1)


def test_the_file_carries_no_observability_marker_outside_the_stage_machine():
    """The count is ten, and all ten are stage sentences."""
    total = SKILL_MD.read_text(encoding="utf-8").count(OBSERVABILITY_MARKER)
    assert total == 10
