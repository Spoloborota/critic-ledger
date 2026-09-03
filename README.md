# critic-ledger

[![CI](https://github.com/Spoloborota/critic-ledger/actions/workflows/tests.yml/badge.svg)](https://github.com/Spoloborota/critic-ledger/actions/workflows/tests.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](pyproject.toml)

Critics find real defects; the loss is what happens next. Findings get "fixed on
the spot" from a summary, a large share of the fixes never fully land, and
nothing in the process notices — so the following round re-finds what was
supposedly repaired, and the word "fixed" stops carrying information.

This plugin packages one discipline against that, for teams running
agent-applied fixes — anyone whose critics' findings must actually land.

- A **round** sends parallel read-only critics at the object under separate
  lenses, judges their findings refute-by-default, hands the upheld ones to a
  separate fixer in small batches, and lets a fresh verifier re-derive every
  claimed fix.
- A **fix-ledger** keeps one row per finding, and the round ends only when a
  script confirms no row is left open.

**It is an expensive procedure** — a round spawns several agents and reads the
object whole, so it runs on an explicit request and never starts itself. The
discipline is held to its own rule: it changes only through a critic round run
on the proposed change.

```mermaid
flowchart TD
    Setup["Stage 0-2: prerequisite, run folder, scope and lenses"]
    Critics{"Stage 3: critic round, parallel lenses"}
    Salvage["Stage 4: immediate salvage"]
    Layout["Stage 5: mechanical layout"]
    Adjudication["Stage 6: adjudication, refute-by-default"]
    FixBatch["Stage 7: fix batch, fixer"]
    Verification["Stage 8: verification, fresh verifier"]
    Recount{{"Stage 9: recount, zero non-terminal rows"}}
    Closed(["Round closed"])

    Setup --> Critics
    Critics --> Salvage
    Salvage --> Layout
    Layout --> Adjudication
    Adjudication -->|upheld| FixBatch
    FixBatch -->|fixed| Verification
    FixBatch -->|criterion-unworkable / premise-not-found| Adjudication
    FixBatch -->|NOTICED OUTSIDE BATCH| Adjudication
    Verification -->|PARTIAL / NOT LANDED: new batch| FixBatch
    Verification -->|new findings| Adjudication
    Verification -->|LANDED| Recount
    Recount -->|two clean passes / residue-scoped pass| Closed
    Recount -->|non-terminal rows remain| Adjudication
```

The stage machine collapsed to its product-facing shape — the ten stages are
indexed in `skills/critic-ledger/SKILL.md`'s Stage machine section, and the
retry conditions drawn above are normative in that skill's
`references/stage-7-fix-batches.md`, `references/stage-8-verification.md` and
`references/stage-9-closure.md`.

## A worked example

Three rows from sanitized real rounds run on this repository: a blocker that was
fixed, a finding that was refuted, and — kept visible rather than quietly
dropped — a residue the owner signed off on instead of fixing. Field values are
quoted from the ledger, trimmed where `…` marks it; the full ledger — with its
verification-pass table and column-by-column legend — is in
[`examples/worked-round/`](examples/worked-round/); read
[how to read it](examples/worked-round/README.md) first.

### DA-2 · blocker → `verified-landed`

> **Claim:** The closure script did not parse every row it was given: a row with
> a stray pipe … was skipped without a word … the script still announced the
> round closable …
>
> **Verdict:** confirmed; reproduced on a fixture whose single damaged row
> disappeared from the count while the exit code stayed 0.
>
> **Criterion:** L1 command and exit code — a fixture ledger carrying one
> unparsable row makes the script exit 2 and print that line's number …
>
> **Fix:** `a1b2c3d` — **verified:** LANDED (V1).

### HB-3 · major → `refuted-with-reason`

> **Claim:** The document was said to have grown two rules … that appeared in
> none of the design notes behind it … normative content nobody sanctioned.
>
> **Verdict:** refuted with command evidence: reading the file as it stood
> before the rewrite showed both rules already present …
>
> **Criterion:** —
>
> **Fix:** — a refuted finding ends at its verdict.

### DC-1 · major → `accepted-residue` (user-signed 2026-08-06)

> **Claim:** The evidence figures quoted in the public text form a fingerprint …
>
> **Verdict:** confirmed as a class of risk … the link back to the author is
> INTENDED … the figures carry the evidence a reader needs …
>
> **Criterion:** L2 deterministic structural check … (upheld criterion,
> deliberately left unsatisfied).
>
> **Fix:** no fix — owner decision on the published figures; the row is residue,
> not a landing (attribution is intended; re-signed by the owner).

Live `recount.py` output over that ledger, captured from a real run rather
than written as an illustration. Reproduce it from
[`examples/worked-round/`](examples/worked-round/) with
`python3 ../../skills/critic-ledger/templates/recount.py fix-ledger.md`:

```text
rows: 12 | terminal: 12 | non-terminal: 0
severity distribution (terminal/rows): blocker 1/1 | major 8/8 | minor 3/3
upheld/refuted: 11 upheld, 1 refuted
residual-defect ESTIMATE (Jackknife capture-recapture): N-hat 14.0 | D 8 raised | f1 8 single-lens | k 4 (HA, HB, HC, HD)
  ESTIMATE is ADVISORY, reported and never acted on: it enters no stop rule and no exit code. Lens diversity does not invalidate it (the source measured little or no impact on the estimate), but the caution that remains is OURS and is named as ours: our four field measurements put the single-lens share at 75-94% and N-hat near 2*D, and they count D as distinct CONFIRMED findings where this line counts distinct RAISED ones, so comparability is not established. Treat the number as advice, not as a target.
new-findings curve: 1 -> 1 -> 0
  time axis: n/a (no started/ended columns — v1 passes table)
ROUND CLOSABLE: zero non-terminal rows.
```

## What this is built on

The discipline was not designed from theory; it was derived from watching
remediation fail. Findings fixed in bulk from a critic's summary came back
partly applied or not applied at all, nothing in the process noticed, and
the following round re-found them. What stopped that was itemizing each
finding with its own address and readiness criterion, handing the batch to a
separate fixer, and letting a fresh verifier re-derive every claimed fix
instead of reading the fixer's report. Every rule here is paired with the
defect that forced it.

**There is no external benchmark for any of this, and none is claimed.** No
controlled comparison against a baseline, no outside arbiter, no efficacy
figure in this README. Collecting that evidence is planned, not done: the
instrument shipped in 0.2.0 — the optional `observability` flag and its
trace and rollup scripts (see [Privacy](#privacy)) — but the measurement
itself has not been taken, and the CHANGELOG says so at every release rather
than quietly.

**The first two below are hard limits; the rest is due diligence.**

- Hard: **one object class.** Every closed run behind these rules was a
  normative document. Nothing here has been exercised on code to the same
  depth.
- Hard: **the verifiers share a model family** with the critics and the
  fixer; the re-derive mandate and the deterministic checks mitigate
  self-preference, they do not solve it. Verifier freshness is measured
  externally, but its *cost* here is not.
- Dogfooding — developing the discipline by running it on its own documents
  — is circular by construction, and an independent trace audit reduces the
  self-checking without removing it.
- The plugin does not decide *when* to call critics — that stays with the
  user, which is why it is gated on an explicit request.

The observations the rules grew out of — the counts, their caveats, and
which defect forced which rule — are in
[`docs/why-critics.md`](docs/why-critics.md), recorded there as provenance
rather than as proof that the discipline works.

## Install

```text
/plugin marketplace add Spoloborota/spoloborota-plugins
/plugin install critic-ledger@spoloborota-plugins
```

Then, on an object you want torn apart:

```text
/critic-ledger plan <path-to-document>
/critic-ledger impl <path-or-commit-range>
```

**What a round costs:** at least 2 agent runs — two critics, when nothing they raise is
upheld — around 4 on a typical small object, never more than the hard budget of 12
simultaneous agents. Wall-clock, token and dollar cost is not measured, and no number
for it is invented here. Since 0.2.0 the instrument exists — an optional
`observability` flag, **on by default since 0.3.0**, that records per-round token and
duration counts into local files (see [Privacy](#privacy)) — but the measurement it
enables has not been taken, so there is still no figure to quote.

Results land in a per-run folder `.critic-ledger/<timestamp-object>/` inside the
reviewed repository — that round's ledger and, where it is private, the verbatim
critic reports. Updates reach installed copies only on a `version` bump;
auto-update is off.

## Privacy

The plugin makes no network calls — nothing it produces ever leaves your
machine. There is no analytics service and no telemetry upload of any kind.

**Observability is on by default.** With it on, a round writes two files into
that round's own folder `.critic-ledger/<run>/` inside the reviewed repository
— `trace.jsonl` and `round-summary.json` — plus the cross-project
`rounds.jsonl` described below. All of them are local files you own and can
delete, computed from your own rounds; **nothing is sent anywhere** — no
network call, no endpoint, no upload of any kind. Turning it off is one line:
`"observability": false` in `pluginConfigs`, or `--config observability=false`
at install.

Everything it produces is a local file you own: the per-run `.critic-ledger/`
folder, git-ignored before it is created, and the scratch copies each critic
reads, removed by the cleanup script. Where the reviewed repository is public
or shared, the verbatim critic reports never enter it — they go instead to a
local unversioned holding marked as not durable.

### Observability — what it is, and what it writes

The flag is the plugin option `observability`: a boolean, `true` by default.
Turn it off non-interactively at install time with
`claude plugin install critic-ledger@spoloborota-plugins --config observability=false`,
or at any time through `/plugin configure`; setting it back to `true` turns it
on again. The value is read from `pluginConfigs` in your **user**
`settings.json`. On Claude Code **v2.1.207 and later** a repository you clone
cannot switch it on for you — *"Entries in a project's `.claude/settings.json`
or `.claude/settings.local.json` are ignored"* — while on **older installs** it
can, because before v2.1.207 those entries were read.

With the flag on, a round writes three files and nothing else:

- **`.critic-ledger/<run>/trace.jsonl`** — one line per unit of work in that
  round, beside that round's ledger. Deleting the file is the complete opt-out
  for it.
- **`.critic-ledger/<run>/round-summary.json`** — that round's rolled-up counts
  and durations, written beside the ledger at closure from the trace and the
  ledger themselves. Deleting the file is the complete opt-out for it.
- **`~/.claude/plugins/data/critic-ledger-*/rounds.jsonl`** — one line per
  **closed** round. This file **accumulates across rounds and across projects
  until you delete it**; `rm ~/.claude/plugins/data/critic-ledger-*/rounds.jsonl`
  is the complete opt-out for it, and `claude plugin uninstall` removes the whole
  data directory unless `--keep-data` is given.

**The trace's fields, in full** (`trace.jsonl`): `v`, `kind`, `round`, `span`,
`parent`, `stage`, `actor`, `unit`, `id_prefix`, `agent_id`, `ids`, `id_tags`,
`flags`, `model_assigned`, `model_actual`, `model_source`, `tokens`,
`tokens_source`, `commit`, `started`, `ended`, `wallclock_s`, `outcome`. Two of
those are identifiers rather than counts, and are named here rather than left to
be discovered: **`agent_id`** is the platform's opaque id for the subagent spawn
a line measures, and **`id_prefix`** is the lens or verifier prefix under which
that actor raises findings. The rest are counts, durations, closed vocabularies
and the run folder's own name. **No field carries free text** — no note, no
message, no finding text, no path outside the run folder, and no content from
the object under review.

**The cross-project rollup's fields, in full** (`rounds.jsonl`): `v`,
`round_key`, `date`, `mode` (the round mode, `plan` or `impl`, and nothing
else), `wallclock_s`, `object` (three counts of how big the reviewed thing was
and how much of it changed — `lines_at_pin`, `changed_lines`, `files_touched` —
and not one file name among them), and the per-lens, per-batch and per-pass
count and duration objects `lenses[]`, `batches[]`, `passes[]`, then `findings`,
`totals` and `metrics`. **No field carries free text** here either. It
deliberately carries **no object name, no absolute clock time and no commit
hash**:
`round_key` is a digest of the run folder's name and `date` is the UTC day the
round closed. That is de-identification, not anonymization — a name you already
guessed can be confirmed by hashing it; what it removes is the ability to read
the list of everything you have ever reviewed off one file.

Token counts come from the completed `Agent` tool result the orchestrator
already receives — its four-counter breakdown where the result carries one,
and its single total where that aggregate is all the result reports. No
transcript is read, and the plugin ships no transcript reader.

## Contributing

This project runs under its own review discipline and does not seek
contributions; [CONTRIBUTING.md](CONTRIBUTING.md) records how to run the tests
and how a change to the discipline is gated.

## License

MIT — see [LICENSE](LICENSE).
