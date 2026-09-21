Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Stage 2 — Scope and lenses

Explicit sub-steps, in this order:

### 2.1 Scope

**(a) Scope.** The orchestrator fixes: the object (paths/commits), mode,
an id prefix for EACH lens and one for the `NOTICED OUTSIDE BATCH` block
(assigned here, not by critics; letter-led, letters and digits only —
the recount script's id contract depends on it), the models per the role
table in the router (escalation only on the user's explicit word, offered as one
line with price), the batch-commit executor (impl: per project
convention), and a timebox per lens. Object
pin = the state at round start; verification always runs against the
CURRENT head — third-party edits mid-round produce new findings via
stage 6, they do not break the round.
**The prefixes are DECLARED in machine form, and that declaration is
the only source of the lens count.** The header's `Lenses:` field
carries, directly under it and with nothing between them, one line per
lens — ` - <PREFIX> | <lens name> | <model>`, the prefix in the id
contract's own alphabet. `scripts/recount.py` reads `k`, the lens
count of the residual-defect estimate, from that run of lines and from
nowhere else; everything softer about a lens (its timebox, `owner-set`,
a dropped lens) goes in prose BELOW the run, because reading stops at
the first line that is not of that shape. The round's verifier-prefix
stem is recorded in its own header field, `Verifier passes:`, and never
among those lines: a verifier writes its rows under `V1`, `V2`, … by the
SAME id contract as a lens, so a `k` counted off the findings table
would grow with every verification pass. That is why `k` is never
counted there — the exclusion is structural, not a filter that guesses
which prefixes look like a verifier's.
**The prefixes a PROCESS writes are declared here too, in their own
field.** The header's `Process prefixes:` line carries, comma-separated
and in the `Lenses:` alphabet, the prefixes of the rows no lens raises —
the `NOTICED OUTSIDE BATCH` prefix fixed at (a) and the one a class-kill
gate's own row takes — or the literal `none` where this round declared
neither. Like `Verifier passes:` it is a declaration of what is NOT a
lens: it never joins the `Lenses:` run, it never enters `k`, and a prefix
it names may never also be a lens's — the recount refuses the collision.
**The contract is filled and CHECKED here, and its text goes to every
lens.** The nine sections of
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/round-contract.md`
are filled now — object, Goals, Non-Goals as pre-signed dispositions, zone
map, lens panel, stopping rule, residue carried in, declared instrument
set, known limitations — and the two signed blocks are signed before the
first spawn (stage 0's gate). Empty Non-Goals are refused outright: a round
with none will litigate everything, which is the defect the contract
exists to stop. The orchestrator then writes the contract's path and sha
into the ledger header.
The contract's own candidate lists — residue carried in, known
limitations, findings the owner already disposed of — reach a lens only
as part of the contract itself, in either form this section allows: its
text substituted whole, or the one pointer to its path inside the copy.
They are never copied into any OTHER file the critics' mandate makes
them read — not the copy's project rules file, not its README, not a
companion brief or checklist handed with the prompt — because a critic
that meets its own expected findings outside the contract is a coverage
test that measures nothing.
**The ZONE MAP is fixed here and reaches the ledger header here.** The
contract's zone map (§4) assigns EVERY section of the object one of three
zones — `Z1`, mechanically checkable contracts (scripts, acceptance
blocks); `Z2`, normative prose, the obligations a later actor must obey;
`Z3`, informative prose (rationale, history, examples) — and it must cover
the object WHOLE: a map that leaves a section unzoned is a defect of the
CONTRACT, caught before the round opens, not a defect of the round. The
orchestrator writes it into the ledger header's `Zone map:` field at this
stage, as the pointer to the contract's §4, or as the table itself where
the object was under the 400-line gate and the contract was pasted into
the header instead of filed. That field is what stage 6 fills each row's
`zone` cell from. **The contract's TEXT is substituted into the
prompt of EVERY lens** — `{round_contract}` in
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/critic-prompt.md` —
identically and VERBATIM, never re-told, shortened or angled for one
lens: lenses judging against differently-worded scopes produce findings
that cannot be compared, which was observed in every round of the field
series. That substitution is mandatory, and a round whose contract reached
only some lenses is not scoped.
ONE equivalent of the body is allowed,
and only one: where the contract file PHYSICALLY LIES inside the copy the
critics read, the orchestrator MAY substitute into `{round_contract}` a
pointer to that path INSIDE THE COPY instead of the text, under two
conditions that must both hold — (a) the path is IDENTICAL for every
lens, so no lens is pointed at a differently-worded scope, and (b) the
ledger header carries the contract's sha exactly as it does today, so an
edit of the contract mid-round stays detectable. Where the contract's own
location is git-ignored — a project convention such as a local work
directory, or the run folder itself — the orchestrator PUTS it there:
after `copy-project.sh` has run, the contract's text is copied byte for
byte into a file inside the copy (`ROUND-CONTRACT.md` at the copy's root),
and the sha the header carries is taken of THAT file; the copy script
never carries it across, so a contract nobody placed leaves the shortcut
unusable and the TEXT is substituted instead. The placed file is a private
document: it falls under the project's leak/PII sanitization discipline,
fail-closed, exactly as a salvaged report does
(`references/stage-1-run-folder.md`) — where that discipline cannot be run
on the contract, the file is not placed and the shortcut stays unusable;
it lives only inside the copy, is never written into the reviewed
repository, and is removed together with the copy by the closing call of
9.17, in the two-step form that call carries — a copy that call refuses
keeps it, and the ledger's `Scratchpad not cleaned` line names that copy,
in the one-line, sanitized form 9.17 prescribes.
Nothing else moves: a
pointer is not a summary, and re-telling, shortening or angling for one
lens stay forbidden whichever of the two forms is substituted.
**Amendments inside a running round are numbered or they do not exist.**
An amendment is dated, numbered `Amendment <n>` and one sentence long
about what it changes; it is entered into the ledger header's
`Contract amendments:` field — written with `scripts/ledger_md.py
set-header`, never by hand — and into the contract's own Amendments table.
`set-header` replaces the whole field, so the value written restates
every earlier `Amendment <n>` entry, in order, followed by the new one; a
value carrying only the new amendment erases the earlier ones.
An UNNUMBERED amendment does not take effect — there is nothing to point
at later. An amendment touching a field the OWNER signed — the Non-Goals,
the stopping rule, the privacy-gate answer, the models — carries the
owner's signature in the same machine form residue uses,
`user-signed <date>`, and is void without it.

### 2.2 Lenses — non-overlapping, and their count derived

**(b) Lenses — non-overlapping, and their count DERIVED, never
assumed.** It equals the number of the object's independent LOAD-BEARING
hypotheses: a claim whose falsity makes the object unfit (a safety invariant, a
compatibility promise, a cost estimate, a rollback plan, a correctness
claim about a transformation). **Floor 2, ceiling 7.** The object's SIZE
drives a lens's DEPTH ("read it whole, not by sampling"), never the
count. A critical hypothesis does NOT get a second lens of its own: it
gets 2–3 repeated independent passes over the same hypothesis, and a
finding counts only when at least two passes agree. The list of
load-bearing hypotheses is written into the ledger header as the
justification of the count — nothing checks the two against each other —
and is SHOWN to the user before any critic is spawned; the user may strike
an item or add one, and that edit IS the mechanism for a user-supplied
lens, which is added on top of the derived count and MARKED in the
header as owner-given. Silence counts as consent: the list is already in
the header and visible. Each lens declares HERE whether it needs the git
history in its copy. **Hard budget: at most 12 simultaneous agents** —
lenses plus repeated passes plus the owner's lens — checked BEFORE any
spawn; over budget, cut the number of hypotheses getting repeated passes
or run the round in waves, never overrun silently. The actual sum goes
into the ledger header.
**A check that ran outside the panel twice becomes a lens.** A check
performed as a post-closure step or a manual run in TWO consecutive rounds
is declared a lens of the panel from the second time on, instead of being
repeated by hand a third time — that is how the post-closure tail
disappears rather than being lived with. The raised check enters the NEXT
round as one of its load-bearing hypotheses on ordinary terms: it takes a
slot under the ceiling of seven and it counts inside the hard budget of
twelve simultaneous agents. It has no exemption from either — where the
hypotheses already number seven or the budget is spent, the next round's
panel is REBUILT around it; the ceiling is never exceeded.
**One lens may be declared the SECURITY LENS, and that is mechanical.**
The contract's lens panel may name one lens as the round's security lens;
its prefix goes into the ledger header's own `Security lens:` field (the
same alphabet as the `Lenses:` prefixes), and `none` is written there when
no lens was so declared. The consequence is not a label but a default at
stage 6: every finding that lens raises is of the security/PII class
unless the adjudicator removes the default IN WRITING, and the recount
enforces exactly that.

### 2.3 Scratchpad copy

**(c) Scratchpad copy.** `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/scripts/copy-project.sh` makes the copy the
critics read — they work on the COPY, not on the working tree. Strict
reflink clone first where its pre-flight allows it, then the git-known
file list (the history is copied
only for the lenses that declared they need it), then an object-only
narrowing (what each step keeps and strips, secret-class files included,
is the script's entry in `references/templates-and-scripts.md`); every
omission is an `EXCLUDED:` line that goes into the ledger header — a
critic that does not know what it never saw writes a lying coverage
statement.
**The clone runs ONLY when git reports no ignored content under the
project root.** It copies everything on disk while the file-list step
copies what git knows, so on a tree that mixes the project with ignored
runtime state it would WIDEN the copy in silence — and the secret-class
sweep does not catch state that is merely private. The gate is
fail-closed on both conditions (non-empty output OR a non-zero exit code
from the pre-flight blocks the clone) and has no opt-out flag; every
ignored top-level entry becomes an `EXCLUDED:` line of class
`git-ignored`, a failed pre-flight one line of class
`git-preflight-failed`. The consequence is stated, not hidden: a real
repository almost always carries ignored content, so **one copy per
critic is the rare case and ONE SHARED COPY PER ROUND the ordinary
one.** That is the price of minimising disclosure, which is a goal of
this stage and not a side effect of saving space. With a shared copy the
history is available to every lens and that fact is recorded in the
header rather than papered over. Where clones ARE made, the number of
simultaneous clones of a private tree equals the
agent sum, not the lens count.
The `--run-id` handed to the script MUST equal the basename of `--dest`,
and any other value is refused: `cleanup-scratchpad.py` compares the two
at teardown (its condition 7) and would otherwise refuse to remove the
copy — as it also refuses a run directory fewer than three levels below
the scratchpad root (its condition 4), so the copy is placed deeper than
that.
The LAYOUT that satisfies both is fixed here rather than re-derived
every round: the copy is made at
`<scratchpad root>/critic-copies/<object-slug>/<run-id>`, whose three
segments put it exactly at the required depth below the scratchpad root
— that root, and not the copy, is the directory handed to `--root`, while
`--run-id` is the last segment, which is also the basename of `--dest`.
The two upper segments are the CALLER's duty: the orchestrator creates
them — `mkdir -p` on the parent of `--dest` — before calling the script,
which refuses a `--dest` whose parent does not exist and creates only the
last segment itself.

### 2.4 The round profile

| profile | assigned when | passes | batches |
|---|---|---|---|
| **F** (few) | fewer than 8 confirmed findings | second pass skipped by default (9.2), connectedness pass as 8.3 plans it | batches as findings fall under the ceiling of 7.6, plus the tail batch of 7.7 |
| **M** | 8 to 19 | second pass skipped by default and run on the user's word (9.2); a pass so run may be narrowed residue-scoped under the three conditions of 9.5, whose (c) is the owner's signature (9.6); connectedness pass as 8.3 plans it | batches by zone and kind (7.6) plus the tail batch of 7.7 |
| **L** | 20 or more | second pass mandatory (9.2), full-scope (8.2) unless that same narrowing is granted (9.5, 9.6), and the connectedness pass of 8.3 | batches by zone and kind (7.6) plus one tail batch of NOTICED minors (7.7) |

The profile is ASSIGNED at the close of stage 6 from the recount's upheld
count — never from a count made by hand — and written into the ledger
header as `- Profile:` by the
orchestrator (no script writes that line); a contract may FIX the profile
in advance in its stopping rule (§6), and then stage 6 records the fixed
value. A profile compresses passes and batch granularity only: it changes
no model, no lens already spawned, no severity route (6.22) and no
signature the contract requires.

Output: a ledger file with a filled header and the critics' copies made.
