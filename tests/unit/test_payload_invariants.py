"""Invariants over the shipped payload read as FILES rather than as CLIs.

Everything else in `tests/unit/` drives a script through a subprocess and
pins its observable behavior. Claims that are not behavior of any single
script but properties of the payload as a whole are enforced here instead.
The three it started from are the claims of the 0.2.0 observability work:

* **No network primitive exists in the payload.** The gate is one command
  over `templates/*.py`, so it is checked over the whole directory here.
  `test_trace.py` and `test_rollup.py` already assert it on their own
  script; neither of them can fail when a network import appears in a
  third file.
* **No shell-out that could reach a network.** The constraint names three
  scripts (`trace.py`, `rollup.py`, `recount.py`) and exempts the two that
  legitimately shell out today (`copy-project.sh`, and `deleted-lines.py`
  via git). `recount.py` is the one of the three that had no such
  assertion anywhere.
* **The SKILL.md stage sentences.** Every stage of the stage machine
  carries an observability instruction; the skill spells them out as ten
  `**With observability on**` sentences, one per stage 0-9. A stage that
  silently loses its sentence is a hole in the trace that no script-level
  test can see. A stage body lives either inline in the router or in a
  `references/stage-*.md` file beside it, and the sweep covers both.

All three read the shipped files from `scripts_dir` / the repository root,
so they hold for a copy of the payload (`CRITIC_LEDGER_SCRIPTS_DIR`)
exactly as they hold for the tree the suite lives in.
"""

from __future__ import annotations

import ast
import re

import pytest

from conftest import REPO_ROOT

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

# The three scripts under the no-subprocess constraint.
NO_SUBPROCESS_SCRIPTS = ("trace.py", "rollup.py", "recount.py")

# The two exempted by name, so this file records the exemption
# instead of leaving it as an unexplained absence.
SHELL_OUT_EXEMPT = ("deleted-lines.py",)

SKILL_MD = REPO_ROOT / "skills" / "critic-ledger" / "SKILL.md"
REFERENCES_DIR = REPO_ROOT / "skills" / "critic-ledger" / "references"
# The stage files whose bodies have already left the router. A literal these
# tests protect is asserted against the file that now HOLDS it, never against
# a union scan that a single stray copy elsewhere would satisfy.
STAGE_0 = REFERENCES_DIR / "stage-0-prerequisites.md"
STAGE_1 = REFERENCES_DIR / "stage-1-run-folder.md"
STAGE_2 = REFERENCES_DIR / "stage-2-scope-and-lenses.md"
STAGES_3_5 = REFERENCES_DIR / "stages-3-5-critics-salvage-layout.md"
STAGE_6 = REFERENCES_DIR / "stage-6-adjudication.md"
STAGE_7 = REFERENCES_DIR / "stage-7-fix-batches.md"
STAGE_8 = REFERENCES_DIR / "stage-8-verification.md"
STAGE_9 = REFERENCES_DIR / "stage-9-closure.md"
# The full description of every template and script, which left the router
# together with the stage bodies; the router keeps a one-line label per file.
TEMPLATES_REF = REFERENCES_DIR / "templates-and-scripts.md"
# Principles 1-3 and 5-7 of the contract in full: the router keeps their
# headline sentences, principle 4 and the severity taxonomy.
CONTRACT_LONG_FORM = REFERENCES_DIR / "contract-long-form.md"
OBSERVABILITY_MARKER = "**With observability on**"
STAGE_MACHINE_HEADING = "## Stage machine"
STAGE_START_RE = re.compile(r"^(\d+)\. \*\*")
# The binding heading form of a stage opener in a `references/stage*.md`
# file: `## Stage N — Name`, em dash U+2014, one heading per stage (three
# of them inside `stages-3-5-critics-salvage-layout.md`).
STAGE_FILE_HEADING_RE = re.compile(r"^## Stage (\d+) — ")


# --- the network gate over the whole payload -------------------------------


def test_no_template_script_imports_a_network_primitive(scripts_dir):
    """The network gate over `templates/*.py`, as one sweep."""
    offenders = []
    for path in sorted(scripts_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        offenders += [
            f"{path.name}: {token}" for token in NETWORK_TOKENS if token in text
        ]
    assert offenders == []


def test_the_gate_covers_every_python_file_that_ships(scripts_dir):
    """The gate is only worth its exit code if it sees the whole directory.

    A new script added to `templates/` without a test of its own is still
    read by the sweep above; this pins that the sweep is not silently
    matching nothing, and that it reaches the three named scripts.
    """
    seen = {path.name for path in scripts_dir.glob("*.py")}
    assert seen >= {
        "check-frontmatter.py",
        "cleanup-scratchpad.py",
        "deleted-lines.py",
        "recount.py",
        "rollup.py",
        "set-cell.py",
        "trace.py",
        "transcribe.py",
        "validate-report.py",
    }


# --- no shell-out from the three named scripts -----------------------------


@pytest.mark.parametrize("script", NO_SUBPROCESS_SCRIPTS)
def test_the_named_scripts_contain_no_subprocess_at_all(scripts_dir, script):
    """A normative constraint on two, a preserved property of the third."""
    text = (scripts_dir / script).read_text(encoding="utf-8")
    assert "subprocess" not in text
    for shell_exec in ("os.system", "os.popen", "os.execv", "os.spawn"):
        assert shell_exec not in text, shell_exec


@pytest.mark.parametrize("script", SHELL_OUT_EXEMPT)
def test_the_exempt_script_still_shells_out_only_through_a_fixed_argv(
    scripts_dir, script
):
    """The exemption is for git through a list argv, never through a shell."""
    text = (scripts_dir / script).read_text(encoding="utf-8")
    assert "import subprocess" in text
    assert "shell=True" not in text


# --- SKILL.md: one observability sentence per stage -------------------------


def stage_blocks() -> list[tuple[int, list[str]]]:
    """The stage machine, split into (stage number, its lines).

    The union of the two places a stage body may live: still inline in the
    router's `## Stage machine` section, or in a `references/stage*.md`
    file beside it. Neither half is allowed to claim the same stage number
    as the other — a stage found twice fails loudly instead of being
    counted twice.
    """
    blocks: list[tuple[int, list[str]]] = []
    lines = SKILL_MD.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line == STAGE_MACHINE_HEADING)
    end = next(
        (
            i
            for i, line in enumerate(lines[start + 1 :], start + 1)
            if line.startswith("## ")
        ),
        len(lines),
    )
    for i in range(start + 1, end):
        match = STAGE_START_RE.match(lines[i])
        if match:
            # The stage's own opening line belongs to its body: a marker
            # written there must count for that stage, not vanish.
            blocks.append((int(match.group(1)), [lines[i]]))
        elif blocks:
            blocks[-1][1].append(lines[i])
    if REFERENCES_DIR.is_dir():
        for path in sorted(REFERENCES_DIR.glob("stage*.md")):
            body: list[str] | None = None
            for line in path.read_text(encoding="utf-8").splitlines():
                match = STAGE_FILE_HEADING_RE.match(line)
                if match:
                    # The heading is that stage's opening line, exactly as
                    # the numbered opener is in the router.
                    body = [line]
                    blocks.append((int(match.group(1)), body))
                elif body is not None:
                    body.append(line)
    numbers = [number for number, _ in blocks]
    assert len(numbers) == len(set(numbers)), f"stage claimed twice: {sorted(numbers)}"
    return sorted(blocks, key=lambda block: block[0])


def test_the_stage_machine_has_ten_stages_numbered_zero_through_nine():
    """Stages 0-9, in order, with nothing renumbered or dropped."""
    assert [number for number, _ in stage_blocks()] == list(range(10))


def test_every_stage_carries_exactly_one_observability_sentence():
    """Ten observability markers, one per stage — not ten anywhere in the file."""
    per_stage = {
        number: sum(line.count(OBSERVABILITY_MARKER) for line in body)
        for number, body in stage_blocks()
    }
    assert per_stage == dict.fromkeys(range(10), 1)


def test_the_file_carries_no_observability_marker_outside_the_stage_machine():
    """The count over the router and its references is ten, and all ten are
    stage sentences."""
    texts = [SKILL_MD.read_text(encoding="utf-8")]
    if REFERENCES_DIR.is_dir():
        texts += [
            path.read_text(encoding="utf-8")
            for path in sorted(REFERENCES_DIR.glob("*.md"))
        ]
    total = sum(text.count(OBSERVABILITY_MARKER) for text in texts)
    assert total == 10
    inside = sum(
        line.count(OBSERVABILITY_MARKER)
        for _, body in stage_blocks()
        for line in body
    )
    assert inside == 10


# --- every shipped template is named in the Templates section ---------------
#
# The stage machine addresses a template by its full substituted path, and the
# Templates section is where a reader learns what each one IS. A template that
# ships without an entry there is invisible: nobody reading the skill knows it
# exists, and nobody editing the skill knows it has to be kept in step. The
# sweep is over the directory, so it covers a template added by a later batch
# without any edit here.


def templates_section() -> str:
    """The Templates section, which is now a file of its own in full."""
    return TEMPLATES_REF.read_text(encoding="utf-8")


def test_every_shipped_template_is_named_in_the_templates_section(scripts_dir):
    section = templates_section()
    shipped = sorted(p.name for p in scripts_dir.iterdir() if p.is_file())
    assert shipped, "no templates found — wrong directory?"
    assert [name for name in shipped if f"templates/{name}" not in section] == []


def test_the_round_contract_template_ships_and_is_self_contained(scripts_dir):
    """The round-contract template: it exists, and it carries its two
    signature blocks.

    The two blocks are what the stage-0 gate checks for, and the two numbers
    in it are marked as OURS rather than borrowed — the file has to say so
    itself, because it is copied out of the plugin and read on its own.
    """
    text = (scripts_dir / "round-contract.md").read_text(encoding="utf-8")
    assert text.count("(OWNER SIGNS)") == 2
    assert text.count("Owner signature:") == 2
    assert "out-of-scope-by-contract" in text
    assert "400 LINES" in text
    assert "HALF AN HOUR" in text
    assert "Amendment" in text


# The two shapes in which a shipped file claims that some content LIVES in
# the router: `… of SKILL.md` and `see SKILL.md for …`. Most of the skill's
# body now lives in `references/*.md`, so such a claim sends its reader to a
# file that no longer holds the thing. Navigational prose about the router
# itself ("SKILL.md is a router", "the router SKILL.md carries …") is not a
# content-location claim and is deliberately not matched.
CONTENT_LOCATION_SHAPES = (
    re.compile(r"of SKILL\.md", re.IGNORECASE),
    re.compile(r"see SKILL\.md for", re.IGNORECASE),
)


def test_no_shipped_pointer_claims_moved_content_still_lives_in_the_router():
    """Templates and agent definitions may not locate content in the router.

    These files are read on their own, away from the skill, so a stale
    pointer in one of them is invisible from inside the skill: nothing else
    here re-reads a prompt template to see where it sends its reader.
    """
    markdown = [
        path
        for directory in (TEMPLATES_DIR, AGENTS_DIR)
        for path in sorted(directory.rglob("*.md"))
    ]
    assert markdown, "no templates or agent definitions found — wrong directory?"
    offenders = []
    for path in markdown:
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if any(shape.search(line) for shape in CONTENT_LOCATION_SHAPES):
                offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert offenders == []


# --- the pipeline-hygiene sentences of 0.3.0 -------------------------------
#
# Each of these is a rule the skill states in prose and nothing executes, so
# the only thing standing between the rule and a silent deletion is a grep.
# They are asserted where the rule LIVES, not where it is summarized: the
# fixer's premise step in both the agent definition and the prompt, the
# verifier's blindness in both of its own two files, and the three-outcome
# back channel in every one of the four places that names the vocabulary —
# a two-outcome sentence left standing anywhere contradicts the others.

AGENTS_DIR = REPO_ROOT / "agents"
FIXER_AGENT = AGENTS_DIR / "fixer.md"
VERIFIER_AGENT = AGENTS_DIR / "verifier.md"
PREMISE_OUTCOME = "premise-not-found"


def text_of(path):
    return path.read_text(encoding="utf-8")


def flat(path):
    """The file's text, lower-cased with its line wrapping collapsed.

    A rule these tests protect is a SENTENCE, and a sentence in these files
    is wrapped at 78 columns: matching the raw text would make a reflow
    look like a deleted rule. Case is folded for the same reason — the
    files shout some of these clauses and not others.
    """
    return re.sub(r"\s+", " ", text_of(path)).lower()


def test_the_fixer_reproduces_the_defect_before_editing(scripts_dir):
    """Stated in the agent definition and in the prompt that spawns it."""
    agent = flat(FIXER_AGENT)
    assert "reproduce the defect before editing" in agent
    assert "stop if the premise does not hold" in agent
    prompt = text_of(scripts_dir / "fixer-prompt.md")
    assert "REPRODUCE THE DEFECT BEFORE YOU EDIT" in prompt


def test_the_back_channel_has_three_outcomes_everywhere_it_is_named(scripts_dir):
    """A vocabulary that differs between the fixer's texts is no vocabulary."""
    for path in (
        FIXER_AGENT,
        scripts_dir / "fixer-prompt.md",
        STAGE_7,
        TEMPLATES_REF,
    ):
        body = text_of(path)
        assert PREMISE_OUTCOME in body, path.name
        assert "criterion-unworkable" in body, path.name
    prompt = text_of(scripts_dir / "fixer-prompt.md")
    assert "exactly one per id, and there are exactly three" in prompt
    assert "no third option" not in prompt


def test_the_second_return_of_an_id_is_never_a_third_fix(scripts_dir):
    """The limit is counted per id and both non-terminal outcomes share it."""
    stage_seven = flat(STAGE_7)
    assert "at most twice" in stage_seven
    assert "returned:<n>" in stage_seven
    assert "nominating a blocker is banned outright" in stage_seven


def test_the_verifier_is_not_shown_the_fixers_justification(scripts_dir):
    """Stated in the agent definition and in the prompt template."""
    assert "not shown the fixer's justification" in flat(VERIFIER_AGENT)
    prompt = text_of(scripts_dir / "verifier-prompt.md")
    assert "WHAT YOU ARE DELIBERATELY NOT GIVEN" in prompt
    assert "would a fresh critic still file here?" in prompt


def test_the_verifier_prompt_carries_no_placeholder_for_a_fixer_report(
    scripts_dir,
):
    """The rule is mechanical here: a placeholder is what would break it."""
    placeholders = set(
        re.findall(r"\{([a-z_]+)\}", text_of(scripts_dir / "verifier-prompt.md"))
    )
    assert placeholders
    assert [name for name in placeholders if "fixer" in name] == []


def test_a_number_matching_is_not_a_mechanism_matching(scripts_dir):
    """Stated in the verifier's mandate and in its definition."""
    for path in (VERIFIER_AGENT, scripts_dir / "verifier-prompt.md"):
        body = flat(path)
        assert "mechanism matching" in body, path.name
        assert "direction of a rule" in body, path.name


def test_the_clean_pass_qualification_and_its_seniority_are_stated():
    """A qualified pair, any terminal close, and seniority over the 20."""
    stage_nine = flat(STAGE_9)
    assert "the pair is qualified where the round ever had a marked row" in (
        stage_nine
    )
    assert "closed by the pass's own hands" in stage_nine
    assert "the qualification is senior to that threshold" in stage_nine


def test_the_sustained_rate_is_never_read_alone():
    """The framing tightening is a PAIRED condition, said in words."""
    stage_nine = flat(STAGE_9)
    assert "per-lens sustained rate" in stage_nine
    assert "the condition is paired" in stage_nine
    assert "shelf share" in stage_nine


def test_the_security_recheck_is_made_by_another_actor_and_blinded():
    """The owner's own ruling does not exempt it, and the re-checker is blind.

    The re-check is armed at stage 6 and its no-rationale rule is restated at
    stage 9, so the two halves are asserted against the two files that hold
    them rather than against one union scan.
    """
    stage_six = flat(STAGE_6)
    assert "the re-checker is blinded" in stage_six
    assert "other than the one that ruled" in stage_six
    assert "the ruling actor of record is the owner" in stage_six
    assert "never the ruling's rationale" in flat(STAGE_9)


def test_the_first_run_ignore_entry_waits_for_the_users_word():
    """Stage 1(a): consent, or fail-closed — and silence is not consent."""
    stage_one = flat(STAGE_1)
    assert "explicit word, never silently" in stage_one
    assert "silence is not consent" in stage_one
    assert "the run folder is not created" in stage_one


def test_degraded_snapshots_are_named_and_live_inside_the_run_folder():
    """The one piece of the snapshot rule in this release, with its path."""
    stage_zero = text_of(STAGE_0)
    assert ".critic-ledger/<run>/fix-batch-<n>-{before,after}/" in stage_zero
    assert "BANNED" in stage_zero
    assert "never reused and never overwritten" in flat(STAGE_0)


def test_security_is_an_example_lens_in_both_modes():
    """The directive's smallest item, and the easiest to lose in a table edit."""
    skill = text_of(SKILL_MD)
    row = next(
        line for line in skill.splitlines() if line.startswith("| Example lenses")
    )
    assert row.count("security") == 2


# --- 0.3.0 zones: one vocabulary across the payload ------------------------
# The zone axis lives in four files at once — the contract template declares
# the map, the ledger template declares the cell and its one mechanical
# consequence, the skill routes rows by it, and `recount.py` enforces it.
# A literal that drifts in ONE of them is a rule that silently stops
# applying, and no script-level test can see that from inside one file.

TEMPLATES_DIR = REPO_ROOT / "skills" / "critic-ledger" / "templates"
LEDGER_TEMPLATE = TEMPLATES_DIR / "ledger.md"
CONTRACT_TEMPLATE = TEMPLATES_DIR / "round-contract.md"
RECOUNT_SCRIPT = TEMPLATES_DIR / "recount.py"

# The seven canonical terminal statuses. A status the recount closes on and
# no shipped prose names is a rule nobody can follow.
TERMINAL_STATUSES = (
    "verified-landed",
    "refuted-with-reason",
    "accepted-residue",
    "refused-user-signed",
    "out-of-scope-by-contract",
    "frozen-carried",
    "logged-no-action",
)
ZONE_LITERALS = ("Z1", "Z2", "Z3")


@pytest.mark.parametrize("status", TERMINAL_STATUSES)
def test_every_terminal_status_is_named_in_the_skill_and_the_template(status):
    """The script's vocabulary and the shipped paper's are the same list."""
    for path in (SKILL_MD, CONTRACT_LONG_FORM, LEDGER_TEMPLATE, RECOUNT_SCRIPT):
        assert status in text_of(path), f"{status} missing from {path.name}"


@pytest.mark.parametrize("zone", ZONE_LITERALS)
def test_the_three_zones_are_named_wherever_the_axis_is_used(zone):
    # The axis is used at stages 2, 6 and 8; the router names no zone at all
    # now, so it is no longer one of the places the axis is USED.
    for path in (
        STAGE_2,
        STAGE_6,
        STAGE_8,
        LEDGER_TEMPLATE,
        CONTRACT_TEMPLATE,
        RECOUNT_SCRIPT,
    ):
        assert zone in text_of(path), f"{zone} missing from {path.name}"


def test_no_fourth_zone_was_invented():
    """Three zones, and the map's vocabulary is closed.

    `Z0` is deliberately NOT in the stray list: the id contract's own
    alphabet `[A-Z0-9]` carries that pair of characters in three of these
    files, and a check that fires on it would be switched off within a week.
    """
    for path in (
        SKILL_MD,
        CONTRACT_LONG_FORM,
        LEDGER_TEMPLATE,
        CONTRACT_TEMPLATE,
        RECOUNT_SCRIPT,
    ):
        text = text_of(path)
        for stray in ("Z4", "Z5", "Z6"):
            assert stray not in text, f"{stray} in {path.name}"
    # And the script's own vocabulary is the same three, in one tuple.
    assert 'ZONES = (ZONE_MECHANICAL, ZONE_NORMATIVE, ZONE_INFORMATIVE)' in (
        text_of(RECOUNT_SCRIPT)
    )


def test_the_zone_never_relaxes_the_fresh_verifier_rule():
    """A verifier is new on every pass, whatever the zone: the source text
    allowed a continuation of an earlier pass, this release does not."""
    stage_eight = flat(STAGE_8)
    assert "a verifier is new on every pass whatever the zone" in stage_eight
    assert "paper and closure, never independence" in stage_eight
    assert "no zone makes you a continuation of an earlier pass" in flat(
        VERIFIER_AGENT,
    )


def test_the_zone_never_lowers_a_severity():
    """A blocker in Z3 is a defect of the MAP, never a cheaper process."""
    for path in (STAGE_6, LEDGER_TEMPLATE):
        assert "the zone map was wrong" in flat(path)
    assert "the zone tag was wrong" in flat(CONTRACT_TEMPLATE)


def test_the_deleted_line_prepass_stays_full_in_every_zone():
    """The zone narrows the JUDGMENT, never the input the verifier judges."""
    assert "still emits the full list in every zone" in flat(STAGE_8)
    assert "still emits the full list for every zone" in flat(CONTRACT_TEMPLATE)
    assert "emits the full list for every zone" in flat(LEDGER_TEMPLATE)


# --- 0.3.0: the standalone sentence rules ----------------------------------
# Each of these is a one- or two-sentence rule whose whole existence IS its
# wording: nothing executes it, so a reflow that swallows it, or a later
# edit that "tightens" it away, is invisible to every other test here.
# They are matched against `flat()` — the files wrap at 78 columns, so the
# raw text of a sentence is broken across lines by construction.

VERIFIER_PROMPT = TEMPLATES_DIR / "verifier-prompt.md"
FIXER_PROMPT = TEMPLATES_DIR / "fixer-prompt.md"


def test_stage_nine_closes_the_ledger_state_header():
    """`ROUND CLOSABLE` is what moves the header into `closed`.

    The literal is checked in BOTH shipped files, because the field's
    vocabulary lives in the template and the duty to write it in the skill;
    either one alone leaves a value nobody sets or a rule with no field.
    """
    for path in (STAGE_9, LEDGER_TEMPLATE):
        assert "ledger state: closed" in flat(path), path.name
    stage_nine = flat(STAGE_9)
    assert "`round closable` is what moves the header into the closed state"\
        in stage_nine
    assert "a calendar-valid iso date" in stage_nine
    assert "\"awaiting signature\" is not closed" in stage_nine
    # And the template still declares all three values of the field.
    template = flat(LEDGER_TEMPLATE)
    assert "{open | closed <iso-date> | frozen (superseded-by-rewrite," in (
        template
    )


def test_old_run_addresses_may_be_relocated_by_the_project():
    """Both lawful outcomes, and no address of the plugin's own repo."""
    stage_one = flat(STAGE_1)
    assert "are not moved automatically" in stage_one
    assert "a project may relocate them itself" in stage_one
    assert "the new address governs new runs" in stage_one
    # The unconditional promise the shipped text used to make, and the
    # out-of-tree address that must never reach the product.
    assert "are not migrated" not in stage_one
    assert "are not migrated" not in flat(SKILL_MD)
    assert ".critic-ledger/legacy" not in text_of(SKILL_MD)
    for path in sorted(REFERENCES_DIR.glob("*.md")):
        assert ".critic-ledger/legacy" not in text_of(path), path.name


def test_a_do_not_touch_fence_traces_to_the_batchs_own_plan():
    """An edit-scope fence with no collision note is an orchestrator bug."""
    stage_seven = flat(STAGE_7)
    assert "a do-not-touch fence in that prompt is traceable to this batch's"\
        " plan" in stage_seven
    assert "the plan of the same batch carries the collision note" in stage_seven
    assert "lifted before the fixer is spawned" in stage_seven


# The pointwise sentences below are asserted against the file that now HOLDS
# each of them — the stage whose body carries it.
# `probe-to-criterion` is named in two stages, so its literal is asserted once
# per stage rather than once per file.
STANDALONE_LITERALS = (
    (STAGE_6, "A design fork goes to the owner: it is never closed by an"
              " adjudication verdict."),
    (STAGE_6, "The orchestrator's own probe run before adjudication is"
              " named `probe-to-criterion`: the probe becomes a class-L1"
              " criterion, and the verifier re-executes it live."),
    (STAGE_8, "A class-L1 criterion born as a `probe-to-criterion` is"
              " re-executed live by the verifier, never read off the"
              " fixer's report"),
    (STAGES_3_5, "Verbatim salvage outranks local formatting and lint hooks:"
                 " where the environment physically prevents writing the text,"
                 " writing past the hook is part of the stage, not"
                 " improvisation — except a hook that blocks on CONTENT (a"
                 " secret or credential scanner), which is never written past:"
                 " its block is raised as a finding of the round."),
    (STAGES_3_5, "An agent that died on a server error has no report:"
                 " fragments are never salvaged, the stage is respawned with a"
                 " fresh actor, and one line of fact goes into the ledger."),
    (STAGE_6, "Before adjudicating a new refutation the orchestrator checks"
              " the run's own `precedents.md`: the file is an INPUT"
              " document of the round, not only an output."),
    (VERIFIER_PROMPT, "Deviations from the pass instruction (if any) and"
                      " why."),
)


@pytest.mark.parametrize(("path", "literal"), STANDALONE_LITERALS)
def test_the_pointwise_insertions_are_present(path, literal):
    assert literal.lower() in flat(path), f"{literal[:40]}… missing"


def test_probe_to_criterion_is_named_in_both_stage_six_and_stage_eight():
    """The whole content of the rule is that ONE name spans the two stages.

    The two stage bodies are two FILES now, so the slice that used to carve
    them out of the router is the file boundary itself.
    """
    assert "probe-to-criterion" in text_of(STAGE_6)
    assert "probe-to-criterion" in text_of(STAGE_8)


def test_the_verifier_prompts_deviation_field_is_not_optional():
    """A report FIELD, not a section left to the agent's initiative."""
    prompt = flat(VERIFIER_PROMPT)
    assert "one further field is mandatory and is not a section left to your"\
        " initiative" in prompt
    assert "write it even when it is empty" in prompt


# --- four more standalone rules of the same kind ---------------------------
# Each of the four is a SENTENCE in shipped paper, spread across two to four
# files at once. A rule that survives in one file and is reworded out of the
# others has silently stopped applying, and nothing script-level can see it.

PASSES_HEADER_PREFIX = "| # | pass (scope)"
NOTICED_BLOCK = "NOTICED OUTSIDE BATCH"
ID_OUTCOMES = ("criterion-unworkable", PREMISE_OUTCOME)


def passes_header_cells() -> list[str]:
    """The shipped passes table's header, cell by cell."""
    header = next(
        line
        for line in text_of(LEDGER_TEMPLATE).splitlines()
        if line.startswith(PASSES_HEADER_PREFIX)
    )
    return [cell.strip() for cell in header.strip().strip("|").split("|")]


def test_the_lens_split_verification_pass_is_named_where_it_is_used():
    """The mode gets a name, in stage 8 and in the prompt that carries it."""
    assert "lens-split verification pass" in text_of(STAGE_8)
    assert "lens-split verification pass" in text_of(VERIFIER_PROMPT)


def test_the_lens_scope_placeholder_exists_and_is_named_in_templates():
    """A mode carried by a placeholder is real only if the prompt has it."""
    placeholders = set(re.findall(r"\{([a-z_]+)\}", text_of(VERIFIER_PROMPT)))
    assert "lens_scope" in placeholders
    # Named where the mode is defined (stage 8) and where the template that
    # carries the placeholder is described (the templates reference).
    assert "{lens_scope}" in text_of(STAGE_8)
    assert "{lens_scope}" in text_of(TEMPLATES_REF)


def test_a_lens_split_pass_is_full_scope_only_without_overlap_or_hole():
    """The union rule is what stops a split from losing an id."""
    stage_eight = flat(STAGE_8)
    assert "with no overlap and no hole" in stage_eight
    assert "the freshness rule above applies to every one of them by name" in (
        stage_eight
    )


def test_the_passes_table_carries_the_verifier_count_column():
    """The count is a column, and it moves no cell any reader addresses."""
    cells = passes_header_cells()
    assert "verifiers" in cells
    # `new findings` keeps index 3 (the recount's positional fallback) and
    # `started`/`ended` keep their place as the last two columns.
    assert cells.index("new findings") == 3
    assert cells[-2:] == ["started", "ended"]
    assert "`verifiers` = how many verifiers the pass had" in text_of(
        LEDGER_TEMPLATE
    )


def test_a_deduplicated_row_reaches_the_verifier_with_the_full_criterion():
    """The briefing carries the primary row's criterion, not a pointer."""
    assert "=<primary-id>" in text_of(STAGE_8)
    assert "the primary row's criterion substituted in full" in flat(STAGE_8)
    prompt = text_of(VERIFIER_PROMPT)
    assert "=<primary-id>" in prompt
    assert "substituted IN FULL" in prompt


def test_the_full_criterion_rule_is_not_a_property_of_the_split_mode():
    """A rule about the verifier's canon, so it holds on an unsplit pass."""
    assert "it holds on an unsplit pass too" in flat(STAGE_8)


def test_executing_a_criterion_is_the_orchestrators_duty_not_the_fixers():
    """Named executor, named moment, and the fixer's paired sentence."""
    stage_seven = flat(STAGE_7)
    assert "read-back" in stage_seven
    assert (
        "a criterion that requires execution is executed by the orchestrator,"
        " never by the fixer" in stage_seven
    )
    assert "critic-ledger:verifier" in stage_seven
    assert "between the fixer's report and the batch commit" in stage_seven
    assert "is not closed by that commit" in stage_seven
    assert (
        "a criterion that requires execution is not yours to satisfy"
        in flat(FIXER_AGENT)
    )


def test_the_verifier_definition_carries_the_stage_seven_read_back():
    """A second, narrow duty at its own moment, distinct from stage 8."""
    verifier = flat(VERIFIER_AGENT)
    assert "read-back" in verifier
    assert "pre-commit read-back of stage 7" in verifier
    assert "no per-id verdicts and you walk no deleted lines" in verifier


def test_the_read_only_constraint_carves_out_the_read_backs_one_command():
    """The bullet that forbids writing says what the read-back may run."""
    assert (
        "the criterion's one command — a tool the round declared, or the"
        " probe recorded at adjudication as the criterion — may be executed"
        in flat(VERIFIER_AGENT)
    )


def test_the_noticed_outside_batch_block_is_named_wherever_the_fixer_reads():
    """The fixer's out-of-batch channel exists wherever the fixer reads."""
    for path in (TEMPLATES_REF, STAGE_2, STAGE_7, FIXER_AGENT, FIXER_PROMPT):
        assert NOTICED_BLOCK in text_of(path), path.name


def test_the_noticed_block_is_never_a_fourth_per_id_outcome():
    """The id-outcome vocabulary is untouched by a report block.

    Mechanically: no line that names the block also names an outcome value,
    so the literal cannot have crept into an enumeration of outcomes.
    """
    for path in (TEMPLATES_REF, STAGE_2, STAGE_7, FIXER_AGENT, FIXER_PROMPT):
        for line in text_of(path).splitlines():
            if NOTICED_BLOCK in line:
                clash = [name for name in ID_OUTCOMES if name in line]
                assert clash == [], f"{path.name}: {line}"
    assert "this is a report block, not a per-id outcome" in flat(STAGE_7)


def test_the_noticed_block_routes_to_stage_six_and_never_into_a_batch():
    """Same route as a verifier's new findings, and no shortcut."""
    stage_seven = flat(STAGE_7)
    assert "travel to stage 6 as new findings" in stage_seven
    assert "never straight into the next fix batch" in stage_seven


def test_the_fixer_prompt_carries_the_noticed_prefix_placeholder():
    """The block's id prefix is the orchestrator's, assigned at stage 2."""
    placeholders = set(re.findall(r"\{([a-z_]+)\}", text_of(FIXER_PROMPT)))
    assert "noticed_prefix" in placeholders
    assert "{noticed_prefix}" in text_of(TEMPLATES_REF)


# --- the shared project copy and the residue-scoped second pass ------------
# Both are rules that shipped paper states and no script enforces, so only
# their wording can be pinned — and for the copy the wording is what tells
# the orchestrator that the copy it just made is a SHARED one.

COPY_SCRIPT = TEMPLATES_DIR / "copy-project.sh"


def test_stage_two_makes_the_strict_clone_conditional():
    """The clone is gated on git reporting no ignored content."""
    stage_two = flat(STAGE_2)
    assert "the clone runs only when git reports no ignored content under"\
        " the project root" in stage_two
    assert "fail-closed on both conditions" in stage_two
    assert "has no opt-out flag" in stage_two


def test_stage_two_no_longer_promises_a_copy_per_critic_unconditionally():
    """The shared copy is the ordinary case, and the text says so."""
    stage_two = flat(STAGE_2)
    assert "one copy per critic is the rare case and one shared copy per"\
        " round the ordinary one" in stage_two
    # The unconditional promise the shipped text used to make.
    assert "one copy per critic when reflink works" not in stage_two
    assert "one copy per critic when reflink works" not in flat(SKILL_MD)


def test_stage_two_states_the_run_id_rule_the_script_enforces():
    """A divergent run id makes the copy unremovable at teardown."""
    stage_two = flat(STAGE_2)
    assert "must equal the basename of `--dest`" in stage_two
    assert "condition 7" in stage_two


def test_the_copy_script_gates_the_clone_and_refuses_a_divergent_run_id():
    """The two behaviors, read off the shipped script itself."""
    script = text_of(COPY_SCRIPT)
    assert "--others --ignored --exclude-standard --directory" in script
    assert "class=git-ignored" in script
    assert "class=git-preflight-failed" in script
    assert "--run-id must equal the basename of --dest" in script
    # The escalation of the disclosure sweep: never a `die` that leaves a
    # half-cleaned copy behind.
    assert "cannot remove $rel from the copy even after chmod -R u+w" in script
    assert 'die "cannot remove $rel from the copy"' not in script


def test_the_copy_script_offers_no_way_to_force_the_clone():
    """An opt-out flag would make the gate decorative."""
    script = text_of(COPY_SCRIPT)
    for flag in ("--fast-clone", "--force-clone", "--no-preflight",
                 "--skip-preflight"):
        assert flag not in script, flag


def test_stage_nine_names_the_residue_scoped_second_pass():
    """The third mode of the second verification pass.

    The stage-9 body is a file of its own now, so the slice that used to
    carve it out of the router is the file boundary itself.
    """
    assert "`residue-scoped second pass`" in flat(STAGE_9)


def test_the_residue_scoped_pass_lists_all_three_conditions():
    """Three conditions, and the binary rule back if any is missing."""
    stage_nine = flat(STAGE_9)
    assert "only when all three conditions hold at once" in stage_nine
    assert "(a) pass 1 was full-scope in the sense of stage 8" in stage_nine
    assert "(b) pass 1 returned 0 not landed on the round's original ids"\
        in stage_nine
    assert "(c) an explicit owner signature exists for this round, written"\
        " into the ledger verbatim" in stage_nine
    assert "absence of any one of the three returns the binary rule above"\
        in stage_nine


def test_the_residue_scoped_pass_is_never_narrowed_without_a_signature():
    """A right, not a default — and no other actor may grant it."""
    stage_nine = flat(STAGE_9)
    assert "the narrowing is a right, not a default" in stage_nine
    assert "without the owner's signature in the ledger the second pass is"\
        " executed in full" in stage_nine
    assert "no other actor may grant the narrowing" in stage_nine


# --- one finding-id contract across the payload ----------------------------
#
# The finding-id pattern is a CONTRACT, not a local convenience: an id the
# recount accepts and the rollup silently drops is a divergence nobody sees
# until a printed number is wrong, and it has already happened twice — once
# in `transcribe.py`, once in `rollup.py` and `trace.py` together. Nothing
# executes a contract that lives as five separate literals, so this is the
# gate: the pattern is read out of the SOURCE TEXT of each script (the
# scripts are never imported — they are CLIs, and importing them would run
# their argument handling) and the bodies must be identical.
#
# `set-cell.py` is read for the same reason the network sweep reads every
# file: it carries no id pattern today — it compares the id cell literally —
# and if a later edit gives it one, the absence assertion below fails and
# the new literal has to join the contract rather than start a sixth copy.
#
# `validate-report.py` is the ONE deliberate exception, and it is asserted AS
# an exception: its narrower single-segment form, plus the comment that says
# so. An exception with no comment is indistinguishable from a drift, which
# is the whole defect this test exists to catch.

# The module-level constant each script names its id pattern with; `None`
# where the script carries no id pattern at all.
ID_PATTERN_CONSTANT = {
    "recount.py": "ID_RE",
    "transcribe.py": "ID",
    "rollup.py": "ID_RE",
    "trace.py": "FINDING_ID_RE",
    "set-cell.py": None,
}
# The documented extraction: a module-level assignment of that constant to a
# raw string, bare or wrapped in `re.compile(`, the pattern being the first
# double-quoted raw literal on the line.
ID_ASSIGNMENT_TEMPLATE = r'^{name} = (?:re\.compile\()?r"([^"]*)"'
# The character class every id pattern in this payload is built from. Its
# absence is what "carries no id pattern" means mechanically.
ID_ALPHABET = "[A-Za-z][A-Za-z0-9]"
# The narrower form `validate-report.py` documents, and the sentence that
# documents it.
NARROWER_ID_BODY = r"([A-Za-z][A-Za-z0-9]*)-(\d+)"
NARROWER_IS_DELIBERATE = "The narrower form is deliberate here"
NARROWER_NAMES_THE_COMPOSITE = (
    "additionally accepts a dash-joined composite prefix (`V-CIT-1`)"
)
# The SECOND literal that states the same contract: the `=<primary-id>`
# pointer a duplicate row carries in its criterion cell. `recount.py` reads
# it behind the closure gate and `rollup.py` reads it for its own count, so a
# widening applied to one and not the other makes the two disagree about one
# cell — which is how this divergence recurred after the id patterns were
# aligned.
DUPLICATE_POINTER_CONSTANT = "DUPLICATE_OF_RE"
DUPLICATE_POINTER_SCRIPTS = ("recount.py", "rollup.py")
# The same extraction as above, except the raw string may sit on the line
# after `re.compile(` — both scripts write the literal wrapped.
DUPLICATE_ASSIGNMENT_TEMPLATE = r'^{name} = re\.compile\(\s*r"([^"]*)"'


def id_pattern_body(scripts_dir, script: str, constant: str) -> str:
    """The script's id-pattern literal, anchors and `(?P<id>…)` removed.

    The five literals are written in three shapes — anchored (`^…$`), a
    named group (`(?P<id>…)`), and both — so the comparison is over the
    BODY, which is the part that states the contract.
    """
    assignment = re.compile(
        ID_ASSIGNMENT_TEMPLATE.format(name=re.escape(constant)), re.MULTILINE
    )
    found = assignment.findall(text_of(scripts_dir / script))
    assert len(found) == 1, f"{script}: {len(found)} `{constant}` assignments"
    body = found[0]
    body = body.removeprefix("^").removesuffix("$")
    if body.startswith("(?P<id>") and body.endswith(")"):
        body = body[len("(?P<id>") : -1]
    return body


def duplicate_pointer_body(scripts_dir, script: str) -> str:
    r"""The script's `=<primary-id>` pointer literal, verbatim.

    Nothing is stripped here, unlike `id_pattern_body`: the `^=\s*` prefix
    and the capturing group are part of what the two scripts must agree on.
    """
    assignment = re.compile(
        DUPLICATE_ASSIGNMENT_TEMPLATE.format(
            name=re.escape(DUPLICATE_POINTER_CONSTANT)
        ),
        re.MULTILINE,
    )
    found = assignment.findall(text_of(scripts_dir / script))
    assert len(found) == 1, \
        f"{script}: {len(found)} `{DUPLICATE_POINTER_CONSTANT}` assignments"
    return found[0]


def test_the_finding_id_pattern_is_one_contract_across_the_payload(scripts_dir):
    """The five scripts, the documented exception, then the pointer pair."""
    bodies = {}
    for script, constant in ID_PATTERN_CONSTANT.items():
        if constant is None:
            assert ID_ALPHABET not in text_of(scripts_dir / script), script
            continue
        bodies[script] = id_pattern_body(scripts_dir, script, constant)
    # Every script that carries the pattern carries the SAME pattern, and
    # the reference copy is the recount's — it is the closure gate.
    assert set(bodies) == {"recount.py", "transcribe.py", "rollup.py", "trace.py"}
    assert set(bodies.values()) == {bodies["recount.py"]}, bodies
    # And the contract is the composite one, not a single-segment prefix.
    assert bodies["recount.py"] == (
        r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)*-\d+"
    )
    # The one exception, asserted as an exception: narrower, and saying so.
    exception = id_pattern_body(scripts_dir, "validate-report.py", "ID_RE")
    assert exception == NARROWER_ID_BODY
    assert exception != bodies["recount.py"]
    reason = text_of(scripts_dir / "validate-report.py")
    assert NARROWER_IS_DELIBERATE in reason
    assert NARROWER_NAMES_THE_COMPOSITE in reason
    # The same contract in its second literal — the `=<primary-id>` pointer.
    pointers = {
        script: duplicate_pointer_body(scripts_dir, script)
        for script in DUPLICATE_POINTER_SCRIPTS
    }
    assert pointers["recount.py"] == pointers["rollup.py"], pointers
    # And it is the id contract above, wrapped in the pointer's own syntax:
    # a pointer wider or narrower than the ids it may name is the divergence.
    assert pointers["recount.py"] == r"^=\s*(" + bodies["recount.py"] + ")"


# --- what the composite id does NOT buy: a lens ----------------------------
#
# The id contract above makes `V-CIT-1` readable by both instruments. What it
# does not do is attribute the row to a lens: the prefix names a verifier
# pass and the stem of what it re-checked. Both scripts already behave that
# way, so nothing here is a behavior claim — it is the claim that the
# behavior is WRITTEN DOWN, in both docstrings, together with the residual
# gap it leaves (the mechanical security backstop is keyed on the lens prefix
# and so never reaches such a row). A rule derivable only by reading the
# source is a rule the next reader re-derives or gets wrong.

COMPOSITE_LENS_SCRIPTS = ("recount.py", "rollup.py")
COMPOSITE_NOT_A_LENS = "a row with a composite id is never attributed to a lens"
# The residual gap, named in the same breath rather than left to be found.
COMPOSITE_BACKSTOP_GAP = "keyed on the declared lens prefix"
COMPOSITE_GAP_CONSEQUENCE = "does not reach a composite-id row either"


def module_docstring(path):
    """The file's MODULE docstring, wrapping collapsed and case folded.

    The claim is about the docstring — the text a reader of `--help` and of
    the file's own head is given — so the assertion reads that node and not
    the whole file: a sentence buried in a comment would satisfy a plain
    grep and leave the documented contract exactly where it was.
    """
    doc = ast.get_docstring(ast.parse(text_of(path))) or ""
    return re.sub(r"\s+", " ", doc).lower()


@pytest.mark.parametrize("script", COMPOSITE_LENS_SCRIPTS)
def test_the_composite_id_is_stated_to_carry_no_lens(scripts_dir, script):
    """The sentence, and the honest gap beside it, in both docstrings."""
    doc = module_docstring(scripts_dir / script)
    assert COMPOSITE_NOT_A_LENS in doc, script
    assert COMPOSITE_BACKSTOP_GAP in doc, script
    assert COMPOSITE_GAP_CONSEQUENCE in doc, script
    assert "known limitation, not a defect" in doc, script


# --- the 0.3.0 addendum: four rules the shipped paper must keep ------------
# Each is a sentence stated once in the payload and enforced by no script,
# so only its wording can be pinned — and each is asserted against the file
# that HOLDS it, never against a union scan a stray copy would satisfy.

READINESS_SCALE = REFERENCES_DIR / "readiness-scale.md"
RULES_OF_USE_HEADING = "Rules of use:"
L1_BASELINE_LITERAL = (
    "exits 0, or does not regress from the recorded baseline exit `<n>`"
)
SUBAGENT_MODEL_ENV = "CLAUDE_CODE_SUBAGENT_MODEL"
SUBAGENT_MODEL_CELL = "subagent-model"


def test_the_l1_criterion_carries_its_recorded_self_baseline():
    """A command already failing before the fix is a baseline, not a bar."""
    scale = flat(READINESS_SCALE)
    assert L1_BASELINE_LITERAL.lower() in scale
    # The baseline is taken AT adjudication, so the rule that a criterion
    # never changes afterwards is untouched by it.
    assert "the baseline is recorded at adjudication" in scale


def test_the_l1_baseline_rule_sits_inside_the_rules_of_use():
    """The rule is a rule OF USE of the ladder, not a note under the table."""
    scale = text_of(READINESS_SCALE)
    assert scale.index(L1_BASELINE_LITERAL) > scale.index(RULES_OF_USE_HEADING)


def test_the_baseline_rule_carries_its_security_carve_out():
    """Without the carve-out an already-failing security command becomes
    the bar it must merely not regress from — the finding disappears."""
    scale = flat(READINESS_SCALE)
    assert "class:security-pii" in scale
    assert "a security command that already fails is a finding of the round"\
        " in its own right" in scale


def test_stage_zero_reads_the_subagent_model_variable():
    """The env read belongs to stage 0; the router keeps its warning."""
    stage_zero = text_of(STAGE_0)
    assert SUBAGENT_MODEL_ENV in stage_zero
    assert f"echo ${SUBAGENT_MODEL_ENV}" in stage_zero
    assert SUBAGENT_MODEL_ENV in text_of(SKILL_MD)
    # The recorded cell is named in all three files that carry it: the
    # router's pointer, the stage that writes it, the header it goes into.
    for path in (SKILL_MD, STAGE_0, LEDGER_TEMPLATE):
        assert SUBAGENT_MODEL_CELL in text_of(path), path.name


def test_the_subagent_model_record_is_not_a_new_stop_condition():
    """Both outcomes are recorded and neither refuses the round."""
    stage_zero = flat(STAGE_0)
    assert "`subagent-model: unset`" in stage_zero
    assert "`subagent-model: set <non-model-value>`" in stage_zero
    assert "this is a record, not a gate: the round continues either way" in (
        stage_zero
    )


def test_the_residue_register_has_four_nomination_occasions():
    """The enumeration is closed, so its count is the rule."""
    stage_nine = text_of(STAGE_9)
    assert "THREE recognized occasions" not in stage_nine
    assert stage_nine.count("FOUR recognized occasions") == 1
    flat_nine = flat(STAGE_9)
    # The fourth occasion excludes exactly two things, and names both.
    assert "is not a blocker and does not carry `origin:fix-application`" in (
        flat_nine
    )
    # The candidate's second route was dropped: a finding sent to "the next
    # round with a note" has no terminal status and no machine literal.
    assert "next round with a note" not in flat_nine


def test_the_noticed_paragraph_points_at_the_fourth_occasion():
    """The route is discoverable from the stage that produces such rows."""
    assert "the fourth nomination occasion of stage 9" in flat(STAGE_7)


def test_a_class_kill_may_close_by_reference_to_an_existing_criterion():
    """The form of the obligatory reaction changes; the obligation does not."""
    stage_seven = flat(STAGE_7)
    assert "the class-kill disposition instead closes by reference to that"\
        " criterion" in stage_seven
    assert "no new gate script and no separate row" in stage_seven
    assert "an orchestrator entry naming the donor row goes into the ledger" in (
        stage_seven
    )
    assert "obligatory, not a right" in stage_seven
    assert "never the right to skip it" in stage_seven


# --- the 0.3.0 addendum, batch D3 ------------------------------------------
# Six more rules the shipped paper states and no script enforces, so again
# only their wording can be pinned, and again each is asserted against the
# file that HOLDS it rather than against a union scan of the payload.

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


def test_the_round_delta_quotes_the_rollups_own_numbers():
    """With observability on the cost line is a TRANSFER of computed numbers.

    Nothing is measured for it — the values are read out of the summary the
    rollup already wrote, which is why no script and no schema moved.
    """
    stage_nine = flat(STAGE_9)
    assert "once the rollup below has written `round-summary.json`, the"\
        " orchestrator quotes out of it the round's `wallclock_s`, its"\
        " `totals.tokens`" in stage_nine
    assert "the count of batches and passes the same file records" in stage_nine
    assert "with observability off the round delta is written exactly as it"\
        " is today" in stage_nine


def test_the_round_delta_cost_line_states_both_of_its_holes():
    """A cost line read as complete would be the defect.

    Two things keep it from being read that way: `wallclock_s` is
    legitimately `null` because the summary is built before the round span
    closes, and the rollup cannot separate the orchestrator's own spend.
    """
    stage_nine = flat(STAGE_9)
    assert "`wallclock_s: n/a: summary built before s1.00 close`" in stage_nine
    assert "`orchestrator: n/a (not separable)`" in stage_nine
    # The wording the rollup itself prints, so the two cannot drift apart.
    assert "orchestrator: n/a (not separable)" in (
        (TEMPLATES_DIR / "rollup.py").read_text(encoding="utf-8")
    )


def test_the_signature_may_be_transcribed_only_beside_the_owners_words():
    """The right to render the phrase and the duty to quote it are ONE rule."""
    stage_nine = flat(STAGE_9)
    assert "the orchestrator may render the owner's human phrase into the"\
        " machine literal" in stage_nine
    assert "must carry the phrase verbatim beside the `user-signed` literal"\
        " it was rendered into" in stage_nine
    # Why the second half is not detachable: the recount sees the literal
    # only, so the licence alone would legalise a manufactured signature.
    assert "a licence to transcribe granted without the duty to quote would"\
        " legalise a signature manufactured out of silence" in stage_nine


def test_the_two_signature_statements_stand_as_one_paragraph():
    """Split across a paragraph break, the duty reads as a separate remark."""
    stage_nine = text_of(STAGE_9)
    start = stage_nine.index("Transcribing into that machine form is a right")
    end = stage_nine.index("in the owner's own words and in quotes.")
    assert "\n\n" not in stage_nine[start:end]


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


def test_the_sequencing_promise_survives_in_the_guardrails_own_terms():
    """The mechanism was dropped, the obligation was not."""
    stage_seven = flat(STAGE_7)
    assert "and every other write-capable agent — strictly sequentially" in (
        stage_seven
    )
    assert "only after its report has arrived and the batch is committed" in (
        stage_seven
    )
    assert "between batches the tree is confirmed quiet with `git status`" in (
        stage_seven
    )


def test_stage_two_names_the_canonical_scratchpad_layout():
    """The layout the script's conditions 4 and 7 imply, written down once."""
    stage_two = flat(STAGE_2)
    assert "`<scratchpad root>/critic-copies/<object-slug>/<run-id>`" in stage_two
    assert "that root, and not the copy, is the directory handed to `--root`" in (
        stage_two
    )
    assert "`--run-id` is the last segment" in stage_two


def test_the_contract_may_reach_a_lens_as_an_in_copy_pointer():
    """The bounded equivalent of pasting the body, with both its conditions."""
    stage_two = flat(STAGE_2)
    assert "where the contract file physically lies inside the copy the"\
        " critics read, the orchestrator may substitute into"\
        " `{round_contract}` a pointer to that path inside the copy" in stage_two
    assert "(a) the path is identical for every lens" in stage_two
    assert "(b) the ledger header carries the contract's sha" in stage_two


def test_the_in_copy_pointer_does_not_touch_the_identity_requirement():
    """The equivalence is about FORM; the scope every lens reads is one."""
    stage_two = flat(STAGE_2)
    assert "identically and verbatim" in stage_two
    assert "re-telling, shortening or angling for one lens stay forbidden" in (
        stage_two
    )


def test_the_deleted_line_walk_is_divided_explicitly_on_a_lens_split_pass():
    """Ids split by scope, deleted lines split by FILE — and both in writing."""
    stage_eight = flat(STAGE_8)
    assert "the deterministic deleted-line walk is divided by that same rule"\
        " and divided explicitly" in stage_eight
    assert "names the one verifier of the pass that walks them all" in stage_eight
    assert "the union covers every deleted-line of the batch with no hole" in (
        stage_eight
    )


def test_the_residue_scoped_condition_a_covers_the_deleted_line_walk():
    """Condition (a) reads full-scope off stage 8, so it inherits the rule."""
    assert "condition (a) takes stage 8's sense of full-scope whole" in (
        flat(STAGE_9)
    )
    assert "a pass whose walk left a hole is not full-scope here either" in (
        flat(STAGE_9)
    )


# --- the 0.3.0 addendum, batch D4 ------------------------------------------
# The front door stopped quoting efficacy figures. That is three properties
# at once, and none of them is behavior of any script: the figures are gone
# from the two files that quoted them, they are still there, verbatim, in the
# one file that keeps them as provenance, and the README says plainly that no
# benchmark exists. The tuple below has the same shape as STANDALONE_LITERALS
# above — one (file, literal) row per sentence, parametrized into one test.

README_MD = REPO_ROOT / "README.md"
WHY_CRITICS = REPO_ROOT / "docs" / "why-critics.md"

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

WITHDRAWAL_LITERALS = (
    (README_MD, "**There is no external benchmark for any of this, and none"
                " is claimed.**"),
    (README_MD, "Collecting that evidence is planned, not done"),
    (WHY_CRITICS, "**These numbers are provenance, not efficacy evidence.**"),
)

# A published asset would have been the other way of showing a round; the
# text block in the README is the decision, and these extensions are what it
# ruled out.
BINARY_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".cast")


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


@pytest.mark.parametrize(("path", "literal"), WITHDRAWAL_LITERALS)
def test_the_withdrawal_sentences_are_present(path, literal):
    assert literal.lower() in flat(path), f"{literal[:40]}… missing"


def test_the_readme_carries_exactly_one_flow_diagram():
    """One diagram, and one only — the modes are not duplicated."""
    assert text_of(README_MD).count("```mermaid") == 1


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


# --- companion text that must move with the thing it describes -------------
#
# The defect class these gates exist for is STALE COMPANION TEXT: a number or
# a vocabulary restated in a second file and left standing when the first file
# changed. Most of that surface is prose citation, which no test can derive
# and which stays on the convention of re-deriving it; the two surfaces below
# CAN be derived, so they are gated here rather than trusted.
#
# (a) The regression suite's case count. It is stated in the suite's own
#     header line and again in the label of every workflow step that runs the
#     suite, and none of those statements is derived from the cases the script
#     actually builds — so all of them can drift, silently, in either
#     direction. The count is derived here, once, from the case ids.
# (b) The verdict-cell tag vocabulary. `recount.py` DEFINES the tags it reads
#     out of a `verdict` cell; the ledger template's verdict-tag comment is
#     where a human reads what they mean. A tag the script gained and the
#     template never heard of is a rule nobody using the template can follow.

REGRESSION_SUITE = REPO_ROOT / "tests" / "run-regression.sh"
# The case ids the suite builds, in the derivation the contributor guide
# documents: the distinct `cNN` tokens of the script itself.
CASE_ID_RE = re.compile(r"\bc[0-9]{2}\b")
# The header line that states the count, and the shape it states it in.
SUITE_HEADER_INDEX = 1
SUITE_HEADER_COUNT_RE = re.compile(r"\((\d+) cases, c01-c(\d+)\)")
# The workflow step that RUNS the suite, recognized by its label. The marker
# is the part a rewording cannot drop without dropping the reference to the
# script; the full shape is what carries the number.
REGRESSION_STEP_MARKER = "recount.py regression suite ("
REGRESSION_STEP_LABEL_RE = re.compile(r"recount\.py regression suite \((\d+) cases\)")
# How far above the payload root workflow files are looked for. A payload
# published on its own carries its own `.github/`; a payload that sits inside
# a larger repository is also run by that repository's workflows. The walk
# stops at the first directory holding a `.git` and never climbs further than
# this in any case, so no directory outside the enclosing repository is read.
WORKFLOW_SEARCH_LEVELS = 3


def regression_case_ids():
    """Every distinct case id the regression suite builds."""
    ids = set(CASE_ID_RE.findall(text_of(REGRESSION_SUITE)))
    # Fail-closed: a truncated or empty read must never pass as agreement.
    assert len(ids) > 50, sorted(ids)
    # The ids are one contiguous block starting at `c01`, which is what makes
    # counting them the same statement as the `c01-cNN` range in the header.
    assert ids == {f"c{n:02d}" for n in range(1, len(ids) + 1)}, sorted(ids)
    return ids


def workflow_files():
    """Every `.github/workflows/*.y{a,}ml` file that can run this payload.

    Discovery is generic on purpose: no workflow is named here, so a renamed
    or a newly added one is covered without an edit to this file, and a
    payload published on its own is covered by exactly the workflows it
    itself ships.
    """
    found = []
    for level, root in enumerate((REPO_ROOT, *REPO_ROOT.parents)):
        if level > WORKFLOW_SEARCH_LEVELS:
            break
        directory = root / ".github" / "workflows"
        if directory.is_dir():
            found += [
                path
                for pattern in ("*.yml", "*.yaml")
                for path in directory.glob(pattern)
                if path.is_file()
            ]
        if (root / ".git").exists():
            break
    return sorted(found)


def test_the_regression_suites_header_states_the_count_it_builds():
    """The stated count, against the cases the script actually builds."""
    derived = len(regression_case_ids())
    header = text_of(REGRESSION_SUITE).splitlines()[SUITE_HEADER_INDEX]
    match = SUITE_HEADER_COUNT_RE.search(header)
    assert match, header
    assert int(match.group(1)) == derived, header
    # The range in the same sentence says it a second way; both are derived.
    assert int(match.group(2)) == derived, header


def test_every_workflow_labels_the_regression_step_with_that_same_count():
    """A step label is read as a promise about what the step ran.

    The label is companion text of the suite: nothing recomputes it when a
    case is added, so it is derived here for every workflow that names it.
    """
    derived = len(regression_case_ids())
    files = workflow_files()
    # Fail-closed twice: a walk that found no workflow, or workflows none of
    # which mentions the suite, is not a clean result — it is a gate that
    # checked nothing.
    assert files, "no workflow files found — wrong root?"
    labelled = [path for path in files if REGRESSION_STEP_MARKER in text_of(path)]
    assert labelled, [str(path) for path in files]
    offenders = []
    for path in labelled:
        for number, line in enumerate(text_of(path).splitlines(), 1):
            if REGRESSION_STEP_MARKER not in line:
                continue
            match = REGRESSION_STEP_LABEL_RE.search(line)
            if match is None:
                offenders.append(f"{path}:{number}: no readable count: {line.strip()}")
            elif int(match.group(1)) != derived:
                offenders.append(
                    f"{path}:{number}: label says {match.group(1)},"
                    f" the suite builds {derived}"
                )
    assert offenders == [], offenders


# The verdict-tag comment of the ledger template, by its opening literal.
VERDICT_TAG_COMMENT_OPEN = "<!-- Verdict-cell tags."
COMMENT_CLOSE = "-->"
# The tags a verdict cell may carry today, named here so that a tag silently
# dropped from BOTH files still fails this gate.
VERDICT_CELL_TAGS = (
    "class:",
    "origin:fix-application",
    "shelf:",
    "class-origin:adjudicator",
    "class-kill:",
)
# The shape a verdict-cell tag literal has in the recount's source, whether it
# is written as a plain constant (`origin:fix-application`) or as the head of
# a tag regex (`class:([a-z0-9-]{1,32})…`): a lower-case stem, a colon, and
# whatever fixed part follows. Anchored at the START of the literal, so a
# header pattern or a message that merely contains a colon is not read as a
# tag, and stopping at the first character outside the slug alphabet, so the
# regex machinery around a tag is not read as part of it.
TAG_LITERAL_RE = re.compile(r"^[a-z][a-z0-9-]*:[a-z0-9-]*")


def verdict_tag_comment() -> str:
    """The ledger template's verdict-tag comment, opener to `-->`."""
    text = text_of(LEDGER_TEMPLATE)
    start = text.index(VERDICT_TAG_COMMENT_OPEN)
    return text[start : text.index(COMMENT_CLOSE, start)]


def tag_literals_defined_by_the_recount():
    """Every verdict-cell tag literal the recount's SOURCE defines.

    Read off the script's module-level constants — the plain strings and the
    heads of the tag regexes — rather than hand-listed, so a sixth tag added
    there has to be documented before this file agrees again. The script is
    never imported: it is a CLI, and importing it would run its argument
    handling.
    """
    stems = set()
    for node in ast.parse(text_of(RECOUNT_SCRIPT)).body:
        if isinstance(node, ast.Assign):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value = node.value
        else:
            continue
        for child in ast.walk(value):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                match = TAG_LITERAL_RE.match(child.value)
                if match:
                    stems.add(match.group(0))
    return stems


@pytest.mark.parametrize("tag", VERDICT_CELL_TAGS)
def test_every_verdict_cell_tag_is_documented_in_the_ledger_template(tag):
    """The vocabulary the script reads is the vocabulary the paper states."""
    assert tag in verdict_tag_comment(), tag


def test_no_tag_the_recount_defines_is_missing_from_that_comment():
    """The same claim, derived instead of listed — a new tag cannot slip in."""
    documented = verdict_tag_comment()
    defined = tag_literals_defined_by_the_recount()
    # Fail-closed: an extraction that found nothing would document nothing.
    assert set(VERDICT_CELL_TAGS) <= defined, sorted(defined)
    assert sorted(tag for tag in defined if tag not in documented) == []


# --- the telemetry spec, batch T8 (R-T6) -----------------------------------
#
# Two more companion-text surfaces, both derivable and therefore gated here
# rather than trusted to the convention of re-deriving prose.
#
# (c) The published "in full" enumeration of `rounds.jsonl` against the keys
#     `project()` actually returns. The README says the list is exhaustive and
#     that the line carries no object name, no absolute clock and no commit
#     hash; `project()` builds its line from an EXPLICIT key allowlist, so a
#     key added there and not added to the README makes a published guarantee
#     false, and a key named in the README that the projection never emits is
#     a promise about a field nobody receives.
# (d) The placement of the leaving-the-machine rule in `observability.md`. The
#     rule is written BELOW the frozen privacy-invariant block on purpose:
#     inserting above it would shift the byte range the freeze is proved by.
#     Order is the requirement, so order is what is asserted.

ROLLUP_SCRIPT = TEMPLATES_DIR / "rollup.py"
OBSERVABILITY_MD = REFERENCES_DIR / "observability.md"

# The paragraph that carries the enumeration, by its opening literal. The
# passage is one paragraph and ends at the first blank line after it.
ROUNDS_IN_FULL_OPEN = "**The cross-project rollup's fields, in full**"
# Backticked tokens in that paragraph that are NOT projected keys, each for a
# stated reason. `plan`/`impl` are the two VALUES `mode` may take, glossed in
# the same sentence; the other three are the keys INSIDE `object`, named so
# that "and not one file name among them" can be checked by a reader. A token
# that is neither a projected key nor on this list is an undeclared claim.
ROUNDS_README_GLOSSES = frozenset(
    {"plan", "impl", "lines_at_pin", "changed_lines", "files_touched"}
)
# A backticked token in that paragraph, with a trailing `[]` stripped: the
# README writes the list-valued keys as `lenses[]`, the dict writes `lenses`.
README_KEY_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)(?:\[\])?`")


def rounds_in_full_paragraph() -> str:
    """The README paragraph enumerating the `rounds.jsonl` fields."""
    text = text_of(README_MD)
    start = text.index(ROUNDS_IN_FULL_OPEN)
    end = text.index("\n\n", start)
    return text[start:end]


def projected_keys() -> set[str]:
    """The literal top-level keys of the dict `project()` returns.

    Read off the source with `ast`, never imported: `rollup.py` is a CLI and
    importing it would run its argument handling — the same reason
    `tag_literals_defined_by_the_recount()` above parses instead of imports.
    A key computed rather than written as a literal would not be a published
    enumeration in the first place, so a non-constant key fails this read.
    """
    tree = ast.parse(text_of(ROLLUP_SCRIPT))
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "project"
    ]
    assert len(functions) == 1, [node.lineno for node in functions]
    dicts = [
        node.value
        for node in ast.walk(functions[0])
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    ]
    assert len(dicts) == 1, len(dicts)
    keys = set()
    for key in dicts[0].keys:
        assert isinstance(key, ast.Constant) and isinstance(key.value, str), key
        keys.add(key.value)
    # Fail-closed: an extraction that found nothing would agree with anything.
    assert len(keys) > 5, sorted(keys)
    return keys


def test_the_readme_enumeration_and_the_projection_agree_key_for_key():
    """The published list is exhaustive, so it is derived from the code.

    Both directions are asserted, because each is a different false claim.
    A key the projection emits and the paragraph omits makes the published
    "in full" untrue by composition. A name the paragraph carries and the
    projection never emits promises a field nobody receives — as false, and
    invisible to a one-sided check.

    The forward direction is INCLUSION rather than equality: the paragraph
    also glosses `mode`'s two values and `object`'s three inner counts, none
    of which is a top-level key of the line. Those five are declared in
    `ROUNDS_README_GLOSSES`, so the reverse direction stays exact — a stray
    key name added to the paragraph is not explained by any of them and
    fails here.
    """
    named = set(README_KEY_RE.findall(rounds_in_full_paragraph()))
    projected = projected_keys()
    missing = sorted(projected - named)
    assert missing == [], missing
    unexplained = sorted(named - projected - ROUNDS_README_GLOSSES)
    assert unexplained == [], unexplained


# The three blocks of `observability.md`, in the order the spec pins them.
# Matched against `flat()` — these are wrapped sentences, and a reflow must
# not read as a deleted rule.
PRIVACY_INVARIANT_ANCHOR = (
    "**the privacy invariant.** everything observability produces is a local"
    " file the person who ran the round owns."
)
LEAVING_THE_MACHINE_ANCHOR = (
    "**whatever leaves the machine leaves only through the cleansing"
    " projection.**"
)
MISSING_NUMBER_ANCHOR = (
    "**a missing number is `n/a: <reason>` — never a failure, and never a"
    " blocked round.**"
)


def test_the_leaving_the_machine_rule_sits_below_the_frozen_invariant():
    """Placement is the requirement, so placement is what is asserted.

    The privacy invariant is a byte-frozen block that three requirements
    cite by line range. The rule about what may leave the machine belongs
    beside it but BELOW it: inserted above, it would shift the very range
    the freeze is proved by. The three anchors are located by index in one
    reading of the file, so the order is checked rather than the presence.
    """
    text = flat(OBSERVABILITY_MD)
    positions = {}
    for name, anchor in (
        ("privacy invariant", PRIVACY_INVARIANT_ANCHOR),
        ("leaving the machine", LEAVING_THE_MACHINE_ANCHOR),
        ("missing number", MISSING_NUMBER_ANCHOR),
    ):
        assert anchor in text, name
        positions[name] = text.index(anchor)
    assert (
        positions["privacy invariant"]
        < positions["leaving the machine"]
        < positions["missing number"]
    ), positions


# --- the payload carries no out-of-tree data, and reaches no out-of-tree data
#
# The mechanical half of a rule the release flow states in prose: a test
# inside the published tree tests only what the published tree contains. A
# regression case that reaches outside this tree for its fixtures — a
# caller-specific identifier, a caller-specific path, or a caller-specific
# count — either always skips in a clone that lacks that data, which makes
# the skip itself the one channel by which the data's shape reaches a public
# clone, or it fails outright. Neither is acceptable, so such a case does not
# ship here; it runs wherever its fixtures actually live.

# The shape of a run-folder name: `<date>-<hhmmss>-<slug>`.
ROUND_ID_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}-\d{6}-[a-z0-9-]+")

# The payload SHOWS that shape — the format has to be shown somewhere — so
# the sweep cannot forbid it outright. What it forbids is a name it has not
# seen before, which is what a literal pasted out of a real run folder is.
# Every identifier the payload may carry is inventoried here with the file
# that shows it: nothing is exempted silently, and adding one is an edit to
# this list that a reviewer sees. Trailing dashes are stripped off a match
# before the comparison — no folder name ends in one, and the pattern's
# lower-case class stops in the middle of `...-lens-DA`.
PAYLOAD_EXAMPLE_ROUND_IDS = frozenset(
    {
        # `references/stage-1-run-folder.md` — the run folder's own example.
        "2026-01-15-101502-auth-plan",
        # `templates/cleanup-scratchpad.py` usage, and the copy-script tests
        # built on it; the second form is that same id with the per-lens
        # suffix the copy script refuses in `--run-id`.
        "2026-02-03-084011-api-spec",
        "2026-02-03-084011-api-spec-lens",
        # `examples/worked-round/residue-register.md` — the two origin runs
        # of the worked example's residue rows.
        "2026-08-03-091734-bench-report",
        "2026-08-08-143000-copy-script",
        # The trace/rollup schema's four canonical example records, and the
        # `--round` value the regression suite and the recount tests pass.
        "2026-08-11-101502-auth-plan",
        "2026-09-01-120000-object",
    }
)

# Directories nothing is authored in and nothing ships from.
NON_SOURCE_DIRS = frozenset(
    {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
     ".mypy_cache", "node_modules"}
)

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


def payload_source_files():
    """Every text file under the payload root, `tests/` INCLUDED.

    Wider than `shipped_payload_files()` on purpose: that helper excludes
    `tests/` for its own good reason, and this sweep exists to cover it too.
    Caches and binary assets are skipped — reading them as text says
    nothing — and every remaining file is read with `errors` ignored, so an
    unexpected encoding degrades to a weaker read rather than to an error.
    """
    files = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        parts = path.relative_to(REPO_ROOT).parts
        if any(part in NON_SOURCE_DIRS for part in parts):
            continue
        if path.suffix.lower() in (*BINARY_SUFFIXES, ".pyc"):
            continue
        files.append(path)
    return files


def test_no_shipped_file_carries_an_unknown_round_identifier():
    """A run-folder name in the payload is an example or it is a leak."""
    files = payload_source_files()
    # Fail-closed: a walk that read nothing agrees with everything.
    assert len(files) > 50, len(files)
    offenders = []
    for path in files:
        where = path.relative_to(REPO_ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for number, line in enumerate(text.splitlines(), 1):
            for match in ROUND_ID_RE.findall(line):
                if match.rstrip("-") not in PAYLOAD_EXAMPLE_ROUND_IDS:
                    offenders.append(f"{where}:{number}: {match}")
    assert offenders == [], offenders


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
