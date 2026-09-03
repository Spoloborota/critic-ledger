Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## Observability (optional, on by default)

Measuring the round's own COST — one span per unit of work in the run
folder's `trace.jsonl`, written by
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/trace.py`, and a
`round-summary.json` beside the ledger, produced by
`${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/rollup.py` — is
OPTIONAL and ON by default; opting out is one line — `"observability": false` in `pluginConfigs`, or `--config observability=false` at install. The switch is read from exactly one line, and
that line is the observability flag line of the router `SKILL.md`.

**Off, nothing happens at any stage**: no file created, no directory
created, no extra instruction read, no number collected. Every per-stage
observability sentence in the stage files `references/stage-*.md` is conditional on the
flag, and each is a no-op while it is off; the ledger's `- Observability:`
and `- Trace:` header lines then read `off` and `none (observability
off)`, which is what tells a later reader that missing numbers mean "off"
and not "lost".

**The privacy invariant.** Everything observability produces is a LOCAL
file the person who ran the round owns. Nothing is sent anywhere. There is
no endpoint, no opt-in-to-share, no aggregation service, and no extension
point where one could be added later without re-opening this discipline
through a round of its own. Numbers reach THIS PLUGIN's author only from
his own machine. A trace written on anyone else's machine stays on that
machine: the flag is on by default and any user can switch it off, and
either way nothing here moves a file anywhere — a trace reaches another
person only if its owner hands it over themselves. The trace
carries no free-text field at all — every value is an enumeration or an
anchored, length-bounded pattern — which is why it needs no sanitization
pass before it can be shown to anyone, unlike the salvaged reports.

**Whatever leaves the machine leaves only through the cleansing
projection.** Local files keep full values, the naming ones included —
anonymization is a property of the SHARING surface, not of collection. Any
output meant to leave the user's machine passes the projection of the
`--rounds` class: a SHA-256 `round_key` in place of the round id, with the
object slug, the commit and the absolute clock stripped. Every NEW
top-level field of `round-summary.json` gets an EXPLICIT projection
disposition — it enters `--rounds` or it does not, and there is no third
state — and every new field also gets an identifiability verdict
(`identifying`, `quasi` or `non-identifying`), recorded as a dated delta to
the field audit before that field ships in a release.

**A missing number is `n/a: <reason>` — never a failure, and never a
blocked round.** A token count that did not arrive is written as JSON
`null` with `tokens_source: "absent"`: never `0`, never `-1`, never
omitted. No metric, script or gate fails because a number is absent, and
the recount's exit codes gain no new value; a missing or unreadable
`trace.jsonl` is reported and changes nothing. Every derived figure that
consumed a `null` prints its coverage inline — `TVR: n/a (7 of 11 spans
without usage)` — instead of averaging the rest, which would be a lie by
omission. Nothing on the observability list can fail a round: a trace
write that errors emits ONE bounded diagnostic line, from a closed
error-class vocabulary and never echoing what it could not read, and the
round continues. A negative claim about usage ("this round had no token
data") is admissible only with the capture's own output attached — the
same rule that makes an unproven negative "not checked" rather than
"absent".
