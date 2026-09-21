"""The prose registry: shipped sentences held by a literal match.

A rule the skill states in prose and nothing executes is kept from a silent
deletion by a literal match and nothing else. Each record below is one such
match: the file under the plugin root that must hold the literal, the
literal itself, and the reason the sentence matters. Three optional fields
narrow the match. `count` is the exact number of occurrences, set wherever
the rule is a number rather than a presence. `section` is the number of the
`### ` section that must hold the literal, set wherever the rule lives in
one section rather than anywhere in its file; a section is matched with its
line wrapping collapsed. `flat` matches its text — the file, or the section
when one is also set — with line wrapping collapsed and case folded, for
sentences the files wrap at 78 columns and capitalize as they please; a
record with neither `flat` nor `section` is matched exactly as the file
spells it.

`test_every_prose_pin_holds` in `test_payload_invariants.py` reads every
record. A pin whose assertion none of these forms can state stays a function
in that file.
"""

from __future__ import annotations

from typing import NamedTuple


class Pin(NamedTuple):
    """One literal a shipped file must hold, and why."""

    file: str
    literal: str
    reason: str
    count: int | None = None
    section: str | None = None
    flat: bool = False


AGENTS = "agents/"
REFERENCES = "skills/critic-ledger/references/"
TEMPLATES = "skills/critic-ledger/templates/"

SKILL_MD = "skills/critic-ledger/SKILL.md"

FIXER_AGENT = AGENTS + "fixer.md"
VERIFIER_AGENT = AGENTS + "verifier.md"
CRITIC_IMPL_AGENT = AGENTS + "critic-impl.md"
CRITIC_PLAN_AGENT = AGENTS + "critic-plan.md"
EXECUTOR_AGENT = AGENTS + "executor.md"
STAGE_0 = REFERENCES + "stage-0-prerequisites.md"
STAGE_1 = REFERENCES + "stage-1-run-folder.md"
STAGE_2 = REFERENCES + "stage-2-scope-and-lenses.md"
STAGES_3_5 = REFERENCES + "stages-3-5-critics-salvage-layout.md"
STAGE_6 = REFERENCES + "stage-6-adjudication.md"
STAGE_7 = REFERENCES + "stage-7-fix-batches.md"
STAGE_8 = REFERENCES + "stage-8-verification.md"
STAGE_9 = REFERENCES + "stage-9-closure.md"
OBSERVABILITY = REFERENCES + "observability.md"
READINESS_SCALE = REFERENCES + "readiness-scale.md"
TEMPLATES_AND_SCRIPTS = REFERENCES + "templates-and-scripts.md"
CONTRACT_TEMPLATE = TEMPLATES + "round-contract.md"
LEDGER_TEMPLATE = TEMPLATES + "ledger.md"
FIXER_PROMPT = TEMPLATES + "fixer-prompt.md"
VERIFIER_PROMPT = TEMPLATES + "verifier-prompt.md"
CRITIC_PROMPT = TEMPLATES + "critic-prompt.md"
EXECUTOR_PROMPT = TEMPLATES + "executor-prompt.md"
README_MD = "README.md"
WHY_CRITICS = "docs/why-critics.md"


PROSE_PINS = (
    # --- the round-contract template -------------------------------------
    Pin(
        CONTRACT_TEMPLATE,
        "(OWNER SIGNS)",
        "The template carries its two signature blocks, which the stage-0 "
        "gate checks for; the file is copied out of the plugin and read on "
        "its own, so it has to carry them itself.",
        count=2,
    ),
    Pin(
        CONTRACT_TEMPLATE,
        "Owner signature:",
        "Each of the template's two signature blocks carries its own owner "
        "signature line; two blocks, two lines.",
        count=2,
    ),
    Pin(
        CONTRACT_TEMPLATE,
        "out-of-scope-by-contract",
        "The template names the literal a finding under a pre-signed "
        "Non-Goal is closed with.",
    ),
    Pin(
        CONTRACT_TEMPLATE,
        "400 LINES",
        "One of the template's two numbers, marked in the file itself as "
        "the plugin's own rather than borrowed.",
    ),
    Pin(
        CONTRACT_TEMPLATE,
        "HALF AN HOUR",
        "The other of the template's two numbers, marked in the file itself "
        "as the plugin's own rather than borrowed.",
    ),
    Pin(
        CONTRACT_TEMPLATE,
        "Amendment",
        "The template carries the amendments a signed contract is changed "
        "by.",
    ),
    Pin(
        CONTRACT_TEMPLATE,
        "never manufactures one out of silence",
        "A pre-signed answer counts as the owner's signature only where it is "
        "written; the sentence forbids reading a signature into an empty "
        "answer.",
        flat=True,
    ),
    # --- the ledger template ----------------------------------------------
    Pin(
        LEDGER_TEMPLATE,
        "no script reads or writes this line",
        "The header's profile line is prose the main session fills by hand; "
        "the sentence stops a later reader from looking for a script that "
        "owns it.",
        count=1,
        flat=True,
    ),
    # --- the fixer and the verifier ---------------------------------------
    Pin(
        FIXER_AGENT,
        "reproduce the defect before editing",
        "The fixer reproduces the defect before editing: stated in the agent "
        "definition and in the prompt that spawns it.",
        flat=True,
    ),
    Pin(
        FIXER_AGENT,
        "stop if the premise does not hold",
        "The agent definition pairs the reproduction step with its stop: a "
        "premise that does not hold ends the fix.",
        flat=True,
    ),
    Pin(
        FIXER_PROMPT,
        "REPRODUCE THE DEFECT BEFORE YOU EDIT",
        "The spawn prompt states the reproduction step in its own words, so "
        "a fixer spawned without the agent definition still reads it.",
    ),
    Pin(
        STAGE_7,
        "at most twice",
        "The return limit is counted per id, and both non-terminal outcomes "
        "share it: the second return of an id is never a third fix.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "returned:<n>",
        "The per-id return count has a literal the ledger records it in.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "nominating a blocker is banned outright",
        "A blocker row cannot be nominated into residue, so its second "
        "return has one route: a fork to the owner.",
        flat=True,
    ),
    Pin(
        VERIFIER_PROMPT,
        "Deviations from the pass instruction (if any) and"
        " why.",
        "The verifier's report carries a deviation field, stated in the "
        "file that holds it.",
        flat=True,
    ),
    Pin(
        VERIFIER_PROMPT,
        "one further field is mandatory and is not a section left to your"
        " initiative",
        "The deviation field is a report FIELD, not a section left to the "
        "agent's initiative.",
        flat=True,
    ),
    Pin(
        VERIFIER_PROMPT,
        "write it even when it is empty",
        "An empty deviation field is written, not omitted, so its absence "
        "never reads as no deviation.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "read-back",
        "The verifier definition carries a second, narrow duty at its own "
        "moment, distinct from stage 8.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "pre-commit read-back of stage 7",
        "The verifier's second duty is named by its moment: the read-back "
        "before a batch commit.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "no per-id verdicts and you walk no deleted lines",
        "The read-back is narrower than a verification pass: no verdicts "
        "per id and no deleted-line walk.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "the criterion's one command — a tool the round declared, or the"
        " probe recorded at adjudication as the criterion — may be executed",
        "The bullet that forbids writing says what the read-back may run.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "changed lines of the batch's diff",
        "The read-back re-reads the lines the batch's diff changed, never "
        "whole sections, and the definition says it in the words stage 7 "
        "uses, so the pair cannot drift apart.",
        flat=True,
    ),
    Pin(
        FIXER_PROMPT,
        "as a reader would",
        "The spawn prompt makes the fixer re-read the whole block around an "
        "edited sentence, so a sentence the edit broke is caught in the "
        "batch.",
        count=1,
        flat=True,
    ),
    Pin(
        FIXER_AGENT,
        "as a reader would",
        "The agent definition carries the same re-reading step as the spawn "
        "prompt, so the pair cannot drift apart.",
        count=1,
        flat=True,
    ),
    Pin(
        FIXER_PROMPT,
        "MEASURED EDIT",
        "A value an edit depends on is measured before the batch and handed "
        "to the fixer, which never estimates it and returns a block that "
        "lacks it.",
        count=1,
        flat=True,
    ),
    Pin(
        FIXER_AGENT,
        "MEASURED EDIT",
        "The agent definition states the measured-value rule in the words of "
        "the spawn prompt, once.",
        count=1,
        flat=True,
    ),
    Pin(
        VERIFIER_PROMPT,
        "You NEVER run the object",
        "The spawn prompt bars the verifier from running the object as its "
        "own evidence; the one command it runs is the criterion's.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "never run the object",
        "The agent definition carries the same bar on running the object as "
        "the spawn prompt, so the pair states one rule.",
        flat=True,
    ),
    Pin(
        VERIFIER_PROMPT,
        "OPENS WITH EXACTLY ONE LINE",
        "A new finding of the verifier is read by the transcription script "
        "only from its one header line; the prompt says which forms the "
        "script takes and which it skips or drops.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "opens with exactly one line",
        "The agent definition states the header-line form of a new finding "
        "in the words of the spawn prompt, so the pair cannot drift apart.",
        flat=True,
    ),
    Pin(
        VERIFIER_PROMPT,
        "negative factual claim",
        "A claim that something is absent carries its command and output in "
        "the verifier's spawn prompt, which is read on its own.",
        flat=True,
    ),
    Pin(
        VERIFIER_AGENT,
        "negative factual claim",
        "The verifier definition carries the rule that a claim of absence "
        "comes with its command and output.",
        flat=True,
    ),
    Pin(
        VERIFIER_PROMPT,
        "major = a fact/contract distortion",
        "The verifier's spawn prompt carries the severity scale itself, in "
        "the words of the router, because it is read without the router.",
        flat=True,
    ),
    # --- the executor -------------------------------------------------------
    Pin(
        EXECUTOR_AGENT,
        "blind to the adjudication",
        "The agent that runs a critic's commands is shown neither the "
        "findings nor their verdicts, so its output stays independent of "
        "what the round expects it to print.",
        flat=True,
    ),
    Pin(
        EXECUTOR_AGENT,
        "every command is run as written",
        "A handed-over command is run verbatim before any correction, so the "
        "output answers the command the critic wrote rather than a "
        "paraphrase of it.",
        flat=True,
    ),
    Pin(
        EXECUTOR_PROMPT,
        "you judge nothing",
        "The spawn prompt limits the agent to running and reporting, so no "
        "verdict on a finding can come out of the run.",
        flat=True,
    ),
    # --- the critics' prompt and definitions ------------------------------
    Pin(
        CRITIC_PROMPT,
        "negative factual claim",
        "A claim that something is absent carries its command and output in "
        "the critic's spawn prompt, which is read on its own.",
        flat=True,
    ),
    Pin(
        CRITIC_IMPL_AGENT,
        "negative factual claim",
        "The code critic's definition carries the rule that a claim of "
        "absence comes with its command and output.",
        flat=True,
    ),
    Pin(
        CRITIC_PLAN_AGENT,
        "negative factual claim",
        "The document critic's definition carries the rule that a claim of "
        "absence comes with its command and output.",
        flat=True,
    ),
    Pin(
        CRITIC_PROMPT,
        "major = a fact/contract distortion",
        "The critic's spawn prompt carries the severity scale itself, in the "
        "words of the router, because it is read without the router.",
        flat=True,
    ),
    Pin(
        CRITIC_PROMPT,
        "filed as an UNVERIFIED hypothesis",
        "A finding that depends on a run the critic did not make is marked "
        "and carries the command that settles it, and is judged on that "
        "command's output.",
        flat=True,
    ),
    Pin(
        CRITIC_IMPL_AGENT,
        "filed as an UNVERIFIED hypothesis",
        "The code critic's definition marks a run-dependent finding in the "
        "words of the spawn prompt, so the pair cannot drift apart.",
        flat=True,
    ),
    Pin(
        CRITIC_PROMPT,
        "IMMUTABLE anchor",
        "The critic cites by an anchor the round's own edits do not shift "
        "wherever the object has one.",
        flat=True,
    ),
    Pin(
        CRITIC_PROMPT,
        "touches nothing outside the scratch copy it is run on",
        "A command the critic hands over is bounded to the copy it runs on, "
        "stated where the critic writes it.",
        flat=True,
    ),
    # --- stages 0 and 1 -----------------------------------------------------
    Pin(
        STAGE_0,
        ".critic-ledger/<run>/fix-batch-<n>-{before,after}/",
        "Degraded snapshots are named, with the path they live at inside the "
        "run folder.",
    ),
    Pin(
        STAGE_0,
        "BANNED",
        "The snapshot rule marks the forbidden place in capitals, with its "
        "mechanical reason beside it.",
    ),
    Pin(
        STAGE_0,
        "never reused and never overwritten",
        "A snapshot folder is written once: never reused, never overwritten.",
        flat=True,
    ),
    Pin(
        STAGE_0,
        "`subagent-model: unset`",
        "The subagent model is recorded when the variable is unset, and the "
        "round goes on.",
        flat=True,
    ),
    Pin(
        STAGE_0,
        "`subagent-model: set <non-model-value>`",
        "The subagent model is recorded when the variable holds something "
        "that is not a model, and the round goes on.",
        flat=True,
    ),
    Pin(
        STAGE_0,
        "this is a record, not a gate: the round continues either way",
        "Both outcomes of the subagent-model read are recorded, and neither "
        "refuses the round.",
        flat=True,
    ),
    Pin(
        STAGE_0,
        "re-derived against the copy before stage 1",
        "Notes a consumer project carries over go stale when the installed "
        "copy is refreshed and the skill never re-checks them, so the stage "
        "that opens a round names who does and when.",
        flat=True,
    ),
    Pin(
        STAGE_1,
        "explicit word, never silently",
        "The first run's ignore entry waits for the user's explicit word.",
        flat=True,
    ),
    Pin(
        STAGE_1,
        "silence is not consent",
        "Consent to the ignore entry is a word, or the stage fails closed: "
        "silence is not consent.",
        flat=True,
    ),
    Pin(
        STAGE_1,
        "the run folder is not created",
        "Without consent to the ignore entry the stage fails closed and "
        "creates no run folder.",
        flat=True,
    ),
    Pin(
        STAGE_1,
        "are not moved automatically",
        "Old run addresses have two lawful outcomes; the first is that the "
        "plugin never moves them itself.",
        flat=True,
    ),
    Pin(
        STAGE_1,
        "a project may relocate them itself",
        "The second lawful outcome for old run addresses: the project may "
        "relocate them.",
        flat=True,
    ),
    Pin(
        STAGE_1,
        "the new address governs new runs",
        "Once a project relocates its old runs, new runs follow the new "
        "address.",
        flat=True,
    ),
    # --- stage 2 ------------------------------------------------------------
    Pin(
        STAGE_2,
        "the clone runs only when git reports no ignored content under"
        " the project root",
        "The strict clone is gated on git reporting no ignored content.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "fail-closed on both conditions",
        "The clone's gate fails closed on either of its two conditions.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "has no opt-out flag",
        "The clone's gate cannot be switched off by a flag.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "must equal the basename of `--dest`",
        "The run id rule the copy script enforces: a divergent run id makes "
        "the copy unremovable at teardown.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "condition 7",
        "The stage names the copy script's condition that enforces the run "
        "id rule.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "`<scratchpad root>/critic-copies/<object-slug>/<run-id>`",
        "The canonical scratchpad layout, which the copy script's conditions "
        "4 and 7 imply, is written down once.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "that root, and not the copy, is the directory handed to `--root`",
        "The layout says which of its directories the copy script takes as "
        "its root.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "`--run-id` is the last segment",
        "The layout says where the run id sits in the copy's path.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "where the contract file physically lies inside the copy the"
        " critics read, the orchestrator may substitute into"
        " `{round_contract}` a pointer to that path inside the copy",
        "The contract may reach a lens as a pointer inside the copy: the "
        "bounded equivalent of pasting the body.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "(a) the path is identical for every lens",
        "The first of the in-copy pointer's two conditions.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "(b) the ledger header carries the contract's sha",
        "The second of the in-copy pointer's two conditions.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "identically and verbatim",
        "The pointer changes the FORM only; the scope every lens reads stays "
        "one and the same.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "re-telling, shortening or angling for one lens stay forbidden",
        "The in-copy pointer does not license a different scope text for "
        "any lens.",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "they are never copied into any other file the critics' mandate"
        " makes them read",
        "The contract's candidate lists reach a lens only inside the "
        "contract, so a critic cannot meet its expected findings elsewhere "
        "and the coverage it reports stays a real test.",
        section="2.1",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "compresses passes and batch granularity only",
        "The profile narrows passes and batch cuts and nothing else: no "
        "model, lens, severity route or required signature moves with it.",
        section="2.4",
        flat=True,
    ),
    Pin(
        STAGE_2,
        "never from a count made by hand",
        "The profile letter comes from the recount's upheld count, so two "
        "readers of the same ledger assign the same profile.",
        section="2.4",
        flat=True,
    ),
    # --- stages 3-5 and stage 6 ---------------------------------------------
    Pin(
        STAGES_3_5,
        "Verbatim salvage outranks local formatting and lint hooks:"
        " where the environment physically prevents writing the text,"
        " writing past the hook is part of the stage, not"
        " improvisation — except a hook that blocks on CONTENT (a"
        " secret or credential scanner), which is never written past:"
        " its block is raised as a finding of the round.",
        "A pointwise rule of the salvage stage, asserted against the file "
        "that holds it.",
        flat=True,
    ),
    Pin(
        STAGES_3_5,
        "An agent that died on a server error has no report:"
        " fragments are never salvaged, the stage is respawned with a"
        " fresh actor, and one line of fact goes into the ledger.",
        "A pointwise rule of the salvage stage, asserted against the file "
        "that holds it.",
        flat=True,
    ),
    Pin(
        STAGES_3_5,
        "The extractor reads the subagent's task TRANSCRIPT, never the"
        " indented hand-back the harness shows the orchestrator",
        "A salvage made from the indented, HTML-escaped hand-back is not "
        "verbatim; the sentence sends the extractor to the transcript.",
        flat=True,
    ),
    Pin(
        STAGES_3_5,
        "as written, on the scratch copy made for that report's commands",
        "A command a critic hands over is run verbatim and only on a "
        "disposable copy; without the phrase an executor may paraphrase the "
        "command or run it against the repository itself.",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "A design fork goes to the owner: it is never closed by an"
        " adjudication verdict.",
        "A pointwise rule of adjudication, asserted against the file that "
        "holds it.",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "The orchestrator's own probe run before adjudication is"
        " named `probe-to-criterion`: the probe becomes a class-L1"
        " criterion, and the verifier re-executes it live.",
        "The probe's name spans two stages, so its sentence is pinned once "
        "per stage; this is the adjudication half.",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "Before adjudicating a new refutation the orchestrator checks"
        " the run's own `precedents.md`: the file is an INPUT"
        " document of the round, not only an output.",
        "A pointwise rule of adjudication, asserted against the file that "
        "holds it.",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "grep",
        "The staleness sweep is a step only if its section says so, and the "
        "sweep is mechanical: the section names its tool.",
        section="6.12",
    ),
    Pin(
        STAGE_6,
        "noticed",
        "The staleness sweep's findings enter the ledger as NOTICED rows, "
        "and the section that owns the sweep says so.",
        section="6.12",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "same step",
        "A donor convention in the precedents file without its ledger row is "
        "a kill the recount cannot see, so the two writes are one step.",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "at the first adjudication batch",
        "The precedents file is opened at one fixed moment, so a missing "
        "file tells a reader that adjudication has not begun rather than "
        "that nothing repeated.",
        section="6.4",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "never the route of a major or a blocker",
        "A profile shortens passes and batches only; without the sentence a "
        "short profile could park an upheld NOTICED major in the tail wave.",
        section="6.22",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "run against the real text of the object before",
        "A draft criterion that prints the wrong number is caught at "
        "adjudication, not handed to the fixer to discover.",
        section="6.25",
        flat=True,
    ),
    Pin(
        STAGE_6,
        "as soon as that critic's report is salvaged",
        "The executor of a critic's commands starts on each report's "
        "arrival, so its outputs are ready when adjudication begins instead "
        "of queued behind the last report.",
        section="6.26",
        flat=True,
    ),
    # --- stage 7 ------------------------------------------------------------
    Pin(
        STAGE_7,
        "a do-not-touch fence in that prompt is traceable to this batch's"
        " plan",
        "An edit-scope fence with no collision note is an orchestrator bug, "
        "so every fence traces to its batch's plan.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "the plan of the same batch carries the collision note",
        "The fence and its collision note live in one batch's plan.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "lifted before the fixer is spawned",
        "A fence that collides with the batch is lifted before the fixer "
        "starts, not after.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "travel to stage 6 as new findings",
        "Rows noticed outside a batch take the same route as a verifier's "
        "new findings.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "never straight into the next fix batch",
        "Rows noticed outside a batch have no shortcut into the next batch.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "the fourth nomination occasion of stage 9",
        "The route to the residue register is discoverable from the stage "
        "that produces such rows.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "the class-kill disposition instead closes by reference to that"
        " criterion",
        "A class kill may close by reference to an existing criterion: the "
        "form of the obligatory reaction changes, the obligation does not.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "no new gate script and no separate row",
        "Closing a class kill by reference adds neither a gate script nor a "
        "row.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "an orchestrator entry naming the donor row goes into the ledger",
        "Closing a class kill by reference leaves an entry naming the donor "
        "row.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "obligatory, not a right",
        "The class-kill reaction stays obligatory when it closes by "
        "reference.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "never the right to skip it",
        "Closing by reference changes the form of the reaction and never "
        "grants a right to skip it.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "and every other write-capable agent — strictly sequentially",
        "The sequencing mechanism was dropped, the obligation was not: "
        "write-capable agents run one after another.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "only after its report has arrived and the batch is committed",
        "The next write-capable agent starts only once the previous one's "
        "batch is committed.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "between batches the tree is confirmed quiet with `git status`",
        "The quiet tree between batches is confirmed by a command, not "
        "assumed.",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "same step",
        "The mirror of the adjudication rule on the side that closes by "
        "reference to a donor: the row travels with its donor.",
        section="7.19",
    ),
    Pin(
        STAGE_7,
        "waves of deferred",
        "Recurrence is detected across waves, so a profile that compresses "
        "them changes the odds; said once, in the section that owns the "
        "rule.",
        section="7.19",
    ),
    Pin(
        STAGE_7,
        "verification passes",
        "Recurrence is detected across verification passes, so a profile "
        "that compresses them changes the odds; said in the section that "
        "owns the rule.",
        section="7.19",
    ),
    Pin(
        STAGE_7,
        "never by a helper"
        " agent",
        "The ban on delegating a ledger write is stated once, in the "
        "section that owns the act of closing a batch; the other stage "
        "files point there instead of repeating it.",
        count=1,
        section="7.17",
    ),
    Pin(
        STAGE_7,
        "replaced by a fresh agent at the nearest checkpoint",
        "A fixer carried across batches accumulates stale context, so the "
        "rule that swaps it for a fresh one is stated in the section that "
        "owns resuming.",
        section="7.3",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "only when they are minor",
        "Only minor rows may wait in the accumulated wave; a graver "
        "noticed row keeps its own route.",
        section="7.7",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "one tail batch",
        "The accumulated minors close the cycle in a single batch, not one "
        "micro-batch per wave.",
        section="7.7",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "the only requirement of this skill",
        "The consumer project's commit convention owns the title of a batch "
        "commit; the skill asks only for the finding ids.",
        section="7.16",
        flat=True,
    ),
    Pin(
        STAGE_7,
        "changed lines of the batch's diff",
        "The read-back re-reads the lines the batch's diff changed, never "
        "whole sections, and says it in the words the verifier definition "
        "uses, so the pair cannot drift apart.",
        section="7.18",
        flat=True,
    ),
    # --- stage 8 ------------------------------------------------------------
    Pin(
        STAGE_8,
        "A class-L1 criterion born as a `probe-to-criterion` is"
        " re-executed live by the verifier, never read off the"
        " fixer's report",
        "The probe's name spans two stages, so its sentence is pinned once "
        "per stage; this is the verification half.",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "with no overlap and no hole",
        "The union rule of a lens-split pass is what stops a split from "
        "losing an id.",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "the freshness rule above applies to every one of them by name",
        "Every verifier of a split pass is held to the freshness rule.",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "it holds on an unsplit pass too",
        "The full-criterion rule is about the verifier's canon, not a "
        "property of the split mode.",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "the deterministic deleted-line walk is divided by that same rule"
        " and divided explicitly",
        "On a split pass ids are split by scope and deleted lines by file, "
        "both in writing.",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "names the one verifier of the pass that walks them all",
        "A split pass may give the whole deleted-line walk to one named "
        "verifier.",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "the union covers every deleted-line of the batch with no hole",
        "However the walk is divided, no deleted line of the batch is left "
        "unwalked.",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "--diff-filter=M",
        "A new file is not rework, and counting it flips the full-inspection "
        "switch on an object nobody reworked; the formula names the filter.",
    ),
    Pin(
        STAGE_8,
        "added: <n> lines in <k> new files",
        "The lines a round added in new files are reported beside the "
        "rework share, not inside it.",
    ),
    Pin(
        STAGE_8,
        "planned once per round",
        "The whole-object pass is planned at one point per profile, and "
        "that point is written in this section alone.",
        section="8.3",
        flat=True,
    ),
    Pin(
        STAGE_8,
        "from the executor's output",
        "A criterion that would mutate the live object is judged from what "
        "the executor printed, never re-run by a verification pass.",
        section="8.6",
        flat=True,
    ),
    # --- stage 9 ------------------------------------------------------------
    Pin(
        STAGE_9,
        "the pair is qualified where the round ever had a marked row",
        "A clean pair of passes is qualified where the round ever had a "
        "marked row.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "closed by the pass's own hands",
        "The qualification covers a marked row closed by the pass itself.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "the qualification is senior to that threshold",
        "The clean-pass qualification outranks the soft threshold of "
        "twenty findings.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "per-lens sustained rate",
        "The framing tightening is read off a per-lens sustained rate.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "the condition is paired",
        "The sustained rate is never read alone: the framing tightening is a "
        "paired condition, said in words.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "shelf share",
        "The sustained rate is paired with the shelf share.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "`residue-scoped second pass`",
        "The third mode of the second verification pass has a name.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "only when all three conditions hold at once",
        "The residue-scoped pass needs all three of its conditions at once.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "(a) pass 1 was full-scope in the sense of stage 8",
        "The first condition of the residue-scoped pass.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "(b) pass 1 returned 0 not landed on the round's original ids",
        "The second condition of the residue-scoped pass.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "(c) an explicit owner signature exists for this round, written"
        " into the ledger verbatim",
        "The third condition of the residue-scoped pass.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "absence of any one of the three returns the binary rule above",
        "One missing condition of the three returns the binary rule.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "the narrowing is a right, not a default",
        "The residue-scoped narrowing is a right, not a default.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "without the owner's signature in the ledger the second pass is"
        " executed in full",
        "Without the owner's signature the second pass runs in full.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "no other actor may grant the narrowing",
        "Only the owner's signature grants the narrowing.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "the orchestrator may render the owner's human phrase into the"
        " machine literal",
        "The right to render the owner's phrase into the machine literal and "
        "the duty to quote it are one rule.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "must carry the phrase verbatim beside the `user-signed` literal"
        " it was rendered into",
        "The rendered literal carries the owner's phrase verbatim beside it.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "a licence to transcribe granted without the duty to quote would"
        " legalise a signature manufactured out of silence",
        "The duty is not detachable: the recount sees the literal only, so "
        "the licence alone would legalise a manufactured signature.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "condition (a) takes stage 8's sense of full-scope whole",
        "Condition (a) reads full-scope off stage 8, so it inherits the "
        "deleted-line walk rule.",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "a pass whose walk left a hole is not full-scope here either",
        "A pass whose deleted-line walk left a hole does not satisfy "
        "condition (a).",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "written with `scripts/ledger_md.py set-header`, never by hand",
        "The closing header write goes through the writer that refuses a "
        "frozen or unfinished ledger; a hand edit skips that refusal.",
        section="9.18",
        flat=True,
    ),
    Pin(
        STAGE_9,
        "senior to every line of this section",
        "The per-profile lines of the second pass never override the "
        "qualification of a round that once had a marked row.",
        section="9.4",
        flat=True,
    ),
    # --- the addendum's references --------------------------------------------
    Pin(
        OBSERVABILITY,
        "state = ",
        "The receiver's reference names the liveness command of the "
        "receiver on macOS.",
    ),
    Pin(
        OBSERVABILITY,
        "is-active",
        "The receiver's reference names the liveness command of the "
        "receiver on Linux.",
    ),
    Pin(
        OBSERVABILITY,
        "--status running --services",
        "The receiver's reference names the liveness command of the "
        "Docker collector, and names it exactly once.",
        count=1,
    ),
    Pin(
        READINESS_SCALE,
        "exits 0, or does not regress from the recorded baseline exit `<n>`",
        "A command already failing before the fix is a baseline, not a bar.",
        flat=True,
    ),
    Pin(
        READINESS_SCALE,
        "the baseline is recorded at adjudication",
        "The baseline is taken at adjudication, so the rule that a criterion "
        "never changes afterwards is untouched by it.",
        flat=True,
    ),
    Pin(
        READINESS_SCALE,
        "class:security-pii",
        "The baseline rule names the class its carve-out applies to.",
        flat=True,
    ),
    Pin(
        READINESS_SCALE,
        "a security command that already fails is a finding of the round"
        " in its own right",
        "Without the carve-out an already-failing security command becomes "
        "the bar it must merely not regress from, and the finding "
        "disappears.",
        flat=True,
    ),
    Pin(
        READINESS_SCALE,
        "has two forms",
        "A mutating level-1 command splits between a scratch copy the "
        "verifier may run it on and a live object only an executor touches; "
        "losing the split lets a read-only actor change the tree.",
        flat=True,
    ),
    # --- the inventory of templates and scripts -----------------------------
    Pin(
        TEMPLATES_AND_SCRIPTS,
        "nothing in the router repeats it",
        "The inventory names where the difference between two installed "
        "copies is read and says the router does not carry it; without the "
        "sentence a refreshed copy changes with no place that says what "
        "changed.",
        flat=True,
    ),
    # --- the fixer's tree ---------------------------------------------------
    Pin(
        FIXER_PROMPT,
        "the live working tree, never the critics",
        "The spawn prompt tells the fixer which tree it edits, in the same "
        "phrase as the agent definition, once.",
        count=1,
    ),
    Pin(
        FIXER_AGENT,
        "the live working tree, never the critics",
        "The agent definition tells the fixer which tree it edits, in the "
        "same phrase as the spawn prompt, once.",
        count=1,
    ),
    # --- the router ---------------------------------------------------------
    Pin(
        SKILL_MD,
        "asserts nothing about which actor implements it",
        "The router defines the orchestrator once, as a role, so that moving "
        "a stage to another actor changes the role table and not the "
        "definition.",
        count=1,
        flat=True,
    ),
    Pin(
        SKILL_MD,
        "not a third mode",
        "The router states that a run which only verifies is a round of "
        "either mode and not a value of the ledger's mode field.",
        flat=True,
    ),
    # --- the front door -----------------------------------------------------
    Pin(
        README_MD,
        "**There is no external benchmark for any of this, and none"
        " is claimed.**",
        "The front door stopped quoting efficacy figures and says plainly "
        "that no benchmark exists.",
        flat=True,
    ),
    Pin(
        README_MD,
        "Collecting that evidence is planned, not done",
        "The front door says the evidence is not collected yet.",
        flat=True,
    ),
    Pin(
        WHY_CRITICS,
        "**These numbers are provenance, not efficacy evidence.**",
        "The one file that keeps the withdrawn figures says what they are.",
        flat=True,
    ),
)
