"""Characterization tests for `templates/copy-project.sh`.

The first tests this script has ever had. Until now its only coverage was
`test_payload_invariants.py` (which reads it as a file) plus shellcheck —
neither of which can see what the script DOES.

What is pinned here is the scope of the copy the critics read, because that
is where the script can fail silently. Step 1 (the strict reflink clone)
means "everything under --src"; steps 2-3 mean "everything git knows about".
On a tree that mixes the project with ignored runtime state the two differ,
and a clone widens the copy without saying so: the disclosure sweep removes
only secret-class paths, so private-but-not-secret state would reach the
critics unannounced. The pre-flight gate makes step 1 conditional on git
reporting no ignored content, and these tests hold it to that.

Every run is hermetic: the git repository under `--src`, the destination and
any command stub live inside pytest's `tmp_path`, `HOME` and git's config
lookups are redirected there by `hardened_env`, and no test reaches the
network or the repository the suite lives in.

Two tests inject a failure by putting a stub earlier on `PATH` than the real
command. That is the only way to reach the two escalation paths from a test:
a git pre-flight that fails with EMPTY stdout, and a secret-class path the
sweep cannot remove. Both stubs delegate to the real binary for every other
invocation, so the rest of the run is unmodified.
"""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest

SCRIPT = "copy-project.sh"
MANIFEST_NAME = "critic-ledger-manifest.json"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def dest_under(tmp_path: Path, name: str = "run") -> Path:
    """A run directory three levels below a scratchpad root.

    The depth mirrors what `cleanup-scratchpad.py` requires of a run
    directory it is asked to remove (its condition 4), so the copies these
    tests make are shaped like the ones the orchestrator makes.
    """
    root = tmp_path / "scratch"
    parent = root / "critic" / "runs"
    parent.mkdir(parents=True, exist_ok=True)
    return parent / name


def copy_files(dest: Path) -> set[str]:
    """Relative paths of every file and symlink in the copy, manifest aside."""
    return {
        str(path.relative_to(dest))
        for path in dest.rglob("*")
        if (path.is_file() or path.is_symlink()) and path.name != MANIFEST_NAME
    }


def excluded_lines(stdout: str) -> list[str]:
    return [
        line[len("EXCLUDED: ") :]
        for line in stdout.splitlines()
        if line.startswith("EXCLUDED: ")
    ]


def make_stub(directory: Path, name: str, body: str) -> Path:
    """Write an executable stub for `name` that falls back to the real one."""
    directory.mkdir(parents=True, exist_ok=True)
    real = shutil.which(name)
    assert real is not None, f"{name} is not on PATH"
    script = directory / name
    script.write_text(
        f'#!/bin/sh\nREAL={real}\n{body}\nexec "$REAL" "$@"\n',
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return script


@pytest.fixture
def clean_project(make_repo):
    """A committed repository with no git-ignored content whatsoever."""
    repo = make_repo("project")
    repo.write("README.md", "# project\n")
    repo.write("src/app.py", "print('hi')\n")
    repo.commit("initial")
    return repo


@pytest.fixture
def mixed_project(make_repo):
    """A repository that also carries ignored runtime state on disk."""
    repo = make_repo("project")
    repo.write("README.md", "# project\n")
    repo.write("src/app.py", "print('hi')\n")
    repo.write(".gitignore", "runtime/\n*.log\n")
    repo.commit("initial")
    repo.write("runtime/history.jsonl", '{"prompt": "secret"}\n')
    repo.write("runtime/session-env/daemon.sock.txt", "state\n")
    repo.write("debug.log", "noise\n")
    return repo


# ---------------------------------------------------------------------------
# (a) a tree with no git-ignored content: step 1 runs
# ---------------------------------------------------------------------------


def test_clean_tree_takes_step_1(run_sh, clean_project, tmp_path):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest)
    assert result.returncode == 0, result.stderr
    assert "STEP1-CLONE" in result.stdout


def test_clean_tree_reports_no_git_ignored_exclusion(
    run_sh, clean_project, tmp_path
):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest)
    assert [line for line in excluded_lines(result.stdout)
            if "git-ignored" in line] == []
    assert "step 1 (strict clone) not run" not in result.stdout


def test_clean_tree_copy_holds_the_project_files(run_sh, clean_project, tmp_path):
    dest = dest_under(tmp_path)
    run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest)
    assert {"README.md", "src/app.py"} <= copy_files(dest)


def test_clean_tree_copy_has_no_git_directory(run_sh, clean_project, tmp_path):
    """Step 1 clones `.git` and must remove it again: unchanged behavior."""
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest)
    assert not (dest / ".git").exists()
    assert any("class=git-history" in line
               for line in excluded_lines(result.stdout))


# ---------------------------------------------------------------------------
# (b) a tree WITH git-ignored content: step 1 is not run
# ---------------------------------------------------------------------------


def test_ignored_content_blocks_step_1(run_sh, mixed_project, tmp_path):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest)
    assert result.returncode == 0, result.stderr
    assert "STEP1-CLONE" not in result.stdout
    assert "STEP2-FILELIST" in result.stdout


def test_ignored_content_prints_the_reason_as_a_notice(
    run_sh, mixed_project, tmp_path
):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest)
    notices = [line for line in result.stdout.splitlines()
               if line.startswith("NOTICE: ")]
    assert any("step 1 (strict clone) not run" in line
               and "git-ignored content" in line for line in notices), notices


def test_ignored_content_is_listed_class_git_ignored(
    run_sh, mixed_project, tmp_path
):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest)
    ignored = [line for line in excluded_lines(result.stdout)
               if "class=git-ignored" in line]
    assert {line.split(" | ")[0] for line in ignored} == {"debug.log", "runtime/"}


def test_ignored_content_reaches_the_manifest(run_sh, mixed_project, tmp_path):
    """An EXCLUDED line that only ever went to stdout would be lost."""
    dest = dest_under(tmp_path)
    run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest)
    manifest = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert sorted(
        entry for entry in manifest["excluded"] if "class=git-ignored" in entry
    ) == ["debug.log | class=git-ignored", "runtime/ | class=git-ignored"]


def test_ignored_content_copy_is_exactly_the_git_known_set(
    run_sh, mixed_project, tmp_path
):
    dest = dest_under(tmp_path)
    run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest)
    assert copy_files(dest) == {".gitignore", "README.md", "src/app.py"}


# ---------------------------------------------------------------------------
# (c) the file list of the copy, not the script's own account of it
# ---------------------------------------------------------------------------


def test_a_file_outside_the_git_known_set_never_appears_in_the_copy(
    run_sh, mixed_project, tmp_path
):
    """Asserted against the copy's own file list, not against stdout."""
    dest = dest_under(tmp_path)
    run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest)
    present = copy_files(dest)
    for ignored in ("runtime/history.jsonl",
                    "runtime/session-env/daemon.sock.txt",
                    "debug.log"):
        assert ignored not in present
    assert not (dest / "runtime").exists()


def test_untracked_but_not_ignored_files_do_reach_the_copy(
    run_sh, mixed_project, tmp_path
):
    """The gate narrows to the git-KNOWN set, not to the tracked set."""
    mixed_project.write("NOTES.md", "uncommitted\n")
    dest = dest_under(tmp_path)
    run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest)
    assert "NOTES.md" in copy_files(dest)


# ---------------------------------------------------------------------------
# (d) the sweep cannot remove a secret-class path
# ---------------------------------------------------------------------------


@pytest.fixture
def undeletable_secret(mixed_project, tmp_path):
    """A copy that will contain `.ssh/`, plus an `rm` that refuses to remove it.

    `vendor/.ssh/config` passes the per-file filter of step 2 (its basename
    is not secret-class), so the directory reaches the copy and the
    disclosure sweep is what removes it. The stub makes that one removal
    fail — twice, so the retry after `chmod -R u+w` fails as well — while
    every other `rm` in the run, the teardown's included, is the real one.
    The directory is nested one level down precisely so that the teardown,
    which removes the copy's TOP-LEVEL entries, is not caught by the stub.
    """
    mixed_project.write("vendor/.ssh/config", "Host example\n")
    mixed_project.commit("add an ssh config directory")
    stub_dir = tmp_path / "stub-rm"
    make_stub(
        stub_dir,
        "rm",
        'for a in "$@"; do case "$a" in */.ssh) exit 1 ;; esac; done',
    )
    return stub_dir


def test_an_unremovable_secret_exits_3(
    run_sh, mixed_project, undeletable_secret, tmp_path
):
    """Exit 3 ("no copy was made"), never exit 2 with a half-cleaned copy."""
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest,
                    extra_path=undeletable_secret)
    assert result.returncode == 3, (result.returncode, result.stdout,
                                    result.stderr)
    assert "chmod -R u+w" in result.stderr


def test_an_unremovable_secret_leaves_an_empty_destination(
    run_sh, mixed_project, undeletable_secret, tmp_path
):
    dest = dest_under(tmp_path)
    run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest,
           extra_path=undeletable_secret)
    assert dest.is_dir()
    assert list(dest.iterdir()) == []


def test_an_unremovable_secret_writes_no_manifest(
    run_sh, mixed_project, undeletable_secret, tmp_path
):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest,
                    extra_path=undeletable_secret)
    assert not (dest / MANIFEST_NAME).exists()
    assert "no copy was made" in result.stderr


# ---------------------------------------------------------------------------
# (e) the pre-flight command itself fails
# ---------------------------------------------------------------------------


@pytest.fixture
def failing_preflight(tmp_path):
    """A `git` whose `ls-files --ignored` fails with EMPTY stdout.

    Empty stdout with a non-zero exit code is the case the gate must read as
    a refusal rather than as "nothing is ignored". Every other git call —
    the work-tree check, and step 2's own file list — reaches the real git.
    """
    stub_dir = tmp_path / "stub-git"
    make_stub(
        stub_dir,
        "git",
        'for a in "$@"; do [ "$a" = "--ignored" ] && exit 128; done',
    )
    return stub_dir


def test_a_failing_preflight_blocks_step_1(
    run_sh, clean_project, failing_preflight, tmp_path
):
    """A clean tree that would otherwise clone: the failure alone blocks it."""
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest,
                    extra_path=failing_preflight)
    assert result.returncode == 0, result.stderr
    assert "STEP1-CLONE" not in result.stdout


def test_a_failing_preflight_falls_through_to_step_2(
    run_sh, clean_project, failing_preflight, tmp_path
):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest,
                    extra_path=failing_preflight)
    assert "STEP2-FILELIST" in result.stdout
    assert copy_files(dest) == {"README.md", "src/app.py"}


def test_a_failing_preflight_is_recorded_with_its_exit_code(
    run_sh, clean_project, failing_preflight, tmp_path
):
    dest = dest_under(tmp_path)
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest,
                    extra_path=failing_preflight)
    recorded = [line for line in excluded_lines(result.stdout)
                if "class=git-preflight-failed" in line]
    assert len(recorded) == 1, excluded_lines(result.stdout)
    assert "128" in recorded[0]
    assert "the git pre-flight failed (exit 128)" in result.stdout


# ---------------------------------------------------------------------------
# --run-id must equal the basename of --dest (cleanup-scratchpad condition 7)
# ---------------------------------------------------------------------------


def test_a_run_id_that_differs_from_the_dest_basename_is_refused(
    run_sh, clean_project, tmp_path
):
    dest = dest_under(tmp_path, "2026-02-03-084011-api-spec")
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest,
                    "--run-id", "2026-02-03-084011-api-spec-lens-DA")
    assert result.returncode == 2
    assert "--run-id must equal the basename of --dest" in result.stderr
    assert "condition 7" in result.stderr


def test_a_refused_run_id_makes_no_copy_at_all(run_sh, clean_project, tmp_path):
    dest = dest_under(tmp_path, "run")
    run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest,
           "--run-id", "run-lens-DA")
    assert not dest.exists()


def test_a_run_id_equal_to_the_dest_basename_is_accepted(
    run_sh, clean_project, tmp_path
):
    dest = dest_under(tmp_path, "run")
    result = run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest,
                    "--run-id", "run")
    assert result.returncode == 0, result.stderr
    assert "RUN-ID: run\n" in result.stdout


def test_an_omitted_run_id_still_defaults_to_the_dest_basename(
    run_sh, clean_project, tmp_path
):
    dest = dest_under(tmp_path, "2026-02-03-084011-api-spec")
    run_sh(SCRIPT, "--src", clean_project.path, "--dest", dest)
    manifest = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["run_id"] == "2026-02-03-084011-api-spec"


# ---------------------------------------------------------------------------
# the gate has no opt-out
# ---------------------------------------------------------------------------


def test_the_script_offers_no_flag_that_forces_the_clone(
    run_sh, mixed_project, tmp_path
):
    """An opt-out would be reached for out of habit; there must be none."""
    dest = dest_under(tmp_path, "run")
    result = run_sh(SCRIPT, "--src", mixed_project.path, "--dest", dest,
                    "--fast-clone")
    assert result.returncode == 2
    assert "unknown argument: --fast-clone" in result.stderr
