# Residue register — {project}

<!-- THE ADDRESS. This file lives at `.critic-ledger/residue-register.md`,
     in the ROOT of the project's `.critic-ledger/` directory and NEVER
     inside a run folder: the register outlives every run, and a run folder
     is deleted, archived and superseded on its own schedule. That address
     is also the convention `scripts/recount.py` derives when it is given
     no `--register <path>`. -->

<!-- WHAT IT IS. One row per finding that was NOMINATED into residue — a
     defect the round chose to carry rather than to fix. A nomination is an
     act of the ORCHESTRATOR, made at machine speed; it becomes ACCEPTED
     risk only when the owner ratifies it. The register is the durable side
     of that: the ledger row says a nomination exists, this file says what
     was accepted, why, against what compensating control, and when it must
     be looked at again. -->

<!-- PRIVACY — stated here explicitly, not inherited. Writing to this file
     is a durable write outside any run folder, so the two salvage gates
     apply to it word for word:
     (1) BEFORE the FIRST write to the register in a given project, confirm
         the repository is private, by the same mechanism and the same
         fail-closed rule as before the first salvage. No confirmation, no
         write: the nomination is not made and the finding stays open.
     (2) The free text of `rationale` and `compensating-control` goes
         through the project's leak/PII sanitization discipline, fail-closed,
         exactly as a salvaged critic report does.
     The path `.critic-ledger/residue-register.md` is also covered by the
     stage-1 ignore check and by the project's publication-exclusion list.
     A register that no ignore entry or exclusion covers is a STOP until the
     owner says otherwise, never a silent write. -->

<!-- APPEND-ONLY. Rows are added and their `status` cell is advanced. No
     row is deleted and none is archived: a register that can be tidied is a
     register that gets tidied. The queue is shortened by the owner's
     ratification cadence and by the escalation forks below, and by nothing
     else. -->

| run-qualified id | severity | claim-hook | rationale | compensating-control | review-by | status | origin-run |
|---|---|---|---|---|---|---|---|

<!-- CELL CONTRACT — `scripts/recount.py` parses this table and fails
     CLOSED on any violation (exit 2, the same rule as a malformed ledger
     row). A literal pipe inside any cell MUST be escaped as `\|`.

     `run-qualified id`  — the finding's ledger id qualified by its run:
                           `<run-folder-name>/<id>`. One row per nominee;
                           a duplicate is a structural error.
     `severity`          — the severity the finding was ruled at. `blocker`
                           may NEVER appear: a blocker is categorically
                           non-nominable, and the recount rejects it both
                           here and in the ledger row.
     `claim-hook`        — the finding's hook line, so the row is readable
                           without opening the run folder.
     `rationale`         — WHY the risk is carried. Mandatory; a blank cell
                           is a structural error.
     `compensating-control`
                         — what limits the risk meanwhile. Mandatory. The
                           literal `none — direct risk accepted` is a
                           legitimate value — a blank cell is not.
     `review-by`         — calendar-valid ISO date at which the acceptance
                           must be looked at again. Defaults: 30 days for a
                           major, 1 year for a minor. Both numbers are OURS,
                           marked as ours; no standard supplies them.
     `status`            — `nominated <date>` -> `ratified <date>` ->
                           `expired-reopened <date>`, or `nominated <date>`
                           -> `withdrawn <date>` when the nomination is
                           withdrawn, each carrying the date it was set. Only
                           the expired-reopened status may carry its cycle
                           counter, as `expired-reopened <date> (#<n>)`.
     `origin-run`        — the run folder the nomination was made in. It
                           stays put when the row is carried across later
                           rounds. -->

## Deadlines, and what happens when one passes

<!-- All three are printed by the recount at EVERY run and none of them
     changes an exit code: they are obligations on the orchestrator, not
     gates on the script. -->

- **An UNRATIFIED nomination expires too.** A row left in `nominated` for
  more than 30 days (ours, marked as ours) is printed as
  `NOMINATION OVERDUE` and goes to the owner as its own fork: ratify it,
  withdraw the nomination — the row's status becomes `withdrawn <date>`,
  and the finding goes back to stage 6 of its round as an open finding
  while its round is open, and enters the next round on this object as a
  re-opened finding once that round is closed — or set a new date on the
  owner's explicit word. A permanently
  `nominated` row is banned: every row has a ratification, an escalation, or
  a way back into the open findings.
- **`review-by` passing RE-OPENS by default,** never renews in silence. The
  recount prints `REVIEW-BY EXPIRED`, and the row enters the next round on
  this object as a re-opened finding of that round's disposition.
- **The second cycle stops the batch act.** A row expiring a SECOND time —
  and equally a finding nominated again after it has once been
  `expired-reopened` — is never ratified inside the batch act and never
  renewed in silence. It goes to the owner as a separate fork carrying a
  FRESH justification: what changed since the first acceptance, why the risk
  is accepted again, what compensating control appeared. Until that fork is
  decided the row counts as an open finding of the round, not as residue.

## Ratification

<!-- The act that turns a nomination into accepted risk. It is the owner's
     and no one else's; the mechanics are stage 9 of the skill
     (references/stage-9-closure.md) and are not restated here. -->

- Batches of at most ten per act of the owner, on the owner's own cadence.
  Ten is not a new number: it is the batch limit this discipline already
  uses, carried over.
- The whole queue is shown BEFORE the act, not only the ten being signed.
- Ratifying writes both sides: `accepted-residue user-signed <date>` into
  the ledger row's terminal cell, `ratified <date>` into this file's
  `status` cell. No row is ratified by silence.
- A row of the security/PII class NEVER rides inside the batch act. It
  reaches the owner one at a time, carrying the conclusion of an
  independent re-check made by an actor or a tool OTHER than the one that
  proposed accepting it, and that conclusion is recorded in this row. The
  same one-at-a-time rule holds whenever a security/PII row's
  `compensating-control` is the literal `none — direct risk accepted`.
