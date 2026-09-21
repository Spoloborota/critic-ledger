"""Invariants over the shipped payload read as FILES rather than as CLIs.

Everything else in `tests/unit/` drives a script through a subprocess and
pins its observable behavior. Claims that are not behavior of any single
script but properties of the payload as a whole are enforced here instead.
One of the ones it started from is:

* **The SKILL.md stage machine.** Stages 0-9 exist, in order, with nothing
  renumbered or dropped. A stage body lives either inline in the router or
  in a `references/stage-*.md` file beside it, and the sweep covers both.

It reads the shipped files from the repository root.
"""

from __future__ import annotations

import ast
import re

import pytest

from conftest import (
    BINARY_SUFFIXES,
    HEADER_7,
    HEADER_8,
    HEADER_9,
    MODULE_NAMES,
    NON_SOURCE_DIRS,
    REPO_ROOT,
    text_of,
)
from prose_pins import PROSE_PINS


SKILL_MD = REPO_ROOT / "skills" / "critic-ledger" / "SKILL.md"
REFERENCES_DIR = REPO_ROOT / "skills" / "critic-ledger" / "references"
# The stage files whose bodies have already left the router. A literal these
# tests protect is asserted against the file that now HOLDS it, never against
# a union scan that a single stray copy elsewhere would satisfy.
STAGE_0 = REFERENCES_DIR / "stage-0-prerequisites.md"
STAGE_1 = REFERENCES_DIR / "stage-1-run-folder.md"
STAGE_2 = REFERENCES_DIR / "stage-2-scope-and-lenses.md"
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
STAGE_MACHINE_HEADING = "## Stage machine"
STAGE_START_RE = re.compile(r"^(\d+)\. \*\*")
# The binding heading form of a stage opener in a `references/stage*.md`
# file: `## Stage N — Name`, em dash U+2014, one heading per stage (three
# of them inside `stages-3-5-critics-salvage-layout.md`).
STAGE_FILE_HEADING_RE = re.compile(r"^## Stage (\d+) — ")


# --- SKILL.md: the stage machine, stage by stage ---------------------------


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


# --- every shipped template is named in the Templates section ---------------
#
# The stage machine addresses a template by its full substituted path, and the
# Templates section is where a reader learns what each one IS. A template that
# ships without an entry there is invisible: nobody reading the skill knows it
# exists, and nobody editing the skill knows it has to be kept in step. The
# sweep is over both directories — the scripts and the prompts and skeletons —
# so it covers a file added to either by a later batch without any edit here.


def templates_section() -> str:
    """The Templates section, which is now a file of its own in full."""
    return TEMPLATES_REF.read_text(encoding="utf-8")


def test_every_shipped_template_is_named_in_the_templates_section(
    scripts_dir, templates_dir,
):
    section = templates_section()
    scripts = sorted(p.name for p in scripts_dir.iterdir() if p.is_file())
    templates = sorted(p.name for p in templates_dir.iterdir() if p.is_file())
    # Fail-closed per directory: one of them read empty must not pass on the
    # files of the other.
    assert scripts, "no scripts found — wrong directory?"
    assert templates, "no templates found — wrong directory?"
    shipped = [f"scripts/{name}" for name in scripts] + [
        f"templates/{name}" for name in templates
    ]
    assert [path for path in shipped if path not in section] == []


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


def flat(path):
    """The file's text, lower-cased with its line wrapping collapsed.

    A rule these tests protect is a SENTENCE, and a sentence in these files
    is wrapped at 78 columns: matching the raw text would make a reflow
    look like a deleted rule. Case is folded for the same reason — the
    files shout some of these clauses and not others.
    """
    return re.sub(r"\s+", " ", text_of(path)).lower()


def test_the_back_channel_has_three_outcomes_everywhere_it_is_named(templates_dir):
    """A vocabulary that differs between the fixer's texts is no vocabulary."""
    for path in (
        FIXER_AGENT,
        templates_dir / "fixer-prompt.md",
        STAGE_7,
        TEMPLATES_REF,
    ):
        body = text_of(path)
        assert PREMISE_OUTCOME in body, path.name
        assert "criterion-unworkable" in body, path.name
    prompt = text_of(templates_dir / "fixer-prompt.md")
    assert "exactly one per id, and there are exactly three" in prompt
    assert "no third option" not in prompt


def test_the_verifier_is_not_shown_the_fixers_justification(templates_dir):
    """Stated in the agent definition and in the prompt template."""
    assert "not shown the fixer's justification" in flat(VERIFIER_AGENT)
    prompt = text_of(templates_dir / "verifier-prompt.md")
    assert "WHAT YOU ARE DELIBERATELY NOT GIVEN" in prompt
    assert "would a fresh critic still file here?" in prompt


def test_the_verifier_prompt_carries_no_placeholder_for_a_fixer_report(
    templates_dir,
):
    """The rule is mechanical here: a placeholder is what would break it."""
    placeholders = set(
        re.findall(r"\{([a-z_]+)\}", text_of(templates_dir / "verifier-prompt.md"))
    )
    assert placeholders
    assert [name for name in placeholders if "fixer" in name] == []


def test_a_number_matching_is_not_a_mechanism_matching(templates_dir):
    """Stated in the verifier's mandate and in its definition."""
    for path in (VERIFIER_AGENT, templates_dir / "verifier-prompt.md"):
        body = flat(path)
        assert "mechanism matching" in body, path.name
        assert "direction of a rule" in body, path.name


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


# kept as code: (i) `security` is counted in one table line, not a file
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
SCRIPTS_DIR = REPO_ROOT / "skills" / "critic-ledger" / "scripts"
LEDGER_TEMPLATE = TEMPLATES_DIR / "ledger.md"
CONTRACT_TEMPLATE = TEMPLATES_DIR / "round-contract.md"
RECOUNT_SCRIPT = SCRIPTS_DIR / "recount.py"
# The recount is one entry point and the modules it is split into; a check
# of "the script's" vocabulary reads them all as one text, so a literal that
# moved into a module is still found and a stray one there still fails. The
# modules are derived from `MODULE_NAMES`, the list the presence check reads,
# so a module added there cannot stay out of these gates; `ledger_md.py` is
# left out because it is the grammar every script shares, not a part of the
# recount.
RECOUNT_SOURCES = (
    RECOUNT_SCRIPT,
    *(SCRIPTS_DIR / name for name in MODULE_NAMES if name != "ledger_md.py"),
)


def text_of_source(path):
    """A file's text; for the recount, its entry point and modules together."""
    if path == RECOUNT_SCRIPT:
        return "\n".join(text_of(source) for source in RECOUNT_SOURCES)
    return text_of(path)


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
        assert status in text_of_source(path), f"{status} missing from {path.name}"


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
        assert zone in text_of_source(path), f"{zone} missing from {path.name}"


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
        text = text_of_source(path)
        for stray in ("Z4", "Z5", "Z6"):
            assert stray not in text, f"{stray} in {path.name}"
    # And the script's own vocabulary is the same three, in one tuple.
    assert 'ZONES = (ZONE_MECHANICAL, ZONE_NORMATIVE, ZONE_INFORMATIVE)' in (
        text_of_source(RECOUNT_SCRIPT)
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


# kept as code: it asserts absence (not in); the registry pins present phrases
def test_old_run_addresses_may_be_relocated_by_the_project():
    """No unconditional promise, and no address of the plugin's own repo."""
    stage_one = flat(STAGE_1)
    # The unconditional promise the shipped text used to make, and the
    # out-of-tree address that must never reach the product.
    assert "are not migrated" not in stage_one
    assert "are not migrated" not in flat(SKILL_MD)
    assert ".critic-ledger/legacy" not in text_of(SKILL_MD)
    for path in sorted(REFERENCES_DIR.glob("*.md")):
        assert ".critic-ledger/legacy" not in text_of(path), path.name


def test_probe_to_criterion_is_named_in_both_stage_six_and_stage_eight():
    """The whole content of the rule is that ONE name spans the two stages.

    The two stage bodies are two FILES now, so the slice that used to carve
    them out of the router is the file boundary itself.
    """
    assert "probe-to-criterion" in text_of(STAGE_6)
    assert "probe-to-criterion" in text_of(STAGE_8)


# --- four more standalone rules of the same kind ---------------------------
# Each of the four is a SENTENCE in shipped paper, spread across two to four
# files at once. A rule that survives in one file and is reworded out of the
# others has silently stopped applying, and nothing script-level can see it.

NOTICED_BLOCK = "NOTICED OUTSIDE BATCH"
ID_OUTCOMES = ("criterion-unworkable", PREMISE_OUTCOME)


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


def test_a_deduplicated_row_reaches_the_verifier_with_the_full_criterion():
    """The briefing carries the primary row's criterion, not a pointer."""
    assert "=<primary-id>" in text_of(STAGE_8)
    assert "the primary row's criterion substituted in full" in flat(STAGE_8)
    prompt = text_of(VERIFIER_PROMPT)
    assert "=<primary-id>" in prompt
    assert "substituted IN FULL" in prompt


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


def test_the_fixer_prompt_carries_the_noticed_prefix_placeholder():
    """The block's id prefix is the orchestrator's, assigned at stage 2."""
    placeholders = set(re.findall(r"\{([a-z_]+)\}", text_of(FIXER_PROMPT)))
    assert "noticed_prefix" in placeholders
    assert "{noticed_prefix}" in text_of(TEMPLATES_REF)


# --- the shared project copy and the residue-scoped second pass ------------
# Both are rules that shipped paper states and no script enforces, so only
# their wording can be pinned — and for the copy the wording is what tells
# the orchestrator that the copy it just made is a SHARED one.

COPY_SCRIPT = SCRIPTS_DIR / "copy-project.sh"


def test_stage_two_no_longer_promises_a_copy_per_critic_unconditionally():
    """The shared copy is the ordinary case, and the text says so."""
    stage_two = flat(STAGE_2)
    assert "one copy per critic is the rare case and one shared copy per"\
        " round the ordinary one" in stage_two
    # The unconditional promise the shipped text used to make.
    assert "one copy per critic when reflink works" not in stage_two
    assert "one copy per critic when reflink works" not in flat(SKILL_MD)


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


# The closing script's own refusal, quoted in the closure stage so the
# reader meets it before the script prints it.
FROZEN_REFUSAL = "LEDGER IS FROZEN"


def test_stage_nine_states_the_frozen_refusal():
    """The closure stage quotes the refusal the closing script prints.

    A reader who meets the refusal only as script output has no text that
    says what a superseded ledger is, so the literal is stated in the
    stage that closes the round.
    """
    assert FROZEN_REFUSAL in text_of(STAGE_9)


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


def test_the_l1_baseline_rule_sits_inside_the_rules_of_use():
    """The rule is a rule OF USE of the ladder, not a note under the table."""
    scale = text_of(READINESS_SCALE)
    assert scale.index(L1_BASELINE_LITERAL) > scale.index(RULES_OF_USE_HEADING)


def test_stage_zero_reads_the_subagent_model_variable():
    """The env read belongs to stage 0, and to stage 0 alone."""
    stage_zero = text_of(STAGE_0)
    assert SUBAGENT_MODEL_ENV in stage_zero
    quoted_env = f'"${SUBAGENT_MODEL_ENV}"'
    assert f"printf '%s' {quoted_env}" in stage_zero
    # The recorded cell is named in all three files that carry it: the
    # router's pointer, the stage that writes it, the header it goes into.
    for path in (SKILL_MD, STAGE_0, LEDGER_TEMPLATE):
        assert SUBAGENT_MODEL_CELL in text_of(path), path.name


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


# --- the 0.3.0 addendum, batch D3 ------------------------------------------
# Six more rules the shipped paper states and no script enforces, so again
# only their wording can be pinned, and again each is asserted against the
# file that HOLDS it rather than against a union scan of the payload.

def test_the_two_signature_statements_stand_as_one_paragraph():
    """Split across a paragraph break, the duty reads as a separate remark."""
    stage_nine = text_of(STAGE_9)
    start = stage_nine.index("Transcribing into that machine form is a right")
    end = stage_nine.index("in the owner's own words and in quotes.")
    assert "\n\n" not in stage_nine[start:end]


# --- the 0.3.0 addendum, batch D4 ------------------------------------------
# The front door stopped quoting efficacy figures. That is three properties
# at once, and none of them is behavior of any script: the figures are gone
# from the two files that quoted them, they are still there, verbatim, in the
# one file that keeps them as provenance, and the README says plainly that no
# benchmark exists. The sentences that say so are records of `prose_pins.py`.

README_MD = REPO_ROOT / "README.md"


def test_the_readme_carries_exactly_one_flow_diagram():
    """One diagram, and one only — the modes are not duplicated."""
    assert text_of(README_MD).count("```mermaid") == 1


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
    body = [node for path in RECOUNT_SOURCES for node in ast.parse(text_of(path)).body]
    for node in body:
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
        # `scripts/cleanup-scratchpad.py` usage, and the copy-script tests
        # built on it; the second form is that same id with the per-lens
        # suffix the copy script refuses in `--run-id`.
        "2026-02-03-084011-api-spec",
        "2026-02-03-084011-api-spec-lens",
        # `examples/worked-round/residue-register.md` — the two origin runs
        # of the worked example's residue rows.
        "2026-08-03-091734-bench-report",
        "2026-08-08-143000-copy-script",
        # The `--round` value the regression suite, the trace/rollup
        # schema's example records and the recount tests all pass.
        "2026-09-01-120000-object",
    }
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


def test_every_example_round_identifier_is_still_shown_somewhere():
    """An exemption no file uses is a stale exemption.

    The list above is read by a reviewer as the inventory of what the
    payload shows; an entry whose carrier has gone silently widens what
    the sweep will accept the next time a literal is pasted in.
    """
    files = payload_source_files()
    assert len(files) > 50, len(files)
    shown = set()
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in ROUND_ID_RE.findall(text):
            shown.add(match.rstrip("-"))
    assert sorted(PAYLOAD_EXAMPLE_ROUND_IDS - shown) == []


def test_the_scripts_directory_ships_nine_python_clis():
    """The count the suite's own docstring and CONTRIBUTING.md quote.

    Both name it in prose, and prose does not recount itself: a script
    added to or removed from the directory fails here rather than
    leaving two documents quoting a number the tree no longer has.
    """
    scripts_dir = REPO_ROOT / "skills" / "critic-ledger" / "scripts"
    clis = sorted(
        path.name
        for path in scripts_dir.glob("*.py")
        if "__main__" in path.read_text(encoding="utf-8")
    )
    assert len(clis) == 9, clis
    assert "the nine standalone" in text_of(REPO_ROOT / "tests" / "unit"
                                           / "conftest.py")
    assert "the nine Python ones" in text_of(REPO_ROOT / "CONTRIBUTING.md")


# --- the `###` section grid of stages 2 and 6-9 -----------------------------
#
# Each of the five stage bodies below carries an addressable grid of `###`
# headings. A heading is an ADDRESS: once it has landed, its number is
# frozen, so a later edit may not renumber it, reorder it or close the gap
# left by one that goes away — renaming it is allowed. A new section takes
# the NEXT FREE number at the end of its stage's run, never a renumbering of
# the ones already there — renumbering would silently redirect every
# reference made to the old address. The tuples below pin the numbers that
# may never disappear, and by their length their count; the test also
# checks that the file's numbers stand in increasing order without repeats.
# A heading renumbered, reordered or dropped in the payload fails here
# rather than drifting away from whatever cites it. A new section that
# re-uses an old gap is not caught here: the rule above is what forbids it.

STAGE_2_SECTION_NUMBERS = (
    "2.1",
    "2.2",
    "2.3",
    "2.4",
)

STAGE_6_SECTION_NUMBERS = (
    "6.1",
    "6.2",
    "6.3",
    "6.4",
    "6.5",
    "6.6",
    "6.7",
    "6.8",
    "6.9",
    "6.10",
    "6.11",
    "6.12",
    "6.13",
    "6.14",
    "6.15",
    "6.16",
    "6.17",
    "6.18",
    "6.19",
    "6.20",
    "6.21",
    "6.22",
    "6.23",
    "6.24",
    "6.25",
    "6.26",
    "6.27",
    "6.28",
    "6.30",
)

STAGE_7_SECTION_NUMBERS = (
    "7.1",
    "7.2",
    "7.3",
    "7.4",
    "7.5",
    "7.6",
    "7.7",
    "7.8",
    "7.9",
    "7.10",
    "7.11",
    "7.12",
    "7.13",
    "7.14",
    "7.15",
    "7.16",
    "7.17",
    "7.18",
    "7.19",
    "7.20",
    "7.21",
    "7.22",
    "7.23",
    "7.24",
)

STAGE_8_SECTION_NUMBERS = (
    "8.1",
    "8.2",
    "8.3",
    "8.4",
    "8.5",
    "8.6",
    "8.7",
    "8.8",
)

STAGE_9_SECTION_NUMBERS = (
    "9.1",
    "9.2",
    "9.3",
    "9.4",
    "9.5",
    "9.6",
    "9.7",
    "9.8",
    "9.9",
    "9.10",
    "9.11",
    "9.12",
    "9.13",
    "9.14",
    "9.15",
    "9.16",
    "9.17",
    "9.18",
    "9.19",
    "9.20",
    "9.21",
    "9.22",
    "9.23",
    "9.24",
    "9.25",
    "9.26",
    "9.27",
    "9.29",
)


def section_headings(path) -> tuple[str, ...]:
    """Every `### ` line of a stage file, in file order."""
    return tuple(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("### ")
    )


def section_numbers(path, stage: int) -> tuple[str, ...]:
    """The `<stage>.<k>` addresses of a stage file, in file order."""
    return tuple(
        match.group(1)
        for line in section_headings(path)
        if (match := re.match(rf"### ({stage}\.\d+)(?=\s|$)", line))
    )


@pytest.mark.parametrize(
    ("stage", "path", "frozen", "size"),
    [
        (2, STAGE_2, STAGE_2_SECTION_NUMBERS, 4),
        (6, STAGE_6, STAGE_6_SECTION_NUMBERS, 29),
        (7, STAGE_7, STAGE_7_SECTION_NUMBERS, 24),
        (8, STAGE_8, STAGE_8_SECTION_NUMBERS, 8),
        (9, STAGE_9, STAGE_9_SECTION_NUMBERS, 28),
    ],
    ids=["2", "6", "7", "8", "9"],
)
def test_stage_section_grid_is_stable(stage, path, frozen, size):
    """Each stage's `###` addresses are ordered, unique and never lose one."""
    assert len(frozen) == size
    found = section_numbers(path, stage)
    assert list(found) == sorted(found, key=lambda s: int(s.split(".")[1]))
    assert len(found) == len(set(found))
    assert set(found) >= set(frozen)


# --- two more companion-text surfaces, all derivable -----------------------
#
# (e) The command stage 1 names for instantiating a ledger, against the
#     subcommand the module actually exposes. Stage 1 stopped telling the
#     orchestrator to COPY the template; if the module's `new` command were
#     renamed, the stage text would send it to a command that does not
#     exist, and nothing else would notice.
# (f) The ledger is not the fixer's to edit. The rule is stated twice — in
#     the agent definition and in the spawn prompt built from the template —
#     because a spawn carries the prompt and not the file, so a rule missing
#     from either is a rule the fixer of that round never saw.

LEDGER_MD_MODULE = SCRIPTS_DIR / "ledger_md.py"
# The module's first subcommand, `new`, read off its source constant rather than
# hand-copied: this gate compares the stage text against what the module
# exposes, so the module is the side that must be derived.
SUBCOMMAND_ASSIGNMENT_RE = re.compile(r'^NEW = "([a-z-]+)"$', re.MULTILINE)
# The forbidding sentence, in the exact wording both fixer texts carry.
FIXER_LEDGER_BAN = "never edit `fix-ledger.md` — not a cell"


def test_stage_1_names_the_subcommand_the_module_exposes():
    """The stage instantiates the ledger by the command that exists."""
    match = SUBCOMMAND_ASSIGNMENT_RE.search(text_of(LEDGER_MD_MODULE))
    # Fail-closed: no constant read means nothing was compared.
    assert match is not None, "no NEW constant in ledger_md.py"
    stage = text_of(STAGE_1)
    assert f"ledger_md.py {match.group(1)} " in stage
    assert "--template" in stage
    assert "--out" in stage


def test_the_fixer_is_told_in_both_texts_not_to_edit_the_ledger():
    """The agent file and the spawn prompt carry the same forbidding line."""
    for path in (FIXER_AGENT, FIXER_PROMPT):
        assert FIXER_LEDGER_BAN in flat(path).lower(), str(path)


# --- the prose registry: sentences whose whole existence is their wording ---
#
# A rule the skill states in prose and nothing executes is held by a literal
# match and nothing else. Those matches are data in `prose_pins.py`: a record
# names the shipped file, the literal, the reason the sentence matters, and
# where the rule needs it the exact count or the `### ` section that owns the
# literal. The one test below reads every record; a pin none of the record's
# forms can state stays a function above, with a comment saying why.


@pytest.mark.parametrize(
    "pin", PROSE_PINS, ids=[f"{pin.file}::{pin.literal[:40]}" for pin in PROSE_PINS]
)
def test_every_prose_pin_holds(pin):
    """The record's literal stands in its file, its section and its count.

    A section runs from its `### <number>` heading to the next `### `
    heading and is matched with its line wrapping collapsed; a `flat` record
    is matched as `flat()` matches, wrapping collapsed and case folded. The
    heading is found by the same address rule `section_numbers` reads —
    the number followed by whitespace or the end of the line — so a bare
    heading the grid test accepts is a heading this test finds too.
    """
    text = text_of(REPO_ROOT / pin.file)
    if pin.section is not None:
        lines = text.splitlines()
        heading = re.compile(rf"### {re.escape(pin.section)}(?=\s|$)")
        start = next(
            (i for i, line in enumerate(lines) if heading.match(line)), None
        )
        assert start is not None, f"{pin.file}: no section {pin.section}"
        body = []
        for line in lines[start + 1 :]:
            if line.startswith("### "):
                break
            body.append(line)
        text = " ".join(" ".join(body).split())
    literal = pin.literal
    if pin.flat:
        text = re.sub(r"\s+", " ", text).lower()
        literal = literal.lower()
    if pin.count is None:
        assert literal in text, f"{pin.literal[:40]}… missing"
    else:
        assert text.count(literal) == pin.count, f"{pin.literal[:40]}… count"


# --- the worked example's dates run forwards -------------------------------
#
# The defect this closes was a fictional date in the worked example that sat
# LATER than dates the schema puts after it. It was fixed pointwise; the
# class was not. What the schema orders is checked here and nothing else: a
# ledger's `Round-started` comes before every verification pass, the passes
# run in the order they are numbered, and the round is closed last. Dates
# the schema does NOT order — a residue ratified in an earlier round, a
# register's review date years out — are deliberately outside the check:
# they are legitimately older or newer than the round they appear in.

WORKED_ROUND_DIR = REPO_ROOT / "examples" / "worked-round"
ROUND_STARTED_RE = re.compile(r"^- Round-started:\s*(\S+?)\.?\s*$", re.MULTILINE)
LEDGER_CLOSED_RE = re.compile(
    r"^- Ledger state:\s*closed\s+(\d{4}-\d{2}-\d{2})", re.MULTILINE,
)
# A timestamp as the schema writes it: an ISO date, optionally with a time.
TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:T(\d{2}:\d{2}:\d{2})Z?)?$")
PASSES_HEADER_START = "| # | pass (scope) |"


def as_instant(value: str, *, end_of_day: bool) -> str | None:
    """Return a comparable `date time` string, or None if this is not one.

    A date with no time is compared at the START of its day when it opens a
    range and at the END when it closes one, so that a round started at
    `09:00` on the day it closed is chronological rather than an offence.
    """
    match = TIMESTAMP_RE.match(value.strip().strip("`"))
    if match is None:
        return None
    day, clock = match.group(1), match.group(2)
    if clock is None:
        clock = "23:59:59" if end_of_day else "00:00:00"
    return f"{day} {clock}"


def passes_table_timestamps(text: str) -> list[tuple[str, str]]:
    """Every `started`/`ended` cell of the verification-passes table, in order.

    The two columns are OPTIONAL (a round with observability off omits them
    entirely), so an absent column is silence and not a failure. They are
    found BY NAME, the way the recount finds every column it reads.
    """
    lines = text.splitlines()
    found: list[tuple[str, str]] = []
    for index, line in enumerate(lines):
        if not line.strip().startswith(PASSES_HEADER_START):
            continue
        header = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if "started" not in header or "ended" not in header:
            return []
        first, last = header.index("started"), header.index("ended")
        for row in lines[index + 2 :]:
            stripped = row.strip()
            if not stripped.startswith("|"):
                break
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) != len(header) or set(stripped) <= set("|- :"):
                continue
            found.append((cells[first], cells[last]))
        return found
    return found


def chronology_offences(name: str, text: str) -> list[str]:
    """Every place the file's dates run backwards where the schema orders them."""
    offences: list[str] = []
    started = ROUND_STARTED_RE.search(text)
    closed = LEDGER_CLOSED_RE.search(text)
    opened_at = (
        as_instant(started.group(1), end_of_day=False) if started else None
    )
    closed_at = as_instant(closed.group(1), end_of_day=True) if closed else None
    if opened_at and closed_at and opened_at > closed_at:
        offences.append(
            f"{name}: Round-started {started.group(1)} is later than "
            f"the closure {closed.group(1)}",
        )
    previous = opened_at
    previous_label = "Round-started"
    for number, (raw_start, raw_end) in enumerate(
        passes_table_timestamps(text), 1,
    ):
        for label, raw, end_of_day in (
            (f"pass {number} started", raw_start, False),
            (f"pass {number} ended", raw_end, True),
        ):
            instant = as_instant(raw, end_of_day=end_of_day)
            if instant is None:
                continue
            if previous is not None and instant < previous:
                offences.append(
                    f"{name}: {label} {raw} is earlier than "
                    f"{previous_label}",
                )
            if closed_at is not None and instant > closed_at:
                offences.append(
                    f"{name}: {label} {raw} is later than the closure",
                )
            previous, previous_label = instant, label
    return offences


def test_the_worked_examples_dates_run_forwards():
    """Every ordered date of the shipped example is non-decreasing."""
    files = sorted(WORKED_ROUND_DIR.glob("*.md"))
    # Fail-closed: no example read means nothing was checked.
    assert len(files) >= 3, [str(path) for path in files]
    anchored = 0
    offences: list[str] = []
    for path in files:
        text = text_of(path)
        if ROUND_STARTED_RE.search(text):
            anchored += 1
        offences += chronology_offences(path.name, text)
    # And the checker must have had at least one file with anchors to read.
    assert anchored >= 1, [str(path) for path in files]
    assert offences == [], offences


# The same example text with ONE date moved backwards, and a passes table
# whose rows run backwards: the checker above must reject both, or its
# silence on the real files says nothing.
BACKWARDS_PASSES = (
    "- Round-started: 2026-08-09T09:00:00Z.\n"
    "- Ledger state: closed 2026-08-09.\n"
    "\n"
    "| # | pass (scope) | verdicts (L/P/NOT) | started | ended |\n"
    "|---|---|---|---|---|\n"
    "| 1 | first | 1/0/0 | 2026-08-09T10:00:00Z | 2026-08-09T11:00:00Z |\n"
    "| 2 | second | 1/0/0 | 2026-08-09T09:30:00Z | 2026-08-09T12:00:00Z |\n"
)


def test_the_chronology_checker_rejects_a_swapped_date():
    """The negative fixture: the same checker, a date put out of order."""
    text = text_of(WORKED_ROUND_DIR / "fix-ledger.md")
    swapped = text.replace(
        "- Round-started: 2026-08-09T09:00:00Z.",
        "- Round-started: 2026-08-19T09:00:00Z.",
    )
    assert swapped != text, "the fixture no longer matches the example"
    assert chronology_offences("swapped", swapped) != []


def test_the_chronology_checker_rejects_a_backwards_passes_table():
    """A pass that starts before the previous one ended is an offence too."""
    offences = chronology_offences("backwards", BACKWARDS_PASSES)
    assert offences != []
    assert "pass 2 started" in offences[0]


def passes_header_cells() -> list[str]:
    """The header cells of the template's verification-passes table."""
    for line in text_of(LEDGER_TEMPLATE).splitlines():
        if line.strip().startswith(PASSES_HEADER_START):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    raise AssertionError("the verification-passes table header is gone")


def test_the_passes_table_carries_the_verifier_count_column():
    """The `verifiers` column exists, `new findings` keeps its position."""
    cells = passes_header_cells()
    assert "verifiers" in cells, cells
    assert cells.index("new findings") == 3, cells
    assert (
        "`verifiers` = how many verifiers the pass had"
        in text_of(LEDGER_TEMPLATE)
    )


# --- the shell harness's table headers stay in sync with the fixture builders

# The harness that drives the shell fixtures is frozen by a signed non-goal
# of this package; its table headers are copied by hand into the fixture
# builders of conftest.py rather than shared through one function. This
# test is the only thing standing between the two copies drifting silently.

REGRESSION_HARNESS = REPO_ROOT / "tests" / "run-regression.sh"
HEADER_CAPTURE_RE = re.compile(r"^H(8|9)?='([^']*)'", re.MULTILINE)


def test_the_regression_headers_match_the_conftest_headers():
    """Each shell-side table header equals the fixture-builder constant it names.

    The frozen harness enumerates the pairs; a builder constant with no
    harness counterpart is out of scope for this check.
    """
    text = text_of(REGRESSION_HARNESS)
    matches = list(HEADER_CAPTURE_RE.finditer(text))
    # Three captures expected; an extraction bug that finds fewer or more
    # must not pass this test vacuously.
    assert len(matches) == 3, matches
    by_suffix = {None: HEADER_7, "8": HEADER_8, "9": HEADER_9}
    for match in matches:
        expected = by_suffix[match.group(1)]
        captured = match.group(2) + "\n"
        assert captured == expected, (
            "the regression harness is frozen by a signed non-goal of this "
            "package; if this pair diverges, the repair belongs to the "
            "change that edited the conftest header or to a reversal of "
            "that freeze — never to an edit here"
        )
