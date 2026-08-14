"""Characterization tests for deleted-lines.py.

The script lists every deleted line of one or more commits, in diff order,
with notes for renames, binary files, whole-file deletions and merges. All
git repositories used here are throwaway ones created inside tmp_path; the
script itself only ever runs read-only git subcommands.

Exit codes: 0 = a listing was produced (an empty one included), 2 = a
fail-closed argument, repository, commit or pathspec error.
"""

from __future__ import annotations

import pytest

SCRIPT = "deleted-lines.py"


@pytest.fixture
def repo_two_commits(make_repo):
    """A repository whose second commit deletes one line of `file.txt`."""
    repo = make_repo()
    repo.write("file.txt", "a\nb\nc\n")
    repo.write("keep.txt", "keep one\nkeep two\n")
    first = repo.commit("first")
    repo.write("file.txt", "a\nc\n")
    second = repo.commit("second")
    return repo, first, second


# --- usage and fail-closed errors ------------------------------------------

@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_prints_the_docstring(run, flag):
    res = run(SCRIPT, flag)
    assert res.returncode == 0, res.stderr
    assert "Usage:  deleted-lines.py" in res.stdout


def test_no_commits_is_an_error(run):
    res = run(SCRIPT)
    assert res.returncode == 2, res.stdout
    assert ("ERROR: no commits given (positional hashes and/or --range A..B)"
            in res.stderr)
    assert "Usage:  deleted-lines.py" in res.stderr


def test_unknown_option(run):
    res = run(SCRIPT, "--nope")
    assert res.returncode == 2, res.stdout
    assert "ERROR: unknown option '--nope'" in res.stderr


@pytest.mark.parametrize("flag", ["--repo", "--range"])
def test_option_without_a_value(run, flag):
    res = run(SCRIPT, flag)
    assert res.returncode == 2, res.stdout
    assert f"ERROR: {flag} needs a value" in res.stderr


def test_directory_that_is_not_a_repository(run, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    res = run(SCRIPT, "--repo", plain, "HEAD")
    assert res.returncode == 2, res.stdout
    assert f"ERROR: {str(plain)!r} is not a git repository" in res.stderr


def test_unknown_commit(run, repo_two_commits):
    repo, _, _ = repo_two_commits
    res = run(SCRIPT, "--repo", repo.path, "deadbee")
    assert res.returncode == 2, res.stdout
    assert "ERROR: no such commit: 'deadbee'" in res.stderr


def test_empty_range_is_an_argument_error(run, repo_two_commits):
    repo, _, second = repo_two_commits
    res = run(SCRIPT, "--repo", repo.path, "--range", f"{second}..{second}")
    assert res.returncode == 2, res.stdout
    assert ("resolves to zero commits — an empty batch is an argument error, "
            "not a result" in res.stderr)


def test_pathspec_matching_nothing(run, repo_two_commits):
    repo, _, second = repo_two_commits
    res = run(SCRIPT, "--repo", repo.path, second, "--paths", "ghost.txt")
    assert res.returncode == 2, res.stdout
    assert ("ERROR: pathspec 'ghost.txt' matches nothing in any of the 1 "
            "commit(s) or their parents" in res.stderr)


def test_paths_swallows_following_positionals(run, repo_two_commits):
    """`--paths` consumes every following non-flag token, commits included."""
    repo, _, second = repo_two_commits
    res = run(SCRIPT, "--repo", repo.path, "--paths", "file.txt", second)
    assert res.returncode == 2, res.stdout
    assert "ERROR: no commits given" in res.stderr
    assert (f"note: --paths consumed 2 token(s) (file.txt, {second}); "
            "--paths is greedy, so put commits BEFORE it or end the list "
            "with a bare '--'" in res.stderr)


# --- the listing -----------------------------------------------------------

def test_single_commit_listing(run, repo_two_commits):
    repo, _, second = repo_two_commits
    res = run(SCRIPT, "--repo", repo.path, second)
    assert res.returncode == 0, res.stderr
    lines = res.stdout.splitlines()
    assert lines[0] == f"COMMIT {second} second"
    assert lines[1] == "file.txt:2: b"
    assert lines[2] == f"SUBTOTAL {second[:7]}: 1 deleted lines in 1 files"
    assert lines[3] == ""
    assert lines[4] == "TOTAL DELETED LINES: 1 (across 1 files, 1 commits)"


def test_repo_defaults_to_the_working_directory(run, repo_two_commits):
    repo, _, second = repo_two_commits
    res = run(SCRIPT, second, cwd=repo.path)
    assert res.returncode == 0, res.stderr
    assert "file.txt:2: b" in res.stdout


def test_commit_without_deletions_yields_an_empty_listing(run, repo_two_commits):
    repo, first, _ = repo_two_commits
    res = run(SCRIPT, "--repo", repo.path, first)
    assert res.returncode == 0, res.stderr
    assert f"SUBTOTAL {first[:7]}: 0 deleted lines in 0 files" in res.stdout
    assert "TOTAL DELETED LINES: 0 (across 0 files, 1 commits)" in res.stdout


def test_range_expands_oldest_first_and_totals_distinct_files(run, make_repo):
    repo = make_repo()
    repo.write("one.txt", "1\n2\n3\n")
    repo.write("two.txt", "x\ny\n")
    base = repo.commit("base")
    repo.write("one.txt", "1\n3\n")
    mid = repo.commit("drop from one")
    repo.write("one.txt", "1\n")
    repo.write("two.txt", "x\n")
    tip = repo.commit("drop from both")

    res = run(SCRIPT, "--repo", repo.path, "--range", f"{base}..{tip}")
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert out.index(f"COMMIT {mid}") < out.index(f"COMMIT {tip}")
    assert f"SUBTOTAL {mid[:7]}: 1 deleted lines in 1 files" in out
    assert f"SUBTOTAL {tip[:7]}: 2 deleted lines in 2 files" in out
    # one.txt contributed to both commits but counts once in the total.
    assert "TOTAL DELETED LINES: 3 (across 2 files, 2 commits)" in out


def test_repeated_commit_arguments_are_deduplicated(run, repo_two_commits):
    repo, _, second = repo_two_commits
    res = run(SCRIPT, "--repo", repo.path, second, second)
    assert res.returncode == 0, res.stderr
    assert res.stdout.count(f"COMMIT {second}") == 1
    assert "TOTAL DELETED LINES: 1 (across 1 files, 1 commits)" in res.stdout


def test_paths_narrows_the_listing(run, make_repo):
    repo = make_repo()
    repo.write("keep.txt", "k1\nk2\n")
    repo.write("other.txt", "o1\no2\n")
    repo.commit("base")
    repo.write("keep.txt", "k1\n")
    repo.write("other.txt", "o1\n")
    tip = repo.commit("drop from both")

    res = run(SCRIPT, "--repo", repo.path, tip, "--paths", "keep.txt")
    assert res.returncode == 0, res.stderr
    assert "keep.txt:2: k2" in res.stdout
    assert "other.txt" not in res.stdout
    assert "TOTAL DELETED LINES: 1 (across 1 files, 1 commits)" in res.stdout


def test_line_numbers_are_old_side_numbers(run, make_repo):
    repo = make_repo()
    repo.write("f.txt", "l1\nl2\nl3\nl4\nl5\nl6\n")
    repo.commit("base")
    repo.write("f.txt", "l1\nl3\nl6\n")
    tip = repo.commit("drop l2, l4, l5")

    res = run(SCRIPT, "--repo", repo.path, tip)
    assert res.returncode == 0, res.stderr
    assert "f.txt:2: l2" in res.stdout
    assert "f.txt:4: l4" in res.stdout
    assert "f.txt:5: l5" in res.stdout


def test_deleted_line_shaped_like_a_diff_header_is_still_listed(run, make_repo):
    """A deleted `-- text` line prints as `--- text` in the diff body."""
    repo = make_repo()
    repo.write("f.txt", "before\n-- a note\nafter\n")
    repo.commit("base")
    repo.write("f.txt", "before\nafter\n")
    tip = repo.commit("drop the note")

    res = run(SCRIPT, "--repo", repo.path, tip)
    assert res.returncode == 0, res.stderr
    assert "f.txt:2: -- a note" in res.stdout
    assert "TOTAL DELETED LINES: 1 (across 1 files, 1 commits)" in res.stdout


def test_trailing_whitespace_of_a_deleted_line_is_preserved(run, make_repo):
    repo = make_repo()
    repo.write("f.txt", "keep\ntrailing   \n")
    repo.commit("base")
    repo.write("f.txt", "keep\n")
    tip = repo.commit("drop")

    res = run(SCRIPT, "--repo", repo.path, tip)
    assert res.returncode == 0, res.stderr
    assert "f.txt:2: trailing   " in res.stdout.splitlines()


# --- notes -----------------------------------------------------------------

def test_whole_file_deletion_is_noted_before_its_lines(run, make_repo):
    repo = make_repo()
    repo.write("gone.txt", "a\nb\nc\n")
    repo.write("stay.txt", "s\n")
    repo.commit("base")
    (repo.path / "gone.txt").unlink()
    tip = repo.commit("remove gone.txt")

    res = run(SCRIPT, "--repo", repo.path, tip)
    assert res.returncode == 0, res.stderr
    out = res.stdout
    note = ("NOTE gone.txt: FILE DELETED ENTIRELY — every line listed for it "
            "is former content")
    assert note in out
    assert out.index(note) < out.index("gone.txt:1: a")
    assert "TOTAL DELETED LINES: 3 (across 1 files, 1 commits)" in out


def test_binary_file_change_is_noted(run, make_repo):
    repo = make_repo()
    repo.write_bytes("blob.bin", bytes(range(256)))
    repo.commit("base")
    repo.write_bytes("blob.bin", bytes(reversed(range(256))))
    tip = repo.commit("change the blob")

    res = run(SCRIPT, "--repo", repo.path, tip)
    assert res.returncode == 0, res.stderr
    assert ("NOTE blob.bin: BINARY file — its deleted bytes cannot be listed "
            "as lines; judge this change by other means" in res.stdout)
    assert "TOTAL DELETED LINES: 0 (across 0 files, 1 commits)" in res.stdout


def test_rename_gets_both_notes_and_lists_under_the_old_path(run, make_repo):
    repo = make_repo()
    body = "".join(f"line {i}\n" for i in range(1, 31))
    repo.write("old.txt", body)
    repo.commit("base")
    (repo.path / "old.txt").unlink()
    repo.write("new.txt", body.replace("line 5\n", ""))
    tip = repo.commit("rename and drop a line")

    res = run(SCRIPT, "--repo", repo.path, tip)
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert ("NOTE old.txt: RENAME source — the deletions below are listed "
            "under this old path" in out)
    assert ("NOTE new.txt: RENAME target — a rename hides deletions unless "
            "the old path is read too" in out)
    assert "old.txt:5: line 5" in out


def test_merge_commit_is_reported_but_not_expanded(run, make_repo):
    repo = make_repo()
    repo.write("f.txt", "base\n")
    repo.commit("base")
    repo.git("checkout", "-q", "-b", "side")
    repo.write("side.txt", "s\n")
    repo.commit("side change")
    repo.git("checkout", "-q", "main")
    repo.write("main.txt", "m\n")
    repo.commit("main change")
    repo.git("merge", "--no-ff", "-q", "-m", "merge side", "side")
    merge = repo.head()

    res = run(SCRIPT, "--repo", repo.path, merge)
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert f"NOTE {merge[:7]}: MERGE COMMIT" in out
    assert (f"SUBTOTAL {merge[:7]}: 0 deleted lines in 0 files "
            f"(merge, not expanded)" in out)
    assert "TOTAL DELETED LINES: 0 (across 0 files, 1 commits)" in out
    assert ("NOTE: 1 of the 1 commits are merges and were NOT expanded — the "
            "total above does not cover them." in out)
