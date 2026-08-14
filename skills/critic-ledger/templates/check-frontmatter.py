#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Mechanical frontmatter check for a SKILL.md against the PORTABLE Agent
Skills specification. The skill's own header is edited by hand;
six-field compatibility otherwise rests on nobody forgetting it.

SCOPE — SKILL.md HEADERS ONLY. Every vocabulary below (the portable six
and the platform extensions) is the SKILL frontmatter vocabulary. Agent
definitions (`agents/*.md`) have a DIFFERENT field set — `tools`, for one
— so running this script on an agent file is outside its contract: it
will report perfectly valid agent fields as UNKNOWN typos. Do not point it
at agents/*.md; `claude plugin validate` is the tool for those.

What the portable spec allows
-----------------------------
The portable specification (agentskills.io) admits EXACTLY SIX top-level
frontmatter fields:

    name, description, license, compatibility, metadata, allowed-tools

Everything else a harness understands — `model`, `effort`, `context`,
`argument-hint`, `disable-model-invocation`, … — is a PLATFORM EXTENSION.
Extensions are NOT errors: this plugin is deliberately Claude Code
specific. They are LISTED so the header's portability is a visible fact
rather than an assumption. A field that is neither portable nor a known
extension is an UNKNOWN field: most likely a typo (`descriptions:`,
`allowed_tools:`) that the harness will silently ignore.

Parsing contract (stdlib only, no YAML library)
-----------------------------------------------
- The frontmatter is the block between the FIRST line of the file and the
  next line that is exactly `---`. The opening delimiter MUST be line 1:
  a `---` further down a markdown document is a horizontal rule, not a
  header, and treating it as one would invent fields out of prose.
- A file whose first line is not `---` simply HAS no frontmatter. That is
  a verdict of its own (`NO FRONTMATTER`), not an error — exit 0.
- Top-level keys are lines matching `<key>:` at column 0 (no leading
  whitespace). Indented lines are continuations — block scalars (`>-`,
  `|`), list items, nested mappings — and are never keys. Quoted keys
  (`"name":`) are NOT recognized; the spec's own examples are unquoted,
  and inventing quote handling without a YAML parser would be guesswork.
- FAIL-CLOSED (never silent): an opening `---` with no closing `---`, or
  a duplicate top-level key (ambiguous — the harness's last-wins is not
  this script's to assume), is a STRUCTURAL ERROR: exit 2, no verdict is
  trustworthy until it is fixed.
- Informational only, never affecting the exit code: the spec's two
  REQUIRED fields (`name`, `description`) are reported when missing. The
  authority on required-field validation is `claude plugin validate
  --strict`; this script's contract is the field INVENTORY.

Usage:  check-frontmatter.py <SKILL.md> [--strict-portable]
        check-frontmatter.py -h | --help             (this text, exit 0)
Exit codes: 0 = no unknown fields (and, under --strict-portable, no
platform extensions either), or `-h`/`--help`; 1 = unknown fields present
— each named — or `--strict-portable` with a non-empty extension list;
2 = the file cannot be read, or its frontmatter is structurally broken.
"""  # noqa: D205  # printed verbatim as the usage text; reflowing changes output

import re
import sys
from pathlib import Path

# The portable specification: exactly these six top-level fields.
PORTABLE = (
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
)

# Known Claude Code extensions OF THE SKILL.md VOCABULARY — recognized so
# they are reported as non-portable rather than as typos. This list, like
# PORTABLE above, describes skill headers ONLY; agent frontmatter has a
# different field set (`tools`, `description`, …), so pointing this script
# at agents/*.md is out of contract and will call agent fields UNKNOWN.
# `allowed-tools` is NOT here: it is portable (above) and a key belongs to
# exactly one list.
PLATFORM_EXTENSIONS = {
    "model": "model the skill's own session runs on",
    "effort": "reasoning-effort level",
    "context": "context-window selection",
    "agent": "agent definition the skill binds to",
    "argument-hint": "argument hint shown for a slash command",
    "arguments": "declared arguments of a slash command",
    "disable-model-invocation": "block autonomous (model-side) triggering",
    "disallowed-tools": "tool denylist (the complement of allowed-tools)",
    "paths": "directory scoping of the skill",
    "user-invocable": "expose (or hide) the skill as a slash command",
    "hooks": "hooks the skill installs",
}

REQUIRED = ("name", "description")

KEY_RE = re.compile(r"^([^\s:#][^:]*):(\s|$)")
DELIM = "---"


def extract_block(lines: list[str]) -> tuple[list[tuple[str, int]] | None, str | None]:
    """Return (keys, error). `keys` is None when the file has no
    frontmatter at all; otherwise a list of (key, line-number) in order of
    appearance, duplicates included.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    if not lines or lines[0].rstrip("\n").rstrip() != DELIM:
        return None, None
    keys: list[tuple[str, int]] = []
    for n, raw in enumerate(lines[1:], 2):
        line = raw.rstrip("\n")
        if line.rstrip() == DELIM:
            return keys, None
        m = KEY_RE.match(line)
        if m:
            keys.append((m.group(1).rstrip(), n))
    return None, (
        f"frontmatter opens with '{DELIM}' on line 1 but is never "
        f"closed by a '{DELIM}' line — the whole file was read as "
        f"a header"
    )


def classify(keys: list[tuple[str, int]]) -> tuple[list[str], list[str], list[str]]:
    """Split ordered keys into the three buckets, preserving order."""
    portable: list[str] = []
    extensions: list[str] = []
    unknown: list[str] = []
    for key, _ in keys:
        if key in PORTABLE:
            portable.append(key)
        elif key in PLATFORM_EXTENSIONS:
            extensions.append(key)
        else:
            unknown.append(key)
    return portable, extensions, unknown


def duplicate_errors(keys: list[tuple[str, int]]) -> list[str]:
    """Return one error message per top-level key that appears more than once."""
    seen: dict[str, int] = {}
    errors: list[str] = []
    for key, n in keys:
        if key in seen:
            errors.append(
                f"line {n}: DUPLICATE top-level key {key!r} "
                f"(first seen on line {seen[key]}) — ambiguous",
            )
        else:
            seen[key] = n
    return errors


def show(label: str, values: list[str]) -> None:
    """Print a labelled, comma-separated bucket, or `(none)` when empty."""
    print(f"{label}: " + (", ".join(values) if values else "(none)"))


def main() -> int:
    """Run the frontmatter check and return the process exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    strict = "--strict-portable" in args
    args = [a for a in args if a != "--strict-portable"]
    if len(args) != 1:
        print(__doc__)
        return 2
    path = args[0]
    try:
        with Path(path).open(encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"cannot read {path}: {exc}")
        return 2
    except UnicodeDecodeError as exc:
        print(f"cannot decode {path} as UTF-8: {exc}")
        return 2

    keys, error = extract_block(lines)
    if error:
        print("STRUCTURAL ERROR — no verdict is trustworthy until fixed:")
        print("  " + error)
        return 2
    if keys is None:
        print(
            f"NO FRONTMATTER: {path} does not start with a '{DELIM}' line "
            f"— nothing to check.",
        )
        return 0

    errors = duplicate_errors(keys)
    if errors:
        print("STRUCTURAL ERRORS — no verdict is trustworthy until fixed:")
        for e in errors:
            print("  " + e)
        return 2

    portable, extensions, unknown = classify(keys)
    print(f"frontmatter of {path}: {len(keys)} top-level field(s)")
    show("portable", portable)
    show("platform-extensions", extensions)
    show("unknown", unknown)
    print(
        f"portable={len(portable)} extensions={len(extensions)} unknown={len(unknown)}",
    )

    missing = [k for k in REQUIRED if k not in portable]
    if missing:
        print(
            "note (not an error here): the spec's required field(s) "
            + ", ".join(missing)
            + " are absent — `claude plugin validate "
            "--strict` is the authority on that",
        )

    if extensions:
        print("NOT PORTABLE AS IS — platform extensions present:")
        for key in extensions:
            print(f"  {key}: {PLATFORM_EXTENSIONS[key]}")

    if unknown:
        print(
            "UNKNOWN FIELDS — neither in the portable six nor a known "
            "platform extension (typo? silently ignored by the harness):",
        )
        for key in unknown:
            print("  " + key)
        return 1
    if strict and extensions:
        print(
            f"--strict-portable: {len(extensions)} platform extension(s) "
            f"— the header does not carry over to other harnesses as is.",
        )
        return 1
    print("OK: no unknown fields." + (" Portable as is." if strict else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
