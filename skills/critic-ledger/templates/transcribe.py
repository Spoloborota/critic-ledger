#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Mechanical transcription of critic findings into a ledger skeleton
(stage 5, between the verbatim salvage and adjudication). One finding =
one ledger row; the id, severity and claim cells are produced by LITERAL
COPY of the finding's header line in the salvage file — this is copying,
not paraphrase, so the information loss is zero and no agent is spent on
it. Measured against a representative sample of real critic reports: 56
findings recognized out of 56, exact match with the ledger id set, zero
losses and zero extras.

Contract of a finding header line
---------------------------------
- The accepted shape is the one mandated by templates/critic-prompt.md:
  `<PREFIX>-<n> | severity | claim`, where PREFIX starts with a letter and
  may contain letters and digits (`DA`, `GB`, `L1`).
- Wrappers seen in real salvages are tolerated and stripped: leading
  spaces, blockquote markers, a markdown heading marker (`##`), and bold
  around the whole line (`**GB-1 | major | ...**`).
- The separator may be `|` (canonical) or an em/en dash (`—`, `–`, used by
  pre-template rounds); BOTH separators of one line must be the SAME
  character — a mixed line is a structural error, not a guess.
- severity is a literal from {blocker, major, minor}, matched
  case-insensitively and COPIED AS WRITTEN (`BLOCKER` stays `BLOCKER`).
- claim is the rest of the line, copied byte for byte; a literal pipe
  inside it is escaped as `\\|` (the cell contract of recount.py), and a
  bold closer is dropped only when the line opened with one.
- Fenced code blocks (``` or ~~~) are SKIPPED whole: a report quoting a
  fixture row or a transcript of another lens's finding as EVIDENCE is
  showing it, not raising it. Only prose-level lines are scanned. The one
  exception is a fence WRAPPING THE WHOLE REPORT — some agents deliver
  their output fenced and the salvage keeps the markers verbatim; that
  outer pair is unwrapped, not skipped (see unwrap_salvage_fence).
- FAIL-CLOSED parsing (never silent, same rule as recount.py): any line
  that LOOKS like a finding header — an id-shaped token followed by a
  separator, at the start of the line under the tolerated wrappers — but
  does not parse (unknown severity, mixed separators, empty claim) is a
  STRUCTURAL ERROR naming file:line and the text. Nothing is written.
- What "LOOKS like" means differs per separator, because the two carry
  different evidence. A PIPE line is always held to the contract, so
  `XX-3 | критично | …` is an error rather than a guess. A DASH line
  counts only when its SECOND field is a severity literal: `GB-1 —
  discussed above, high confidence.` is a coverage statement
  cross-referencing an id — the very convention adjudication uses — and
  is passed over as prose, not reported. A dash line whose second field
  IS a severity but whose next separator is a pipe stays a mixed-separator
  error.
- A duplicate id — inside one report, across reports, or already present
  in the target ledger — is a STRUCTURAL ERROR too.

Contract of the emitted row
---------------------------
- Eight cells:
  `| id | sev | claim | verdict | criterion | fix | verified | terminal |`.
  Transcription fills the FIRST THREE only; the verdict and the readiness
  criterion belong to adjudication (the main session), the rest to the fix
  and verification passes. Empty cells are deliberate: they are what makes
  a freshly transcribed row non-terminal for recount.py.
- Rows are appended directly after the separator row of the FIRST findings
  table of the ledger (the table whose header's first cell is `id`), in
  the order the reports were given on the command line and, inside a
  report, in file order. Existing rows keep their place.
- The write is all-or-nothing: every report is parsed and every check
  passes BEFORE the ledger is touched, and the new text is written through
  a temporary file plus an atomic replace. A partially transcribed ledger
  must be impossible.

After transcription the recognized id set is printed with a per-file
count, so that coverage claims of the reports can be checked against what
was actually laid out.

Usage:  transcribe.py <report.md> [<report.md> ...] --ledger <ledger.md>
        transcribe.py <report.md> [...] --stdout      (print rows, no write)
        transcribe.py -h | --help                     (this text, exit 0)
In `--stdout` mode stdout carries ONLY the rows (so the output can be piped
or appended) and the run summary goes to stderr; in `--ledger` mode the
summary goes to stdout.
Exit codes: 0 = rows transcribed (or printed), or `-h`/`--help`;
2 = structural error or usage error — nothing was written.
"""  # noqa: D205, D301  # printed usage text; reflow/r-string would change output

import re
import sys
from pathlib import Path
from typing import TypedDict, cast

SEVERITIES = ("blocker", "major", "minor")
SEP = r"|—–"  # pipe, em dash, en dash
WRAP = r"^[\s>]*(?:\#{1,6}\s*)?(?P<bold>\*\*|__)?[ \t]*"
ID = r"(?P<id>[A-Za-z][A-Za-z0-9]*-\d+)"

# A line that merely LOOKS like a finding header: the id shape followed by
# a separator. Everything is_candidate() accepts must parse or the run fails.
CAND_RE = re.compile(
    WRAP + ID + r"[ \t]*(?P<sep>[" + SEP + r"])"
    r"(?P<rest>.*)$",
)
FULL_RE = re.compile(
    WRAP + ID + r"[ \t]*(?P<sep>[" + SEP + r"])[ \t]*"
    r"(?P<sev>" + "|".join(SEVERITIES) + r")[ \t]*(?P=sep)[ \t]*"
    r"(?P<claim>\S.*?)[ \t]*$",
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
NEXT_SEP_RE = re.compile(r"[" + SEP + r"]")

ESC = "\x00PIPE\x00"

# A fence needs an opening and a closing marker before it can wrap anything.
MIN_FENCE_MARKERS = 2
# How many finding headers an outer fence must hold to count as a wrapper.
MIN_WRAPPED_FINDINGS = 2
# A markdown row must have at least the two delimiting pipes.
MIN_ROW_CELLS = 2


class Finding(TypedDict):
    """One finding recognized in a salvage file, with its provenance."""

    id: str
    sev: str
    claim: str
    file: str
    line: int


def is_candidate(line: str) -> bool:
    """True when `line` must parse as a finding header or fail the run.

    A PIPE-separated id line is always a candidate: the canonical shape is
    unambiguous, so `XX-3 | критично | …` is a structural error and not a
    guess. A DASH-separated one is a candidate ONLY when its second field
    is a severity literal — `GB-1 — discussed above` is ordinary prose
    cross-referencing an id (a shape the adjudication stage endorses), and
    demoting it is what keeps prose from aborting a whole transcription.
    """
    m = CAND_RE.match(line)
    if not m:
        return False
    if m.group("sep") == "|":
        return True
    nxt = NEXT_SEP_RE.search(m.group("rest"))  # any separator, so that a
    if not nxt:  # MIXED line stays an error
        return False
    return m.group("rest")[: nxt.start()].strip().lower() in SEVERITIES


def unwrap_salvage_fence(lines: list[str]) -> list[str]:
    """Neutralize an OUTER fence that wraps a whole critic report.

    Some agents deliver their report inside one code fence, and the salvage
    rule forbids editing the text, so the markers survive into the salvage.
    That wrapper is not an evidence quote, and skipping it would hide every
    finding in the file.
    The candidate is the FIRST fenced block — the first two markers, paired
    by the same toggling the scanner uses, NOT the outermost markers of the
    file (pairing marker[0] with marker[-1] swallows a report whose
    evidence blocks merely happen to be several). It is a wrapper only when
    its interior holds MORE THAN ONE well-formed finding header and nothing
    outside it holds any — an evidence quote never looks like that. The two
    markers are blanked in place (line numbers stay exact) and fences
    INSIDE the wrapper keep toggling normally.
    """
    marks = [i for i, ln in enumerate(lines) if FENCE_RE.match(ln)]
    if len(marks) < MIN_FENCE_MARKERS:
        return lines
    first, close = marks[0], marks[1]
    outside = lines[:first] + lines[close + 1 :]
    if any(FULL_RE.match(ln.rstrip("\n")) for ln in outside):
        return lines
    inner = sum(1 for ln in lines[first + 1 : close] if FULL_RE.match(ln.rstrip("\n")))
    if inner < MIN_WRAPPED_FINDINGS:
        return lines
    out = list(lines)
    out[first] = out[close] = "\n"
    return out


def split_row(line: str) -> list[str] | None:
    """Cells of a markdown table row, or None. Mirrors recount.py."""
    cells = [
        c.strip().replace(ESC, "|") for c in line.replace("\\|", ESC).strip().split("|")
    ]
    if len(cells) < MIN_ROW_CELLS or cells[0] != "" or cells[-1] != "":
        return None
    return cells[1:-1]


def parse_report(path: str) -> tuple[list[Finding], list[str]]:
    """Return (findings, errors). A finding is a dict with the three cells
    copied literally from the salvage, plus its provenance.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    findings: list[Finding] = []
    errors: list[str] = []
    with Path(path).open(encoding="utf-8") as fh:
        lines = unwrap_salvage_fence(fh.readlines())
    in_fence = False
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if FENCE_RE.match(line):  # ``` / ~~~ toggles a code block
            in_fence = not in_fence
            continue
        if in_fence:  # quoted rows are not findings
            continue
        if not is_candidate(line):
            continue
        m = FULL_RE.match(line)
        if not m:
            errors.append(
                f"{path}:{n}: looks like a finding header but does "
                f"not parse (severity not one of "
                f"{'/'.join(SEVERITIES)}, mixed separators, or "
                f"empty claim): {line.strip()[:120]}",
            )
            continue
        claim = m.group("claim")
        if m.group("bold"):  # drop the matching closer
            claim = re.sub(r"(\*\*|__)$", "", claim).rstrip()
        if not claim:
            errors.append(
                f"{path}:{n}: finding header with an empty claim: {line.strip()[:120]}",
            )
            continue
        finding: Finding = {
            "id": m.group("id"),
            "sev": m.group("sev"),
            "claim": claim.replace("|", "\\|"),
            "file": path,
            "line": n,
        }
        findings.append(finding)
    return findings, errors


def row(finding: Finding) -> str:
    """Eight cells; only id, severity and claim are filled."""
    return f"| {finding['id']} | {finding['sev']} | {finding['claim']} |  |  |  |  |  |"


def find_table(lines: list[str]) -> tuple[int | None, list[str] | None, str | None]:
    """Return (insert_index, existing_ids, error). insert_index is the line
    index right after the separator of the first findings table.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if not cells or cells[0].lower() != "id":
            continue
        if i + 1 >= len(lines) or not re.fullmatch(
            r"\|[-| :]+\|",
            lines[i + 1].strip(),
        ):
            return (
                None,
                None,
                (
                    f"line {i + 2}: the findings header at line "
                    f"{i + 1} is not followed by a separator row "
                    f"— refusing to guess where rows go"
                ),
            )
        existing: list[str] = []
        for raw2 in lines[i + 2 :]:
            s = raw2.strip()
            if s.startswith("#"):
                break
            if not s.startswith("|") or re.fullmatch(r"\|[-| :]+\|", s):
                continue
            cells2 = split_row(s)
            if cells2:
                existing.append(cells2[0])
        return i + 2, existing, None
    return (
        None,
        None,
        (
            "no findings table found (no header row whose first "
            "cell is `id`) — wrong file or broken table?"
        ),
    )


def write_atomic(path: str, lines: list[str]) -> None:
    """Write `lines` to `path` through a temporary file and an atomic replace."""
    tmp = path + ".transcribe.tmp"
    with Path(tmp).open("w", encoding="utf-8") as fh:
        fh.writelines(lines)
    Path(tmp).replace(path)


def main() -> int:
    """Transcribe the reports named on the command line and return the exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    to_stdout = "--stdout" in args
    args = [a for a in args if a != "--stdout"]
    ledger = None
    if "--ledger" in args:
        i = args.index("--ledger")
        if i + 1 >= len(args):
            print("--ledger needs a path")
            return 2
        ledger = args[i + 1]
        del args[i : i + 2]
    if not args or (ledger is None) == (not to_stdout):
        print(__doc__)
        return 2

    findings: list[Finding] = []
    errors: list[str] = []
    per_file: list[tuple[str, list[str]]] = []
    for path in args:
        try:
            got, errs = parse_report(path)
        except OSError as exc:
            print(f"cannot read {path}: {exc}")
            return 2
        findings.extend(got)
        errors.extend(errs)
        per_file.append((path, [f["id"] for f in got]))

    seen: dict[str, str] = {}
    for f in findings:
        if f["id"] in seen:
            errors.append(
                f"{f['file']}:{f['line']}: DUPLICATE FINDING ID "
                f"{f['id']} (first seen at {seen[f['id']]})",
            )
        else:
            seen[f["id"]] = f"{f['file']}:{f['line']}"

    lines: list[str] = []
    insert_at: int | None = None
    if ledger is not None:
        try:
            with Path(ledger).open(encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            print(f"cannot read {ledger}: {exc}")
            return 2
        insert_at, existing, err = find_table(lines)
        if err:
            errors.append(f"{ledger}: {err}")
        else:
            existing_ids = cast("list[str]", existing)
            errors.extend(
                f"{f['file']}:{f['line']}: id {f['id']} is "
                f"ALREADY a row of {ledger} — refusing to "
                f"transcribe it twice"
                for f in findings
                if f["id"] in existing_ids
            )

    if errors:
        print("STRUCTURAL ERRORS — nothing was written:")
        for e in errors:
            print("  " + e)
        return 2
    if not findings:
        print("no findings recognized in: " + ", ".join(args))
        return 2

    rows = [row(f) for f in findings]
    if to_stdout:
        print("\n".join(rows))
    else:
        head = lines[:insert_at]
        if head and not head[-1].endswith("\n"):
            head[-1] += "\n"  # separator was the last line, no newline
        write_atomic(
            cast("str", ledger),
            head + [r + "\n" for r in rows] + lines[insert_at:],
        )

    out = sys.stderr if to_stdout else sys.stdout
    print(
        f"transcribed {len(findings)} findings"
        + ("" if to_stdout else f" into {ledger} after line {insert_at}"),
        file=out,
    )
    for path, ids in per_file:
        print(f"  {path}: {len(ids)} — {', '.join(ids) or '(none)'}", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
