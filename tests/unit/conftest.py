"""Shared fixtures for the CLI characterization suite.

The suite pins the CURRENT observable behavior of the seven standalone,
stdlib-only CLI scripts that ship under `skills/critic-ledger/templates/`,
plus the one shipped POSIX-shell script (`copy-project.sh`, driven through
`sh` by the `run_sh` fixture). Every script is exercised through a real
subprocess call, because argv, stdout/stderr, exit codes and filesystem
effects are the contract those scripts publish.

The directory holding the scripts under test is resolved once, from the
`CRITIC_LEDGER_SCRIPTS_DIR` environment variable, and falls back to the
repository-relative `skills/critic-ledger/templates/`. That single
indirection lets the same suite validate a copy of the scripts (a
pre-refactor snapshot, a candidate build) without editing a test.

Safety rules the fixtures enforce:

* every path a script is pointed at is created inside pytest's `tmp_path`;
* `HOME` and git's configuration lookups are redirected into `tmp_path`,
  so no user or system configuration takes part in a run;
* git repositories used as fixtures are created inside `tmp_path` too —
  no test ever writes to the repository the suite lives in.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR_ENV = "CRITIC_LEDGER_SCRIPTS_DIR"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCRIPTS_DIR = REPO_ROOT / "skills" / "critic-ledger" / "templates"

SCRIPT_NAMES = (
    "check-frontmatter.py",
    "cleanup-scratchpad.py",
    "deleted-lines.py",
    "recount.py",
    "set-cell.py",
    "transcribe.py",
    "validate-report.py",
)

# Shipped scripts that are POSIX shell rather than Python. They are driven
# through `sh` by the `run_sh` fixture, never through the interpreter.
SHELL_SCRIPT_NAMES = ("copy-project.sh",)

# The two shipped scripts this conftest CHECKS FOR but never runs: their own
# modules (`test_trace.py`, `test_rollup.py`) drive them through a private
# subprocess helper rather than through the `run` fixture, and `SCRIPT_NAMES`
# is that fixture's execution whitelist. They are named separately so that
# the presence check below covers all ten shipped scripts while the whitelist
# — and what those two modules say about it — stays exactly as it was.
CHECKED_ONLY_NAMES = ("trace.py", "rollup.py")

MANIFEST_NAME = "critic-ledger-manifest.json"
MANIFEST_VERSION = "critic-ledger/scratchpad-manifest@1"


# ---------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------

def hardened_env(home: Path) -> dict[str, str]:
    """A process environment with HOME and git config redirected into tmp."""
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / "config"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Suite Author",
            "GIT_AUTHOR_EMAIL": "author@example.invalid",
            "GIT_COMMITTER_NAME": "Suite Author",
            "GIT_COMMITTER_EMAIL": "author@example.invalid",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    for leaked in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                   "GIT_OBJECT_DIRECTORY", "GIT_CEILING_DIRECTORIES"):
        env.pop(leaked, None)
    return env


@pytest.fixture(scope="session")
def scripts_dir() -> Path:
    """Directory holding the scripts under test."""
    raw = os.environ.get(SCRIPTS_DIR_ENV)
    directory = Path(raw).expanduser().resolve() if raw else DEFAULT_SCRIPTS_DIR
    if not directory.is_dir():
        pytest.fail(f"scripts directory does not exist: {directory} "
                    f"(set {SCRIPTS_DIR_ENV} to override)")
    missing = [
        n
        for n in (*SCRIPT_NAMES, *SHELL_SCRIPT_NAMES, *CHECKED_ONLY_NAMES)
        if not (directory / n).is_file()
    ]
    if missing:
        pytest.fail(f"scripts missing from {directory}: {', '.join(missing)}")
    return directory


@pytest.fixture
def sandbox_home(tmp_path: Path) -> Path:
    return tmp_path / "home"


@pytest.fixture
def run(scripts_dir: Path, sandbox_home: Path, tmp_path: Path):
    """Invoke one of the scripts under test and return the CompletedProcess."""
    default_cwd = tmp_path / "cwd"
    default_cwd.mkdir(exist_ok=True)
    env = hardened_env(sandbox_home)

    def _run(script: str, *args: object, cwd: Path | None = None,
             stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        if script not in SCRIPT_NAMES:
            msg = f"unknown script {script!r}"
            raise AssertionError(msg)
        cmd = [sys.executable, str(scripts_dir / script), *map(str, args)]
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            cwd=str(cwd if cwd is not None else default_cwd),
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )

    return _run


@pytest.fixture
def run_sh(scripts_dir: Path, sandbox_home: Path, tmp_path: Path):
    """Invoke one of the shipped SHELL scripts through `sh`.

    `extra_path` prepends a directory to `PATH`, which is how a test injects
    a stub for one of the external commands the script shells out to (git,
    rm). The stub directory always lives inside `tmp_path`.
    """
    default_cwd = tmp_path / "cwd"
    default_cwd.mkdir(exist_ok=True)

    def _run(script: str, *args: object, cwd: Path | None = None,
             extra_path: Path | None = None) -> subprocess.CompletedProcess[str]:
        if script not in SHELL_SCRIPT_NAMES:
            msg = f"unknown shell script {script!r}"
            raise AssertionError(msg)
        env = hardened_env(sandbox_home)
        if extra_path is not None:
            env["PATH"] = f"{extra_path}{os.pathsep}{env['PATH']}"
        cmd = ["sh", str(scripts_dir / script), *map(str, args)]
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            cwd=str(cwd if cwd is not None else default_cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )

    return _run


# ---------------------------------------------------------------------------
# throwaway git repositories (always inside tmp_path)
# ---------------------------------------------------------------------------

@dataclass
class GitRepo:
    """A disposable git repository living inside tmp_path."""

    path: Path
    env: dict[str, str]

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(self.path), *args],  # noqa: S607
            env=self.env, capture_output=True, text=True, check=True,
        )

    def write(self, relpath: str, text: str) -> Path:
        target = self.path / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def write_bytes(self, relpath: str, blob: bytes) -> Path:
        target = self.path / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        return target

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.head()

    def head(self, rev: str = "HEAD") -> str:
        return self.git("rev-parse", rev).stdout.strip()


@pytest.fixture
def make_repo(tmp_path: Path, sandbox_home: Path):
    """Factory building an initialized, disposable git repository."""
    env = hardened_env(sandbox_home)

    def _make(name: str = "repo") -> GitRepo:
        path = tmp_path / name
        path.mkdir(parents=True)
        subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-c", "init.defaultBranch=main", "init", "-q",  # noqa: S607
             str(path)],
            env=env, capture_output=True, text=True, check=True,
        )
        repo = GitRepo(path=path, env=env)
        repo.git("config", "user.name", "Suite Author")
        repo.git("config", "user.email", "author@example.invalid")
        repo.git("config", "commit.gpgsign", "false")
        return repo

    return _make


# ---------------------------------------------------------------------------
# scratchpad fixtures for cleanup-scratchpad.py (never outside tmp_path)
# ---------------------------------------------------------------------------

@dataclass
class ScratchRun:
    target: Path
    manifest: Path
    data: dict[str, object]


@dataclass
class Scratch:
    """A scratchpad root and a checked-project root, both inside tmp_path."""

    root: Path
    project: Path
    runs: list[ScratchRun] = field(default_factory=list)

    def make_run(
        self,
        dir_name: str = "sample-run",
        *,
        parts: tuple[str, ...] = ("critic", "runs"),
        create_target: bool = True,
        contents: dict[str, str] | None = None,
        manifest_at: Path | None = None,
        write_manifest: bool = True,
        **overrides: object,
    ) -> ScratchRun:
        """Create a run directory plus its manifest.

        `parts` are the intermediate segments under the scratchpad root, so
        the default target sits three levels below it — the depth the
        script's condition 4 requires. Any manifest field can be replaced
        through `**overrides` (including `run_id`, which otherwise mirrors
        the directory name).
        """
        target = self.root.joinpath(*parts, dir_name)
        if contents is None:
            contents = {"copy-1/file.txt": "a" * 2048, "notes.md": "b" * 2048}
        size = 0
        if create_target:
            target.mkdir(parents=True)
            for rel, text in contents.items():
                blob = target / rel
                blob.parent.mkdir(parents=True, exist_ok=True)
                blob.write_text(text, encoding="utf-8")
                size += len(text.encode("utf-8"))
        top_level = sorted({rel.split("/")[0] for rel in contents})

        data: dict[str, object] = {
            "manifest_version": MANIFEST_VERSION,
            "absolute_path": str(target),
            "run_id": dir_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "project_root": str(self.project),
            "created": top_level,
            "size_bytes": size,
        }
        data.update(overrides)

        manifest = manifest_at if manifest_at is not None else target / MANIFEST_NAME
        if write_manifest:
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        run = ScratchRun(target=target, manifest=manifest, data=data)
        self.runs.append(run)
        return run

    def sidecar_path(self, run_id: str) -> Path:
        return self.root / "sidecars" / run_id / MANIFEST_NAME


@pytest.fixture
def scratch(tmp_path: Path) -> Scratch:
    """A resolved scratchpad root and project root, both under tmp_path.

    The paths are resolved because the script's condition 3 refuses any
    target whose textual path differs from its symlink-resolved form, and
    the temporary directory itself may sit behind a symbolic link.
    """
    base = tmp_path.resolve()
    root = base / "scratchpad"
    project = base / "project"
    root.mkdir()
    project.mkdir()
    (project / "README.md").write_text("checked project\n", encoding="utf-8")
    return Scratch(root=root, project=project)


def hours_ago(hours: float) -> str:
    """An ISO 8601 timestamp with an offset, `hours` in the past."""
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


# ---------------------------------------------------------------------------
# ledger / report builders
# ---------------------------------------------------------------------------

HEADER_7 = (
    "| id | sev | claim | verdict | fix | verified | terminal |\n"
    "|---|---|---|---|---|---|---|\n"
)
HEADER_8 = (
    "| id | sev | claim | verdict | criterion | fix | verified | terminal |\n"
    "|---|---|---|---|---|---|---|---|\n"
)
# The v3 schema: `zone` inserted THIRD, so that `criterion`, `fix`,
# `verified` and `terminal` keep their addresses from the END of the row.
HEADER_9 = (
    "| id | sev | zone | claim | verdict | criterion | fix | verified | "
    "terminal |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)


def write_ledger(path: Path, rows: str, *, header: str = HEADER_8,
                 preamble: str = "", suffix: str = "") -> Path:
    """Write a ledger file: optional preamble, findings table, optional tail."""
    body = rows if rows.endswith("\n") or not rows else rows + "\n"
    path.write_text(preamble + header + body + suffix, encoding="utf-8")
    return path


@pytest.fixture
def ledger(tmp_path: Path):
    """Factory writing a ledger file into tmp_path."""
    counter = {"n": 0}

    def _ledger(rows: str, *, header: str = HEADER_8, preamble: str = "",
                suffix: str = "", name: str | None = None) -> Path:
        counter["n"] += 1
        path = tmp_path / (name or f"ledger-{counter['n']}.md")
        return write_ledger(path, rows, header=header, preamble=preamble,
                            suffix=suffix)

    return _ledger


@pytest.fixture
def report(tmp_path: Path):
    """Factory writing a critic-report file into tmp_path."""
    counter = {"n": 0}

    def _report(text: str, *, name: str | None = None) -> Path:
        counter["n"] += 1
        path = tmp_path / (name or f"report-{counter['n']}.md")
        path.write_text(text, encoding="utf-8")
        return path

    return _report


FENCE = "```"
