#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Scratchpad cleanup for a critic-ledger round: removes the copies of the
project that were made for the critics, and NOTHING else.

The danger this script exists to remove is not the agent's intent — it is the
shell. A deletion command WRITTEN BY AN AGENT still reaches a shell, where an
empty variable turns "remove this directory" into "remove the root". So the
removal here is done by the LANGUAGE (os.unlink / os.rmdir over an open
directory descriptor), never by a shell: there is no `rm`, no `subprocess`, no
`shutil.rmtree(path)` — and no string that a shell could re-expand.

Two more rules follow from the same fear:

- The path to delete is NEVER taken from an argument, an environment variable
  or a guess. It comes from a MANIFEST written by whoever created the copy.
- The manifest is a SECONDARY check, not proof of origin (design/02:126-133):
  the same actor that writes it also calls the cleanup, and such a file can be
  planted anywhere. It catches a MISMATCH — an attempt to remove a directory
  that does not look like the ones we create. The PRIMARY defence is path
  ownership: conditions 1-4 and 8 below.

By default the script runs DRY: it prints the plan (each path, the verdict of
every condition, the file count, the size and the top level of the contents)
and deletes nothing. Real deletion happens only on a second, explicit call with
`--confirm`. The confirmation is the orchestrator's, not the owner's
(design/02:163-172): cleanup is a technical operation inside the scratchpad,
and the two-step shape protects against a WRONG PATH, not against the
orchestrator. The dry-run output goes into the ledger header.

Any refusal is a RECORD, not a crash: the directory stays where it is and the
ledger header gets the line "scratchpad not cleaned: reason, path".


THE MANIFEST FORMAT (canon: design/02:126-133, field list at design/02:128)
--------------------------------------------------------------------------
A JSON object, written by the copier INTO the run directory it describes, named
`critic-ledger-manifest.json`, mode 0600 (design/02:173-176). Required
fields:

    {
      "manifest_version": "critic-ledger/scratchpad-manifest@1",
      "absolute_path":    "/abs/path/to/<scratchpad-root>/.../<run-id>",
      "run_id":           "2026-02-03-084011-api-spec",
      "created_at":       "2026-02-03T08:40:11Z",
      "project_root":     "/abs/path/to/the/project/that/was/copied",
      "created":          ["copy-1", "copy-2"],
      "size_bytes":       123456
    }

- `absolute_path` is the directory to delete — the ONLY source of that path.
  It is kept in the file even though it is a path, because condition 6 needs
  it; the file itself never leaves the scratchpad (design/02:173-176).
- `run_id` is the run identifier, and by convention also the basename of the
  run directory; condition 7 compares them (or compares against `--run-id`
  when the orchestrator passes it explicitly).
- `created_at` is ISO 8601 and MUST carry a timezone offset. It is the age
  source for `--older-than-hours` — the mtime of the file is not, because a
  manifest can be touched by a backup, an editor or a copy.
- `project_root` is the root of the project that was copied. Condition 8 needs
  it: the skill never deletes anything inside the checked project, and without
  a project root that condition cannot be evaluated at all, so a manifest
  without it is refused (fail-closed).
- `created` (top-level entries the copier made) and `size_bytes` are the
  "what was created / how big" part of the field list. They are NOT turned
  into a refusal — a stale listing is not evidence of a wrong path — but a
  disagreement with the filesystem is printed as a MISMATCH note.

A manifest may also sit OUTSIDE the directory it describes (a sidecar). That
is tolerated: conditions 1-8 do not depend on where the file lies, except that
the in-directory case gets one extra identity check under condition 6.


THE EIGHT CONDITIONS (design/02:141-153) — a failure of ANY ONE is a refusal
---------------------------------------------------------------------------
 1. the path is absolute;
 2. the path contains no `..`;
 3. the path does not change when symbolic links are resolved — i.e. no
    segment of it is a link;
 4. the resolved path lies STRICTLY inside the resolved scratchpad root and at
    least three levels deeper;
 5. the manifest exists;
 6. the path in the manifest matches the resolved actual one;
 7. the run id in the manifest matches the run id;
 8. the resolved path does not start with the resolved root of the checked
    project — compared BY SEGMENTS, after resolving both, never as a substring
    of a string (finding GD-18).

Plus, from the same section: a manifest that cannot be read or does not parse
is a refusal, and the scratchpad root itself must be an absolute path of an
existing directory, passed as an argument (design/02:136-140) — there is no
default and the environment is not a source.

Substitution between the check and the deletion (finding GD-4, design/02:154):
the directory is opened ONCE, with O_NOFOLLOW; the identity of the open
descriptor is compared against the checked path by (device, inode); every
removal below it goes through descriptor-relative calls, and the recursion
never follows a symbolic link.


INTERFACE
---------
    cleanup-scratchpad.py --root <scratchpad root>
                         [--manifest <path>] [--older-than-hours N]
                         [--run-id <id>] [--project-root <path>]
                         [--confirm]

    --root                the scratchpad root; required, absolute, existing
                          directory. No default; the environment is not a
                          source (design/02:136-140).
    --manifest            act on this one manifest. Without it the script
                          discovers every `critic-ledger-manifest.json`
                          under the root.
    --older-than-hours N  only manifests older than N hours (age from
                          `created_at`, not from mtime) — the interrupted-round
                          branch: cleanup runs at the next start of the skill
                          in the same project, over manifests older than a day
                          (design/02:170-172, so N=24).
    --run-id              the run id condition 7 must match. Default: the
                          basename of the directory the manifest describes.
    --project-root        the checked project's root for condition 8. Default:
                          the manifest's `project_root`. When both are given
                          they must agree.
    --confirm             actually delete. Without it: dry run.

Exit code: 0 only when there were no refusals (deleted and already-absent
entries are both fine); 1 when at least one manifest was refused; 2 on a usage
error (a bad root, an unreadable `--manifest` argument).

Provenance note: design/NN-*.md paths, round names (design-r1, skill-md-r1,
...), round-report paths (critic-rounds/<round>/...) and finding ids (GD-#,
GC-#, ...) cited here point at the author's private development notes; they are
provenance markers, not files shipped with this plugin.
"""  # noqa: D205  # module docstring wording is frozen verbatim

import argparse
import datetime as _dt
import json
import os
import stat
import sys
from typing import Any, cast

MANIFEST_NAME = "critic-ledger-manifest.json"
MANIFEST_VERSION_PREFIX = "critic-ledger/scratchpad-manifest@"
MIN_DEPTH_BELOW_ROOT = 3
# Step between the size units below.
BYTES_PER_UNIT = 1024

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

CONDITION_TITLES = {
    1: "path is absolute",
    2: "path has no '..' segment",
    3: "path unchanged by symlink resolution",
    4: f"inside the resolved scratchpad root, >= {MIN_DEPTH_BELOW_ROOT} levels deeper",
    5: "manifest exists",
    6: "manifest path matches the resolved actual path",
    7: "manifest run id matches the run id",
    8: "path is not inside the checked project's root",
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def segments(path: str) -> list[str]:
    """Split an absolute path into its segments ('/a/b' -> ['a', 'b'])."""
    return [p for p in path.split(os.sep) if p not in ("", ".")]  # noqa: PTH206  # deliberate textual split, not Path.parts


def is_inside(child: str, parent: str) -> bool:
    """True when `child` lies strictly inside `parent`, compared BY SEGMENTS.

    Both are expected to be already resolved. Segment comparison, never a
    substring test: '/tmp/scratch-evil' must NOT count as inside
    '/tmp/scratch' (finding GD-18).
    """
    c, p = segments(child), segments(parent)
    return len(c) > len(p) and c[: len(p)] == p


def depth_below(child: str, parent: str) -> int:
    """Number of path segments `child` has below `parent`."""
    return len(segments(child)) - len(segments(parent))


def dir_stats(path: str) -> tuple[int, int, list[str]]:
    """(file count, byte size, top-level entries) without following links."""
    files = 0
    size = 0
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        for name in filenames + dirnames:
            full = os.path.join(dirpath, name)  # noqa: PTH118  # os.path by design
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if not stat.S_ISDIR(st.st_mode):
                files += 1
                size += st.st_size
    top: list[str] = []
    try:
        for name in sorted(os.listdir(path)):  # noqa: PTH208  # os-level listing
            try:
                st = os.lstat(os.path.join(path, name))  # noqa: PTH118  # os.path by design
            except OSError:
                top.append(f"{name} (unreadable)")
                continue
            if stat.S_ISLNK(st.st_mode):
                top.append(f"{name} -> (symlink)")
            elif stat.S_ISDIR(st.st_mode):
                top.append(f"{name}/")
            else:
                top.append(name)
    except OSError as exc:
        top.append(f"(unreadable: {exc})")
    return files, size, top


def human(nbytes: int) -> str:
    """Format a byte count with a binary unit suffix."""
    unit = "B"
    val = float(nbytes)
    for nxt in ("KiB", "MiB", "GiB"):
        if val < BYTES_PER_UNIT:
            break
        val /= BYTES_PER_UNIT
        unit = nxt
    return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"


# --------------------------------------------------------------------------
# the unit of work: one manifest
# --------------------------------------------------------------------------


class Unit:
    """One manifest and everything the run decided about it."""

    created_at: _dt.datetime

    def __init__(self, manifest_path: str) -> None:
        """Start an empty record for the manifest at `manifest_path`."""
        self.manifest_path = manifest_path
        self.data: Any = None
        self.target: str | None = None  # the declared path, verbatim from the manifest
        self.checks: list[tuple[int, str, str]] = []  # (number, verdict, detail)
        self.errors: list[str] = []  # failures that are not one of the eight
        self.notes: list[str] = []
        self.status: str | None = None  # deleted | planned | refused | absent | skipped
        self.reason = ""

    def check(self, number: int, verdict: str, detail: str) -> None:
        """Record the verdict of one numbered condition."""
        self.checks.append((number, verdict, detail))

    def fail(self, detail: str) -> None:
        """A refusal that is not one of the eight conditions (a deletion that
        could not be carried out safely).
        """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
        self.errors.append(detail)

    def refused(self) -> bool:
        """True when any condition failed or a deletion could not be done."""
        return bool(self.errors) or any(v == FAIL for _, v, _ in self.checks)

    def first_failure(self) -> str:
        """Return the first failing condition or error as a one-line reason."""
        for number, verdict, detail in self.checks:
            if verdict == FAIL:
                return f"condition {number} ({CONDITION_TITLES[number]}): {detail}"
        if self.errors:
            return self.errors[0]
        return ""


def read_manifest(unit: Unit) -> bool:
    """Condition 5 plus the readable/parsable/format gates.

    Returns True when the manifest is usable. Every failure here is a refusal:
    "a manifest that cannot be read or is broken" is one, and the format check
    is what catches a file of a FOREIGN shape that happens to carry the name.
    """
    path = unit.manifest_path
    try:
        st = os.lstat(path)
    except OSError as exc:
        unit.check(5, FAIL, f"manifest not found: {exc.strerror}: {path}")
        return False
    if stat.S_ISLNK(st.st_mode):
        unit.check(5, FAIL, f"manifest is a symbolic link, refused: {path}")
        return False
    if not stat.S_ISREG(st.st_mode):
        unit.check(5, FAIL, f"manifest is not a regular file: {path}")
        return False
    try:
        with open(path, encoding="utf-8") as fh:  # noqa: PTH123  # os-level by design
            raw = fh.read()
    except OSError as exc:
        unit.check(5, FAIL, f"manifest unreadable: {exc.strerror}: {path}")
        return False
    try:
        data = json.loads(raw)
    except ValueError as exc:
        unit.check(5, FAIL, f"manifest is not valid JSON: {exc}")
        return False
    if not isinstance(data, dict):
        unit.check(5, FAIL, "manifest is not a JSON object — foreign format")
        return False

    version = data.get("manifest_version")
    if not isinstance(version, str) or not version.startswith(MANIFEST_VERSION_PREFIX):
        unit.check(
            5,
            FAIL,
            f"foreign manifest format: manifest_version={version!r}, "
            f"expected a string starting with {MANIFEST_VERSION_PREFIX!r}",
        )
        return False

    required = {
        "absolute_path": str,
        "run_id": str,
        "created_at": str,
        "project_root": str,
        "created": list,
        "size_bytes": int,
    }
    missing: list[str] = []
    for field, typ in required.items():
        value = data.get(field, None)
        if value is None:
            missing.append(f"{field} (missing)")
        elif not isinstance(value, typ) or (typ is int and isinstance(value, bool)):
            missing.append(
                f"{field} (expected {typ.__name__}, got {type(value).__name__})",
            )
    if missing:
        unit.check(5, FAIL, "foreign manifest format: " + "; ".join(missing))
        return False
    if not data["absolute_path"] or not data["project_root"]:
        unit.check(
            5,
            FAIL,
            "foreign manifest format: empty absolute_path or project_root",
        )
        return False

    try:
        ts = _dt.datetime.fromisoformat(data["created_at"])
    except ValueError as exc:
        unit.check(
            5,
            FAIL,
            f"broken manifest: created_at={data['created_at']!r} "
            f"is not ISO 8601 ({exc})",
        )
        return False
    if ts.tzinfo is None:
        unit.check(
            5,
            FAIL,
            f"broken manifest: created_at={data['created_at']!r} "
            f"carries no timezone offset; the age of a manifest "
            f"must not depend on the reader's clock zone",
        )
        return False

    unit.data = data
    unit.created_at = ts
    unit.target = data["absolute_path"]
    unit.check(5, PASS, f"manifest read and of a known format: {path}")
    return True


def run_conditions(
    unit: Unit,
    resolved_root: str,
    cli_run_id: str | None,
    cli_project_root: str | None,
) -> None:
    """Evaluate conditions 1-4 and 6-8 (5 was done while reading).

    They are ALL evaluated even when the target does not exist: nothing is
    deleted in that case anyway, but a manifest pointing outside the root is
    a defect worth reporting rather than swallowing.
    """
    target = cast("str", unit.target)

    # 1 - absolute
    if os.path.isabs(target):  # noqa: PTH117  # os.path by design
        unit.check(1, PASS, target)
    else:
        unit.check(1, FAIL, f"not an absolute path: {target!r}")

    # 2 - no '..'
    if ".." in target.split(os.sep):  # noqa: PTH206  # textual split by design
        unit.check(2, FAIL, f"path contains a '..' segment: {target!r}")
    else:
        unit.check(2, PASS, "no '..' segment")

    resolved = os.path.realpath(target)
    normalized = os.path.normpath(target)

    # 3 - unchanged by symlink resolution
    if resolved == target:
        unit.check(3, PASS, "no segment of the path is a symbolic link")
    elif normalized != target and os.path.realpath(normalized) == normalized:
        unit.check(
            3,
            FAIL,
            f"path is not in canonical form: {target!r} normalizes to "
            f"{normalized!r} (no symbolic link involved — the "
            f"difference is textual)",
        )
    else:
        unit.check(
            3,
            FAIL,
            f"path changes when links are resolved: {target!r} -> "
            f"{resolved!r}; a segment of it is a symbolic link",
        )

    # 4 - strictly inside the root, at least three levels deeper
    if not is_inside(resolved, resolved_root):
        unit.check(
            4,
            FAIL,
            f"resolved path {resolved!r} is not inside the resolved "
            f"scratchpad root {resolved_root!r} (segment comparison)",
        )
    else:
        depth = depth_below(resolved, resolved_root)
        if depth < MIN_DEPTH_BELOW_ROOT:
            unit.check(
                4,
                FAIL,
                f"resolved path is only {depth} level(s) below the root, "
                f"{MIN_DEPTH_BELOW_ROOT} required: {resolved!r}",
            )
        else:
            unit.check(4, PASS, f"inside {resolved_root!r}, {depth} levels deeper")

    # 6 - the manifest's path matches the resolved actual one
    manifest_real = os.path.realpath(unit.manifest_path)
    exists = os.path.lexists(target)
    if resolved != target:
        unit.check(
            6,
            FAIL,
            f"the declared path is not the resolved actual one: "
            f"{target!r} resolves to {resolved!r}",
        )
    elif not exists:
        # nothing on disk to compare against; the textual half still holds
        unit.check(
            6,
            PASS,
            "declared path is already canonical (nothing on disk to "
            "compare against — the target is absent)",
        )
    elif (
        is_inside(manifest_real, resolved) or os.path.dirname(manifest_real) == resolved  # noqa: PTH120  # os.path
    ):
        holder = os.path.dirname(manifest_real)  # noqa: PTH120  # os.path by design
        if holder == resolved:
            unit.check(
                6,
                PASS,
                f"the manifest lies directly in the directory it describes: {holder!r}",
            )
        else:
            unit.check(
                6,
                FAIL,
                f"the manifest lies at {manifest_real!r}, deeper than "
                f"the directory it describes ({resolved!r}); a manifest "
                f"must sit in its own run directory or outside it",
            )
    else:
        unit.check(
            6,
            PASS,
            f"sidecar manifest {manifest_real!r} for {resolved!r}; "
            f"declared path is canonical",
        )

    # 7 - run id
    declared_id = unit.data["run_id"]
    expected = cli_run_id or os.path.basename(resolved.rstrip(os.sep))  # noqa: PTH119  # os.path by design
    origin = "--run-id" if cli_run_id else "the basename of the run directory"
    if declared_id == expected:
        unit.check(7, PASS, f"run id {declared_id!r} matches {origin}")
    else:
        unit.check(
            7,
            FAIL,
            f"run id in the manifest is {declared_id!r}, but {origin} "
            f"says {expected!r}",
        )

    # 8 - not inside the checked project
    project = cli_project_root or unit.data["project_root"]
    if cli_project_root and unit.data["project_root"]:
        a = os.path.realpath(cli_project_root)
        b = os.path.realpath(unit.data["project_root"])
        if a != b:
            unit.check(
                8,
                FAIL,
                f"--project-root {a!r} disagrees with the manifest's "
                f"project_root {b!r}",
            )
            return
    if not project:
        unit.check(8, FAIL, "no project root to compare against (fail-closed)")
        return
    project_real = os.path.realpath(project)
    if resolved == project_real:
        unit.check(
            8,
            FAIL,
            f"the path to delete IS the checked project's root: {resolved!r}",
        )
    elif is_inside(resolved, project_real):
        unit.check(
            8,
            FAIL,
            f"the path to delete lies inside the checked project "
            f"{project_real!r}: {resolved!r}; the skill never deletes "
            f"anything inside the checked project",
        )
    else:
        unit.check(
            8,
            PASS,
            f"outside the checked project {project_real!r} (segment comparison)",
        )


# --------------------------------------------------------------------------
# deletion — by the language, over one open descriptor
# --------------------------------------------------------------------------


class Purge:
    """Recursive removal through descriptor-relative calls only.

    No shell, no path re-resolution below the opened root: every step is
    `os.unlink(name, dir_fd=...)` / `os.rmdir(name, dir_fd=...)` on a plain
    NAME inside a directory we already hold open, and every descent uses
    O_NOFOLLOW so a symbolic link can never be walked into.
    """

    OPEN_FLAGS = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )

    def __init__(self, keep_rel: str | None) -> None:
        """Prepare a purge that keeps `keep_rel` (and its parents) for last."""
        # relative posix path of the manifest inside the target, or None
        self.keep_rel = keep_rel
        self.keep_dirs: set[str] = set()
        if keep_rel:
            parts = keep_rel.split("/")
            for i in range(1, len(parts)):
                self.keep_dirs.add("/".join(parts[:i]))
        self.files = 0
        self.dirs = 0

    def open_sub(self, name: str, parent_fd: int) -> int:
        """Open `name` inside an already-open directory, never following links."""
        return os.open(name, self.OPEN_FLAGS, dir_fd=parent_fd)

    def walk(self, fd: int, rel_prefix: str) -> None:
        """Remove everything below the open directory `fd`, depth first."""
        for name in sorted(os.listdir(fd)):  # listing by descriptor
            rel = f"{rel_prefix}/{name}" if rel_prefix else name
            st = os.lstat(name, dir_fd=fd)
            if stat.S_ISDIR(st.st_mode):
                sub = self.open_sub(name, fd)
                try:
                    sub_st = os.fstat(sub)
                    if (sub_st.st_dev, sub_st.st_ino) != (st.st_dev, st.st_ino):
                        msg = (
                            f"directory {rel!r} changed identity between the "
                            f"lookup and the open — refusing to descend"
                        )
                        raise OSError(msg)
                    self.walk(sub, rel)
                finally:
                    os.close(sub)
                if rel not in self.keep_dirs:
                    os.rmdir(name, dir_fd=fd)
                    self.dirs += 1
            else:
                if rel == self.keep_rel:
                    continue
                os.unlink(name, dir_fd=fd)
                self.files += 1

    def finish_manifest(self, target_fd: int) -> None:
        """Delete the manifest last, then the directories that held it."""
        if not self.keep_rel:
            return
        parts = self.keep_rel.split("/")
        fds = [target_fd]
        try:
            for part in parts[:-1]:
                fds.append(self.open_sub(part, fds[-1]))
            os.unlink(parts[-1], dir_fd=fds[-1])
            self.files += 1
            for i in range(len(parts) - 2, -1, -1):
                os.rmdir(parts[i], dir_fd=fds[i])
                self.dirs += 1
        finally:
            for extra in fds[1:]:
                os.close(extra)


def delete_target(unit: Unit) -> bool:
    """Open the target once, verify its identity, delete through it."""
    target = cast("str", unit.target)
    parent = os.path.dirname(target)  # noqa: PTH120  # os.path by design
    try:
        pre = os.lstat(target)
    except OSError as exc:
        unit.fail(f"target vanished before the open: {exc.strerror}")
        return False
    if not stat.S_ISDIR(pre.st_mode):
        unit.fail(
            f"target is not a directory (mode {stat.filemode(pre.st_mode)}) "
            f"— refusing to delete: {target}",
        )
        return False

    try:
        parent_fd = os.open(parent, Purge.OPEN_FLAGS)
    except OSError as exc:
        unit.fail(f"cannot open the parent directory {parent}: {exc.strerror}")
        return False
    try:
        try:
            target_fd = os.open(
                os.path.basename(target),  # noqa: PTH119  # os.path by design
                Purge.OPEN_FLAGS,
                dir_fd=parent_fd,
            )
        except OSError as exc:
            unit.fail(
                f"cannot open the target directory (its type may have "
                f"changed): {exc.strerror}: {target}",
            )
            return False
        try:
            post = os.fstat(target_fd)
            if not stat.S_ISDIR(post.st_mode):
                unit.fail(
                    "the open descriptor is not a directory — "
                    "substituted between the check and the open",
                )
                return False
            if (post.st_dev, post.st_ino) != (pre.st_dev, pre.st_ino):
                unit.fail(
                    f"identity changed between the check and the open: "
                    f"({pre.st_dev},{pre.st_ino}) -> "
                    f"({post.st_dev},{post.st_ino}) — substitution, "
                    f"refusing to delete",
                )
                return False

            manifest_real = os.path.realpath(unit.manifest_path)
            keep_rel: str | None = None
            if is_inside(manifest_real, target):
                keep_rel = os.path.relpath(manifest_real, target).replace(os.sep, "/")

            purge = Purge(keep_rel)
            purge.walk(target_fd, "")
            purge.finish_manifest(target_fd)
        finally:
            os.close(target_fd)  # type: ignore[possibly-undefined]  # bound above
        os.rmdir(os.path.basename(target), dir_fd=parent_fd)  # noqa: PTH119  # os.path
        purge.dirs += 1
    except OSError as exc:
        unit.fail(f"deletion stopped: {exc}")
        return False
    finally:
        os.close(parent_fd)

    if keep_rel is None:
        # sidecar manifest: it is outside the deleted tree, remove it last
        try:
            os.unlink(unit.manifest_path)  # noqa: PTH108  # os-level removal
            purge.files += 1
            unit.notes.append(f"sidecar manifest removed last: {unit.manifest_path}")
        except OSError as exc:
            unit.notes.append(
                f"sidecar manifest could not be removed: "
                f"{exc.strerror}: {unit.manifest_path}",
            )

    unit.reason = f"removed {purge.files} file(s) and {purge.dirs} directory(ies)"
    return True


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def discover(resolved_root: str) -> list[str]:
    """Return every manifest found under the resolved scratchpad root."""
    found = []
    for dirpath, _dirnames, filenames in os.walk(resolved_root, followlinks=False):
        if MANIFEST_NAME in filenames:
            found.append(os.path.join(dirpath, MANIFEST_NAME))  # noqa: PTH118  # os.path by design
    return sorted(found)


def report_unit(unit: Unit, index: int, total: int) -> None:
    """Print one unit's manifest, target, condition verdicts and status."""
    print(f"[{index}/{total}] manifest: {unit.manifest_path}")
    print(f"        target: {unit.target or '(unknown)'}")
    for number, verdict, detail in sorted(unit.checks, key=lambda c: c[0]):
        print(
            f"          {verdict} condition {number} "
            f"({CONDITION_TITLES[number]}): {detail}",
        )
    for err in unit.errors:
        print(f"          {FAIL} deletion: {err}")
    for note in unit.notes:
        print(f"          note: {note}")
    print(
        f"        status: {cast('str', unit.status).upper()}"
        + (f" — {unit.reason}" if unit.reason else ""),
    )
    print()


def main(argv: list[str] | None = None) -> int:
    """Run the cleanup (dry by default) and return the process exit code."""
    ap = argparse.ArgumentParser(
        prog="cleanup-scratchpad.py",
        description="Remove critic-ledger project copies from the scratchpad, "
        "by manifest, by the language, dry by default.",
    )
    ap.add_argument(
        "--root",
        required=True,
        help="scratchpad root (absolute, existing directory; no "
        "default, the environment is not a source)",
    )
    ap.add_argument("--manifest", help="act on this manifest only")
    ap.add_argument(
        "--older-than-hours",
        type=float,
        default=None,
        help="only manifests older than N hours; age comes from "
        "created_at in the manifest, not from mtime",
    )
    ap.add_argument(
        "--run-id",
        help="run id condition 7 must match (default: basename of the run directory)",
    )
    ap.add_argument(
        "--project-root",
        help="checked project's root for condition 8 (default: "
        "project_root from the manifest)",
    )
    ap.add_argument(
        "--confirm",
        action="store_true",
        help="actually delete; without it the script only prints the plan",
    )
    args = ap.parse_args(argv)

    # --- the root is checked by the script itself (design/02:136-140) ---
    root = args.root
    if not os.path.isabs(root):  # noqa: PTH117  # os.path by design
        print(
            f"refusing: --root must be an absolute path, got {root!r}",
            file=sys.stderr,
        )
        return 2
    if os.sep + ".." + os.sep in root + os.sep or root.endswith(os.sep + ".."):
        print(
            f"refusing: --root must not contain a '..' segment: {root!r}",
            file=sys.stderr,
        )
        return 2
    if not os.path.isdir(root):  # noqa: PTH112  # os.path by design
        print(
            f"refusing: --root is not an existing directory: {root!r}",
            file=sys.stderr,
        )
        return 2
    resolved_root = os.path.realpath(root)

    mode = "CONFIRMED — deleting" if args.confirm else "DRY RUN — deleting nothing"
    print(f"cleanup-scratchpad: {mode}")
    print(f"scratchpad root: {root}")
    if resolved_root != root:
        print(f"resolved root:   {resolved_root}")
    print()

    if args.manifest:
        if not os.path.isabs(args.manifest):  # noqa: PTH117  # os.path by design
            print(
                f"refusing: --manifest must be an absolute path, got {args.manifest!r}",
                file=sys.stderr,
            )
            return 2
        manifests = [args.manifest]
    else:
        manifests = discover(resolved_root)
        if not manifests:
            print(f"no {MANIFEST_NAME} found under {resolved_root}")
            print("summary: deleted=0 refused=0 already-absent=0 skipped=0")
            return 0

    now = _dt.datetime.now(_dt.UTC)
    deleted = refused = absent = skipped = 0
    total = len(manifests)

    for index, manifest_path in enumerate(manifests, start=1):
        unit = Unit(manifest_path)
        if not read_manifest(unit):
            unit.status = "refused"
            unit.reason = unit.first_failure()
            refused += 1
            report_unit(unit, index, total)
            continue

        if args.older_than_hours is not None:
            age_h = (now - unit.created_at).total_seconds() / 3600.0
            if age_h < args.older_than_hours:
                unit.status = "skipped"
                unit.reason = (
                    f"age {age_h:.2f} h (created_at "
                    f"{unit.data['created_at']}) is below the "
                    f"--older-than-hours {args.older_than_hours} "
                    f"threshold"
                )
                skipped += 1
                report_unit(unit, index, total)
                continue
            unit.notes.append(
                f"age {age_h:.2f} h from created_at "
                f"{unit.data['created_at']} (not from mtime)",
            )

        run_conditions(unit, resolved_root, args.run_id, args.project_root)

        if unit.refused():
            unit.status = "refused"
            unit.reason = unit.first_failure()
            refused += 1
            report_unit(unit, index, total)
            continue

        if not os.path.lexists(cast("str", unit.target)):
            unit.status = "already absent"
            unit.reason = (
                "the path from the manifest does not exist; nothing "
                "to delete, the manifest is left in place"
            )
            absent += 1
            report_unit(unit, index, total)
            continue

        files, size, top = dir_stats(cast("str", unit.target))
        declared = unit.data.get("created") or []
        actual_top = [t.rstrip("/").split(" ->")[0] for t in top]
        leftovers = [d for d in declared if d not in actual_top]
        if leftovers:
            unit.notes.append(
                "mismatch note: entries listed in the manifest "
                "but absent on disk: " + ", ".join(map(str, leftovers)),
            )
        if (
            unit.data.get("size_bytes")
            and size
            and abs(unit.data["size_bytes"] - size) > max(size, 1) * 0.5
        ):
            unit.notes.append(
                f"mismatch note: manifest says "
                f"{human(unit.data['size_bytes'])}, on disk "
                f"{human(size)}",
            )
        unit.notes.append(f"contents: {files} file(s), {human(size)}")
        unit.notes.append("top level: " + (", ".join(top) if top else "(empty)"))

        if not args.confirm:
            unit.status = "planned"
            unit.reason = (
                "would be deleted on a second call with --confirm (nothing was touched)"
            )
            report_unit(unit, index, total)
            continue

        if delete_target(unit):
            unit.status = "deleted"
            deleted += 1
        else:
            unit.status = "refused"
            unit.reason = unit.first_failure()
            refused += 1
        report_unit(unit, index, total)

    print(
        f"summary: deleted={deleted} refused={refused} "
        f"already-absent={absent} skipped={skipped}",
    )
    if not args.confirm:
        planned = total - refused - absent - skipped
        print(
            f"dry run: {planned} path(s) would be deleted; re-run with "
            f"--confirm to delete them",
        )
    if refused:
        print(
            "ledger header line(s) to write: "
            "'scratchpad not cleaned: <reason>, <path>' for each refusal",
        )
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
