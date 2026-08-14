#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Reference deleted-line pre-pass for a critic-ledger verification pass
(stage 8). The verifier's mandate is to walk EVERY deleted line of the fix
batch's diff — every such line needs either an equivalent in the new text
or a covering finding id. Collecting that list by eye is the last manual
step inside a mandate that was introduced precisely because fix-loss
survives inattentive reading (fix-loss went 1 -> 0 after the deleted-line
mandate). THIS script collects the list deterministically; the verifier
JUDGES the list instead of assembling it.

What the script does NOT do
---------------------------
- It does NOT classify lines. No "normative vs refactoring", no
  "important vs cosmetic": that split is ADJUDICATION, and the mode table
  (`SKILL.md`, row "Deleted-line scan") makes it a judgment call in impl
  mode too. The script is mechanical; the agent is the judge.
- It does NOT filter. Blank and whitespace-only deletions are listed like
  any other line — a dropped blank line can be a lost paragraph break in
  a normative document. Silence about a line would be indistinguishable
  from a line that does not exist.
- It does NOT read the new text and never decides whether a deletion is
  covered. Every emitted line is a CANDIDATE for the verifier's judgment.

Input
-----
One or more batch commits, and/or `--range A..B` (rev-list semantics: the
commits reachable from B but not from A, i.e. A itself is EXCLUDED),
oldest first. `--repo <path>` defaults to the current directory.
`--paths <p1> <p2> ...` narrows to the object's paths (git pathspecs);
the list ends at the next `--`-prefixed token or at a bare `--`.

Output (stdout; one line per record, greppable and readable)
-----------------------------------------------------------
    COMMIT <full-sha> <subject>
    <old-path>:<old-lineno>: <exact text of the deleted line>
    NOTE <path>: <rename / binary / whole-file-deletion / merge mark>
    SUBTOTAL <short-sha>: N deleted lines in M files
    TOTAL DELETED LINES: N (across M files, K commits)

Records appear in DIFF order, so a file's NOTEs stand next to that file's
deleted lines rather than in a separate block. A rename source, a binary
file and a whole-file deletion are marked where they occur.

The text after `<path>:<lineno>: ` is the diff's own bytes with the
leading `-` removed and NOTHING else stripped — trailing whitespace and
CRs are preserved, because a whitespace-only edit is exactly the kind of
deletion that hides. Bytes that are not valid UTF-8 survive the round
trip via `surrogateescape`. `<old-lineno>` is the line number in the OLD
(pre-commit) version of the file, derived from the hunk headers of a
`--unified=0` diff.

M in the TOTAL is the number of DISTINCT old paths that contributed at
least one deleted line, across all commits (a file touched by two commits
counts once); the per-commit SUBTOTAL counts that commit's own files.

Renames, binary files and whole-file deletions get an explicit NOTE
rather than silence: a rename can carry content deletions that the
`b/`-side path would hide, and a binary file's deletions cannot be listed
at all — the verifier must be told, not left to assume.

Merge commits are NOT expanded: `git show` prints no diff for them by
default, and a silent zero would be a false "nothing was deleted". Such a
commit is reported as a NOTE and counted in the summary; diffing the
chosen parent explicitly is the verifier's call.

Usage:  deleted-lines.py [<commit> ...] [--range A..B] [--repo <path>]
                         [--paths <p1> <p2> ...]
Exit codes: 0 = the listing was produced (including a legitimately empty
one: `TOTAL DELETED LINES: 0`); 2 = fail-closed error — bad arguments, no
such repository/commit/range, or a pathspec that matches nothing in any
of the commits (a silently empty listing from a typo'd path would be the
worst possible output of this script).

Read-only by construction: every git invocation goes through `git()`,
which runs a fixed argument list (no shell) and refuses any subcommand
outside the read-only allowlist below.
"""  # noqa: D205  # printed usage text; reflowing it would change output

import re
import subprocess
import sys
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import io

# Read-only git subcommands. Anything else raises: this script must never
# be able to mutate the repository under review.
READ_ONLY = ("rev-parse", "rev-list", "log", "show", "ls-tree")

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")


def git(repo: str, *argv: str) -> tuple[int, str, str]:
    """Run a read-only git command. Returns (returncode, stdout_text,
    stderr_text); stdout is decoded with surrogateescape so that
    non-UTF-8 bytes survive to stdout unchanged.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    if not argv or argv[0] not in READ_ONLY:
        msg = f"refusing non-read-only git command: {argv!r}"
        raise AssertionError(msg)
    proc = subprocess.run(  # noqa: S603  # fixed argument list, never a shell
        ["git", "-C", repo, "-c", "core.quotePath=false", *argv],  # noqa: S607  # `git` is intentionally resolved from PATH
        capture_output=True,
        check=False,
    )
    return (
        proc.returncode,
        proc.stdout.decode("utf-8", "surrogateescape"),
        proc.stderr.decode("utf-8", "surrogateescape"),
    )


def fail(msg: str) -> int:
    """Print an error to stderr and return the fail-closed exit code."""
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def parse_args(args: list[str]) -> str | tuple[str, list[str], list[str], list[str]]:
    """Return (repo, commits, ranges, paths) or a string with the error."""
    repo = "."
    commits: list[str] = []
    ranges: list[str] = []
    paths: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-h", "--help"):
            return "help"
        if a in ("--repo", "--range"):
            if i + 1 >= len(args):
                return f"{a} needs a value"
            if a == "--repo":
                repo = args[i + 1]
            else:
                ranges.append(args[i + 1])
            i += 2
            continue
        if a == "--paths":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                paths.append(args[i])
                i += 1
            if i < len(args) and args[i] == "--":
                i += 1
            continue
        if a.startswith("--"):
            return f"unknown option {a!r}"
        commits.append(a)
        i += 1
    if not commits and not ranges:
        msg = "no commits given (positional hashes and/or --range A..B)"
        if paths:
            msg += (
                f" — note: --paths consumed {len(paths)} token(s) "
                f"({', '.join(paths)}); --paths is greedy, so put commits "
                f"BEFORE it or end the list with a bare '--'"
            )
        return msg
    return repo, commits, ranges, paths


def resolve_commits(
    repo: str,
    commits: list[str],
    ranges: list[str],
) -> tuple[list[str] | None, str | None]:
    """Expand ranges, verify every hash, keep input order, drop repeats.
    Returns (list-of-sha, error-or-None).
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    resolved: list[str] = []
    for c in commits:
        rc, out, err = git(repo, "rev-parse", "--verify", "--quiet", f"{c}^{{commit}}")
        if rc != 0 or not out.strip():
            return None, (
                f"no such commit: {c!r}" + (f" ({err.strip()})" if err.strip() else "")
            )
        resolved.append(out.strip())
    for r in ranges:
        rc, out, err = git(repo, "rev-list", "--reverse", r)
        if rc != 0:
            return None, f"bad --range {r!r}: {err.strip() or 'rev-list failed'}"
        got = out.split()
        if not got:
            return None, (
                f"--range {r!r} resolves to zero commits — an empty "
                f"batch is an argument error, not a result"
            )
        resolved.extend(got)
    seen: set[str] = set()
    ordered: list[str] = []
    for sha in resolved:
        if sha not in seen:
            seen.add(sha)
            ordered.append(sha)
    return ordered, None


def check_paths(repo: str, shas: list[str], paths: list[str]) -> str | None:
    """Every pathspec must match something in at least one processed
    commit or its first parent; otherwise the empty listing would be a
    typo, not a fact. Returns an error string or None.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    for p in paths:
        for sha in shas:
            for rev in (sha, f"{sha}^"):
                rc, out, _ = git(repo, "ls-tree", "-r", "--name-only", rev, "--", p)
                if rc == 0 and out.strip():
                    break
            else:
                continue
            break
        else:
            return (
                f"pathspec {p!r} matches nothing in any of the "
                f"{len(shas)} commit(s) or their parents"
            )
    return None


def commit_header(repo: str, sha: str) -> tuple[str | None, str | None]:
    """Return the commit's `<sha> <subject>` header line, or an error."""
    rc, out, err = git(repo, "log", "-1", "--format=%H %s", sha)
    if rc != 0:
        return None, err.strip() or "git log failed"
    return out.rstrip("\n"), None


def parents(repo: str, sha: str) -> list[str]:
    """Return the parent shas of a commit."""
    rc, out, _ = git(repo, "rev-list", "--parents", "-n", "1", sha)
    return out.split()[1:] if rc == 0 else []


def diff_text(repo: str, sha: str, paths: list[str]) -> tuple[str | None, str | None]:
    """Return the commit's `--unified=0` diff text, or an error."""
    argv = [
        "show",
        "--unified=0",
        "--format=",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--find-renames",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        sha,
    ]
    if paths:
        argv += ["--", *list(paths)]
    rc, out, err = git(repo, *argv)
    if rc != 0:
        return None, err.strip() or "git show failed"
    return out, None


def header_paths(line: str) -> tuple[str, str]:
    """Best-effort (old, new) path out of a `diff --git a/X b/Y` line.
    Only a FALLBACK label, for the files that never get a `--- ` header:
    a binary file and a mode-only change have none. Ambiguous if a path
    itself contains ' b/', hence the equal-halves check first.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    rest = line[len("diff --git ") :]
    cuts = [m.start() for m in re.finditer(r" b/", rest)]
    for i in cuts:
        old, new = rest[:i], rest[i + 1 :]
        if old.startswith("a/") and old[2:] == new[2:]:
            return old[2:], new[2:]
    if cuts and rest.startswith("a/"):
        return rest[2 : cuts[0]], rest[cuts[0] + 3 :]
    return rest, rest


def scan_diff(text: str) -> list[tuple[object, ...]]:
    """Parse a git `--unified=0` diff into ORDERED records, so that a
    file's notes stand next to that file's deleted lines:
        ("del", old_path, old_lineno, text) | ("note", path, mark)

    State matters. A file header `--- a/x` and a DELETED LINE whose own
    text begins with `-- ` are byte-identical in shape, so header lines
    are recognized only OUTSIDE a hunk, and inside a hunk every `-` line
    is a deletion. `diff --git` (which can never be a diff body line,
    since body lines start with `-`, `+`, ` ` or `\\`) is what closes the
    previous hunk. This is also why a naive `grep -c '^-'` over the same
    diff overcounts: it swallows the `--- ` header of every file.
    """  # noqa: D205, D301, D415  # docstring wording is frozen verbatim
    records: list[tuple[object, ...]] = []
    path: str | None = None
    fallback = "?"
    old_no = 0
    in_hunk = False
    for line in text.split("\n"):
        if line.startswith("diff --git "):
            old_p, new_p = header_paths(line)
            path, fallback, in_hunk = None, old_p or new_p, False
            continue
        m = HUNK_RE.match(line)
        if m:
            old_no, in_hunk = int(m.group(1)), True
            continue
        if in_hunk:
            # Diff BODY. Only `-` lines matter; `+`, `\ No newline at end
            # of file` and anything else are not old-side content.
            if line.startswith("-"):
                records.append(("del", path or fallback, old_no, line[1:]))
                old_no += 1
            continue
        # --- header territory --------------------------------------
        if line.startswith("--- "):
            src = line[4:]
            path = None if src == "/dev/null" else src.removeprefix("a/")
            continue
        if line.startswith("rename from "):
            records.append(
                (
                    "note",
                    line[len("rename from ") :],
                    (
                        "RENAME source — the deletions below are listed "
                        "under this old path"
                    ),
                ),
            )
            continue
        if line.startswith("rename to "):
            records.append(
                (
                    "note",
                    line[len("rename to ") :],
                    (
                        "RENAME target — a rename hides deletions unless "
                        "the old path is read too"
                    ),
                ),
            )
            continue
        if line.startswith("deleted file mode "):
            records.append(
                (
                    "note",
                    path or fallback,
                    (
                        "FILE DELETED ENTIRELY — every line listed for it "
                        "is former content"
                    ),
                ),
            )
            continue
        if line.startswith(("Binary files ", "GIT binary ")):
            records.append(
                (
                    "note",
                    path or fallback,
                    (
                        "BINARY file — its deleted bytes cannot be listed "
                        "as lines; judge this change by other means"
                    ),
                ),
            )
            continue
        if line.startswith("@@@"):
            records.append(
                ("note", path or fallback, "COMBINED (merge) hunk — not expanded"),
            )
    return records


def main() -> int:
    """Print the deleted-line listing for the requested commits."""
    parsed = parse_args(sys.argv[1:])
    if parsed == "help":
        print(__doc__)
        return 0
    if isinstance(parsed, str):
        print(__doc__, file=sys.stderr)
        return fail(parsed)
    repo, commits, ranges, paths = parsed

    rc, _, err = git(repo, "rev-parse", "--git-dir")
    if rc != 0:
        return fail(
            f"{repo!r} is not a git repository: "
            f"{err.strip() or 'git rev-parse --git-dir failed'}",
        )

    shas, problem = resolve_commits(repo, commits, ranges)
    if problem:
        return fail(problem)
    shas = cast("list[str]", shas)
    problem = check_paths(repo, shas, paths)
    if problem:
        return fail(problem)

    # stdout must carry the diff's bytes through unchanged.
    cast("io.TextIOWrapper", sys.stdout).reconfigure(errors="surrogateescape")

    total = 0
    all_files: set[object] = set()
    merges = 0
    for sha in shas:
        header, problem = commit_header(repo, sha)
        if problem:
            return fail(f"{sha}: {problem}")
        print(f"COMMIT {header}")
        if len(parents(repo, sha)) > 1:
            merges += 1
            print(
                f"NOTE {sha[:7]}: MERGE COMMIT — `git show` prints no diff "
                f"for it by default, so NO deleted lines are listed here. "
                f"Diff the intended parent explicitly before judging.",
            )
            print(
                f"SUBTOTAL {sha[:7]}: 0 deleted lines in 0 files (merge, not expanded)",
            )
            print()
            continue
        text, problem = diff_text(repo, sha, paths)
        if problem:
            return fail(f"{sha}: {problem}")
        records = scan_diff(cast("str", text))
        for rec in records:
            if rec[0] == "note":
                print(f"NOTE {rec[1]}: {rec[2]}")
            else:
                print(f"{rec[1]}:{rec[2]}: {rec[3]}")
        dels = [r for r in records if r[0] == "del"]
        files = {r[1] for r in dels}
        total += len(dels)
        all_files |= files
        print(f"SUBTOTAL {sha[:7]}: {len(dels)} deleted lines in {len(files)} files")
        print()

    print(
        f"TOTAL DELETED LINES: {total} (across {len(all_files)} files, "
        f"{len(shas)} commits)",
    )
    if merges:
        print(
            f"NOTE: {merges} of the {len(shas)} commits are merges and were "
            f"NOT expanded — the total above does not cover them.",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
