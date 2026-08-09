"""Characterization tests for validate-report.py.

The script is the deterministic half of critic-report acceptance: it turns
id-prefix and severity defects into PROBLEMS (exit 1) and everything softer
into MARKS (never affecting the exit code). Exit codes: 0 = no problems,
1 = problems found, 2 = unreadable report or bad arguments.
"""

from __future__ import annotations

import pytest

from conftest import FENCE

SCRIPT = "validate-report.py"

# A report with a recognizable header, a coverage statement and one
# well-formed finding carrying file:line evidence — the zero-marks shape.
FULL_REPORT = ("# Critic report\n"
               "\n"
               "- object: the parser module\n"
               "- lens: correctness\n"
               "- method: manual reading of the source\n"
               "- coverage: the whole module was examined\n"
               "\n"
               "## Findings\n"
               "\n"
               "GA-1 | major | the parser drops a trailing row (src/mod.py:12)\n")


def bare(*lines):
    """A report with no header and no coverage statement (four notes)."""
    return "".join(line + "\n" for line in lines)


# --- happy path ------------------------------------------------------------

def test_clean_report_produces_the_full_shape(run, report):
    path = report(FULL_REPORT)
    res = run(SCRIPT, path, "GA")
    assert res.returncode == 0, res.stdout
    assert res.stdout == (
        f"report: {path}\n"
        f"expected id prefix: GA\n"
        f"this script never rejects a report: the verdict 're-run this lens' "
        f"is the orchestrator's.\n"
        f"\n"
        f"findings (1):\n"
        f"  line 10: GA-1 | major\n"
        f"\n"
        f"problems (0):\n"
        f"  (none)\n"
        f"\n"
        f"marks (0):\n"
        f"  (none)\n"
        f"\n"
        f"summary: findings=1 problems=0 suspicious=0 notes=0\n"
    )


def test_severity_case_is_tolerated(run, report):
    res = run(SCRIPT, report(FULL_REPORT.replace("| major |", "| Major |")), "GA")
    assert res.returncode == 0, res.stdout
    assert "  line 10: GA-1 | Major" in res.stdout
    assert "problems (0):" in res.stdout


@pytest.mark.parametrize("line", [
    "GA-1 | major | claim (src/mod.py:12)",
    "- GA-1 | major | claim (src/mod.py:12)",
    "* GA-1 | major | claim (src/mod.py:12)",
    "> GA-1 | major | claim (src/mod.py:12)",
    "### GA-1 | major | claim (src/mod.py:12)",
    "| GA-1 | major | claim (src/mod.py:12) |",
    "**GA-1** | major | claim (src/mod.py:12)",
])
def test_finding_shapes_that_are_detected(run, report, line):
    res = run(SCRIPT, report(bare(line)), "GA")
    assert res.returncode == 0, res.stdout
    assert "findings (1):" in res.stdout
    assert "problems (0):" in res.stdout


# --- problems --------------------------------------------------------------

def test_foreign_prefix_is_a_problem(run, report):
    res = run(SCRIPT, report(bare("GB-1 | major | claim (a.py:1)")), "GA")
    assert res.returncode == 1, res.stdout
    assert ("line 1: id 'GB-1' carries a foreign prefix 'GB'; this lens was "
            "assigned 'GA'" in res.stdout)


def test_prefix_differing_only_in_case_gets_a_hint(run, report):
    res = run(SCRIPT, report(bare("ga-1 | major | claim (a.py:1)")), "GA")
    assert res.returncode == 1, res.stdout
    assert ("line 1: id 'ga-1' carries a foreign prefix 'ga'; this lens was "
            "assigned 'GA' (letter case differs)" in res.stdout)


@pytest.mark.parametrize("bad_id", ["GA1", "GA-1a", "GA_1"])
def test_malformed_ids_are_problems(run, report, bad_id):
    res = run(SCRIPT, report(bare(f"{bad_id} | major | claim (a.py:1)")), "GA")
    assert res.returncode == 1, res.stdout
    assert (f"line 1: id {bad_id!r} is not a well-formed finding id "
            f"<PREFIX>-<n> (expected prefix 'GA')" in res.stdout)


def test_empty_first_cell_is_detected_and_reported(run, report):
    res = run(SCRIPT, report(bare("|  | major | claim (a.py:1) |")), "GA")
    assert res.returncode == 1, res.stdout
    assert "findings (1):" in res.stdout
    assert "line 1: id '' is not a well-formed finding id" in res.stdout


def test_unaccepted_severity_is_a_problem(run, report):
    res = run(SCRIPT, report(bare("GA-1 | critical | claim (a.py:1)")), "GA")
    assert res.returncode == 1, res.stdout
    assert ("line 1: GA-1: severity 'critical' is not one of the literals "
            "blocker, major, minor" in res.stdout)


def test_duplicate_finding_id_is_a_problem(run, report):
    text = bare("GA-1 | major | first (a.py:1)", "GA-1 | minor | second (b.py:2)")
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 1, res.stdout
    assert ("line 2: GA-1: duplicate finding id — already used at line 1"
            in res.stdout)


def test_duplicate_detection_ignores_letter_case(run, report):
    text = bare("GA-1 | major | first (a.py:1)", "ga-1 | major | second (b.py:2)")
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 1, res.stdout
    assert "duplicate finding id — already used at line 1" in res.stdout


def test_report_without_findings_is_a_problem(run, report):
    res = run(SCRIPT, report("# Report\n\nNothing was found.\n"), "GA")
    assert res.returncode == 1, res.stdout
    assert "findings (0):" in res.stdout
    assert "  (none)" in res.stdout
    assert ("no findings found in the report — an empty report is not a report "
            "(a critic that found nothing still owes a coverage statement)"
            in res.stdout)


def test_long_first_cell_is_not_read_as_a_finding(run, report):
    long_cell = "a table row whose first cell is far too long to be an id"
    res = run(SCRIPT, report(bare(f"| {long_cell} | major | text |")), "GA")
    assert res.returncode == 1, res.stdout
    assert "findings (0):" in res.stdout


# --- marks -----------------------------------------------------------------

def test_missing_evidence_is_only_a_mark(run, report):
    res = run(SCRIPT, report(bare("GA-1 | major | a claim with no evidence")),
              "GA")
    assert res.returncode == 0, res.stdout
    assert ("line 1: GA-1: suspicious: no file:line evidence (nor an explicit "
            "command) in its block — the evidence may still be an exact quote; "
            "a human decides" in res.stdout)
    assert "suspicious=1" in res.stdout


@pytest.mark.parametrize("evidence", [
    "see src/mod.py:12",
    "see Makefile:12",
    "run `grep -n TODO src`",
    "    $ python3 tool.py --check",
    "run `./tool.sh --check`",
])
def test_evidence_forms_that_clear_the_mark(run, report, evidence):
    text = bare("GA-1 | major | a claim", evidence)
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 0, res.stdout
    assert "suspicious=0" in res.stdout


def test_command_inside_a_fenced_block_counts_as_evidence(run, report):
    text = bare("GA-1 | major | a claim", FENCE, "grep -c TODO src/mod.py",
                FENCE)
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 0, res.stdout
    assert "suspicious=0" in res.stdout


def test_url_with_a_port_is_not_read_as_a_file_reference(run, report):
    text = bare("GA-1 | major | a claim", "see https://example.com:8080 for it")
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 0, res.stdout
    assert "suspicious=1" in res.stdout


def test_a_block_ends_at_the_next_markdown_heading(run, report):
    text = bare("GA-1 | major | a claim", "", "## Coverage", "", "src/mod.py:12")
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 0, res.stdout
    assert "suspicious=1" in res.stdout


def test_missing_header_fields_and_coverage_are_notes(run, report):
    res = run(SCRIPT, report(bare("GA-1 | major | claim (a.py:1)")), "GA")
    assert res.returncode == 0, res.stdout
    for field in ("'object'", "'lens'", "'method'"):
        assert (f"note: header field {field} not recognized above the first "
                f"finding" in res.stdout)
    assert ("note: no coverage statement recognized (what was examined vs "
            "skipped) — not a failure" in res.stdout)
    assert "notes=4" in res.stdout


def test_marks_never_change_the_exit_code(run, report):
    res = run(SCRIPT, report(bare("GA-1 | major | claim without evidence")), "GA")
    assert res.returncode == 0, res.stdout
    assert "summary: findings=1 problems=0 suspicious=1 notes=4" in res.stdout


# --- fences ----------------------------------------------------------------

def test_quoted_rows_inside_a_fence_are_not_findings(run, report):
    text = bare("GA-1 | major | real finding (a.py:1)", "", FENCE,
                "GB-9 | major | quoted from another lens", FENCE)
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 0, res.stdout
    assert "findings (1):" in res.stdout
    assert "GB-9" not in res.stdout


def test_a_fence_wrapping_the_whole_report_is_unwrapped(run, report):
    text = bare("salvaged verbatim:", "", FENCE,
                "GA-1 | major | first (a.py:1)",
                "GA-2 | minor | second (b.py:2)", FENCE)
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 0, res.stdout
    assert "findings (2):" in res.stdout
    assert "  line 4: GA-1 | major" in res.stdout
    assert "  line 5: GA-2 | minor" in res.stdout


def test_a_fence_holding_one_finding_stays_a_quote(run, report):
    text = bare("salvaged verbatim:", "", FENCE,
                "GA-1 | major | only one (a.py:1)", FENCE)
    res = run(SCRIPT, report(text), "GA")
    assert res.returncode == 1, res.stdout
    assert "findings (0):" in res.stdout


# --- usage and IO ----------------------------------------------------------

@pytest.mark.parametrize("argv", [(), ("only-one.md",),
                                  ("a.md", "GA", "extra")])
def test_wrong_argument_count_prints_usage(run, argv):
    res = run(SCRIPT, *argv)
    assert res.returncode == 2, res.stdout
    assert "Usage:  validate-report.py <report.md> <EXPECTED_PREFIX>" in res.stdout


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_flags_print_usage_and_exit_two(run, report, flag):
    res = run(SCRIPT, report(FULL_REPORT), "GA", flag)
    assert res.returncode == 2, res.stdout
    assert "Usage:  validate-report.py" in res.stdout


@pytest.mark.parametrize("prefix", ["G-A", "1GA", "GA!", ""])
def test_malformed_expected_prefix(run, report, prefix):
    res = run(SCRIPT, report(FULL_REPORT), prefix)
    assert res.returncode == 2, res.stdout
    assert (f"bad expected prefix {prefix!r}: it must start with a letter and "
            f"contain only letters and digits" in res.stdout)


def test_unreadable_report(run, tmp_path):
    missing = tmp_path / "absent.md"
    res = run(SCRIPT, missing, "GA")
    assert res.returncode == 2, res.stdout
    assert res.stdout.startswith(f"cannot read report {str(missing)!r}: ")


def test_non_utf8_report(run, tmp_path):
    path = tmp_path / "report.md"
    path.write_bytes(b"GA-1 | major | \xff\xfe\n")
    res = run(SCRIPT, path, "GA")
    assert res.returncode == 2, res.stdout
    assert "cannot read report" in res.stdout
