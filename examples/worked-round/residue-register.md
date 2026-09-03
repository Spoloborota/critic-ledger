# Residue register — worked example

> **Both rows are INVENTED for this example.** No id, path, date, actor name,
> rationale or compensating control in either is carried over from a real
> round — the ledger beside this file's `DC-1` row is invented for the same
> reason. A register row is free prose about a risk somebody accepted, and
> free prose is exactly what an example may not borrow. The skeleton this
> file is filled from is
> `../../skills/critic-ledger/templates/residue-register.md`, which carries
> the rules; this file carries only two rows.
>
> **The address is wrong on purpose.** A real register lives at the ROOT of
> the project's own run-folder directory and NEVER inside a run folder,
> because it outlives every run: run folders are archived, superseded and
> deleted on their own schedule, and the record of what risk the project
> accepted may not go with them. It sits beside this ledger only so the
> example is readable in one place.
>
> Two gates run before the FIRST write to a register in any project, by the
> same fail-closed rule as the first salvage of a verbatim report: the
> repository is confirmed private, and the free text of `rationale` and
> `compensating-control` goes through the project's leak and PII
> sanitization. No confirmation, no write — the nomination is not made and
> the finding stays open.

The register is APPEND-ONLY. Rows are added and their `status` cell is
advanced; no row is deleted and none is archived, because a register that can
be tidied is a register that gets tidied. The queue is shortened by the
owner's ratification cadence and by the escalation forks below, and by nothing
else.

| run-qualified id | severity | claim-hook | rationale | compensating-control | review-by | status | origin-run |
|---|---|---|---|---|---|---|---|
| 2026-08-03-091734-bench-report/DC-1 | major | A shipped README table quotes throughput numbers measured on the author's own hardware; the exact combination could be cross-referenced against unpublished benchmark logs if those logs ever surfaced. | The link back to the author is INTENDED and the numbers carry the evidence a reader needs; the residue is the correlation with the private logs, which matters only if those logs ever leak. | The benchmark logs stay unpublished; the table is re-read at every release. | 2026-09-05 | ratified 2026-08-06 | 2026-08-03-091734-bench-report |
| 2026-08-08-143000-copy-script/FA-3 | minor | On one platform the copy script leaves an empty scratch directory behind when it exits on a size ceiling. | The stray directory carries no content and no name from the project under review; fixing it means restructuring the exit path, which is more risk than the defect. | The cleanup script names and removes such directories on its next run, and reports what it removed. | 2027-08-08 | nominated 2026-08-08 | 2026-08-08-143000-copy-script |

The first row is the one this round carried IN: the ledger beside this file
records it as `DC-1`, closed with `accepted-residue user-signed 2026-08-06`,
and its ratification wrote both sides in one act — the ledger's `terminal`
cell and this file's `status` cell. The second row belongs to a different
object and is still a NOMINATION: an act of the orchestrator, made at machine
speed, which becomes accepted risk only when the owner ratifies it. Until
then its ledger row sits in `awaiting-signature`, which is not a status but a
place a row waits — counted apart from an open row, and still exiting 1.

## Deadlines, and what happens when one passes

All three are printed by the recount at every run and none of them changes an
exit code: they are obligations on the orchestrator, not gates on the script.

- **An unratified nomination expires too.** A row left in `nominated` for more
  than 30 days (ours, marked as ours) is printed as `NOMINATION OVERDUE` and
  goes to the owner as its own fork: ratify it, withdraw the nomination — the
  row returns to adjudication as an open finding — or set a new date on the
  owner's explicit word. A permanently `nominated` row is banned.
- **`review-by` passing RE-OPENS by default,** never renews in silence. The
  recount prints `REVIEW-BY EXPIRED` and the row enters the next round on that
  object as a re-opened finding.
- **The second cycle stops the batch act.** A row expiring a SECOND time is
  never ratified inside the batch act and never renewed in silence: it goes to
  the owner as a separate fork carrying a FRESH justification, and until that
  fork is decided it counts as an open finding of the round.

## Ratification

- Batches of at most ten per act of the owner, on the owner's own cadence, and
  the whole queue is shown BEFORE the act, not only the ten being signed.
- Ratifying writes both sides — `accepted-residue user-signed <date>` into the
  ledger row, `ratified <date>` here. No row is ratified by silence.
- A row of the security/PII class NEVER rides inside the batch act. It reaches
  the owner one at a time, carrying the conclusion of an independent re-check
  made by an actor or a tool OTHER than the one that proposed accepting it,
  and that conclusion is recorded in this row. Neither row above is of that
  class.
