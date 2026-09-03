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
