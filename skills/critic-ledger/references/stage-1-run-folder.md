Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

**Artifact address and privacy.** The round's artifacts live INSIDE the
project under review, in a per-run folder:

```
.critic-ledger/
  2026-01-15-101502-auth-plan/
    fix-ledger.md      fixed name; the run folder carries the uniqueness
    precedents.md      created by the ORCHESTRATOR at the first repeated
                       ruling, never in advance; an empty one never exists
    critics/           verbatim critic reports
    verify/            verbatim verifier reports
```

Seconds are part of the folder name on purpose: two rounds on the same
object inside one minute would otherwise share a directory and mix two
runs' ledgers and manifests. If the name is taken even so, the round
refuses and names the occupied path instead of writing over it; colons are
absent deliberately (they break paths on Windows). The short object name is
at most 32 characters, lowercased, every non-alphanumeric replaced by a
hyphen — the object's FULL path stays in the ledger header, the short name
is only an address. The folder is created at the round's first step (stage
1), entered into the project's `.gitignore` BEFORE it is created, and its
creation is announced to the user on the first run in this project. Project
conventions for durable artifacts, if any, are senior to this default;
register the directory in the project's local index if one exists. Runs
already made under the older `<repo>/critic-rounds/<object-slug>/` address
are not moved automatically; a project may relocate them itself, as a
one-off deliberate decision recorded where that project records decisions.
Either way, the new address governs new runs.

BEFORE the first salvage, confirm the repository is private — and the check
has a MECHANISM, not just a requirement: list the remotes; zero remotes
means local and private; a non-empty list means asking the user with that
list shown, because a remote's privacy cannot be established from the
working tree. The gate is fail-closed: no answer, a command that did not
run, or output that did not parse all count as "not private". Verbatim
critic reports never enter a public/shared repository — keep them in a local
unversioned holding with an explicit "not durable" note instead. Salvage
into any repo is subject to the project's leak/PII sanitization discipline,
fail-closed: if the project declares a sanitization pass and it cannot be
run, the salvage stays out of the repo.

## Stage 1 — Run folder

Explicit sub-steps, in this order:

**(a) Ignore-list BEFORE the folder.** `.critic-ledger/` is entered
into the project's `.gitignore` and the entry confirmed BEFORE the run
folder is created — otherwise a window exists in which artifacts already
sit in the tree and no rule covers them. If the entry cannot be made,
the round does not start.
**On the FIRST run in a project the entry is made after the user's
explicit word, never silently** — a round writes into a file the project
owns, so it asks: state the line to be added and the file, and wait for
the answer. Both the question and the answer happen BEFORE the run folder
is created, so no window opens in which an unignored folder already sits
on disk. The question has exactly TWO outcomes: consent — the entry is
written and the round proceeds to (b); refusal OR no answer — fail-closed,
the round does NOT start and the run folder is not created. Silence is not
consent and there is no third outcome: both readings fall under "if the
entry cannot be made, the round does not start", which until now covered
only a technical failure to write. This is checked on EVERY invocation, not only
the first: a branch switch, a stash, a foreign commit or a regenerated
`.gitignore` can drop it; a missing entry is restored and the user told.
The ignore rule is a DEFAULT a project may override — a project that
deliberately versions its rounds as evidence keeps them versioned,
and what is checked instead is
that the folder sits in that project's publication-exclusion list.
The SAME check covers `.critic-ledger/residue-register.md`, the durable
residue register that sits beside the run folders rather than inside one:
whatever entry or exclusion covers the directory must cover it, and a
register no rule covers is a stop until the user says otherwise, never a
silent write.
**(b) Create the run folder** at the address fixed above
(`.critic-ledger/<YYYY-MM-DD-HHMMSS-object>/`), with its `critics/`
and `verify/` subdirectories, and, on the FIRST run in this project,
tell the user plainly that the folder was created and ignored.
**(c) Blank ledger** `fix-ledger.md` from `${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/ledger.md`, created
in the run folder HERE — before any critic is spawned.
**With observability on**, create an empty `trace.jsonl` in the run
folder and append to it, with
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/trace.py append`,
the `open` record of the round span `s1.00` (`stage: 1`,
`parent: null`, actor `orchestrator`, unit `round`) whose `kind: "span"`
close record is written only at stage 9 — a round interrupted before
then leaves `s1.00` unclosed and a reader says so rather than inventing
an end — then write the header lines fixed at stage 0 and fill
`Round-started` and `Trace:`.
Output: the run folder in place with its `critics/` and `verify/`
subdirectories, the ignore entry confirmed, and a blank ledger inside it.
