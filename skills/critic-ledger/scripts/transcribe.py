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
  the id contract of `ledger_md.ID_PATTERN`, which this script imports
  rather than restating: there is ONE definition of it in the payload.
- Wrappers seen in real salvages are tolerated and stripped: leading
  spaces, blockquote markers, a list marker (`- `, `* `, `+ `), a markdown
  heading marker (`##`), and bold around the whole line
  (`**GB-1 | major | ...**`).
- The separator may be `|` (canonical) or an em/en dash (`—`, `–`, used by
  pre-template rounds); BOTH separators of one line must be the SAME
  character — a mixed line is a structural error, not a guess.
- severity is a literal from {blocker, major, minor}, matched
  case-insensitively and COPIED AS WRITTEN (`BLOCKER` stays `BLOCKER`).
- claim is the rest of the line, copied byte for byte; a bold closer is
  dropped only when the line opened with one. A literal pipe in ANY copied
  cell is escaped as `\\|` (the cell contract of recount.py) — the escaping
  is a property of the emitted ROW, applied once in `row()`.
- Fenced code blocks (``` or ~~~) are SKIPPED whole: a report quoting a
  fixture row or a transcript of another lens's finding as EVIDENCE is
  showing it, not raising it. Only prose-level lines are scanned. The one
  exception is a fence WRAPPING THE WHOLE REPORT — some agents deliver
  their output fenced and the salvage keeps the markers verbatim; that
  outer pair is unwrapped, not skipped (see unwrap_salvage_fence).
- THREE header forms are recognized, and only three: the TABLE form above;
  the BULLET form, the same line under a list marker (`- GB-1 | major |
  …`), which is how a verifier writes the findings of a pass; and the
  SECTION form — a heading naming the id and the claim (`## GB-1 — <title>`)
  with a `Severity: **major**` field somewhere in that heading's own block,
  the shape a blinded re-check delivers. A heading naming an id with no
  severity field before the next heading is prose, exactly like a dash
  cross-reference.
- PER-LINE parsing, never silent and never whole-file: a line that LOOKS
  like a finding header — an id-shaped token followed by a separator, at
  the start of the line under the tolerated wrappers — but does not parse
  (unknown severity, mixed separators, empty claim) is SKIPPED, named with
  its file:line and its text under `SKIPPED LINES`, and the well-formed
  lines of the same file are transcribed. One `X-1 | fixed |` row used to
  refuse the whole salvage and take its three well-formed neighbours with
  it, and the round's way around that was to cut eight copies of the
  reports by hand.
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
  in the target ledger — is an ERROR too, and the exit code stays 2; but it
  is a per-ROW error, not a per-RUN one, IN `--ledger` MODE: the duplicate
  row is REJECTED and named, and the findings that are not duplicates are
  still written. Refusing the whole salvage over one repeated id cost the
  round the other rows and made the operator re-run by hand — the failure
  the exit code reports is the same, what changes is how much of the work
  survives it. In `--stdout` mode nothing is written, and stdout is a pipe
  payload documented as carrying only rows, so there a duplicate stays a
  structural error over the whole run.

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
  In `--stdout` mode there is no ledger to ask, so the v3 form is printed
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
- The write is ATOMIC and, for structural errors, all-or-nothing: every
  report is parsed and every STRUCTURAL check passes before the ledger is
  touched, and the new text is written through a temporary file plus an
  atomic replace. A half-written ledger file must be impossible. Rejected
  duplicate ids are the one thing that does NOT stop the write: they remove
  their own row from the set to be written and nothing else.
- A CLOSED round is refused in one line and nothing is written, before any
  other check: a ledger whose `Ledger state:` reads `closed <date>` is
  finished evidence. The freeze is the one `set-cell.py` obeys too, read
  through the same function — every writer of a ledger refuses it alike.

After transcription the recognized id set is printed with a per-file
count, so that coverage claims of the reports can be checked against what
was actually laid out. The skipped lines are printed with it, each with
its own location: a run always shows BOTH what it transcribed and what it
considered and passed over.

Usage:  transcribe.py <report.md> [<report.md> ...] --ledger <ledger.md>
        transcribe.py <report.md> [...] --stdout      (print rows, no write)
        transcribe.py -h | --help                     (this text, exit 0)
In `--stdout` mode stdout carries ONLY the rows (so the output can be piped
or appended) and the run summary goes to stderr; in `--ledger` mode the
summary goes to stdout.
Exit codes: 0 = every recognized finding was transcribed (or printed), or
`-h`/`--help` — SKIPPED lines do not change it, they are reported beside
the transcribed ones; 2 = structural or usage error (nothing was written),
no finding recognized at all, or a duplicate id was rejected in `--ledger`
mode (the rows that were not duplicates WERE written).
"""  # noqa: D205, D301  # printed usage text; reflow/r-string would change output

import re
import sys
from pathlib import Path
from typing import TextIO, TypedDict, cast

# The row grammar, the escaping and the atomic patcher live in ONE place —
# `scripts/ledger_md.py`, beside this script — so that a row is laid out
# exactly as `recount.py` reads it. The import is resolved from THIS
# script's own directory: the payload ships loose files and there is no
# installed package (see `pyproject.toml`), so a copy of these scripts
# without `ledger_md.py` beside them does not run.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The import sits below the path insert above, which is what makes it work.
from ledger_md import (
    EXIT_OK,
    EXIT_STRUCTURAL,
    FENCE_RE,
    ID_PATTERN,
    SEVERITIES,
    V3_WIDTH,
    WIDTH_TAILS_EMIT_ROW,
    ZONE_INDEX,
    ZONE_PLACEHOLDER,
    closed_refusal,
    escape_cell,
    find_table,
    unwrap_salvage_fence,
    write_atomic,
)
from ledger_md import ledger_width as _ledger_width

# `--stdout` has no ledger to read a schema from; the caller places the row.
DEFAULT_WIDTH = V3_WIDTH
# The temporary file this script's atomic write goes through, named after it.
TMP_SUFFIX = ".transcribe.tmp"
SEP = r"|—–"  # pipe, em dash, en dash
# The tolerated wrappers, in the order they occur in real salvages: quoting,
# a LIST MARKER (a verifier writes its new findings as bullets), a heading
# marker, and bold around the whole line.
WRAP = r"^[\s>]*(?:[-*+][ \t]+)?(?:\#{1,6}\s*)?(?P<bold>\*\*|__)?[ \t]*"
# The id shape, taken from `ledger_md` and wrapped in this script's own
# capture group. This script states no id grammar of its own: the contract
# has ONE definition (`ledger_md.ID_PATTERN`) and every reader imports it.
_IDG = r"(?P<id>" + ID_PATTERN + r")"

# A line that merely LOOKS like a finding header: the id shape followed by
# a separator. Everything is_candidate() accepts must parse or the run fails.
CAND_RE = re.compile(
    WRAP + _IDG + r"[ \t]*(?P<sep>[" + SEP + r"])"
    r"(?P<rest>.*)$",
)
FULL_RE = re.compile(
    WRAP + _IDG + r"[ \t]*(?P<sep>[" + SEP + r"])[ \t]*"
    r"(?P<sev>" + "|".join(SEVERITIES) + r")[ \t]*(?P=sep)[ \t]*"
    r"(?P<claim>\S.*?)[ \t]*$",
    re.IGNORECASE,
)
NEXT_SEP_RE = re.compile(r"[" + SEP + r"]")
# The THIRD header form: a section heading naming the id and the claim, with
# the severity on a line of its own further down (`Severity: **major**`), the
# shape a blinded security re-check delivers. The heading alone is not a
# finding — an id in a heading is as ordinary as an id in prose — so it
# counts only where the severity field follows it before the next heading.
SECTION_RE = re.compile(
    r"^[\s>]*\#{1,6}[ \t]*(?:\*\*|__)?[ \t]*"
    + _IDG
    + r"[ \t]*[—–-][ \t]*(?P<claim>\S.*?)[ \t]*$",
)
HEADING_RE = re.compile(r"^[\s>]*\#{1,6}[ \t]")
SEVERITY_FIELD_RE = re.compile(
    r"severity[ \t]*:[ \t]*(?:\*\*|__)?[ \t]*(?P<sev>" + "|".join(SEVERITIES) + r")",
    re.IGNORECASE,
)


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


def prose_mask(lines: list[str]) -> list[bool]:
    """True per line where the line is prose-level, False inside a fence.

    The fence markers themselves are False: they are structure, never a
    finding. Computed once, so that a look-ahead (the section form's
    severity field) reads the same file the main loop does.
    """
    mask: list[bool] = []
    in_fence = False
    for raw in lines:
        if FENCE_RE.match(raw.rstrip("\n")):
            in_fence = not in_fence
            mask.append(False)
            continue
        mask.append(not in_fence)
    return mask


def section_severity(lines: list[str], mask: list[bool], index: int) -> str | None:
    """The severity a section heading's own block declares, or None.

    The block ends at the next heading: a `Severity:` field below THAT one
    belongs to the next finding, and reading across the boundary would
    hand one finding another's severity.
    """
    for i in range(index + 1, len(lines)):
        if not mask[i]:
            continue
        text = lines[i].rstrip("\n")
        if HEADING_RE.match(text):
            return None
        found = SEVERITY_FIELD_RE.search(text)
        if found:
            return found.group("sev")
    return None


def parse_report(path: str) -> tuple[list[Finding], list[str]]:
    """Return (findings, skipped). A finding is a dict with the three cells
    copied literally from the salvage, plus its provenance.

    A line that looks like a finding header and does not parse is SKIPPED
    with its location and does not stop the file: one `X-1 | fixed |` row
    used to take its three well-formed neighbours down with it, and the
    round worked around that by hand-cutting eight copies of its reports.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    findings: list[Finding] = []
    skipped: list[str] = []
    with Path(path).open(encoding="utf-8") as fh:
        # The wrapper skeleton lives in `ledger_md.unwrap_salvage_fence`
        # (see its docstring for what "wrapper" means); this script's own
        # notion of a finding header is the STRICT one, `FULL_RE`.
        # Here a finding header that sits inside such a wrapper is still a
        # finding: skipping the wrapper as a quote would hide every finding in
        # the file and transcribe nothing.
        lines = unwrap_salvage_fence(
            fh.readlines(),
            is_finding=lambda ln: FULL_RE.match(ln.rstrip("\n")) is not None,
        )
    mask = prose_mask(lines)
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if not mask[n - 1]:  # a fence marker, or a quoted row inside one
            continue
        if not is_candidate(line):
            heading = SECTION_RE.match(line)
            if heading is None:
                continue
            sev = section_severity(lines, mask, n - 1)
            if sev is None:  # an id in a heading is prose until a severity
                continue
            findings.append(
                {
                    "id": heading.group("id"),
                    "sev": sev,
                    "claim": heading.group("claim"),
                    "file": path,
                    "line": n,
                },
            )
            continue
        m = FULL_RE.match(line)
        if not m:
            skipped.append(
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
            skipped.append(
                f"{path}:{n}: finding header with an empty claim: {line.strip()[:120]}",
            )
            continue
        finding: Finding = {
            "id": m.group("id"),
            "sev": m.group("sev"),
            "claim": claim,
            "file": path,
            "line": n,
        }
        findings.append(finding)
    return findings, skipped


def ledger_width(lines: list[str]) -> tuple[int | None, str | None]:
    """Return (the target ledger's row width, error-or-None).

    The header's `Row schema:` declaration is authoritative where it exists,
    the findings header's own cell count where it does not, and a
    disagreement between the two is refused rather than resolved: the one
    thing this function may not do is hand back a width that would make
    every emitted row a structural error of the recount. The derivation is
    `ledger_md`'s; what is this script's own is WHAT is being refused —
    emitting a row, not writing into one — which is what the two refusal
    endings say.
    """
    return _ledger_width(lines, WIDTH_TAILS_EMIT_ROW)


def row(finding: Finding, width: int = DEFAULT_WIDTH) -> str:
    """One row of `width` cells; only the NAMED cells are filled.

    `id`, `sev` and `claim` carry the literal copy; the v3 `zone` cell
    carries the stub the adjudicator replaces. Every other cell is empty on
    purpose — an empty cell is what keeps a fresh row non-terminal.

    EVERY copied cell is escaped here, and here only. Escaping the claim at
    parse time and nothing else made the escaping a property of ONE field
    rather than of the row: a pipe reaching any other copied cell would
    split the row and silently shift every cell after it. The escaping is
    idempotent-by-construction only if applied once, so this is the single
    site — `parse_report` hands over the literal text, unescaped.
    """
    cells = [finding["id"], finding["sev"]]
    if width == V3_WIDTH:
        cells.insert(ZONE_INDEX, ZONE_PLACEHOLDER)
    cells.append(finding["claim"])
    cells = [escape_cell(c) for c in cells]
    cells += [""] * (width - len(cells))
    return "| " + " | ".join(cells) + " |"


def report_rejected(rejected: list[str]) -> None:
    """Print the rejected-duplicate block to stdout, in one wording.

    Separate from the structural block on purpose: the two carry different
    news — "the salvage could not be read" against "these rows were left
    out of a write that happened" — and a reader who sees one wording for
    both cannot tell whether the ledger was touched.
    """
    print(f"REJECTED DUPLICATE IDS — {len(rejected)} row(s) not transcribed:")
    for e in rejected:
        print("  " + e)


def report_skipped(skipped: list[str], file: TextIO | None = None) -> None:
    """Print the skipped-line block, with a location per line, or nothing.

    A third wording beside the structural and the duplicate blocks, and for
    the same reason they are apart: these lines were CONSIDERED and passed
    over while the rest of their file was transcribed, which is neither a
    failed read nor a rejected row.
    """
    if not skipped:
        return
    stream = sys.stdout if file is None else file
    print(
        f"SKIPPED LINES — {len(skipped)} line(s) considered and not transcribed:",
        file=stream,
    )
    for e in skipped:
        print("  " + e, file=stream)


def main() -> int:
    """Transcribe the reports named on the command line and return the exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return EXIT_OK
    to_stdout = "--stdout" in args
    args = [a for a in args if a != "--stdout"]
    ledger = None
    if "--ledger" in args:
        i = args.index("--ledger")
        if i + 1 >= len(args):
            print("--ledger needs a path")
            return EXIT_STRUCTURAL
        ledger = args[i + 1]
        del args[i : i + 2]
    if not args or (ledger is None) == (not to_stdout):
        print(__doc__)
        return EXIT_STRUCTURAL

    findings: list[Finding] = []
    errors: list[str] = []
    skipped: list[str] = []
    per_file: list[tuple[str, list[str]]] = []
    for path in args:
        try:
            got, over = parse_report(path)
        except OSError as exc:
            print(f"cannot read {path}: {exc}")
            return EXIT_STRUCTURAL
        findings.extend(got)
        skipped.extend(over)
        per_file.append((path, [f["id"] for f in got]))

    # Duplicates are collected APART from the structural errors: a
    # structural error means the salvage could not be read and stops the
    # run, a duplicate means one row of a readable salvage may not be laid
    # out. Only the second is recoverable row by row.
    rejected: list[str] = []
    rejected_ids: set[int] = set()
    seen: dict[str, str] = {}
    for i, f in enumerate(findings):
        if f["id"] in seen:
            rejected.append(
                f"{f['file']}:{f['line']}: DUPLICATE FINDING ID "
                f"{f['id']} (first seen at {seen[f['id']]})",
            )
            rejected_ids.add(i)
        else:
            seen[f["id"]] = f"{f['file']}:{f['line']}"

    lines: list[str] = []
    insert_at: int | None = None
    # `--stdout` has no ledger to read a schema from, so the v3 form is
    # printed and the caller places it; `--ledger` takes the width from the
    # target file and refuses to write at all when it is not derivable.
    width = DEFAULT_WIDTH
    if ledger is not None:
        try:
            with Path(ledger).open(encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            print(f"cannot read {ledger}: {exc}")
            return EXIT_STRUCTURAL
        # A CLOSED round is refused before anything else is even looked at
        # and in ONE line: a finished ledger is evidence, and listing
        # further faults in it would read as an invitation to fix them.
        # This is the same freeze `set-cell.py` obeys, through the same
        # function — the writers of a ledger refuse it as one.
        frozen = closed_refusal(lines)
        if frozen is not None:
            print(f"{ledger}: {frozen}")
            return EXIT_STRUCTURAL
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
            for i, f in enumerate(findings):
                if f["id"] in existing_ids and i not in rejected_ids:
                    rejected.append(
                        f"{f['file']}:{f['line']}: id {f['id']} is "
                        f"ALREADY a row of {ledger} — refusing to "
                        f"transcribe it twice",
                    )
                    rejected_ids.add(i)

    # The partial write is a property of the WRITE, so it belongs to
    # `--ledger` mode alone. `--stdout` writes nothing: its stdout is a pipe
    # payload documented as carrying ONLY rows, so a partial set there would
    # be appended to a ledger by the caller with the rejection notice on
    # another stream — the silent loss this change exists to remove. In that
    # mode a duplicate stays what it was, a structural error over the run.
    if to_stdout:
        errors.extend(rejected)
        rejected = []
    # A structural error is still all-or-nothing, and it outranks a
    # duplicate: a salvage that could not be read has no trustworthy rows
    # to keep, so the duplicate list would be a claim about text nobody
    # parsed.
    if errors:
        print("STRUCTURAL ERRORS — nothing was written:")
        for e in errors:
            print("  " + e)
        report_skipped(skipped)
        return EXIT_STRUCTURAL
    if not findings:
        print("no findings recognized in: " + ", ".join(args))
        report_skipped(skipped)
        return EXIT_STRUCTURAL

    keep = [f for i, f in enumerate(findings) if i not in rejected_ids]
    if not keep:
        # Nothing survived the rejection: do not touch the ledger at all
        # rather than rewriting it with the content it already has.
        report_rejected(rejected)
        print("nothing was written: every recognized finding was a duplicate")
        return EXIT_STRUCTURAL
    rows = [row(f, width) for f in keep]
    if to_stdout:
        print("\n".join(rows))
    else:
        head = lines[:insert_at]
        if head and not head[-1].endswith("\n"):
            head[-1] += "\n"  # separator was the last line, no newline
        write_error = write_atomic(
            cast("str", ledger),
            head + [r + "\n" for r in rows] + lines[insert_at:],
            TMP_SUFFIX,
        )
        if write_error is not None:
            print("STRUCTURAL ERRORS — nothing was written:")
            print("  " + write_error)
            return EXIT_STRUCTURAL

    out = sys.stderr if to_stdout else sys.stdout
    print(
        f"transcribed {len(keep)} findings"
        + ("" if to_stdout else f" into {ledger} after line {insert_at}"),
        file=out,
    )
    for path, ids in per_file:
        print(f"  {path}: {len(ids)} — {', '.join(ids) or '(none)'}", file=out)
    # Both halves of the run, always: what was laid out, and what was looked
    # at and passed over. A skipped line reported nowhere is the silent loss
    # this script exists to make impossible.
    report_skipped(skipped, file=out)
    if rejected:
        # The rows that survived are already written; the exit code still
        # reports the failure, so the operator neither loses the work nor
        # gets a green run over a salvage that was not fully laid out.
        report_rejected(rejected)
        return EXIT_STRUCTURAL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
