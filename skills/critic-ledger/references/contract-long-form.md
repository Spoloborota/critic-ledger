Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## The contract — long form

Principles 1–3 and 5–7 of the router's `## The contract`, verbatim. Principle 4 (the ledger row schema) stands in the router in full and is not repeated here. The closing paragraph is not a principle: it is the drafting rule for the lists a contract declares.

1. **Critics are strictly read-only.** They never edit or write files and
   never run any state-changing git command (checkout/add/stash/restore/
   reset/commit). They observe and report. Read-only commands (grep, counts,
   `git log/show/diff`) are allowed and — for factual claims — required.
2. **Maximum flaws, ZERO solutions.** A critic enumerates as many real or
   potential defects as possible under its assigned lens, each as an atomic
   finding (one finding = one defect) with concrete evidence (file:line,
   exact quote, or command+output). Critics never propose fixes, never
   adjudicate their own findings. Positive confirmations ("checked,
   clean") are NOT findings and take no severity — they belong in the
   report's coverage statement.
3. **Adjudication belongs to the orchestrator (main loop), never to
   critics.** Default to refuting each finding (refute-by-default); every
   security/PII ruling — a refutation exactly as much as an acceptance — is
   re-checked before the owner signs it, by an actor or a tool OTHER than
   the one that ruled (stages 6 and 9), because refuters have been wrong.
   The user owns all "ship it / acceptable / ignore" calls.

5. **Fixes are targeted batches, ≤10 ids each**, applied by a SEPARATE
   fixer subagent — never the main loop that adjudicated — run strictly
   sequentially and with no git access at all. A batch is coherent BY ZONE
   AND BY KIND, as references/stage-7-fix-batches.md 7.6 defines it, not by
   lens and not by claim topic. The ORCHESTRATOR commits after every batch,
   with the finding ids in the commit message and the commit hash written
   into the fix cells immediately. Never "fix" a document by wholesale
   rewrite — rewrites silently drop both fixed and unrelated content; a
   rewrite is a new artifact requiring a fresh round.
6. **Verification is a separate pass by a FRESH actor on EVERY pass** —
   never a continuation of the critic, never a continuation of the previous
   verifier, and structurally never the fixer, since the fixer is a
   subagent of its own. The mandate is "do not trust claimed fixes —
   re-derive". Per-id verdicts LANDED / PARTIAL / NOT LANDED — plus
   `LANDED OTHERWISE (<what was actually done>)` for a fix that closes the
   finding by another route — with file:line evidence, each checked against
   that row's readiness criterion and not against a general impression. For
   mechanically checkable items a deterministic grep/script beats LLM
   judgment.

7. **SEVEN terminal statuses**: `verified-landed` / `refuted-with-reason`
   / `accepted-residue` / `refused-user-signed` /
   `out-of-scope-by-contract` / `frozen-carried` / `logged-no-action`. The fourth exists only for
   findings marked as the security/PII class when they were ruled on; for
   those a refusal is terminal too. Both `accepted-residue` and
   `refused-user-signed` require the user's explicit signature in machine
   form (`user-signed <date>` / `refused-user-signed <date>`, the date a
   calendar-valid ISO one) — silence is not a status. The round closes only
   when a programmatic recount reports zero non-terminal rows.
   `out-of-scope-by-contract` and `frozen-carried` come from the round's SCOPE CONTRACT (stage 0, filled at
   stage 2) and need no LIVE signature, because the owner signed before the
   round opened: `out-of-scope-by-contract (NG-<n>, signed <date>)` closes a
   finding whose whole claim is a declared Non-Goal, and
   `frozen-carried (stop-rule, <date>)` closes a row still open when the
   contract's stop rule fired — the second ends the ROUND, not the finding,
   which enters the next round on this object as a re-opened one. Both are
   recognized only under their complete literal, and neither reaches a row
   marked `class:security-pii` without that row's own live signature.
   `logged-no-action` comes from the round's ZONE MAP: it closes an
   INFORMATIVE finding — one whose `zone` cell reads `Z3` — that the owner
   logged and chose to act on in no way, in a closing batch he signs off in
   ONE act of at most ten rows. It is accepted at that zone alone and only in
   the nine-cell schema, where the `zone` cell exists to be checked at all,
   and it does not reach a row marked `class:security-pii` without that row's
   own live signature either.
   A finding may also be NOMINATED into residue instead of fixed, and a
   nomination is not yet a status: the row waits in the named non-terminal
   state `awaiting-signature (nominated <date>)` until the user ratifies it,
   blockers are categorically non-nominable, and a round holding such a row
   is reported as awaiting ratification, never as closed. The mechanism —
   who nominates, against what register, and how ratification happens — is
   stage 9.

**A list the contract declares is copied, never remembered.** A survival or
completeness list — what a rename legitimately leaves standing, what a sweep
must find — is copied verbatim from the ratified text that defines it, never
enumerated from memory, and names every token shape the identifier takes
(bare word, `UPPER_CASE` variable, hyphenated and path components) or states
which shapes it does not sweep.
