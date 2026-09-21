Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

**Platform reality — the agents' "orchestrator-only" rule is not enforced.**
Agent definitions have no `disable-model-invocation` equivalent (that field
exists for skills; this skill deliberately does NOT set it, so that a plain
prose request can trigger a round — the router's Gate section and the
description's "explicit user request" requirement are the guard): nothing at
the platform level stops a session from auto-delegating to a `critic-ledger`
agent by description match outside a round. The only guard is the description text of
each definition. This residual risk is ACCEPTED and stated here rather than
papered over — exactly like the fixer's no-git guarantee, which is mechanical
(Bash absent from the tool set) where this one is not.

**Shell hygiene binds the orchestrator's own commands too.** The POSIX form
required of a command handed to a critic or an executor is required of the
orchestrator's own bookkeeping: generated content and dividers are written
with `printf '%s'`, never `echo`, whose zsh form interprets backslash
escapes instead of passing them through; a token that begins with `=` is
quoted (`'==='`), since zsh expands it before any command sees it; and a
list or a whole command is passed as a quoted array (`"${arr[@]}"`), never
a bare `$VAR`, which zsh does not split.
