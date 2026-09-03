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
  `<PREFIX>-<n> | severity | claim`, where PREFIX is ONE OR MORE segments
  joined by dashes, each segment letter-led and continuing with letters and
  digits (`DA`, `GB`, `L1`, and the COMPOSITE `V-CIT` a verifier writes) —
  the id contract of recount.py, not a second one.
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
  `XX-3 | urgent | …` is an error rather than a guess. A DASH line
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
- The row's WIDTH IS THE TARGET LEDGER'S, never a hard-wired literal. Three
  schemas are in use — v1 (7 cells), v2 (8, with the readiness criterion)
  and v3 (9, with the zone column third) — and a row of the wrong width is
  a structural error of recount.py, so the form is CHOSEN, not assumed:
    * the ledger header's `Row schema: v1 | v2 | v3` field decides it;
    * with no such field the width is the cell count of the findings
      table's own header (7, 8 or 9);
    * with a field AND a header that disagree, nothing is written — a
      declaration contradicting the table is never resolved by guessing;
    * with neither readable, nothing is written either: emitting a row of
      a foreign width is worse than emitting none.
  In `--stdout` mode there is no ledger to ask, so the v2 form is printed
  and the caller places it.
- Filled cells are NAMED, not counted: `id`, `sev` and `claim` carry the
  literal copy, and in v3 the `zone` cell carries the stub `·`. In v1 and
  v2 those named cells are still the first three; in v3 they are not a
  contiguous prefix any more, since the zone comes between `sev` and
  `claim`. The zone is a JUDGMENT against the round contract's zone map and
  belongs to the ADJUDICATOR at stage 6 — transcription stays literal
  copying, so it leaves a visible stub rather than a guess. The verdict and
  the readiness criterion belong to adjudication too, the rest to the fix
  and verification passes. Empty cells are deliberate: they are what makes
  a freshly transcribed row non-terminal for recount.py. The v3 row is
  therefore exactly `| <id> | <sev> | · | <claim> | | | | | |`.
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

import os
import re
import sys
from pathlib import Path
from typing import TypedDict, cast

SEVERITIES = ("blocker", "major", "minor")
# The three findings-table schemas, by cell count.
V1_WIDTH = 7
V2_WIDTH = 8
V3_WIDTH = 9
ROW_WIDTHS = (V1_WIDTH, V2_WIDTH, V3_WIDTH)
# `--stdout` has no ledger to read a schema from; the caller places the row.
DEFAULT_WIDTH = V2_WIDTH
# The header field that declares the schema, and the width each name means.
ROW_SCHEMA_RE = re.compile(r"^\s*[-*]?\s*row schema:\s*(.*?)\s*$", re.IGNORECASE)
ROW_SCHEMA_WIDTHS = {"v1": V1_WIDTH, "v2": V2_WIDTH, "v3": V3_WIDTH}
# The v3 zone column and the stub transcription leaves in it.
ZONE_INDEX = 2
ZONE_PLACEHOLDER = "·"
SEP = r"|—–"  # pipe, em dash, en dash
WRAP = r"^[\s>]*(?:\#{1,6}\s*)?(?P<bold>\*\*|__)?[ \t]*"
# The id contract of recount.py (its `ID_RE`), character for character: a
# prefix of one or more letter-led segments joined by dashes, then `-<n>`.
ID = r"(?P<id>[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)*-\d+)"

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
    unambiguous, so `XX-3 | urgent | …` is a structural error and not a
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


def ledger_width(lines: list[str]) -> tuple[int | None, str | None]:
    """Return (the target ledger's row width, error-or-None).

    The header's `Row schema:` declaration is authoritative where it exists,
    the findings header's own cell count where it does not, and a
    disagreement between the two is refused rather than resolved: the one
    thing this function may not do is hand back a width that would make
    every emitted row a structural error of the recount.
    """
    declared: list[str] = []
    for raw in lines:
        m = ROW_SCHEMA_RE.match(raw.rstrip("\n"))
        if m:
            declared.append(m.group(1).strip())
    if len(declared) > 1:
        return None, (
            f"{len(declared)} `Row schema:` header fields — the schema is "
            f"declared once per ledger; refusing to pick one"
        )
    from_header: int | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if cells and cells[0].lower() == "id":
            from_header = len(cells)
            break
    if declared:
        value = declared[0].lower()
        if value not in ROW_SCHEMA_WIDTHS:
            return None, (
                f"`Row schema: {declared[0]}` is not one of "
                f"{'/'.join(ROW_SCHEMA_WIDTHS)} — refusing to guess the "
                f"row form"
            )
        width = ROW_SCHEMA_WIDTHS[value]
        if from_header is not None and from_header != width:
            return None, (
                f"`Row schema: {declared[0]}` declares {width} cells but the "
                f"findings header has {from_header} — refusing to write rows "
                f"of either width while the two disagree"
            )
        return width, None
    if from_header is None:
        return None, (
            "no findings table found (no header row whose first cell is "
            "`id`) and no `Row schema:` field — the row form is not derivable"
        )
    if from_header not in ROW_WIDTHS:
        return None, (
            f"the findings header has {from_header} cells; the row form is "
            f"one of {'/'.join(str(w) for w in ROW_WIDTHS)} — refusing to "
            f"emit a row of a width nothing reads"
        )
    return from_header, None


def row(finding: Finding, width: int = DEFAULT_WIDTH) -> str:
    """One row of `width` cells; only the NAMED cells are filled.

    `id`, `sev` and `claim` carry the literal copy; the v3 `zone` cell
    carries the stub the adjudicator replaces. Every other cell is empty on
    purpose — an empty cell is what keeps a fresh row non-terminal.
    """
    cells = [finding["id"], finding["sev"]]
    if width == V3_WIDTH:
        cells.insert(ZONE_INDEX, ZONE_PLACEHOLDER)
    cells.append(finding["claim"])
    cells += [""] * (width - len(cells))
    return "| " + " | ".join(cells) + " |"


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


def write_atomic(path: str, lines: list[str]) -> str | None:
    """Write `lines` to `path` through a temporary file and an atomic replace.

    The temporary path is PREDICTABLE, so the temporary file is created
    EXCLUSIVELY (`O_EXCL`): anything already sitting there — a leftover
    file, or a symlink pointing somewhere else entirely — makes the write
    REFUSE instead of writing through it, and that file is left exactly
    where it is, since it is not this script's to delete. Returns the
    error to report, or None when the replace happened.
    """
    tmp = path + ".transcribe.tmp"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except OSError as exc:
        return (
            f"cannot create the temporary file {tmp}: {exc} — something is "
            f"already there and is NOT overwritten (it is left as it is); "
            f"remove it once you know what it is, then run this again"
        )
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    Path(tmp).replace(path)
    return None


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
    # `--stdout` has no ledger to read a schema from, so the v2 form is
    # printed and the caller places it; `--ledger` takes the width from the
    # target file and refuses to write at all when it is not derivable.
    width = DEFAULT_WIDTH
    if ledger is not None:
        try:
            with Path(ledger).open(encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            print(f"cannot read {ledger}: {exc}")
            return 2
        derived, width_err = ledger_width(lines)
        if width_err is not None:
            errors.append(f"{ledger}: {width_err}")
        else:
            width = cast("int", derived)
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

    rows = [row(f, width) for f in findings]
    if to_stdout:
        print("\n".join(rows))
    else:
        head = lines[:insert_at]
        if head and not head[-1].endswith("\n"):
            head[-1] += "\n"  # separator was the last line, no newline
        write_error = write_atomic(
            cast("str", ledger),
            head + [r + "\n" for r in rows] + lines[insert_at:],
        )
        if write_error is not None:
            print("STRUCTURAL ERRORS — nothing was written:")
            print("  " + write_error)
            return 2

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
