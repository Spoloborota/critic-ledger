"""Tests for `scripts/extract_final.py`, the stage-4 salvage extractor.

The script reads a subagent's task transcript — one JSON record per line —
and writes that agent's final message, verbatim, under one header line. It
is driven here the way `ledger_md.py new` is: a subprocess call built in
this file, not the `run` fixture.

Every fixture here is a hand-written synthetic JSONL line built inside the
test; no captured transcript enters the published tree.
"""

from __future__ import annotations

import json
import subprocess
import sys

SCRIPT = "extract_final.py"
# The script's code for "no report found", the shared structural code.
NO_REPORT = 2


def assistant(*blocks: dict) -> str:
    """One synthetic transcript line: an assistant message with `blocks`."""
    return json.dumps(
        {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}
    )


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def handback_block(message: str) -> dict:
    return {
        "type": "tool_use",
        "id": "toolu_synthetic",
        "name": "SubagentHandback",
        "input": {"message": message},
    }


def user_line(text: str) -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": text}})


def run_extract(scripts_dir, sandbox_home, tmp_path, *args):
    """Invoke the extractor in a subprocess, the way stage 4 does."""
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, str(scripts_dir / SCRIPT), *map(str, args)],
        cwd=str(tmp_path),
        env={"PATH": "/usr/bin:/bin", "HOME": str(sandbox_home)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_handback_message_is_written_when_there_is_one(
    scripts_dir, sandbox_home, tmp_path,
):
    """The hand-back wins over every assistant text, the last one included."""
    report = "# Report\n\n| id | sev |\n|---|---|\n| DA-1 | major |"
    src = tmp_path / "task.jsonl"
    src.write_text(
        "\n".join(
            [
                user_line("brief"),
                assistant(text_block("working")),
                assistant(handback_block(report)),
                assistant(text_block("done")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    dst = tmp_path / "critics" / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L, pass 1.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert dst.read_text(encoding="utf-8") == (
        "<!-- Lens L, pass 1. Source: SubagentHandback message. -->\n\n"
        + report
        + "\n"
    )
    assert result.stdout.startswith(f"OK {dst} SubagentHandback message ")


def test_the_last_assistant_text_is_written_when_there_is_no_handback(
    scripts_dir, sandbox_home, tmp_path,
):
    """Without a hand-back the LAST non-empty assistant text is the report."""
    src = tmp_path / "task.jsonl"
    src.write_text(
        "\n".join(
            [
                assistant(text_block("first")),
                "not json at all",
                assistant(text_block("the final report")),
                assistant(text_block("   ")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    dst = tmp_path / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert dst.read_text(encoding="utf-8") == (
        "<!-- Lens L. Source: last assistant text. -->\n\nthe final report\n"
    )
    assert "last assistant text" in result.stdout


def test_a_transcript_with_no_report_writes_nothing(
    scripts_dir, sandbox_home, tmp_path,
):
    """No hand-back and no assistant text: the structural code, no file."""
    src = tmp_path / "task.jsonl"
    src.write_text(user_line("brief") + "\n" + assistant() + "\n", encoding="utf-8")
    dst = tmp_path / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == NO_REPORT
    assert "no report found" in result.stdout
    assert not dst.exists()


def write_transcript(tmp_path, *lines: str):
    """Write the synthetic transcript lines to `task.jsonl`; return its path."""
    src = tmp_path / "task.jsonl"
    src.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return src


def test_the_last_of_two_handbacks_is_written(
    scripts_dir, sandbox_home, tmp_path,
):
    """A resumed agent hands back twice: the SECOND message is the report."""
    src = write_transcript(
        tmp_path,
        assistant(handback_block("first pass report")),
        assistant(handback_block("second pass report")),
    )
    dst = tmp_path / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    written = dst.read_text(encoding="utf-8")
    assert "second pass report" in written
    assert "first pass report" not in written


def test_a_blank_handback_falls_back_to_the_last_text(
    scripts_dir, sandbox_home, tmp_path,
):
    """A whitespace-only hand-back is no report; the last text is used."""
    src = write_transcript(
        tmp_path,
        assistant(handback_block("   \n")),
        assistant(text_block("the text report")),
    )
    dst = tmp_path / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert dst.read_text(encoding="utf-8") == (
        "<!-- Lens L. Source: last assistant text. -->\n\nthe text report\n"
    )
    assert "last assistant text" in result.stdout


def test_a_symlink_at_dst_is_replaced_and_its_target_untouched(
    scripts_dir, sandbox_home, tmp_path,
):
    """The write never goes THROUGH a link sitting at `--dst`."""
    src = write_transcript(tmp_path, assistant(text_block("report")))
    target = tmp_path / "target.md"
    target.write_text("KEEP\n", encoding="utf-8")
    dst = tmp_path / "L.md"
    dst.symlink_to(target)
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.read_text(encoding="utf-8") == "KEEP\n"
    assert not dst.is_symlink()
    assert dst.is_file()
    assert "report" in dst.read_text(encoding="utf-8")


def test_an_existing_dst_is_replaced_with_a_notice(
    scripts_dir, sandbox_home, tmp_path,
):
    """A re-salvage to a reused name says so, and leaves no temporary file."""
    src = write_transcript(tmp_path, assistant(text_block("new report")))
    dst = tmp_path / "L.md"
    dst.write_text("EARLIER\n", encoding="utf-8")
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "replaced" in result.stdout
    assert "new report" in dst.read_text(encoding="utf-8")
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith("L.md")] == [
        "L.md"
    ]


def test_a_new_dst_carries_no_replace_notice(
    scripts_dir, sandbox_home, tmp_path,
):
    """A first write says nothing about replacing."""
    src = write_transcript(tmp_path, assistant(text_block("report")))
    dst = tmp_path / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "replaced" not in result.stdout


def test_an_unwritable_dst_is_the_structural_code_without_a_traceback(
    scripts_dir, sandbox_home, tmp_path,
):
    """The parent of `--dst` is a regular file: exit 2, one line, no file."""
    src = write_transcript(tmp_path, assistant(text_block("report")))
    parent = tmp_path / "afile"
    parent.write_text("", encoding="utf-8")
    dst = parent / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == NO_REPORT
    assert "Traceback" not in result.stdout + result.stderr
    assert "cannot be written" in result.stdout
    assert parent.read_text(encoding="utf-8") == ""


def test_the_size_line_counts_the_message_as_written(
    scripts_dir, sandbox_home, tmp_path,
):
    """A trailing newline is stripped before the counts: `abc` is 1 line."""
    src = write_transcript(tmp_path, assistant(handback_block("abc\n")))
    dst = tmp_path / "L.md"
    result = run_extract(
        scripts_dir, sandbox_home, tmp_path,
        "--src", src, "--dst", dst, "--header", "Lens L.",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith(" 3 chars 1 lines")
