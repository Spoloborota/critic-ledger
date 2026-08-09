#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Reference report-acceptance script for a critic-ledger round (run on
a report AFTER its verbatim salvage, as the deterministic half of report
acceptance).

Acceptance of a critic report is a HYBRID, and this script is only its
deterministic half. It checks the two mechanically COMPLETE traits — the
id prefixes of the findings and the severity literals — and reports
everything else as a MARK for a human reader. It NEVER rejects a report:
the verdict "re-run this lens" belongs to the orchestrator, because a
single false positive here would burn a whole critic run.

What is a PROBLEM (a line in the problems list, exit 1)
-------------------------------------------------------
- Finding id: every finding heading must carry `<PREFIX>-<n>` with the
  PREFIX handed out by the orchestrator for this lens. A foreign prefix
  (another lens's, or the verifier's) or a malformed id (`GA1`, `GA-1a`,
  `GA-`) is a problem: the ledger's recount contract depends on ids
  (`recount.py:85`), and prefixes are unique per lens by design.
- Severity: the second cell must be one of the literals `blocker`,
  `major`, `minor`. Anything else — a Russian analogue, a seven-level
  scale word, an empty cell — is a problem. (Case is tolerated: `Major`
  passes. The rule constrains the word, and case alone has never been the
  defect; the normalized literal is echoed in the mark.)
- Duplicate finding ids: two findings numbered the same cannot both be
  tracked in the ledger.
- Zero findings: an empty report is a problem — a critic that found
  nothing must still say so in a coverage statement, and a report the
  script cannot see any finding in is not a report.

What is a MARK only (never a problem, never affects the exit code)
------------------------------------------------------------------
- `suspicious: no file:line evidence` — the finding's block (from its
  heading to the next heading or the end) carries neither a `path:line`
  reference nor an explicit command. This is deliberately SOFT: the
  second branch of the evidence rule — an exact quote — is mechanically
  indistinguishable from prose. On the design-r1 reports a literal
  evidence check false-positived on GC-2, whose evidence is a verbatim
  quote of the platform documentation. Counted separately in the summary.
- Missing header fields (object / lens / method) and a missing coverage
  statement. Real salvaged reports vary in header shape (see
  `critic-rounds/design-r1/r1-critic-gd.md`, which has no commands
  section at all), so a header check strict enough to be a gate would
  mostly produce noise.
- The remaining acceptance trait — "no proposed solutions" — is not
  checked at all: it is wholly the orchestrator's judgment.

Finding detection
-----------------
A finding heading is a line whose first pipe-separated cell looks like an
id (letters, then optional separator, then digits) or whose second cell
is a severity-ish word. Leading `>`, `-`, `*`, `#`, backticks and a
leading table pipe are stripped first, so blockquoted, bulleted, bolded
and table-shaped findings are all seen. Detection is deliberately WIDER
than the strict id rule: a malformed or foreign id must be FOUND in order
to be reported, not silently skipped.

Fenced code blocks (``` or ~~~) are SKIPPED whole during detection. A
report that QUOTES a fixture row or another lens's finding as evidence is
showing it, not raising it; counting such rows inflated both the finding
count and the foreign-prefix problem list. Evidence detection still reads
inside fences — only the "is this a finding heading" scan stops at them.
The one exception is a fence WRAPPING THE WHOLE REPORT: some agents
deliver their output fenced and the verbatim salvage keeps the markers, so
that outer pair is unwrapped rather than skipped (see
`unwrap_salvage_fence`) — otherwise a valid report reads as empty.

Usage:  validate-report.py <report.md> <EXPECTED_PREFIX>
Exit codes: 0 = zero problems (marks may still be present); 1 = problems
found — the orchestrator decides what they mean; 2 = the report cannot be
parsed at all (unreadable file, bad arguments).

Provenance note: design/NN-*.md paths, round names (design-r1,
skill-md-r1, ...), round-report paths (critic-rounds/<round>/...) and
finding ids (GD-#, GC-#, ...) cited here point at the author's private
development notes; they are provenance markers, not files shipped with
this plugin.
"""  # noqa: D205  # printed usage text; reflowing it would change output

import re
import sys
from pathlib import Path
from typing import TypedDict

# Strict id contract, identical to the ledger recount (`recount.py:85`).
ID_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)-(\d+)$")
# Loose id: letters, an optional separator, digits, optional junk tail.
IDISH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*[\s\-‐-―_.]*\d+[A-Za-z0-9]*$")  # noqa: RUF001  # deliberate U+2010..U+2015 dash range
PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")

# A finding heading needs at least an id cell and a severity cell.
MIN_FINDING_CELLS = 2
# Longest first cell still considered an id rather than prose.
MAX_ID_CELL_LEN = 40
# A fence needs an opening and a closing marker before it can wrap anything.
MIN_FENCE_MARKERS = 2
# How many finding headings an outer fence must hold to count as a wrapper.
MIN_WRAPPED_FINDINGS = 2
# The script takes exactly a report path and an expected prefix.
EXPECTED_ARG_COUNT = 2


class Finding(TypedDict, total=False):
    """One finding heading found in a report, plus the extent of its block."""

    line: int
    cells: list[str]
    id: str
    severity: str
    end: int


ACCEPTED_SEVERITY = ("blocker", "major", "minor")
# Detection-only vocabulary: words that make a line LOOK like a finding
# heading even when its id is broken. Never used to accept a severity.
SEVERITY_ISH = {
    "blocker",
    "major",
    "minor",
    "blocking",
    "critical",
    "crit",
    "high",
    "medium",
    "moderate",
    "low",
    "trivial",
    "cosmetic",
    "nit",
    "блокер",
    "блокирующая",
    "блокирующий",
    "критично",
    "критичная",
    "критичный",
    "критическая",
    "критический",
    "важно",
    "важная",
    "важный",
    "серьезно",
    "серьезная",
    "значимая",
    "средняя",
    "мажор",
    "минор",
    "мелочь",
    "мелкая",
    "незначительно",
    "незначительная",
    "низкая",
    "высокая",
}

# Evidence: `path.ext:123`, `dir/name:123`, or a capitalized extensionless
# filename (`Makefile:12`, `LICENSE:3`, `Dockerfile:7`). A `//` inside the
# match is rejected so that a URL with a port is not read as a file
# reference; the third alternative, which can contain neither `/` nor `.`,
# is guarded instead by a lookbehind, so `https://Example:8080` and the
# tail of a longer path cannot enter through it.
FILELINE_RE = re.compile(
    r"[A-Za-z0-9_.@+\\/-]*[A-Za-z0-9_)-]\.[A-Za-z][A-Za-z0-9]{0,9}:\d+"
    r"|[A-Za-z0-9_.@+\\/-]*/[A-Za-z0-9_.@+-]+:\d+"
    r"|(?<![A-Za-z0-9_./@+\\-])[A-Z][A-Za-z0-9_-]{2,}:\d+",
)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
CMD_WORDS = {
    "grep",
    "rg",
    "egrep",
    "fgrep",
    "cat",
    "sed",
    "awk",
    "nl",
    "head",
    "tail",
    "wc",
    "ls",
    "find",
    "git",
    "python",
    "python3",
    "sh",
    "bash",
    "zsh",
    "jq",
    "diff",
    "curl",
    "node",
    "npm",
    "make",
    "pytest",
    "xargs",
    "sort",
    "uniq",
    "comm",
    "stat",
    "du",
    "shasum",
    "md5",
    "printf",
    "test",
    "tree",
    "claude",
    "cp",
    "readlink",
    "realpath",
}

HEADER_FIELDS = (
    ("object", ("объект", "object")),
    ("lens", ("линза", "линзой", "lens")),
    ("method", ("метод", "method")),
)
COVERAGE_MARKERS = (
    "покрыти",
    "coverage",
    "не осматрив",
    "не проверял",
    "не проверено",
    "не читал",
    "вне таймбокса",
    "did not examine",
    "not examined",
    "skipped",
)


def clean_cell(text: str) -> str:
    """Strip markdown decoration a cell may be wrapped in."""
    return text.strip().strip("*_`~ ").strip()


def normalize(text: str) -> str:
    """Lower-case a cell and trim the punctuation comparisons ignore."""
    return clean_cell(text).lower().replace("ё", "е").strip(" .,:;!?")  # noqa: RUF001  # deliberate Cyrillic yo -> ye folding


def split_cells(line: str) -> list[str] | None:
    """Pipe-split a line, dropping markdown-table edge pipes."""
    stripped = line.strip().lstrip(">#-*_ ").strip()
    if "|" not in stripped:
        return None
    cells = [c.strip() for c in stripped.split("|")]
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells or None


def is_finding_line(cells: list[str] | None) -> bool:
    """True when the cells look like a finding heading of this report."""
    if not cells or len(cells) < MIN_FINDING_CELLS:
        return False
    first = clean_cell(cells[0])
    if not first or len(first) > MAX_ID_CELL_LEN:
        return normalize(cells[1]) in SEVERITY_ISH and len(first) <= MAX_ID_CELL_LEN
    if IDISH_RE.match(first):
        return True
    return normalize(cells[1]) in SEVERITY_ISH


def unwrap_salvage_fence(lines: list[str]) -> list[str]:
    """Neutralize an OUTER fence that wraps a whole critic report.

    Some agents deliver their report inside one code fence and the salvage
    keeps the markers verbatim (`critic-rounds/skill-md-r1/r1-critic-da.md`
    line 5). Skipping that wrapper as if it were a quote would hide every
    finding and turn a valid report into "no findings found". The candidate
    is the FIRST fenced block — the first two markers, paired by the same
    toggling the scanner uses, NOT the outermost markers of the file
    (pairing marker[0] with marker[-1] swallows a report that merely has
    several evidence blocks, as `critic-rounds/skill-md-r1/r1-critic-db.md`
    does). It is a wrapper only when its interior holds MORE THAN ONE
    finding heading and nothing outside it holds any — an evidence quote
    never looks like that. Markers are blanked in place so line numbers
    stay exact; fences INSIDE the wrapper keep toggling.
    """
    marks = [i for i, ln in enumerate(lines) if FENCE_RE.match(ln)]
    if len(marks) < MIN_FENCE_MARKERS:
        return lines
    first, close = marks[0], marks[1]
    if any(
        is_finding_line(split_cells(ln)) for ln in lines[:first] + lines[close + 1 :]
    ):
        return lines
    if (
        sum(1 for ln in lines[first + 1 : close] if is_finding_line(split_cells(ln)))
        < MIN_WRAPPED_FINDINGS
    ):
        return lines
    out = list(lines)
    out[first] = out[close] = "\n"
    return out


def find_findings(lines: list[str]) -> list[Finding]:
    """Return the list of finding headings, each with its block extent.

    The heading scan runs over the wrapper-unwrapped copy; the caller keeps
    the ORIGINAL lines for evidence blocks and header/coverage checks.
    """
    found: list[Finding] = []
    in_fence = False
    for n, raw in enumerate(unwrap_salvage_fence(lines), 1):
        if FENCE_RE.match(raw):  # ``` / ~~~ toggles a code block
            in_fence = not in_fence
            continue
        if in_fence:  # quoted fixture rows are evidence,
            continue  # not findings of THIS report
        cells = split_cells(raw)
        if cells is not None and is_finding_line(cells):
            found.append(
                {
                    "line": n,
                    "cells": cells,
                    "id": clean_cell(cells[0]),
                    "severity": clean_cell(cells[1]),
                },
            )
    # Block of a finding: heading .. next finding heading or next markdown
    # heading (a coverage statement must not lend evidence to the last
    # finding), whichever comes first.
    starts = [f["line"] for f in found] + [len(lines) + 1]
    for i, f in enumerate(found):
        end = starts[i + 1]
        for n in range(f["line"] + 1, end):
            if re.match(r"^#{1,6}\s", lines[n - 1]):
                end = n
                break
        f["end"] = end
    return found


def has_evidence(block: list[str]) -> bool:
    """file:line reference, or an explicit command, anywhere in the block."""
    for raw in block:
        for m in FILELINE_RE.finditer(raw):
            if "//" not in m.group(0):
                return True
        if re.match(r"^\s*[$%>]\s*\S", raw) and not raw.lstrip().startswith(
            (">>", "> "),
        ):
            return True
        for code in INLINE_CODE_RE.findall(raw):
            head = code.strip().split()
            if head and head[0].strip("$%").split("/")[-1] in CMD_WORDS:
                return True
            if head and head[0].startswith(("./", "../")):
                return True
    in_fence = False
    for raw in block:
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            head = raw.strip().split()
            if head and (
                head[0].strip("$%") in CMD_WORDS
                or head[0].startswith(("./", "$", "../"))
            ):
                return True
    return False


def check_findings(found: list[Finding], prefix: str) -> tuple[list[str], list[str]]:
    """Return (problems, suspicious) — the two separate mark channels."""
    problems: list[str] = []
    suspicious: list[str] = []
    seen: dict[str, int] = {}
    for f in found:
        loc = f"line {f['line']}"
        m = ID_RE.match(f["id"])
        if not m:
            problems.append(
                f"{loc}: id {f['id']!r} is not a well-formed "
                f"finding id <PREFIX>-<n> (expected prefix "
                f"{prefix!r})",
            )
        elif m.group(1) != prefix:
            hint = (
                " (letter case differs)" if m.group(1).lower() == prefix.lower() else ""
            )
            problems.append(
                f"{loc}: id {f['id']!r} carries a foreign prefix "
                f"{m.group(1)!r}; this lens was assigned "
                f"{prefix!r}{hint}",
            )
        sev = normalize(f["severity"])
        if sev not in ACCEPTED_SEVERITY:
            problems.append(
                f"{loc}: {f['id']}: severity {f['severity']!r} "
                f"is not one of the literals "
                f"{', '.join(ACCEPTED_SEVERITY)}",
            )
        key = f["id"].lower()
        if key in seen:
            problems.append(
                f"{loc}: {f['id']}: duplicate finding id — "
                f"already used at line {seen[key]}",
            )
        else:
            seen[key] = f["line"]
    return problems, suspicious


def main() -> int:
    """Validate the report named on the command line and return the exit code."""
    args = [a for a in sys.argv[1:] if a not in ("-h", "--help")]
    if len(sys.argv[1:]) != len(args) or len(args) != EXPECTED_ARG_COUNT:
        print(__doc__)
        return 2
    path, prefix = args
    if not PREFIX_RE.match(prefix):
        print(
            f"bad expected prefix {prefix!r}: it must start with a letter "
            f"and contain only letters and digits",
        )
        return 2
    try:
        with Path(path).open(encoding="utf-8") as fh:
            lines = fh.readlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"cannot read report {path!r}: {exc}")
        return 2

    found = find_findings(lines)
    problems, suspicious = check_findings(found, prefix)

    if not found:
        problems.append(
            "no findings found in the report — an empty report "
            "is not a report (a critic that found nothing still "
            "owes a coverage statement)",
        )

    for f in found:
        if not has_evidence(lines[f["line"] - 1 : f["end"] - 1]):
            suspicious.append(
                f"line {f['line']}: {f['id']}: suspicious: no file:line "
                f"evidence (nor an explicit command) in its block — the "
                f"evidence may still be an exact quote; a human decides",
            )

    notes: list[str] = []
    head_end = found[0]["line"] - 1 if found else len(lines)
    header = "\n".join(lines[:head_end]).lower()
    for name, markers in HEADER_FIELDS:
        if not any(mk in header for mk in markers):
            notes.append(
                f"note: header field {name!r} not recognized above "
                f"the first finding — header shape varies between "
                f"real reports; not a failure",
            )
    body = "\n".join(lines).lower()
    if not any(mk in body for mk in COVERAGE_MARKERS):
        notes.append(
            "note: no coverage statement recognized (what was "
            "examined vs skipped) — not a failure",
        )

    print(f"report: {path}")
    print(f"expected id prefix: {prefix}")
    print(
        "this script never rejects a report: the verdict "
        "'re-run this lens' is the orchestrator's.",
    )
    print()
    print(f"findings ({len(found)}):")
    for f in found:
        print(f"  line {f['line']}: {f['id']} | {f['severity']}")
    if not found:
        print("  (none)")
    print()
    print(f"problems ({len(problems)}):")
    for p in problems:
        print("  " + p)
    if not problems:
        print("  (none)")
    print()
    print(f"marks ({len(suspicious) + len(notes)}):")
    for s in suspicious:
        print("  " + s)
    for note in notes:
        print("  " + note)
    if not suspicious and not notes:
        print("  (none)")
    print()
    print(
        f"summary: findings={len(found)} problems={len(problems)} "
        f"suspicious={len(suspicious)} notes={len(notes)}",
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
