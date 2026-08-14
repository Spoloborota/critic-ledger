"""Characterization tests for cleanup-scratchpad.py.

The script removes manifest-declared scratchpad run directories, dry by
default, and refuses anything that fails one of its eight path-ownership
conditions. Exit codes: 0 = no refusal, 1 = at least one refusal, 2 = a
usage error (bad --root, non-absolute --manifest).

SAFETY: every path handed to the script here — the scratchpad root, the
checked project root, the manifests and the declared targets — is built by
the `scratch` fixture inside pytest's `tmp_path`, and `HOME` is redirected
there too. No test points the script at a path outside `tmp_path`, and the
only tests that pass `--confirm` operate on directories the fixture itself
created moments earlier.
"""

from __future__ import annotations

import json

import pytest

from conftest import MANIFEST_NAME, hours_ago

SCRIPT = "cleanup-scratchpad.py"


# --- usage errors ----------------------------------------------------------

def test_root_is_required(run):
    res = run(SCRIPT)
    assert res.returncode == 2, res.stdout
    assert "--root" in res.stderr


def test_relative_root_is_refused(run):
    res = run(SCRIPT, "--root", "relative/dir")
    assert res.returncode == 2, res.stdout
    assert ("refusing: --root must be an absolute path, got 'relative/dir'"
            in res.stderr)


def test_root_with_a_parent_segment_is_refused(run, scratch):
    bad = f"{scratch.root}/../scratchpad"
    res = run(SCRIPT, "--root", bad)
    assert res.returncode == 2, res.stdout
    assert f"refusing: --root must not contain a '..' segment: {bad!r}" in res.stderr


def test_root_that_does_not_exist_is_refused(run, tmp_path):
    missing = tmp_path.resolve() / "nowhere"
    res = run(SCRIPT, "--root", missing)
    assert res.returncode == 2, res.stdout
    assert (f"refusing: --root is not an existing directory: {str(missing)!r}"
            in res.stderr)


def test_root_that_is_a_file_is_refused(run, tmp_path):
    path = tmp_path.resolve() / "afile"
    path.write_text("x", encoding="utf-8")
    res = run(SCRIPT, "--root", path)
    assert res.returncode == 2, res.stdout
    assert "is not an existing directory" in res.stderr


def test_relative_manifest_is_refused(run, scratch):
    res = run(SCRIPT, "--root", scratch.root, "--manifest", "m.json")
    assert res.returncode == 2, res.stdout
    assert ("refusing: --manifest must be an absolute path, got 'm.json'"
            in res.stderr)


def test_empty_root_reports_no_manifests(run, scratch):
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert f"no {MANIFEST_NAME} found under {scratch.root}" in res.stdout
    assert "summary: deleted=0 refused=0 already-absent=0 skipped=0" in res.stdout


# --- dry run ---------------------------------------------------------------

def test_dry_run_plans_without_touching_anything(run, scratch):
    unit = scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    out = res.stdout
    assert out.startswith("cleanup-scratchpad: DRY RUN — deleting nothing\n")
    assert f"scratchpad root: {scratch.root}" in out
    assert f"[1/1] manifest: {unit.manifest}" in out
    assert f"        target: {unit.target}" in out
    assert ("status: PLANNED — would be deleted on a second call with "
            "--confirm (nothing was touched)" in out)
    assert "summary: deleted=0 refused=0 already-absent=0 skipped=0" in out
    assert ("dry run: 1 path(s) would be deleted; re-run with --confirm to "
            "delete them" in out)
    assert unit.target.is_dir()
    assert (unit.target / "notes.md").is_file()
    assert unit.manifest.is_file()


def test_dry_run_prints_every_condition_as_pass(run, scratch):
    scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    for number in range(1, 9):
        assert f"PASS condition {number} (" in res.stdout
    assert "FAIL condition" not in res.stdout


def test_dry_run_reports_contents_and_top_level(run, scratch):
    scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert "note: contents: 3 file(s), " in res.stdout
    assert (f"note: top level: copy-1/, {MANIFEST_NAME}, notes.md"
            in res.stdout)


def test_manifest_selects_a_single_unit(run, scratch):
    first = scratch.make_run("run-one")
    scratch.make_run("run-two")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", first.manifest)
    assert res.returncode == 0, res.stdout
    assert "[1/1] manifest:" in res.stdout
    assert "run-two" not in res.stdout


def test_discovery_finds_every_manifest_in_sorted_order(run, scratch):
    scratch.make_run("run-b")
    scratch.make_run("run-a")
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert res.stdout.index("[1/2] manifest:") < res.stdout.index("[2/2] manifest:")
    assert res.stdout.index("run-a") < res.stdout.index("run-b")
    assert ("dry run: 2 path(s) would be deleted" in res.stdout)


def test_symlinked_root_prints_the_resolved_root(run, scratch, tmp_path):
    scratch.make_run()
    link = tmp_path.resolve() / "root-link"
    link.symlink_to(scratch.root)
    res = run(SCRIPT, "--root", link)
    assert res.returncode == 0, res.stdout
    assert f"scratchpad root: {link}" in res.stdout
    assert f"resolved root:   {scratch.root}" in res.stdout


# --- real deletion ---------------------------------------------------------

def test_confirm_deletes_the_run_directory(run, scratch):
    unit = scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root, "--confirm")
    assert res.returncode == 0, res.stdout
    assert res.stdout.startswith("cleanup-scratchpad: CONFIRMED — deleting\n")
    assert ("status: DELETED — removed 3 file(s) and 2 directory(ies)"
            in res.stdout)
    assert "summary: deleted=1 refused=0 already-absent=0 skipped=0" in res.stdout
    assert "dry run:" not in res.stdout
    assert not unit.target.exists()
    assert not unit.manifest.exists()
    # everything above the run directory survives
    assert unit.target.parent.is_dir()
    assert scratch.project.is_dir()


def test_confirm_deletes_a_run_holding_only_its_manifest(run, scratch):
    unit = scratch.make_run(contents={})
    res = run(SCRIPT, "--root", scratch.root, "--confirm")
    assert res.returncode == 0, res.stdout
    assert ("status: DELETED — removed 1 file(s) and 1 directory(ies)"
            in res.stdout)
    assert not unit.target.exists()


def test_confirm_deletes_a_nested_tree(run, scratch):
    unit = scratch.make_run(contents={"a/b/c/deep.txt": "x" * 16,
                                      "a/b/other.txt": "y" * 16})
    res = run(SCRIPT, "--root", scratch.root, "--confirm")
    assert res.returncode == 0, res.stdout
    assert ("status: DELETED — removed 3 file(s) and 4 directory(ies)"
            in res.stdout)
    assert not unit.target.exists()


def test_sidecar_manifest_is_removed_last(run, scratch):
    unit = scratch.make_run(manifest_at=scratch.sidecar_path("sample-run"))
    res = run(SCRIPT, "--root", scratch.root, "--confirm")
    assert res.returncode == 0, res.stdout
    assert "PASS condition 6 (manifest path matches the resolved actual path)" \
        in res.stdout
    assert f"note: sidecar manifest removed last: {unit.manifest}" in res.stdout
    assert not unit.target.exists()
    assert not unit.manifest.exists()


def test_dry_run_recognizes_a_sidecar_manifest(run, scratch):
    unit = scratch.make_run(manifest_at=scratch.sidecar_path("sample-run"))
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert f"sidecar manifest {str(unit.manifest)!r}" in res.stdout
    assert unit.target.is_dir()


def test_already_absent_target_is_not_a_refusal(run, scratch):
    unit = scratch.make_run(create_target=False,
                            manifest_at=scratch.sidecar_path("sample-run"))
    res = run(SCRIPT, "--root", scratch.root, "--confirm")
    assert res.returncode == 0, res.stdout
    assert ("status: ALREADY ABSENT — the path from the manifest does not "
            "exist; nothing to delete, the manifest is left in place"
            in res.stdout)
    assert "summary: deleted=0 refused=0 already-absent=1 skipped=0" in res.stdout
    assert unit.manifest.is_file()


# --- the manifest gate (condition 5) ---------------------------------------

def test_missing_manifest_file(run, scratch):
    missing = scratch.root / "critic" / "runs" / "gone" / MANIFEST_NAME
    res = run(SCRIPT, "--root", scratch.root, "--manifest", missing)
    assert res.returncode == 1, res.stdout
    assert "        target: (unknown)" in res.stdout
    assert (f"FAIL condition 5 (manifest exists): manifest not found: No such "
            f"file or directory: {missing}" in res.stdout)
    assert "summary: deleted=0 refused=1 already-absent=0 skipped=0" in res.stdout
    assert ("ledger header line(s) to write: 'scratchpad not cleaned: "
            "<reason>, <path>' for each refusal" in res.stdout)


def test_manifest_that_is_a_symlink(run, scratch):
    unit = scratch.make_run(manifest_at=scratch.sidecar_path("sample-run"))
    link = scratch.root / "critic" / "runs" / "sample-run" / MANIFEST_NAME
    link.symlink_to(unit.manifest)
    res = run(SCRIPT, "--root", scratch.root, "--manifest", link)
    assert res.returncode == 1, res.stdout
    assert f"manifest is a symbolic link, refused: {link}" in res.stdout


def test_manifest_that_is_a_directory(run, scratch):
    unit = scratch.make_run(write_manifest=False)
    unit.manifest.mkdir()
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert f"manifest is not a regular file: {unit.manifest}" in res.stdout


def test_manifest_that_is_not_json(run, scratch):
    unit = scratch.make_run(write_manifest=False)
    unit.manifest.write_text("not json at all\n", encoding="utf-8")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert "manifest is not valid JSON:" in res.stdout


def test_manifest_that_is_not_an_object(run, scratch):
    unit = scratch.make_run(write_manifest=False)
    unit.manifest.write_text("[1, 2, 3]\n", encoding="utf-8")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert "manifest is not a JSON object — foreign format" in res.stdout


def test_foreign_manifest_version(run, scratch):
    unit = scratch.make_run(manifest_version="some-other-tool/manifest@1")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("foreign manifest format: manifest_version="
            "'some-other-tool/manifest@1', expected a string starting with "
            "'critic-ledger/scratchpad-manifest@'" in res.stdout)


def test_missing_required_field(run, scratch):
    unit = scratch.make_run(write_manifest=False)
    data = dict(unit.data)
    del data["project_root"]
    unit.manifest.write_text(json.dumps(data), encoding="utf-8")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert "foreign manifest format: project_root (missing)" in res.stdout


@pytest.mark.parametrize(("field", "value", "expected"), [
    ("run_id", 7, "run_id (expected str, got int)"),
    ("created", "copy-1", "created (expected list, got str)"),
    ("size_bytes", "12", "size_bytes (expected int, got str)"),
    ("size_bytes", True, "size_bytes (expected int, got bool)"),
])
def test_field_of_the_wrong_type(run, scratch, field, value, expected):
    unit = scratch.make_run(**{field: value})
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert f"foreign manifest format: {expected}" in res.stdout


def test_empty_absolute_path(run, scratch):
    unit = scratch.make_run(absolute_path="")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("foreign manifest format: empty absolute_path or project_root"
            in res.stdout)


def test_created_at_that_is_not_iso(run, scratch):
    unit = scratch.make_run(created_at="last tuesday")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("broken manifest: created_at='last tuesday' is not ISO 8601"
            in res.stdout)


def test_created_at_without_a_timezone_offset(run, scratch):
    unit = scratch.make_run(created_at="2000-01-02T03:04:05")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("carries no timezone offset; the age of a manifest must not depend "
            "on the reader's clock zone" in res.stdout)


# --- the eight path conditions ---------------------------------------------

def test_condition_1_non_absolute_target(run, scratch):
    unit = scratch.make_run(absolute_path="critic/runs/sample-run")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("FAIL condition 1 (path is absolute): not an absolute path: "
            "'critic/runs/sample-run'" in res.stdout)
    assert ("status: REFUSED — condition 1 (path is absolute)" in res.stdout)
    assert unit.target.is_dir()


def test_condition_2_parent_segment_in_the_target(run, scratch):
    declared = f"{scratch.root}/critic/runs/../runs/sample-run"
    unit = scratch.make_run(absolute_path=declared)
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert (f"FAIL condition 2 (path has no '..' segment): path contains a "
            f"'..' segment: {declared!r}" in res.stdout)
    assert unit.target.is_dir()


def test_condition_3_symlinked_segment(run, scratch):
    unit = scratch.make_run()
    (scratch.root / "link").symlink_to(scratch.root / "critic")
    declared = f"{scratch.root}/link/runs/sample-run"
    unit.manifest.write_text(
        json.dumps({**unit.data, "absolute_path": declared}), encoding="utf-8")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("FAIL condition 3 (path unchanged by symlink resolution): path "
            "changes when links are resolved" in res.stdout)
    assert unit.target.is_dir()


def test_condition_3_non_canonical_but_link_free(run, scratch):
    declared = f"{scratch.root}/critic/./runs/sample-run"
    unit = scratch.make_run(absolute_path=declared)
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("path is not in canonical form:" in res.stdout)
    assert "no symbolic link involved — the difference is textual" in res.stdout


def test_condition_4_outside_the_root(run, scratch, tmp_path):
    outside = tmp_path.resolve() / "elsewhere" / "a" / "b"
    outside.mkdir(parents=True)
    unit = scratch.make_run(absolute_path=str(outside))
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("FAIL condition 4 (inside the resolved scratchpad root, >= 3 "
            "levels deeper)" in res.stdout)
    assert "is not inside the resolved scratchpad root" in res.stdout
    assert outside.is_dir()


def test_condition_4_too_shallow(run, scratch):
    unit = scratch.make_run("shallow-run", parts=())
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("resolved path is only 1 level(s) below the root, 3 required"
            in res.stdout)
    assert unit.target.is_dir()


def test_condition_6_manifest_deeper_than_its_directory(run, scratch):
    unit = scratch.make_run(
        manifest_at=(scratch.root / "critic" / "runs" / "sample-run" / "sub"
                     / MANIFEST_NAME))
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("FAIL condition 6 (manifest path matches the resolved actual "
            "path)" in res.stdout)
    assert "deeper than the directory it describes" in res.stdout
    assert unit.target.is_dir()


def test_condition_7_run_id_mismatch_against_the_basename(run, scratch):
    unit = scratch.make_run(run_id="a-different-id")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("FAIL condition 7 (manifest run id matches the run id): run id in "
            "the manifest is 'a-different-id', but the basename of the run "
            "directory says 'sample-run'" in res.stdout)


def test_condition_7_run_id_mismatch_against_the_flag(run, scratch):
    unit = scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest,
              "--run-id", "expected-run")
    assert res.returncode == 1, res.stdout
    assert ("run id in the manifest is 'sample-run', but --run-id says "
            "'expected-run'" in res.stdout)


def test_condition_7_run_id_flag_that_agrees(run, scratch):
    unit = scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest,
              "--run-id", "sample-run")
    assert res.returncode == 0, res.stdout
    assert "PASS condition 7 (manifest run id matches the run id): run id " \
        "'sample-run' matches --run-id" in res.stdout


def test_condition_8_target_inside_the_checked_project(run, scratch):
    unit = scratch.make_run(project_root=str(scratch.root))
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("FAIL condition 8 (path is not inside the checked project's root)"
            in res.stdout)
    assert "the skill never deletes anything inside the checked project" in res.stdout
    assert unit.target.is_dir()


def test_condition_8_target_is_the_project_root(run, scratch):
    unit = scratch.make_run()
    unit.manifest.write_text(
        json.dumps({**unit.data, "project_root": str(unit.target)}),
        encoding="utf-8")
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest)
    assert res.returncode == 1, res.stdout
    assert ("the path to delete IS the checked project's root" in res.stdout)
    assert unit.target.is_dir()


def test_condition_8_project_root_flag_disagrees(run, scratch, tmp_path):
    other = tmp_path.resolve() / "other-project"
    other.mkdir()
    unit = scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest,
              "--project-root", other)
    assert res.returncode == 1, res.stdout
    assert (f"--project-root {str(other)!r} disagrees with the manifest's "
            f"project_root {str(scratch.project)!r}" in res.stdout)


def test_condition_8_project_root_flag_that_agrees(run, scratch):
    unit = scratch.make_run()
    res = run(SCRIPT, "--root", scratch.root, "--manifest", unit.manifest,
              "--project-root", scratch.project)
    assert res.returncode == 0, res.stdout
    assert "PASS condition 8 (path is not inside the checked project's root)" \
        in res.stdout


# --- age filtering ---------------------------------------------------------

def test_recent_manifest_is_skipped(run, scratch):
    unit = scratch.make_run(created_at=hours_ago(1))
    res = run(SCRIPT, "--root", scratch.root, "--older-than-hours", "24",
              "--confirm")
    assert res.returncode == 0, res.stdout
    assert "status: SKIPPED — age 1.0" in res.stdout
    assert "is below the --older-than-hours 24 threshold" in res.stdout
    assert "summary: deleted=0 refused=0 already-absent=0 skipped=1" in res.stdout
    assert unit.target.is_dir()


def test_old_manifest_passes_the_age_filter(run, scratch):
    unit = scratch.make_run(created_at=hours_ago(48))
    res = run(SCRIPT, "--root", scratch.root, "--older-than-hours", "24")
    assert res.returncode == 0, res.stdout
    assert "note: age 48.0" in res.stdout
    assert "(not from mtime)" in res.stdout
    assert "status: PLANNED" in res.stdout
    assert unit.target.is_dir()


def test_age_comes_from_created_at_not_from_mtime(run, scratch):
    """A freshly written manifest with an old `created_at` still passes."""
    unit = scratch.make_run(created_at=hours_ago(100))
    assert unit.manifest.stat().st_mtime > 0
    res = run(SCRIPT, "--root", scratch.root, "--older-than-hours", "24")
    assert res.returncode == 0, res.stdout
    assert "status: PLANNED" in res.stdout


# --- mismatch notes --------------------------------------------------------

def test_entries_listed_in_the_manifest_but_absent_on_disk(run, scratch):
    scratch.make_run(created=["copy-1", "notes.md", "ghost"])
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert ("note: mismatch note: entries listed in the manifest but absent on "
            "disk: ghost" in res.stdout)


def test_size_disagreement_is_a_note_not_a_refusal(run, scratch):
    scratch.make_run(size_bytes=10_000_000)
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert "note: mismatch note: manifest says 9.5 MiB, on disk " in res.stdout
    assert "status: PLANNED" in res.stdout


def test_zero_size_declaration_still_gets_a_note(run, scratch):
    """A declared 0 is compared like any other value, not treated as absent."""
    scratch.make_run(size_bytes=0)
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert "note: mismatch note: manifest says 0 B, on disk " in res.stdout
    assert "status: PLANNED" in res.stdout


def test_empty_target_against_a_nonzero_declaration_gets_a_note(run, scratch):
    """The mirror case: nothing on disk, a non-zero declaration."""
    scratch.make_run(contents={}, size_bytes=10_000_000,
                     manifest_at=scratch.sidecar_path("sample-run"))
    res = run(SCRIPT, "--root", scratch.root)
    assert res.returncode == 0, res.stdout
    assert "note: mismatch note: manifest says 9.5 MiB, on disk 0 B" in res.stdout
    assert "status: PLANNED" in res.stdout


# --- deletion refusals -----------------------------------------------------

def test_target_that_is_a_regular_file_is_refused(run, scratch):
    unit = scratch.make_run(create_target=False, contents={}, size_bytes=0,
                            manifest_at=scratch.sidecar_path("sample-run"))
    unit.target.parent.mkdir(parents=True, exist_ok=True)
    unit.target.write_text("not a directory\n", encoding="utf-8")
    res = run(SCRIPT, "--root", scratch.root, "--confirm")
    assert res.returncode == 1, res.stdout
    assert "FAIL deletion: target is not a directory (mode " in res.stdout
    assert "summary: deleted=0 refused=1 already-absent=0 skipped=0" in res.stdout
    assert unit.target.is_file()


def test_a_refused_unit_does_not_stop_the_others(run, scratch):
    good = scratch.make_run("run-good")
    bad = scratch.make_run("run-bad", run_id="wrong-id")
    res = run(SCRIPT, "--root", scratch.root, "--confirm")
    assert res.returncode == 1, res.stdout
    assert "summary: deleted=1 refused=1 already-absent=0 skipped=0" in res.stdout
    assert not good.target.exists()
    assert bad.target.is_dir()
