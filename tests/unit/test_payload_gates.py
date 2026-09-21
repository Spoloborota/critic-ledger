"""Content gates over the shipped payload, read as FILES rather than as CLIs.

* **No network primitive exists in the payload.** The gate is one command
  over `scripts/*.py`, so it is checked over the whole directory here.
  A per-script test cannot fail when a network import appears in a third
  file.
"""

from __future__ import annotations

import ast
import re
import subprocess

import pytest

from conftest import BINARY_SUFFIXES, NON_SOURCE_DIRS, REPO_ROOT, text_of

SCRIPTS_DIR = REPO_ROOT / "skills" / "critic-ledger" / "scripts"
TEMPLATES_DIR = REPO_ROOT / "skills" / "critic-ledger" / "templates"
COPY_SCRIPT = SCRIPTS_DIR / "copy-project.sh"
WHY_CRITICS = REPO_ROOT / "docs" / "why-critics.md"
README_MD = REPO_ROOT / "README.md"
SKILL_MD = REPO_ROOT / "skills" / "critic-ledger" / "SKILL.md"


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


# --- the network gate over the whole payload -------------------------------


def test_no_template_script_imports_a_network_primitive(scripts_dir):
    """The network gate over `scripts/*.py`, as one sweep."""
    offenders = []
    for path in sorted(scripts_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        offenders += [
            f"{path.name}: {token}" for token in NETWORK_TOKENS if token in text
        ]
    assert offenders == []


def test_the_copy_script_offers_no_way_to_force_the_clone():
    """An opt-out flag would make the gate decorative."""
    script = text_of(COPY_SCRIPT)
    for flag in ("--fast-clone", "--force-clone", "--no-preflight",
                 "--skip-preflight"):
        assert flag not in script, flag


# Spelled in two halves ON PURPOSE: the invariant below is that this token
# does not occur under the payload, and a test file carrying it whole would
# be the very hit `grep -rn` must not find.
SPAWN_PARAM = "run_in_" + "background"
# The payload's prose and scripts, named by directory: `tests/` is left out
# because a local virtualenv and a pytest cache live under it, and neither
# ships.
PAYLOAD_DIRS = ("skills", "agents", "docs", "examples")


def payload_text_files():
    """Every shipped prose/script file, top-level documents included."""
    files = [path for path in sorted(REPO_ROOT.glob("*.md")) if path.is_file()]
    for name in PAYLOAD_DIRS:
        directory = REPO_ROOT / name
        if not directory.is_dir():
            continue
        files += [path for path in sorted(directory.rglob("*")) if path.is_file()]
    return files


def test_the_payload_promises_no_spawn_parameter_it_cannot_pass():
    """The foreground promise named an input the orchestrator does not have.

    A requirement resting on a nonexistent parameter is unenforceable, and
    the sweep is over the payload rather than over stage 7 alone so that the
    name cannot reappear in a second file.
    """
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in payload_text_files()
        if SPAWN_PARAM in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []


# The withdrawn figures, as the pattern the requirement is written with. The
# decimal comma is in it because `16,6` is the same claim as `16.6`.
# The alternatives are anchored against ADJACENT DIGITS, because unanchored
# they match digit runs that merely contain a figure: `525` fires inside
# `1525`, `8.5` inside `18.5`, `47%` inside `147%`. Unanchored, the absence
# assertion below would be about substrings rather than about the withdrawn
# claims, and an unrelated future number sharing a digit run would fail it.
# The guards forbid a digit — or a digit and a decimal separator — before the
# figure, and a digit, or a decimal separator followed by a digit, after it.
# A trailing `.` that ends a sentence is not part of a number, so `525.` at
# the end of a sentence still matches, which is how the figure is written in
# the file that KEEPS it.
WITHDRAWN_FIGURES = re.compile(
    r"(?<!\d)(?<!\d[.,])"
    r"(?:47%|16[.,]6|525|2[.,]7|8[.,]5|~100%|70%|1→0)"
    r"(?!\d)(?![.,]\d)"
)
# Every one of them, as it stands in the file that KEEPS them.
FIGURES_KEPT = {"47%", "16.6", "525", "2.7", "8.5", "~100%", "70%", "1→0"}
# The two files the withdrawal cleared.
FIGURE_FREE = (README_MD, SKILL_MD)


def shipped_payload_files():
    """Every shipped file, walked by directory rather than by `git`.

    The suite must pass over a COPY of the payload (`CRITIC_LEDGER_SCRIPTS_DIR`),
    where no index exists, so the walk is over `PAYLOAD_DIRS` — the same
    directories `payload_text_files()` uses, for the same reason it leaves
    `tests/` out — plus every top-level file, which that helper narrows to
    `*.md` and this one does not. A local run leaves caches inside the payload
    (`__pycache__`, `.mypy_cache`, `.ruff_cache`); none of them ships, so a
    path with a dot-directory in it is not a shipped file.
    """

    def ships(path):
        parts = path.relative_to(REPO_ROOT).parts[:-1]
        return path.is_file() and not any(
            part.startswith(".") or part == "__pycache__" for part in parts
        )

    files = [path for path in sorted(REPO_ROOT.glob("*")) if path.is_file()]
    for name in PAYLOAD_DIRS:
        directory = REPO_ROOT / name
        if not directory.is_dir():
            continue
        files += [path for path in sorted(directory.rglob("*")) if ships(path)]
    return files


@pytest.mark.parametrize("path", FIGURE_FREE)
def test_no_efficacy_figure_is_left_in_the_front_door_files(path):
    """The withdrawal, as the absence it is defined by."""
    hits = WITHDRAWN_FIGURES.findall(text_of(path))
    assert hits == [], f"{path.name}: {hits}"


def test_every_withdrawn_figure_survives_where_it_is_provenance():
    """Withdrawal is a re-framing, not a deletion.

    A test that only checked the absence would be satisfied by deleting the
    observations outright, which is the opposite of what was decided.
    """
    assert set(WITHDRAWN_FIGURES.findall(text_of(WHY_CRITICS))) == FIGURES_KEPT


def test_no_binary_asset_ships_with_the_payload():
    """The round is shown as text; nothing renders it as an image or a cast."""
    files = shipped_payload_files()
    # Fail-closed: an empty walk must never be reported as a clean one.
    assert len(files) > 30, len(files)
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in files
        if path.suffix.lower() in BINARY_SUFFIXES
    ]
    assert offenders == []


# Reaching out of the payload root, in the two forms a test can write it.
# Both are patterns rather than plain substrings, which is what lets the
# sweep cover this file too: the source below carries each token with a
# backslash in it and therefore does not match itself. The word boundary in
# the first also keeps `workflow_files()`'s bounded, git-stopped climb out
# of the sweep — that walk is over the ENCLOSING repository's workflows,
# declared and capped, and is not what this gate is about.
REACH_ABOVE_ROOT = (
    re.compile(r"\bREPO_ROOT\.parent\b"),
    re.compile(r"\bparents\[3\]"),
)


def test_no_test_in_the_payload_reaches_above_the_payload_root():
    """The published suite tests the published tree and nothing above it."""
    sources = sorted((REPO_ROOT / "tests").rglob("*.py"))
    # Fail-closed: no sources found means the sweep proved nothing.
    assert len(sources) > 5, [str(path) for path in sources]
    offenders = []
    for path in sources:
        if any(part in NON_SOURCE_DIRS for part in path.parts):
            continue
        text = text_of(path)
        for number, line in enumerate(text.splitlines(), 1):
            for pattern in REACH_ABOVE_ROOT:
                if pattern.search(line):
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}"
                    )
    assert offenders == [], offenders


# --- the plugin opens no connection and reads no environment ---------------
#
# The invariant is one COMMAND, and every requirement that leans on it cites
# that command rather than paraphrasing it: a paraphrase is a second
# predicate, and the two would drift. The pattern below is that text,
# character for character.
#
# It is checked in BOTH halves, because either alone proves nothing. The
# first half runs it over the shipped scripts and requires zero matches —
# the invariant itself. The second half runs the SAME pattern over three
# lines of positive control and requires exactly three matches — that the
# predicate still catches what it was written to catch. A predicate quietly
# broken (a `\s` where a POSIX class belongs, which BSD `grep -E` reads as
# the letter `s`) would pass the first half on every tree forever.
NETWORK_PREDICATE = (
    r"^[[:space:]]*(import|from)[[:space:]]+(urllib|http|socket|requests|ssl)"
    r"([[:space:].]|$)|urlopen\(|os\.environ|getenv\(|expanduser\(|Path\.home\("
)
# The three lines of the self-test, and the count they must produce.
POSITIVE_CONTROL = "import http\nfrom urllib import request\nx = os.environ\n"
POSITIVE_CONTROL_MATCHES = 3

# The sweep is RECURSIVE over BOTH shipped directories, `scripts/` and
# `templates/`, so a script added in a subdirectory of either — or put in
# `templates/` instead of `scripts/` — cannot escape it. Exactly one file
# is exempt, and it is named here — so that the exemption is recorded
# instead of showing up as an
# unexplained absence: `otel/otel-receiver.py` is a LOOPBACK LISTENER the
# user installs and starts himself. It imports `http.server` for the
# listening half and `socket` for `status`; it opens no outbound
# connection, and the two tests below hold it to that.
NETWORK_SERVER_EXEMPT = ("otel/otel-receiver.py",)

# What the exempt receiver may still never import: every one of these is a
# CLIENT — a way to reach out — and reaching out is what the invariant is
# about, not the word `socket`.
OUTBOUND_CLIENT_MODULES = (
    "urllib",
    "requests",
    "http.client",
    "ftplib",
    "smtplib",
)
# `socket` is admitted in ONE function of the receiver, the loopback
# connect that answers "is the port up"; and that function is called from
# ONE place, the `status` subcommand.
SOCKET_HOLDER = "port_answers"
SOCKET_CALLER = "status"

# The OTHER half of the predicate the exemption suspends is
# environment-reading, and it is NOT suspended: the receiver may expand a
# path the user typed, and nothing more. A later `os.environ` read in that
# file would otherwise pass every gate in silence.
# The PATH is the environment too: a lookup on it reads the environment
# without naming it, so the third literal closes that door as well.
ENV_FORBIDDEN = ("os.environ", "getenv(", "shutil.which(")
ENV_ALLOWED = ("expanduser(", "Path.home(")

# `subprocess` is admitted too, and ONLY for service management —
# `install`, `uninstall`, `status`. The receiving path must execute
# nothing at all, so the file declares the split with this marker line and
# the test holds it: `serve` and its handler are defined ABOVE it, the
# three service subcommands BELOW it, and the only mention of
# `subprocess` above the marker is the import itself.
SERVICE_MARKER = "# --- service management ---"
SERVE_SIDE = ("def make_handler(", "def serve(")
SERVICE_SIDE = ("def install(", "def uninstall(", "def status(")


def swept_templates():
    """Every shipped script the network sweep must read, under both roots."""
    roots = (SCRIPTS_DIR, TEMPLATES_DIR)
    exempt = {TEMPLATES_DIR / name for name in NETWORK_SERVER_EXEMPT}
    return sorted(
        p for root in roots for p in root.rglob("*.py") if p not in exempt
    )


def test_no_template_imports_a_network_or_environment_module():
    """Zero matches over the shipped scripts: the invariant itself."""
    scripts = swept_templates()
    assert scripts, f"{SCRIPTS_DIR} {TEMPLATES_DIR}"
    found = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["grep", "-nE", NETWORK_PREDICATE, *[str(p) for p in scripts]],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    assert found.stdout == "", found.stdout
    assert found.returncode == 1, found.returncode


def test_the_network_predicate_still_catches_what_it_was_written_for():
    """Exactly three matches on the positive control: the predicate is intact."""
    found = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["grep", "-nE", NETWORK_PREDICATE, "-"],  # noqa: S607
        input=POSITIVE_CONTROL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert found.returncode == 0, found.stderr
    assert len(found.stdout.splitlines()) == POSITIVE_CONTROL_MATCHES, found.stdout


def test_the_exempt_receiver_opens_no_outbound_connection():
    """The exempt file listens; it never reaches out.

    The exemption buys `http.server` and one loopback connect, nothing
    else — so no client module is imported at all, and `socket` is touched
    in exactly one function, which exactly one subcommand calls.

    It buys NOTHING on the environment half of the predicate: the file may
    expand a path the user typed and no more. And the `subprocess` the
    three service subcommands need is confined below the marker line, so
    the receiving path executes nothing.
    """
    for name in NETWORK_SERVER_EXEMPT:
        path = TEMPLATES_DIR / name
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        offenders = sorted(
            module for module in imported
            if module in OUTBOUND_CLIENT_MODULES
        )
        assert offenders == [], f"{name}: {offenders}"
        assert "urlopen(" not in text, name

        holders = set()
        callers = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Attribute)
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id == "socket"
                ):
                    holders.add(node.name)
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == SOCKET_HOLDER
                ):
                    callers.add(node.name)
        assert holders == {SOCKET_HOLDER}, f"{name}: {sorted(holders)}"
        assert callers == {SOCKET_CALLER}, f"{name}: {sorted(callers)}"

        # The environment half of the predicate, unsuspended.
        for forbidden in ENV_FORBIDDEN:
            assert forbidden not in text, f"{name}: {forbidden}"
        for allowed in ENV_ALLOWED:
            assert allowed in text, f"{name}: {allowed}"

        # The execution half: one marker, the serve side above it, the
        # three service subcommands below it, and no `subprocess` above it
        # other than the import statement that brings it in.
        lines = text.splitlines()
        marks = [i for i, line in enumerate(lines) if line.strip() == SERVICE_MARKER]
        assert len(marks) == 1, f"{name}: {marks}"
        head = "\n".join(lines[: marks[0]])
        tail = "\n".join(lines[marks[0] :])
        for anchor in SERVE_SIDE:
            assert anchor in head, f"{name}: {anchor}"
            assert anchor not in tail, f"{name}: {anchor}"
        for anchor in SERVICE_SIDE:
            assert anchor in tail, f"{name}: {anchor}"
            assert anchor not in head, f"{name}: {anchor}"
        above = [
            line for line in head.splitlines()
            if not line.lstrip().startswith("import subprocess")
        ]
        assert "subprocess" not in "\n".join(above), name
        assert "subprocess" in tail, name
