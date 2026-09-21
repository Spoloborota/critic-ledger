#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Write a subagent's final message, verbatim, from its task transcript.

The stage-4 salvage keeps every report verbatim. A report the harness hands
back to the main session arrives indented and HTML-escaped, which is not
verbatim; the subagent's own task transcript still holds the text as the
agent wrote it. This script reads that transcript — one JSON record per
line — and writes the agent's final message into the salvage file:

- the message of the agent's `SubagentHandback` call, where there is one
  (the last such call wins);
- otherwise the agent's last non-empty assistant text.

The file gets one header line and then the message:
`<!-- {header} Source: {source kind}. -->`, a blank line, the message.
The script prints one size line, `OK <dst> <source kind> <n> chars <m>
lines`, and nothing of the message itself. Both counts are taken on the
message as written, trailing whitespace stripped.

The file is written through a temporary file and an atomic replace, never
THROUGH a symlink: a link sitting at `--dst` is itself replaced by a
regular file, and whatever it pointed to is left untouched. An existing
`--dst` is replaced, and the size line then ends with
`(replaced an existing file)`, so a re-salvage to a reused name never
passes in silence.

The task transcript lives where the platform keeps it, in the session
store under the user's home directory — a machine-local path that no
artifact of the round quotes; the extractor only reads it, writes nothing
to `--dst` but the extracted final message under its one header line, and
never copies the transcript file anywhere. That header line is the
caller's `--header` text followed by the source kind, and the extractor
writes the text as given: the caller never puts a path into `--header` —
the transcript's least of all — and the extractor adds none.

Usage:  extract_final.py --src <task transcript> --dst <salvage file>
                         --header "<text>"
        extract_final.py -h | --help               (this text, exit 0)
Exit codes: 0 = the final message was written, or `-h`/`--help`;
2 = no report found in the transcript (nothing written), or a usage error.
2 = also the salvage file cannot be written (its folder cannot be made, or
the write fails): one line names the failure, no traceback, and `--dst` is
left as it was.
"""

import argparse
import json
import sys
from pathlib import Path

# The exit codes live in ONE place — `scripts/ledger_md.py`, beside this
# script. The import is resolved from THIS script's own directory: the
# payload ships loose files and there is no installed package (see
# `pyproject.toml`), so a copy of this script without `ledger_md.py` beside
# it does not run.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The import sits below the path insert above, which is what makes it work.
from ledger_md import EXIT_OK, EXIT_STRUCTURAL, write_atomic

HANDBACK_TOOL = "SubagentHandback"
SOURCE_HANDBACK = "SubagentHandback message"
SOURCE_LAST_TEXT = "last assistant text"
NO_REPORT = "no report found"
WRITE_FAILED = "the salvage file cannot be written:"
TMP_SUFFIX = ".extract-final.tmp"


def assistant_blocks(line: str) -> list[dict[str, object]]:
    """Return the content blocks of one transcript line's assistant message.

    A line that is not JSON, or not an assistant message, yields no blocks:
    a transcript carries many kinds of record, and only the agent's own
    messages can hold its report.
    """
    try:
        record = json.loads(line)
    except ValueError:
        return []
    message = record.get("message") if isinstance(record, dict) else None
    if not isinstance(message, dict) or message.get("role") != "assistant":
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def final_message(text: str) -> tuple[str | None, str]:
    """Return (the final message or None, its source kind)."""
    handback: str | None = None
    last_text: str | None = None
    for line in text.splitlines():
        for block in assistant_blocks(line):
            if block.get("type") == "tool_use" and block.get("name") == HANDBACK_TOOL:
                arguments = block.get("input")
                message = (
                    arguments.get("message") if isinstance(arguments, dict) else None
                )
                if isinstance(message, str) and message.strip():
                    handback = message
            elif block.get("type") == "text":
                body = block.get("text")
                if isinstance(body, str) and body.strip():
                    last_text = body
    if handback is not None:
        return handback, SOURCE_HANDBACK
    return last_text, SOURCE_LAST_TEXT


def main(argv: list[str] | None = None) -> int:
    """Extract the final message named on the command line; return the code."""
    parser = argparse.ArgumentParser(
        prog="extract_final.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--src", required=True, help="the subagent's task transcript")
    parser.add_argument("--dst", required=True, help="the salvage file to write")
    parser.add_argument("--header", required=True, help="the header text; never a path")
    args = parser.parse_args(argv)
    try:
        text = Path(args.src).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"{NO_REPORT}: the transcript cannot be read: {exc.strerror}")
        return EXIT_STRUCTURAL
    body, source = final_message(text)
    if body is None:
        print(NO_REPORT)
        return EXIT_STRUCTURAL
    out = Path(args.dst)
    written = body.rstrip()
    existed = out.exists() or out.is_symlink()
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        error = write_atomic(
            str(out),
            [f"<!-- {args.header} Source: {source}. -->\n\n{written}\n"],
            TMP_SUFFIX,
        )
    except OSError as exc:
        error = exc.strerror or type(exc).__name__
    if error is not None:
        print(f"{WRITE_FAILED} {args.dst}: {error}")
        return EXIT_STRUCTURAL
    lines = written.count("\n") + 1
    notice = " (replaced an existing file)" if existed else ""
    print(f"OK {args.dst} {source} {len(written)} chars {lines} lines{notice}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
