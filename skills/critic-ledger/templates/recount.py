#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Reference recount script for a critic-ledger ledger (stage 8, and any
time a count is quoted). Ledger COUNTS, the new-findings CURVE, and the
inter-round DELTA are computed by THIS script, never by hand: manual
counting produced real errors in the rounds this discipline was derived
from; no errors were observed from programmatic counting.

Contract of ledger cell values
------------------------------
- The findings table is the FIRST markdown table whose header row starts
  with `| id |`. Only rows between that header and the next markdown
  heading are counted (a "Disposition of previous rounds" appendix with
  the same shape is NOT part of the round count).
- A row is one line, in one of THREE accepted schemas:
    * 9 cells (v3, current): `| id | sev | zone | claim | verdict |
      criterion | fix | verified | terminal |`;
    * 8 cells (v2): the same row without `zone`;
    * 7 cells (v1, legacy, written before the readiness-criterion column
      existed): the v2 row without `criterion`.
  All three stay recountable: the id is always the FIRST cell and the
  severity the second, while `verified`, `terminal`, `fix` and — since
  the zone column exists — `criterion` are addressed from the END of the
  row (`cells[-1]`, `cells[-2]`, `cells[-3]`, `cells[-4]`), so no schema
  branching is needed for any of them. `criterion` is the FOURTH cell
  from the end at widths 8 and 9 ALIKE; at width 7 the schema has no such
  cell at all and the consistency check below does not apply to those
  rows. A hard index counted from the START of the row is used for NONE
  of `criterion`/`fix`/`verified`/`terminal`: the zone column was
  inserted THIRD precisely so that end-addressing survives it, and a
  `cells[4]` read of a 9-cell row would silently return the `verdict`
  prose instead of the criterion. A literal pipe inside any cell MUST be
  escaped as `\\|`.
- The row's ZONE, and what it does and does not change. The `zone` cell of
  a 9-cell row carries `Z1`, `Z2` or `Z3` — the review depth the round's
  SCOPE CONTRACT assigned to the section of the object the finding lands
  in, taken from the contract's zone map and written by the ADJUDICATOR
  (`templates/transcribe.py` leaves the placeholder `·` there, since
  transcription is literal copying and the zone is a judgment). A zone
  changes the PAPER and the CLOSURE ROUTE of a row and nothing else: it
  never lowers a severity, never relaxes a check, and never weakens the
  fresh-verifier rule. The one mechanical consequence read here is the
  terminal status `logged-no-action`, which no row outside `Z3` may take.
- The ROW SCHEMA IS DECLARED IN THE HEADER, and a declaration that
  disagrees with the table is a STRUCTURAL error. The optional header
  field `Row schema: v1 | v2 | v3` is what tells a reader — this script,
  `templates/transcribe.py`, a verifier — which form the table takes
  without counting cells first. When it is present it must name the width
  the findings header actually has (v1 = 7, v2 = 8, v3 = 9); a value
  outside that vocabulary, a second such field, and a declaration that
  contradicts the table are all structural errors, because a schema
  declared wrong is worse than none. When it is ABSENT nothing changes:
  the width comes from the table's own header, exactly as it always did,
  which is what keeps every ledger written before the field recounting
  unchanged.
- id: a lens/verifier prefix and a number: `<PREFIX>-<n>`. PREFIX is ONE OR
  MORE segments joined by dashes, each segment letter-led and continuing
  with letters and digits: `DA`, `L1`, and the COMPOSITE `V-CIT` a verifier
  writes when the lens it re-checked has to stay visible in the id. The
  number is the tail and every segment is non-empty, so `-1`, `V--1`,
  `1-V` and `V-CIT-` are not ids. A prefix is everything before the final
  `-<n>`, which is how a row is matched to its lens.
  Range ids are banned; duplicate ids are a structural error.
- FAIL-CLOSED parsing (never silent): the accepted row width is the width
  of THIS table's own header — 7, 8 or 9, and mixing them inside one table
  is banned. Any line inside the findings table that starts with `|` but
  is not the header, the separator, or a well-formed row of exactly that
  width is a STRUCTURAL ERROR — the script exits 2 and names the line. A
  dropped row must be impossible, and an unescaped pipe in a 7-cell table
  must not pass as an 8-cell row. A header too narrow for a row to hold
  id, severity, verified and terminal in distinct cells (the degenerate
  `| id |`) is reported by width and its rows are NOT read: the header
  diagnostic is the whole structural report, exit 2, never a traceback.
- Readiness criterion (8- and 9-cell schemas; a 7-cell row carries no such
  column and is not checked): a row whose terminal status is
  `verified-landed` or `accepted-residue` MUST carry a non-empty
  criterion cell that is not a dash (an accepted-residue finding is
  UPHELD — it keeps the criterion written at adjudication); a row whose
  terminal status is `refuted-with-reason` or `refused-user-signed` MUST
  carry exactly the em-dash "—" (deliberately not needed, as opposed to
  forgotten). Any violation is a STRUCTURAL ERROR — exit 2, no count is
  trustworthy until fixed.
- Verdict-cell TAGS, optional and machine-read. The `verdict` cell is free
  adjudication prose, so each tag inside it carries a fixed boundary — an
  alphabet and a terminator — exactly like every other literal this script
  parses:
    * `class:<slug>` names the DEFECT CLASS a finding belongs to. The slug
      is free in meaning but not in alphabet, or it could not be lifted
      back out of the prose: `[a-z0-9-]`, 1-32 characters, terminated by
      the first character outside that alphabet, i.e. extracted by
      `class:([a-z0-9-]{1,32})(?![a-z0-9-])`. Capitals, spaces, dots,
      slashes and underscores are banned; a `class:` whose slug is outside
      the alphabet or longer than 32 is a STRUCTURAL ERROR, never a guess
      at where the slug ends. ONE exception, for compatibility: `class:`
      immediately followed by whitespace, by a `|`, or by the end of the
      cell is English PROSE and not an attempted tag — it is ignored, and
      neither grouped nor reported. Ledgers written before this tag
      existed carry `[class: <name>]` and sentences ending "... the
      security class: user-signed <date>", and an old ledger must recount
      exactly as it did in 0.2.0; a tag never attaches a slug across
      whitespace, so nothing readable is lost. `class:Foo`, `class:.x`
      and an over-long slug stay structural errors. Grouping is by EXACT
      slug match: nothing is normalized, literals are compared.
    * `origin:fix-application from:<batch>` marks a finding whose
      substance is a defect in APPLYING an earlier fix, and names the
      batch whose fix it was. `<batch>` is that batch's identifier — the
      value of the `fix` cell of the row whose fix was applied defectively
      (the per-batch commit hash), or the batch's snapshot-path name where
      no commit sanction exists. Same anchoring, widened to 40 characters:
      `from:([a-z0-9-]{1,40})(?![a-z0-9-])`. A tag whose `from:` cannot be
      read is reported as UNATTRIBUTED and is never charged to the latest
      batch by guess.
    * `shelf:<slug>` marks a REFUTATION that a pre-signed disposition of the
      round's contract closed WHOLLY — the "contract shelf" — and the slug
      names that disposition (`shelf:ng-2`). Optional, set by the
      adjudicator, and read by exactly one report: the shelf share printed
      beside the per-lens sustained rate under `--prev`, which exists so
      that a lens is never judged by its sustained rate alone. Same
      anchoring and the same alphabet as `class:`
      (`shelf:([a-z0-9-]{1,32})(?![a-z0-9-])`), the same fail-closed rule
      for a slug outside it, and the same prose exception: `shelf:`
      immediately followed by whitespace, by a `|`, or by the end of the
      cell is English prose and not an attempted tag.
  A ledger carrying none of these tags recounts exactly as it did before:
  each report below is printed only when the tag it reads is present.
- Terminal cell values that COUNT AS TERMINAL — exactly the seven
  canonical names (aliases, including other-language ones mapped in the
  ledger header, must be normalized to these before the closing recount):
    * starts with "verified-landed" — AND the row's `verified` cell must
      contain "LANDED" and not "NOT LANDED" (consistency check). The
      verification outcome "fixed otherwise than the critic proposed"
      lives in the `verified` cell as the literal
      `LANDED OTHERWISE (<what was actually done>)`: compatible with the
      LANDED substring check, told apart by OTHERWISE, and terminal ONLY
      with a non-empty description in parentheses — a bare
      `LANDED OTHERWISE` or empty `()` is NON-terminal with a diagnostic
      (without a description the outcome is "partial", never terminal);
    * starts with "refuted-with-reason";
    * starts with "accepted-residue" — AND the cell must contain the
      literal "user-signed" (silence is not a signature) FOLLOWED by an
      ISO date: `user-signed <YYYY-MM-DD>`. An undated signature is
      NON-terminal with a diagnostic — the date is what makes the
      signature auditable;
    * starts with "refused-user-signed" — the machine-readable owner
      signature that alone makes a REFUSED security/PII finding terminal;
      it too must carry the date (`refused-user-signed <YYYY-MM-DD>`);
      a bare "refused" without that literal, or the literal without a
      date, is NON-terminal with a diagnostic, never silence.
    * starts with "out-of-scope-by-contract" — the disposition the round's
      SCOPE CONTRACT pre-signed. It needs no live signature (the owner
      signed when the Non-Goals were authored), which is exactly why it is
      recognized only under its COMPLETE literal template,
      `out-of-scope-by-contract (NG-<n>, signed <YYYY-MM-DD>)`: the
      Non-Goal it invokes is named, and the date in the cell is the date
      the contract was signed. Anything shorter — the bare status, a
      missing `NG-<n>`, an undated `signed` — is NON-terminal with a
      diagnostic. ONE combination is a STRUCTURAL error rather than a
      status: a row whose `verdict` carries `class:security-pii` may not
      take this route without a live `user-signed <date>` in the terminal
      cell, because a class both of whose outcomes need the owner's word
      is not disposed of by a signature given in advance.
    * starts with "frozen-carried" — the disposition of a row still open
      when the contract's STOP RULE fired, under the complete literal
      `frozen-carried (stop-rule, <YYYY-MM-DD>)`, the date being that
      row's own freeze. It is terminal FOR THIS ROUND and needs no live
      signature (the owner signed the stop rule before the round opened),
      and — this is the whole difference from `superseded-by-rewrite` — it
      does NOT block closability: a round closed over a fired stop rule is
      a legitimate exit, an unclosable one never is. The row is carried
      into the next round on this object as a re-opened finding.
    * starts with "logged-no-action" — the disposition of an informative
      finding the owner logged and decided to act on in no way. It exists
      ONLY in the v3 schema and ONLY at `zone` = `Z3`: the status is
      reached through a closing batch the owner signs off in ONE act (the
      batch limit of ten, exactly as residue ratification), and the zone
      is what says the finding is informative in the first place. Two
      combinations are STRUCTURAL errors rather than statuses, because
      neither leaves anything to check the condition against:
      `logged-no-action` in a 7- or 8-cell row, which carries no `zone`
      cell at all, and `logged-no-action` in a row whose `zone` is
      anything other than `Z3`. A third is a structural error for the
      same reason it is under `out-of-scope-by-contract`: a row whose
      `verdict` carries `class:security-pii` may not take this route
      without a live `user-signed <date>` in the terminal cell — a class
      both of whose outcomes need the owner's own word never travels
      inside a batch act. No older ledger can be affected by any of the
      three: the status does not exist in them by construction.
  The signature date must be a CALENDAR-VALID date: `9999-99-99` or
  `2026-02-30` is NON-terminal with a diagnostic — a date that cannot
  exist is not auditable. That is the ONLY date check: the script does
  NOT check that the date is not in the future, nor that it postdates
  the finding or the verification.
  Anything else — "open", a date, an empty cell, prose — is NON-terminal.
- TWO NAMED NON-TERMINAL WAITS, told apart from an open row and from each
  other, and counted apart from both:
    * `awaiting-signature (nominated <YYYY-MM-DD>)` — a residue NOMINEE
      queued for the owner's ratification. The date is the nomination's own
      and is mandatory: an `awaiting-signature` cell carrying no
      calendar-valid `nominated <date>` is an ORDINARY OPEN row with a
      diagnostic, because a nomination whose age cannot be read cannot be
      chased. A row whose severity cell says `blocker` may never carry this
      value — blockers are categorically non-nominable and the combination
      is a STRUCTURAL ERROR. Like `accepted-residue`, a nominee is an
      UPHELD finding and keeps the criterion written at adjudication.
    * `awaiting-logged-no-action (listed <YYYY-MM-DD>)` — a `Z3` row
      picked into a closing batch and waiting for the owner's own act, the
      date being the day it was listed. The date is what makes the wait
      ageable, and the limit on it is 30 days — NOT a new number, the
      carry-over of the nomination limit above — after which the row is
      printed under `Z3 CLOSURE OVERDUE` and the orchestrator owes the
      owner its own fork: close it, take it out of the batch (the row goes
      back to adjudication as an open finding), or set a new date on the
      owner's explicit word. A permanent wait is banned here exactly as a
      permanent `nominated` is. Unlike a nomination the date is not what
      NAMES the wait — a cell carrying no readable `listed <date>` is
      still this wait and still exits 1, because the queue it belongs to
      is the one the owner's closing act drains — but such a row is
      REPORTED as unageable, never passed over in silence.
  Both feed the SAME exit-code branch as an open row, so the exit contract
  gains buckets but no new code: FOUR buckets, still TWO codes. The buckets
  are checked in this order and EXACTLY ONE state line is printed, that of
  the first bucket that matches:
    1. any OPEN row (non-terminal and in NEITHER wait) -> `ROUND NOT
       CLOSABLE`, exit 1 — the state this script has always reported;
    2. no open row, at least one `awaiting-signature` ->
       `ROUND AWAITING RATIFICATION`, exit 1 — the round is NOT closed, the
       signature has not been given;
    3. no open row and no `awaiting-signature`, at least one
       `awaiting-logged-no-action` -> `ROUND AWAITING Z3 CLOSURE`, exit 1 —
       the round is NOT closed, the owner's act has not been made;
    4. none of the three -> `ROUND CLOSABLE`, exit 0.
  In the MIXED state (both waits present) `ROUND AWAITING RATIFICATION`
  rules; the `awaiting-logged-no-action` rows still get their own list and
  do NOT get a second state line. Exit 0 therefore means after this change
  exactly what it meant before it: every row of the ledger is terminal,
  ratified residue included.
- A FROZEN ledger (header line `Ledger state:` containing "FROZEN") is
  never closable: the script reports the frozen state and exits 3.
  `superseded-by-rewrite` is a whole-ledger freeze marker, NOT a per-row
  terminal value.
- THE STOP RULE'S FREEZE, and it is not that one. The header field
  `Stop-rule freeze: <YYYY-MM-DD> | carried-to: <next run id | pending>`
  is what a `frozen-carried` row leans on, and the field is ONE per
  ledger, written ONCE, by whichever freeze occasion came first. A second
  occasion does not rewrite it: the header keeps the FIRST date, and each
  row's own `terminal` cell carries the date that row was frozen. So:
  two such header lines are a STRUCTURAL error (an overwrite is never a
  silent replacement); a field that is present but does not take the
  literal shape above is a STRUCTURAL error; a `frozen-carried` row with
  no such field in the header is a STRUCTURAL error (a carry to nowhere);
  and `carried-to: pending` AT THE MOMENT THE ROUND CLOSES is a
  STRUCTURAL error too — the next round must be named before the carry
  can be believed. When the ledger closes with such rows the script
  prints `FROZEN CARRIED: <n> rows → <carried-to>`.
- THE SECURITY-LENS BACKSTOP against a class mark nobody set. The checks
  above see only the row where `class:security-pii` IS written; a finding
  the adjudicator never classed at all is invisible to them by
  construction. So the header may declare one lens as the security lens —
  `Security lens: <PREFIX> | none`, the prefix in the `Lenses:` alphabet —
  and every findings row whose id carries that prefix must then hold
  either `class:security-pii` or the written removal of the default,
  `declassed:security-pii — <reason>` with a NON-EMPTY free-prose reason,
  in its `verdict` cell. A row with a FILLED verdict cell holding neither,
  and a `declassed:` whose reason is empty, are STRUCTURAL errors.
  AN EMPTY `verdict` CELL IS A STATE, NOT A DEFECT — the state "not
  adjudicated". A fresh stage-5 layout carries findings rows whose verdict
  cells are still blank, and refusing to recount it made this script
  useless exactly where it helps most: before adjudication. So an empty
  verdict cell is exempt from the backstop and is reported instead, as
  `not adjudicated: <n> rows`; the rows are non-terminal anyway, so the
  round stays not-closable on their account and the exit code is the
  ordinary one for open rows. The relaxation is EXACTLY the empty case:
  a filled cell that says nothing about the class is the structural error
  it always was, because a verdict that was written and left the class out
  is a judgment made, not a judgment pending. `security-pii` is the ONE
  reserved slug for this class: `class:security`, `class:pii` and
  `class:sec-pii` are other classes and are not read here. The backstop
  does not claim completeness — a security-relevant finding can come from
  another lens, and marking it stays the adjudicator's judgment; what is
  closed is the main path around every gate this class has.
- THE PROCESS PREFIXES, declared and never guessed. The header field
  `Process prefixes: <PREFIX>[, <PREFIX>…] | none` names the prefixes whose
  rows a PROCESS wrote rather than a lens — the fixer's `NOTICED OUTSIDE
  BATCH` channel, a class-kill gate — in the `Lenses:` alphabet and read by
  this field's OWN anchored pattern, so it never reaches `k` (that side of
  it is under `Also computed:` below). ABSENT, it changes nothing at all:
  every ledger written before the field recounts unchanged, and the literal
  `none` says the same thing. Present and unreadable, it is a STRUCTURAL
  error, and it is unreadable in four ways: a value outside that alphabet; a
  line that ENDS AT THE COLON, since present-and-empty is not absent and a
  check armed by a trailing space an editor may strip is not armed at all; a
  SECOND such field (an overwrite is never a silent replacement); and a
  prefix the `Lenses:` field also declares, because a process prefix is what
  is NOT a lens and must be distinct from every lens prefix. A declaration
  that disarms itself on a typo is worse than no declaration.
- The row's status lives ONLY in its cells; prose never overrides it.

Also computed:
- The SEVERITY DISTRIBUTION (severity cell x terminal status). Severity is
  cell index 1 in ALL THREE schemas, so no schema detection is involved and
  the line is printed for 7-, 8- and 9-cell ledgers alike.
- The UPHELD/REFUTED split, which needs the criterion cell and is therefore
  8- and 9-cell only: a 7-cell ledger prints `n/a (v1 ledger — no criterion
  column)` rather than guessing. A row is UPHELD iff its criterion cell is
  not the literal em-dash "—", or its terminal cell begins with "refused".
- The CLASS RECURRENCES: the number of UPHELD rows per `class:` slug, and
  a `CLASS-KILL DUE: <slug>` warning from the SECOND one — the point at
  which the next step for that class is a mechanical gate rather than one
  more fix. The "second recurrence" trigger is OURS, Tricorder-shaped: no
  standard supplies it. It is a warning and never changes the exit code.
  A DEFECT CLASS IS NOT A SIGNATURE MODE, and the count knows the
  difference. The security-lens backstop below obliges EVERY row of the
  declared security lens to carry `class:security-pii`, so two rows of that
  one lens would otherwise produce `CLASS-KILL DUE: security-pii` where no
  defect class recurred at all — the slug there is the lens's signature
  mode. So a `class:security-pii` on a row of the DECLARED security lens is
  the lens DEFAULT and counts toward NO kill, unless the same verdict cell
  carries `class-origin:adjudicator` — the written statement that the
  adjudicator chose the class rather than inheriting it. Everywhere else
  the slug counts exactly as it always did: on a row of any other prefix,
  and in a ledger that declares no security lens, nothing set the class but
  the adjudicator. The CENSUS LINE is unchanged and counts every tag: what
  narrows is the kill trigger, and where the two numbers differ one line
  names the gap rather than leaving a reader to derive it.
  THE OPEN KILL IS PRINTED, not left to be believed. The warning above
  speaks of "a 3rd recurrence with no kill in flight", so the kill that IS
  in flight is made visible: a row carrying `class-kill:<slug>` in its
  verdict cell is the gate's own ledger row for that class, and while it is
  NOT terminal the report prints `kill in flight: <slug> (<id>)`. It is a
  state literal like every other line in this block and changes no exit
  code; a ledger carrying no such tag prints nothing here.
- The INJECTION RATE per fix batch: the findings tagged
  `origin:fix-application from:<batch>` over the number of rows that batch
  fixed. Both sides come from machine-readable cells. DENOMINATOR: the
  rows a batch fixed all carry that batch's identifier in their `fix`
  cell, grouped by literal match — the ledger's "Batch deltas" prose is a
  historical snapshot and is deliberately NOT parsed. NUMERATOR: the
  `from:<batch>` reference, which alone says whose fix produced the
  finding; a tagged row without a readable one is listed as
  `INJECTION UNATTRIBUTED` instead of lowering the share in silence, and a
  batch identified by neither a hash nor a snapshot name gets
  `injection rate: n/a (batch not identifiable)` rather than an invented
  denominator. Batches are ordered by first appearance in the table, and
  two CONSECUTIVE batches at 7% or above print `INJECTION RATE HIGH`. That
  literal is deliberately not the class-kill one and carries a different
  weight: it is a printed metric that obliges exactly one thing, a fork to
  the user, and it never changes the exit code. 7% and 3.5% are LITERATURE
  reference points (undisciplined / disciplined floor), marked as such in
  the output and never as a measurement of this project.
- The RESIDUAL-DEFECT ESTIMATE, Jackknife capture-recapture over the
  per-lens finding sets: `N-hat = D + ((k-1)/k) * f1`, where `D` is the
  number of DISTINCT findings the lenses RAISED (before adjudication —
  a refuted claim was still raised — with cross-lens duplicates collapsed
  by the existing `=<primary-id>` convention in the criterion cell), `f1`
  the number of those raised by exactly ONE lens, and `k` the number of
  lenses. Printed ONLY at `k >= 4`; below that the line reads `n/a: k<4`
  and no number is computed, because the estimator is not applied outside
  its own applicability condition.
  `k` HAS EXACTLY ONE SOURCE, and it is declared here: the machine part of
  the ledger header's `Lenses:` field — a run of lines directly under it,
  each ` - <PREFIX> | <lens name> | <model>`, the prefix in the same
  `[A-Z][A-Z0-9]{0,3}` alphabet the id contract uses. `k` is the number of
  such parsed lines and nothing else. It is NEVER a count of distinct id
  prefixes in the findings table: a verification pass writes its rows under
  `V1`, `V2`, … by the SAME id contract, so that count would inflate `k`
  with every pass. Verifier prefixes are declared in their own header field
  (`Verifier passes:`) and never in `Lenses:`, so they stay out of `k` by
  construction rather than by a guessing filter. The prefixes of the rows a
  PROCESS writes — the fixer's `NOTICED OUTSIDE BATCH` channel, a class-kill
  gate — are declared the same way, in `Process prefixes:` and never in
  `Lenses:`, read by that field's own anchored pattern and out of `k` for
  the same reason. A header with no `Lenses:`
  field, or one whose lines do not parse, gives
  `n/a: k not derived from the header` and no estimate — guessing `k` is
  banned.
  A row with a composite id is never attributed to a lens. The composite
  form `V-CIT-1` is a full id under the contract above and this script
  reads it like any other, but its prefix carries a VERIFIER pass and the
  stem of what that pass re-checked — not a lens — so the row enters no
  per-lens quantity, takes no part in `k`, and appears in no per-lens
  report. That is not a gap this script closes by guessing: no report may
  pretend to know the lens of such a row. The residual gap is named
  honestly rather than left to be discovered — the mechanical security
  backstop is keyed on the declared lens PREFIX, so it does not reach a
  composite-id row either, and the security/PII classification of such a
  row stays the adjudicator's own judgment. A known limitation, not a
  defect.
  The output always carries the word ESTIMATE and the caveat beside it.
  Lens diversity does not invalidate it — the source measured little or no
  impact on the estimation results — so this script does not claim that
  disjoint lenses inflate the number. The caution that remains is OURS
  and is printed as ours: our four field measurements put the single-lens
  share at 75-94% and `N-hat` near `2*D`, but they count `D` as distinct
  CONFIRMED findings where this line counts distinct RAISED ones, so
  comparability is NOT established. The number is advisory: it enters no
  stop rule, no gate and no exit code.
- The SEVERITY-WEIGHTED PLATEAU, printed beside the binary streak rule and
  never instead of it: the moving average of the major+blocker deltas over
  a window of THREE ledgers — this one and two `--prev` — which is two
  deltas, averaged. The quantity per ledger is the count of rows whose
  severity cell reads `major` or `blocker`; the severity cell is index 1 in
  all three schemas, so a 7-cell ledger takes part like any other.
  With fewer inputs the line is `severity plateau: n/a: <reason>` and the
  ordinary delta is unaffected.
- The new-findings CURVE from the "Verification passes" table (header
  starting `| # |`): the first integer of each "new findings" cell.
  Kill-criterion warning when the curve has not decayed for three
  consecutive passes. The "new findings" column is located BY NAME when the
  passes header names it and by index 3 otherwise, so the positional
  behaviour of older ledgers is preserved exactly.
  When that table carries `started` and `ended` as its last two columns the
  curve is ALSO printed on a time axis, with the wall-clock of each pass;
  when it does not, one line says why there is no time axis. A timestamp
  that is present but unparseable is REPORTED BY NAME and the time axis is
  suppressed — it NEVER changes the exit code, because those two columns
  exist only when observability is on and a measurement must not be able to
  fail a round.
- With `--trace <trace.jsonl>`: one report-only line counting the round's
  trace records and the unreadable lines skipped. A missing trace is
  `trace: none`; nothing about a trace changes the exit code.
- With `--prev <old-ledger.md>`: the inter-round DELTA — newly-terminal /
  regressed / still-open / new-open, by id, against the previous ledger.
  Completeness invariant: every currently NON-terminal id lands in
  exactly one of regressed / still-open / new-open — a brand-new open
  finding is never silently dropped from the delta.
  The flag is REPEATABLE, up to TWO paths: one gives the delta exactly as
  it has always been, two additionally give the severity-weighted plateau.
  A third `--prev` is a usage error, not a silently widened window.
  With two, the CHRONOLOGY IS DERIVED, never taken on trust from the
  argument order: each passed ledger declares its own `Round-started:
  <ISO-date>` header field, the two `--prev` are ordered by it whatever
  order the arguments came in, and the DELTA is taken against the NEARER
  of the two. A re-ordering prints the notice `prev order: reordered by
  Round-started` — a notice, not an error. If that field is missing,
  unparseable, or the same in both `--prev` in any of the passed ledgers,
  the window has no derivable order: the plateau is not computed
  (`n/a: the order of the previous ledgers is not derived`), the ordinary
  delta is unaffected, and the order is never guessed from the arguments.
  `--prev` ALSO prints the PER-LENS SUSTAINED RATE — upheld over raised for
  each declared lens, taken over the WINDOW (this ledger plus the `--prev`
  ledgers that parsed), which is what makes it sustained rather than one
  round's rate — and, BESIDE IT and never on a line of its own, the SHELF
  SHARE: the share of that lens's refutations carrying a `shelf:` tag. The
  two travel together on purpose. A lens below the 92% baseline gets its
  framing TIGHTENED in the next round — never dropped — and that call is
  PAIRED: the rate alone never triggers it, because a lens whose
  refutations were all closed by the contract's shelf was cheap to refute,
  not wrong to raise. The baseline is OURS (one measured round), not a
  literature figure. Lens prefixes come from the same single source as `k`,
  the header's machine-form `Lenses:` lines, never from the id prefixes in
  the table. Every part of the block is report-only: no line here reaches
  an exit code, and a number that cannot be computed is `n/a: <reason>`,
  never `0` — an absent `shelf:` tag means the tag was never set, which is
  not a shelf share of zero.
- The RESIDUE REGISTER, a durable file that outlives any one run: it holds
  one row per nominee, `run-qualified id | severity | claim-hook |
  rationale | compensating-control | review-by | status | origin-run`.
  `rationale` and `compensating-control` may not be blank (the literal
  `none — direct risk accepted` is a legitimate compensating control, an
  empty cell is not); `review-by` is a calendar-valid ISO date; `status` is
  `nominated <date>`, `ratified <date>` or `expired-reopened <date>`, the
  last optionally carrying its cycle counter as `(#<n>)`; a blocker may not
  appear at all. A malformed register is a STRUCTURAL ERROR (exit 2) by the
  same fail-closed rule as a malformed ledger row. Its PATH comes from
  `--register <path>`; without the flag it is DERIVED from the layout
  convention this script is allowed to lean on — the register sits beside
  the run folders, in the `.critic-ledger/` directory that contains the
  ledger, so `<root>/.critic-ledger/<run>/fix-ledger.md` gives
  `<root>/.critic-ledger/residue-register.md`. A ledger outside such a
  directory derives nothing and the report says so.
  What is printed (REPORT-ONLY — no register line ever reaches an exit
  code): the aggregate, `rows | nominated | ratified | expired-reopened |
  age of the oldest`; `NOMINATION OVERDUE` for a `nominated` row past 30
  days, that limit being OURS and marked as ours; `REVIEW-BY EXPIRED` for a
  `ratified` row whose `review-by` has passed, since expiry RE-OPENS by
  default and is never a silent renewal; `SECOND CYCLE — OWNER FORK
  REQUIRED` for a row re-opened a second time, which no batch ratification
  may carry; and `NOMINATION WITHOUT A REGISTER ROW` for an
  `awaiting-signature` ledger id that no register row accounts for (ids are
  matched on the register's run-qualified form, `<run>/<id>`).
  The block is printed only when the register is IN PLAY — the flag was
  given, or the derived file exists, or the ledger carries a nomination —
  so a ledger with no register and no nomination recounts byte for byte as
  it did before this script learned about residue at all.
  HONEST BOUNDARY: this report is visibility, not traction. Nothing here
  drains the queue. Only two efforts do, and both are outside the script —
  the owner's ratification cadence, and the escalations above. The register
  is append-only in this release: there is no archiving and no deletion of
  rows, so without a cadence it grows monotonically, and the only
  counterweights are the printed age of the oldest row and the mandatory
  escalation forks. That is a deliberate limit: draining the queue
  automatically would be the residue accepting itself.
- The PRINTING POLICY of the two auxiliary blocks, stated side by side
  here because they deliberately DIFFER and neither is a defect of the
  other: the residual-defect ESTIMATE line prints on EVERY recount — as
  `n/a: <reason>` whenever it cannot be computed — because a stopping
  metric that goes silent when it is not derivable is indistinguishable
  from one nobody ran; the residue-register block prints only when the
  register is in play, because a ledger that never heard of residue has
  to recount byte for byte as it did before this script learned about it.
  Harmonizing the two is a SPEC question and is deliberately not decided
  by this script.

Usage:  recount.py <ledger.md> [--prev <old-ledger.md>]... [--trace <trace.jsonl>]
                   [--register <residue-register.md>]
        `--prev` may be given at most twice (the plateau window).
        recount.py -h | --help                       (this text, exit 0)
Exit codes: 0 = zero non-terminal rows (closable), or `-h`/`--help`;
1 = open rows remain, or the round is awaiting ratification, or it is
awaiting the owner's closing act — the three non-closable states share one
code and are told apart by their state lines; 2 = structural error
(malformed table — fix before trusting any count); 3 = ledger is FROZEN
(superseded by a rewrite; not closable).
"""  # noqa: D205, D301  # printed usage text; reflow/r-string would change output

import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypedDict

# The id contract: a prefix of one or more dash-joined letter-led segments,
# then the number. The composite form is what lets a verifier keep the lens
# it re-checked inside the id (`V-CIT-1`) instead of renaming the row after
# a recount refuses it; every segment stays non-empty and letter-led, so
# `-1`, `V--1`, `1-V` and `V-CIT-` remain structural errors.
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)*-\d+$")
# An owner signature is the literal `user-signed` IMMEDIATELY followed by an
# ISO date: an undated signature is not a signature.
SIGNED_DATE_RE = re.compile(r"user-signed\s+(\d{4}-\d{2}-\d{2})")
ESC = "\x00PIPE\x00"

# A markdown row must have at least the two delimiting pipes.
MIN_ROW_CELLS = 2
# The narrowest findings table whose ROWS can be addressed at all: a row
# addresses id first, severity second, verified and terminal last-but-one
# and last, so four distinct cells are the minimum. A header narrower than
# this is degenerate — a findings header of a single id cell — and its
# width diagnostic is the whole structural report: its rows are not read.
ADDRESSABLE_ROW_CELLS = 4
# The three accepted findings-table widths, by schema version.
V1_WIDTH = 7
V2_WIDTH = 8
V3_WIDTH = 9
ROW_WIDTHS = (V1_WIDTH, V2_WIDTH, V3_WIDTH)
# From this width up the schema carries the readiness-criterion column, and
# the cell is addressed from the END (`cells[-4]`) at widths 8 and 9 alike.
CRITERION_MIN_WIDTH = V2_WIDTH
CRITERION_FROM_END = -4
# `verdict` is the one cell an inserted `zone` column DOES move, so it is the
# one cell still addressed from the start: index 3 at widths 7 and 8, index 4
# at width 9. Everything the docstring bans a start-index for — criterion,
# fix, verified, terminal — is addressed from the end.
VERDICT_INDEX = 3
VERDICT_INDEX_V3 = 4
# The zone cell of a v3 row: THIRD, so that end-addressing survives it.
ZONE_INDEX = 2
# The zone vocabulary of the round contract's zone map.
ZONE_MECHANICAL = "Z1"
ZONE_NORMATIVE = "Z2"
ZONE_INFORMATIVE = "Z3"
ZONES = (ZONE_MECHANICAL, ZONE_NORMATIVE, ZONE_INFORMATIVE)
# What `templates/transcribe.py` writes into `zone`: transcription is literal
# copying, so the zone is left for the adjudicator behind a visible stub.
ZONE_PLACEHOLDER = "·"
# The optional header declaration of the row schema, and the width each
# version names. Absent = nothing changes; present and disagreeing with the
# table = a structural error.
ROW_SCHEMA_FIELD_RE = re.compile(r"^\s*[-*]?\s*row schema:\s*(.*?)\s*$", re.IGNORECASE)
ROW_SCHEMA_WIDTHS = {"v1": V1_WIDTH, "v2": V2_WIDTH, "v3": V3_WIDTH}
# A verification-passes row must reach the "new findings" cell (index 3) —
# the positional fallback used when the passes header does not name it.
NEW_FINDINGS_INDEX = 3
# Header cell names the passes table is read by, when it carries them.
NEW_FINDINGS_NAME = "new findings"
STARTED_NAME = "started"
ENDED_NAME = "ended"
# Length of the window the kill criterion looks at.
KILL_CRITERION_WINDOW = 3
# Severity classes always reported, in this order; any other value observed
# in the severity cell is reported after them, sorted.
SEVERITY_ORDER = ("blocker", "major", "minor")
# A row whose criterion cell is exactly this is refuted/refused, never upheld.
NOT_NEEDED = "—"
# The passes table's timestamps: ISO-8601 UTC, seconds resolution.
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# --- verdict-cell tags -----------------------------------------------------
# The verdict cell is free adjudication prose, so a tag inside it is given a
# fixed boundary — an alphabet and a terminator — like every other literal
# this script parses. See the tag bullet in the module docstring.
CLASS_TAG = "class:"
CLASS_TAG_RE = re.compile(r"class:([a-z0-9-]{1,32})(?![a-z0-9-])")
# Non-whitespace characters after which `class:` is PROSE rather than an
# attempted tag; whitespace and the end of the cell say the same thing.
CLASS_TAG_PROSE = ("|",)
# The DEFECT CLASS / SIGNATURE MODE split, in one written literal. Every row
# of the declared security lens must carry `class:security-pii` — the
# backstop below obliges it — so that slug on such a row says which lens
# raised the finding, not that a defect class recurred. The adjudicator who
# means the class itself says so in the same cell, and only then does the
# tag count toward a class-kill. Written out rather than inferred: an origin
# that has to be guessed is an origin no counter can rely on.
CLASS_ORIGIN_ADJUDICATOR = "class-origin:adjudicator"
CLASS_ORIGIN_ADJUDICATOR_RE = re.compile(
    r"class-origin:adjudicator(?![a-z0-9-])",
)
# The gate's OWN ledger row, tagged with the class it kills. It is the one
# thing the class-kill warning speaks of and nothing used to show: while
# such a row is not terminal, the kill is in flight.
CLASS_KILL_TAG_RE = re.compile(r"class-kill:([a-z0-9-]{1,32})(?![a-z0-9-])")
FIX_APPLICATION_TAG = "origin:fix-application"
FROM_TAG_RE = re.compile(r"from:([a-z0-9-]{1,40})(?![a-z0-9-])")
# The slug alphabet's ceiling, shared by every verdict-cell tag that takes
# one: a boundary readers can rely on is one boundary, not one per tag.
SLUG_MAX = 32
# `shelf:<slug>` — a refutation closed WHOLLY by a pre-signed disposition of
# the round's contract, the slug naming that disposition. Read by exactly
# one report, the shelf share printed beside the per-lens sustained rate.
SHELF_TAG = "shelf:"
SHELF_TAG_RE = re.compile(r"shelf:([a-z0-9-]{1,32})(?![a-z0-9-])")
# The sustained-rate baseline. OURS — one measured round — and never a
# trigger on its own: the framing is tightened only when the shelf share
# beside the rate agrees.
SUSTAINED_BASELINE_PCT = 92.0
# The SECOND upheld finding of one class is the class-kill trigger. That
# number is OURS, Tricorder-shaped — no standard supplies it.
CLASS_KILL_THRESHOLD = 2
# Injection rate: LITERATURE reference points, printed as such and never as
# our own measurement — 7% undisciplined, 3.5% disciplined floor — and the
# run of consecutive batches at or above the first one that raises the flag.
INJECTION_HIGH_PCT = 7.0
INJECTION_FLOOR_PCT = 3.5
INJECTION_HIGH_RUN = 2
PERCENT = 100.0
# Fix-cell values that identify no batch at all.
NO_BATCH = ("", "-", "—")

# --- the round contract: the two statuses it brings with it ----------------
# A finding whose whole claim is covered by a declared Non-Goal reaches a
# terminal status with NO live signature — the signature was given when the
# Non-Goals were authored — which is precisely why the literal is recognized
# only COMPLETE: the Non-Goal is named and the contract's signing date is in
# the cell, or the row is not disposed of by the contract at all.
OUT_OF_SCOPE = "out-of-scope-by-contract"
OUT_OF_SCOPE_RE = re.compile(
    r"out-of-scope-by-contract\s*\(NG-\d+,\s*signed\s+(\d{4}-\d{2}-\d{2})\)",
)
# The security/PII class marker: ONE literal, and this is it. Every check
# keyed on the class reads this slug and no synonym of it.
SECURITY_PII_SLUG = "security-pii"
# The written removal of the security/PII default, in the same row: the
# literal plus a reason that is free prose but never empty.
DECLASSED_TAG = "declassed:security-pii"
DECLASSED_RE = re.compile(r"declassed:security-pii\s*—\s*\S")
# The security lens is declared in its own header field, in the same prefix
# alphabet and from the same source as `Lenses:`.
SECURITY_LENS_RE = re.compile(
    r"^\s*[-*]?\s*security lens:\s*(.+?)\s*$",
    re.IGNORECASE,
)
LENS_PREFIX_RE = re.compile(r"[A-Z][A-Z0-9]{0,3}")
NO_SECURITY_LENS = "none"

# --- the prefixes that belong to a PROCESS rather than to a lens -----------
# Two writers put rows in the findings table that no lens raised: the
# fixer's `NOTICED OUTSIDE BATCH` channel and a class-kill gate. Their rows
# take an id prefix under the same contract as a lens's, so without a
# declaration they are machine-indistinguishable from a lens's rows. The
# field declares them, and it is read by a pattern of its OWN: it extends
# neither `LENSES_FIELD_RE`/`LENS_LINE_RE` nor `SECURITY_LENS_RE`, because a
# process prefix reaching `lens_prefixes` would inflate `k`. The field says
# what is NOT a lens; it never adds to what is.
# The value group is ZERO-WIDTH-CAPABLE (`.*?`, not `.+?`) on purpose: a line
# ending at the colon must read as a PRESENT field with an empty value, which
# the parse then refuses. With a one-or-more group that line matches nothing
# at all and is indistinguishable from an absent field, so the fail-closed
# behaviour would hang on a trailing space an editor is free to strip.
PROCESS_PREFIXES_RE = re.compile(
    r"^\s*[-*]?\s*process prefixes:\s*(.*?)\s*$",
    re.IGNORECASE,
)
NO_PROCESS_PREFIXES = "none"

# --- the stop rule's freeze, which is NOT `superseded-by-rewrite` ----------
# A row still open when the contract's stop rule fires is frozen and carried,
# and that is a TERMINAL status: it closes the round, not the finding. The
# header field it leans on is ONE per ledger and written ONCE — the collision
# rule, since the field has two independent writers (a stop rule firing, and
# the one-off freeze of an exhausted blocker).
FROZEN_CARRIED = "frozen-carried"
FROZEN_CARRIED_RE = re.compile(
    r"frozen-carried\s*\(stop-rule,\s*(\d{4}-\d{2}-\d{2})\)",
)
# Loose first, strict second: the loose form is what COUNTS the field (two of
# them is the observable collision), the strict one is what reads its value.
FREEZE_FIELD_RE = re.compile(r"^\s*[-*]?\s*stop-rule freeze:", re.IGNORECASE)
FREEZE_VALUE_RE = re.compile(
    r"^\s*[-*]?\s*stop-rule freeze:\s*(\d{4}-\d{2}-\d{2})\s*\|\s*"
    r"carried-to:\s*(\S.*?)\s*$",
    re.IGNORECASE,
)
CARRIED_TO_PENDING = "pending"

# --- residue: the two named waits and the durable register -----------------
# A residue nominee sits in a NAMED non-terminal state until the owner
# ratifies it, and a second named wait holds rows waiting for an act of the
# owner's own. Both are non-terminal (exit 1) and both are counted apart
# from an ordinary open row. See the two bullets in the module docstring.
AWAITING_SIGNATURE = "awaiting-signature"
AWAITING_LOGGED_NO_ACTION = "awaiting-logged-no-action"
# The terminal status the Z3 closing act produces. Recognized only in the v3
# schema and only at zone Z3 — see the docstring's terminal-status list.
LOGGED_NO_ACTION = "logged-no-action"
NOMINATED_RE = re.compile(r"nominated\s+(\d{4}-\d{2}-\d{2})")
LISTED_RE = re.compile(r"listed\s+(\d{4}-\d{2}-\d{2})")
# The severity that may never be nominated into residue.
BLOCKER = "blocker"
# Layout convention the register path is derived from when `--register` is
# absent; the docstring's register bullet states it as the contract.
RUN_ROOT_DIR = ".critic-ledger"
REGISTER_NAME = "residue-register.md"
REGISTER_HEADER_FIRST = "run-qualified id"
REGISTER_WIDTH = 8
# The register's three statuses, each carrying the date it was set and the
# last of them optionally carrying its cycle counter.
REGISTER_STATUS_RE = re.compile(
    r"^(nominated|ratified|expired-reopened)\s+(\d{4}-\d{2}-\d{2})"
    r"(?:\s+\(#(\d+)\))?$",
)
REGISTER_STATUSES = ("nominated", "ratified", "expired-reopened")
# An UNRATIFIED nomination has a deadline of its own: 30 days is OURS,
# marked as ours — no standard supplies it.
NOMINATION_MAX_DAYS = 30
# The cycle from which a re-opened row may no longer ride inside a batch
# ratification act.
SECOND_CYCLE = 2
# Register cells that count as blank wherever a blank is banned.
REGISTER_BLANK = ("", "-", "—")

# --- stopping metrics: the residual-defect ESTIMATE and the plateau --------
# k comes from ONE declared source — the machine part of the ledger header's
# `Lenses:` field, one line per lens, ` - <PREFIX> | <lens name> | <model>`.
# It is NEVER a count of distinct id prefixes in the findings table: a
# verifier pass writes its rows under the SAME id contract (`V1`, `V2`, …),
# so counting prefixes would inflate k with every verification pass. The
# verifier prefixes are declared in their own header field and never here,
# so they stay out of k by construction rather than by a guessing filter.
LENSES_FIELD_RE = re.compile(r"^\s*[-*]?\s*lenses:", re.IGNORECASE)
LENS_LINE_RE = re.compile(
    r"^\s+[-*]\s+([A-Z][A-Z0-9]{0,3})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*$",
)
# The `=<primary-id>` gloss a duplicate row carries in its criterion cell:
# the same cross-lens deduplication convention adjudication already uses.
# The pointer names an id under the same contract as `ID_RE` above,
# composite prefixes included: `=V-CIT-1` is a pointer, not prose.
DUPLICATE_OF_RE = re.compile(
    r"^=\s*([A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)*-\d+)",
)
# Jackknife capture-recapture applies from FOUR lenses up; below that the
# estimate is not printed at all — `n/a: k<4`, never a number.
JACKKNIFE_MIN_LENSES = 4
# The severity-weighted plateau: a moving average over a window of THREE
# ledgers (the current one and two `--prev`), which is two deltas, and the
# severities that carry weight in it.
PLATEAU_WINDOW = 3
MAX_PREV = 2
PLATEAU_SEVERITIES = ("blocker", "major")
# Chronology is DERIVED, never taken on trust from the argument order: each
# passed ledger declares its own start in this header field.
ROUND_STARTED_RE = re.compile(
    r"^\s*[-*]?\s*round-started:\s*(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


class Row(TypedDict):
    """One parsed findings-table row, addressed by cell name."""

    id: str
    severity: str
    verdict: str
    verified: str
    terminal: str
    criterion: str | None
    zone: str | None
    fix: str
    line: int


class PassRow(TypedDict):
    """One parsed verification-passes row.

    `new` is None when the row does not reach the new-findings cell or that
    cell holds no integer; `started`/`ended` are None when the table has no
    such column at all (a v1 passes table) and the raw cell text otherwise —
    including the empty string, which is a v2 cell that cannot be read.
    """

    ordinal: str
    new: int | None
    started: str | None
    ended: str | None


class RegisterRow(TypedDict):
    """One parsed residue-register row, addressed by cell name.

    `status` is the bare status word and `status_date` the date that word
    carries; `cycle` is the re-open counter, 1 unless the row spells a
    higher one out as `(#<n>)`.
    """

    rid: str
    severity: str
    review_by: date
    status: str
    status_date: date
    cycle: int
    line: int


def split_row(line: str) -> list[str] | None:
    """Return the inner cells of a markdown table row, or None if malformed."""
    cells = [
        c.strip().replace(ESC, "|") for c in line.replace("\\|", ESC).strip().split("|")
    ]
    if len(cells) < MIN_ROW_CELLS or cells[0] != "" or cells[-1] != "":
        return None
    return cells[1:-1]


def parse_findings(lines: list[str]) -> tuple[list[Row], list[str]]:
    """Return (rows, errors); rows = list of dicts for the FIRST findings
    table only (header `| id |` ... up to the next heading).
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    rows: list[Row] = []
    errors: list[str] = []
    in_table = False
    width = 0
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not in_table:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and cells[0].lower() == "id":
                in_table, width = True, len(cells)
                if width not in ROW_WIDTHS:
                    errors.append(
                        f"line {n}: findings header has {width} "
                        f"cells; the table must be {V1_WIDTH}-cell (v1, "
                        f"legacy), {V2_WIDTH}-cell (v2, with criterion) "
                        f"or {V3_WIDTH}-cell (v3, with zone)",
                    )
                    if width < ADDRESSABLE_ROW_CELLS:
                        # Degenerate header (`| id |`): too narrow for a row
                        # to carry id/severity/verified/terminal in distinct
                        # cells, so no row of this table can be read — the
                        # width diagnostic above IS the structural report
                        # (exit 2 at the call site). Reading on would index
                        # past the end of the row and raise an IndexError,
                        # which the shell would see as exit 1 — the code that
                        # means "open rows remain".
                        break
            continue
        if stripped.startswith("#"):
            break  # next heading ends the findings table
        if not stripped.startswith("|"):
            continue  # prose/blank inside the section
        if re.fullmatch(r"\|[-| :]+\|", stripped):
            continue  # separator
        cells = split_row(stripped)
        if cells is None or len(cells) != width:
            errors.append(
                f"line {n}: malformed row "
                f"({0 if cells is None else len(cells)} cells, "
                f"need {width} — this table's header width; "
                f"unescaped pipe?): {stripped[:80]}",
            )
            continue
        if not ID_RE.fullmatch(cells[0]):
            errors.append(
                f"line {n}: first cell is not a valid id "
                f"(<Prefix>-<n>, every prefix segment letter-led, "
                f"dash-joined segments allowed as in `V-CIT-1`): "
                f"{cells[0]!r}",
            )
            continue
        # criterion/fix/verified/terminal are addressed from the END: one
        # addressing serves all three schemas (7-, 8- and 9-cell), and the
        # zone column was inserted THIRD so that it stays that way. A hard
        # index from the start would read `verdict` prose as the criterion
        # of a v3 row — a check silently switched off.
        row: Row = {
            "id": cells[0],
            # Severity is cell index 1 in ALL THREE schemas, which is why
            # the distribution needs no schema detection.
            "severity": cells[1],
            # `verdict` is the one cell the zone column displaces, so it is
            # the one cell still taken by a start index — and the branch is
            # written out rather than inferred.
            "verdict": cells[VERDICT_INDEX_V3 if width == V3_WIDTH else VERDICT_INDEX],
            "verified": cells[-2],
            "terminal": cells[-1],
            "criterion": (
                cells[CRITERION_FROM_END] if width >= CRITERION_MIN_WIDTH else None
            ),
            "zone": cells[ZONE_INDEX] if width == V3_WIDTH else None,
            "fix": cells[-3],
            "line": n,
        }
        problem = (
            criterion_error(row)
            or class_tag_error(row)
            or shelf_tag_error(row)
            or nomination_error(row)
            or contract_status_error(row)
            or logged_no_action_error(row)
        )
        if problem:
            errors.append(problem)
            continue
        rows.append(row)
    return rows, errors


def criterion_error(row: Row) -> str | None:
    """Consistency of the readiness-criterion cell — a STRUCTURAL error
    (fail-closed), not a soft warning. 8- and 9-cell schemas only: a 7-cell
    legacy row has no criterion column and is exempt.
    """  # noqa: D205  # docstring wording is frozen; only the closing quotes moved
    crit = row["criterion"]
    if crit is None:
        return None
    t = row["terminal"].lower()
    if t.startswith("verified-landed") and crit in ("", "-", "—"):
        return (
            f"line {row['line']}: {row['id']} is verified-landed but its "
            f"readiness-criterion cell is {crit!r} — a confirmed finding "
            f"must carry the criterion written at adjudication"
        )
    if t.startswith("accepted-residue") and crit in ("", "-", "—"):
        return (
            f"line {row['line']}: {row['id']} is accepted-residue but its "
            f"readiness-criterion cell is {crit!r} — an upheld finding "
            f"keeps the criterion written at adjudication (an empty or "
            f"dash cell is banned)"
        )
    if t.startswith(AWAITING_SIGNATURE) and crit in ("", "-", "—"):
        return (
            f"line {row['line']}: {row['id']} is {AWAITING_SIGNATURE} but "
            f"its readiness-criterion cell is {crit!r} — a residue NOMINEE "
            f"is an upheld finding and keeps the criterion written at "
            f"adjudication, exactly as a ratified residue does"
        )
    if t.startswith(("refuted-with-reason", "refused")) and crit != "—":
        return (
            f"line {row['line']}: {row['id']} is refuted/refused but its "
            f"readiness-criterion cell is {crit!r} — it must be exactly "
            f"the em-dash '—' (deliberately not needed, not forgotten)"
        )
    return None


def nomination_error(row: Row) -> str | None:
    """Reject a BLOCKER nominated into the residue queue.

    Blockers are categorically non-nominable: residue is the route for risk
    that may be CARRIED, and by the severity taxonomy a blocker means the
    object is unfit for its purpose — there is nothing there to carry. The
    combination is a STRUCTURAL error rather than a warning, because a rule
    that only warns is a rule that gets walked past.
    """
    if not row["terminal"].strip().lower().startswith(AWAITING_SIGNATURE):
        return None
    if row["severity"].strip().lower() != BLOCKER:
        return None
    return (
        f"line {row['line']}: {row['id']} is severity {BLOCKER} and carries "
        f"`{AWAITING_SIGNATURE}` — a blocker is categorically non-nominable: "
        f"it closes through a fix, through a gate or through a refutation, "
        f"never through residue"
    )


def class_slugs(row: Row) -> list[str]:
    """The `class:` slugs the row's verdict cell carries, by exact match."""
    return CLASS_TAG_RE.findall(row["verdict"])


def contract_status_error(row: Row) -> str | None:
    """Reject a security/PII row disposed of by the contract's pre-signature.

    `out-of-scope-by-contract` closes a finding on a signature given BEFORE
    the round, when the Non-Goals were authored. The security/PII class is
    the one class both of whose outcomes — accept and refuse — need the
    owner's live word, so a pre-signed disposition does not reach it: the
    combination is a STRUCTURAL error unless the row also carries a live
    `user-signed <date>` in its terminal cell. A warning would not do; a rule
    that only warns is a rule that gets walked past.
    """
    if not row["terminal"].strip().lower().startswith(OUT_OF_SCOPE):
        return None
    if SECURITY_PII_SLUG not in class_slugs(row):
        return None
    if SIGNED_DATE_RE.search(row["terminal"]):
        return None
    return (
        f"line {row['line']}: {row['id']} carries `class:{SECURITY_PII_SLUG}` "
        f"and `{OUT_OF_SCOPE}` with no live `user-signed <date>` — the "
        f"contract's pre-signed disposition does not reach a class both of "
        f"whose outcomes require the owner's own word"
    )


def logged_no_action_error(row: Row) -> str | None:
    """Reject a `logged-no-action` the zone does not authorize.

    The status closes an INFORMATIVE finding in a batch the owner signs off
    in one act, and the only thing that says a finding is informative is the
    contract's zone map, carried in the row's `zone` cell. So the status is
    readable only where that cell exists (the v3 schema) and only where it
    reads `Z3`. In a 7- or 8-cell row there is no cell to check the
    condition against at all — that is a STRUCTURAL error rather than an
    undefined case, because a mass closure route accepted on no condition is
    exactly the hole the zone was introduced to avoid. The security/PII
    exception is the one `contract_status_error` states for the other
    pre-signed route, word for word: a class both of whose outcomes need the
    owner's own word is never disposed of inside a batch act.
    """
    t = row["terminal"].strip().lower()
    if not t.startswith(LOGGED_NO_ACTION):
        return None
    zone = row["zone"]
    if zone is None:
        return (
            f"line {row['line']}: {row['id']} carries `{LOGGED_NO_ACTION}` in a "
            f"{V1_WIDTH}- or {V2_WIDTH}-cell row — the status exists only in "
            f"the {V3_WIDTH}-cell (v3) schema, where the `zone` cell its "
            f"condition reads exists at all"
        )
    if zone.strip().upper() != ZONE_INFORMATIVE:
        return (
            f"line {row['line']}: {row['id']} carries `{LOGGED_NO_ACTION}` with "
            f"zone {zone.strip()!r} — the status is accepted at zone "
            f"{ZONE_INFORMATIVE} alone; a finding outside the informative zone "
            f"closes through a fix, a refutation or residue"
        )
    if SECURITY_PII_SLUG in class_slugs(row) and not SIGNED_DATE_RE.search(
        row["terminal"],
    ):
        return (
            f"line {row['line']}: {row['id']} carries `class:{SECURITY_PII_SLUG}` "
            f"and `{LOGGED_NO_ACTION}` with no live `user-signed <date>` — a "
            f"class both of whose outcomes require the owner's own word is "
            f"never closed inside a batch act"
        )
    return None


def findings_header_width(lines: list[str]) -> int:
    """Cell count of the FIRST findings header, or 0 when there is none."""
    for raw in lines:
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if cells and cells[0].lower() == "id":
            return len(cells)
    return 0


def row_schema_error(lines: list[str], width: int) -> str | None:
    """Check the header's optional `Row schema:` declaration against the table.

    The field exists so that a reader knows what it parses without counting
    cells first, which is worth nothing if the declaration may disagree with
    the table. Absent, it changes nothing at all — every ledger written
    before the field has none, and its width keeps coming from the findings
    header exactly as it always did.
    """
    found: list[str] = []
    for raw in lines:
        m = ROW_SCHEMA_FIELD_RE.match(raw.rstrip("\n"))
        if m:
            found.append(m.group(1).strip())
    if not found:
        return None
    if len(found) > 1:
        return (
            f"{len(found)} `Row schema:` header fields — the schema is "
            f"declared ONCE per ledger; a second declaration is an overwrite, "
            f"never a silent replacement"
        )
    value = found[0].lower()
    if value not in ROW_SCHEMA_WIDTHS:
        return (
            f"`Row schema: {found[0]}` is not one of "
            f"{'/'.join(ROW_SCHEMA_WIDTHS)} — a schema declared in a "
            f"vocabulary nothing reads is worse than none"
        )
    declared = ROW_SCHEMA_WIDTHS[value]
    if declared != width:
        return (
            f"`Row schema: {found[0]}` declares {declared} cells but the "
            f"findings header has {width} — a declaration that contradicts "
            f"the table is a structural error, not a hint"
        )
    return None


def waiting_state(row: Row) -> tuple[str | None, str | None]:
    """Return (the row's named wait or None, problem-or-None).

    A named wait is non-terminal but is NOT an open row: it is counted and
    printed apart from one, and it is what the second and third exit buckets
    read. An `awaiting-signature` cell whose `nominated <date>` is missing or
    is not a calendar date names no wait at all — the row falls back to
    ORDINARY OPEN with a diagnostic, because a nomination whose age cannot be
    read cannot be chased for its deadline.
    """
    t = row["terminal"].strip().lower()
    if t.startswith(AWAITING_SIGNATURE):
        m = NOMINATED_RE.search(t)
        if m is None:
            return None, (
                f"{row['id']}: {AWAITING_SIGNATURE} without the literal "
                f"'nominated <date>' (YYYY-MM-DD) — a nomination carries "
                f"the date it was made; counted as an open row"
            )
        try:
            date.fromisoformat(m.group(1))
        except ValueError:
            return None, (
                f"{row['id']}: nomination date {m.group(1)!r} is not a "
                f"calendar date (YYYY-MM-DD); counted as an open row"
            )
        return AWAITING_SIGNATURE, None
    if t.startswith(AWAITING_LOGGED_NO_ACTION):
        # The date does NOT name this wait: the row belongs to the queue the
        # owner's closing act drains whether or not it can be aged, so it
        # stays in bucket 3 either way. What an unreadable date costs is the
        # 30-day limit, and that is reported rather than passed over.
        m = LISTED_RE.search(t)
        if m is None:
            return AWAITING_LOGGED_NO_ACTION, (
                f"{row['id']}: {AWAITING_LOGGED_NO_ACTION} without the literal "
                f"'listed <date>' (YYYY-MM-DD) — the wait is counted, but its "
                f"age cannot be read and the {NOMINATION_MAX_DAYS}-day limit "
                f"cannot be applied to it"
            )
        try:
            date.fromisoformat(m.group(1))
        except ValueError:
            return AWAITING_LOGGED_NO_ACTION, (
                f"{row['id']}: listed date {m.group(1)!r} is not a calendar "
                f"date (YYYY-MM-DD); the wait is counted, its age is not"
            )
        return AWAITING_LOGGED_NO_ACTION, None
    return None, None


def listed_date(row: Row) -> date | None:
    """The calendar-valid date an `awaiting-logged-no-action` row was listed."""
    m = LISTED_RE.search(row["terminal"].strip().lower())
    if m is None:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def z3_overdue_lines(rows: list[Row], waiting: list[str], today: date) -> list[str]:
    """Return one line per Z3 row whose wait has outrun the 30-day limit.

    The limit is NOT a new number: it is the nomination limit of the residue
    queue, carried over because both are the same shape — a row parked on an
    act of the owner's that has not happened. Report-only, like every other
    escalation here: it names a fork the orchestrator owes the owner, and
    reaches no exit code, which stays the wait's own (1).
    """
    out: list[str] = []
    for r in rows:
        if r["id"] not in waiting:
            continue
        listed = listed_date(r)
        if listed is None:
            continue
        held = (today - listed).days
        if held <= NOMINATION_MAX_DAYS:
            continue
        out.append(
            f"Z3 CLOSURE OVERDUE: {r['id']} (listed {listed}, {held} days; the "
            f"{NOMINATION_MAX_DAYS}-day limit is the residue queue's own, "
            f"carried over and not a new number) — put it to the owner as its "
            f"own fork: close it, take it out of the batch (the row returns to "
            f"adjudication as an open finding), or set a new date on the "
            f"owner's explicit word. A permanent wait is banned.",
        )
    return out


def class_tag_error(row: Row) -> str | None:
    """Reject a `class:` tag whose slug is outside the tag alphabet.

    Fail-closed, like every other literal this script parses: a `class:`
    that ATTEMPTS a slug and produces none readable under
    `class:([a-z0-9-]{1,32})(?![a-z0-9-])` is a STRUCTURAL error rather
    than a guess at where the slug ends.

    ONE case is deliberately not an error: `class:` immediately followed
    by whitespace, by a `|`, or by the end of the cell is English PROSE,
    not an attempted tag — it is ignored, groups nothing and reports
    nothing. The reason is compatibility, which outranks the widest
    reading of the fail-closed rule: verdict cells written before the tag
    existed carry the hand convention `[class: <name>]` and ordinary
    sentences ending "... the security class: user-signed <date>", and an
    old ledger must recount exactly as it did in 0.2.0. A tag never
    attaches a slug across whitespace, so nothing readable is lost by
    skipping these; what stays an error is `class:Foo`, `class:.x` and a
    slug longer than 32 — a boundary that is sometimes guessed is a
    boundary no reader can rely on.
    """
    return tag_slug_error(row, CLASS_TAG, CLASS_TAG_RE)


def shelf_tag_error(row: Row) -> str | None:
    """Reject a `shelf:` tag whose slug is outside the tag alphabet.

    The same rule as `class:`, deliberately and not by coincidence: one
    boundary for every verdict-cell tag that takes a slug. A `shelf:`
    followed straight away by whitespace, a `|` or the end of the cell is
    prose here too — the tag is optional, and a ledger that never sets it
    must recount exactly as it did before the tag existed.
    """
    return tag_slug_error(row, SHELF_TAG, SHELF_TAG_RE)


def tag_slug_error(
    row: Row,
    tag: str,
    pattern: re.Pattern[str],
) -> str | None:
    """Return the diagnostic for a slug-carrying verdict tag, or None.

    The shared body of the two checks above: find each occurrence of the
    tag, skip the ones that are prose by the boundary rule, and refuse the
    rest unless the slug parses under the tag's own pattern.
    """
    verdict = row["verdict"]
    at = verdict.find(tag)
    while at != -1:
        after = verdict[at + len(tag) : at + len(tag) + 1]
        prose = after == "" or after.isspace() or after in CLASS_TAG_PROSE
        if not prose and pattern.match(verdict, at) is None:
            return (
                f"line {row['line']}: {row['id']} carries a `{tag}` tag "
                f"whose slug is not 1-{SLUG_MAX} characters of [a-z0-9-]: "
                f"{verdict[at : at + 40]!r}"
            )
        at = verdict.find(tag, at + len(tag))
    return None


def signature_date_error(row_id: str, terminal: str) -> str | None:
    """Return a diagnostic when the signature date is not a calendar date.

    CALENDAR VALIDITY ONLY: `9999-99-99` and `2026-02-30` are rejected
    because they name no day. The date is NOT checked against today (a
    future date passes) and NOT checked for ordering against the finding.
    """
    m = SIGNED_DATE_RE.search(terminal)
    if m is None:
        return None
    try:
        date.fromisoformat(m.group(1))
    except ValueError:
        return (
            f"{row_id}: signature date {m.group(1)!r} is not a "
            f"calendar date (YYYY-MM-DD)"
        )
    return None


def terminal_status(row: Row) -> tuple[bool, str | None]:
    """Return (is_terminal, problem-or-None)."""
    t = row["terminal"].lower()
    if t.startswith("verified-landed"):
        v = row["verified"]
        if "NOT LANDED" in v.upper() or v.strip() in ("", "-", "—"):
            return False, (
                f"{row['id']}: terminal says verified-landed but "
                f"verified cell is {v.strip()!r}"
            )
        if "LANDED" not in v.upper():
            return False, (
                f"{row['id']}: terminal says verified-landed but "
                f"verified cell carries no LANDED verdict"
            )
        if re.search(r"LANDED\s+OTHERWISE", v, re.IGNORECASE):
            m = re.search(r"LANDED\s+OTHERWISE\s*\(([^)]*)\)", v, re.IGNORECASE)
            if not m or not m.group(1).strip():
                return False, (
                    f"{row['id']}: 'LANDED OTHERWISE' without a "
                    f"non-empty description in parentheses — "
                    f"fixed-otherwise is invalid without one and "
                    f"counts as partial"
                )
        return True, None
    if t.startswith("refuted-with-reason"):
        return True, None
    if t.startswith("accepted-residue"):
        if "user-signed" not in t:
            return False, (
                f"{row['id']}: accepted-residue without the "
                f"literal 'user-signed' — silence is not a "
                f"signature"
            )
        if not SIGNED_DATE_RE.search(t):
            return False, (
                f"{row['id']}: accepted-residue signature carries "
                f"no date — the literal is 'user-signed <date>' "
                f"(YYYY-MM-DD)"
            )
        bad_date = signature_date_error(row["id"], t)
        if bad_date:
            return False, bad_date
        return True, None
    if t.startswith("refused-user-signed"):
        if not SIGNED_DATE_RE.search(t):
            return False, (
                f"{row['id']}: refusal signature carries no date "
                f"— the literal is 'refused-user-signed <date>' "
                f"(YYYY-MM-DD)"
            )
        bad_date = signature_date_error(row["id"], t)
        if bad_date:
            return False, bad_date
        return True, None
    if t.startswith("refused"):
        return False, (
            f"{row['id']}: refusal without the literal "
            f"'refused-user-signed' — a refused security/PII "
            f"finding is terminal only with the owner signature"
        )
    if t.startswith(OUT_OF_SCOPE):
        return complete_literal(
            row,
            OUT_OF_SCOPE_RE,
            f"{OUT_OF_SCOPE} (NG-<n>, signed <YYYY-MM-DD>)",
            "a pre-signed disposition is recognized only in full, so that "
            "the Non-Goal it invokes is named and the contract's signing "
            "date stands in the cell",
        )
    if t.startswith(LOGGED_NO_ACTION):
        # The zone condition and the security/PII exception are STRUCTURAL
        # errors checked at parse time (`logged_no_action_error`), so a row
        # that reaches here has passed both: at zone Z3, in a v3 row, and
        # with the owner's live signature where the class demands one.
        return True, None
    if t.startswith(FROZEN_CARRIED):
        return complete_literal(
            row,
            FROZEN_CARRIED_RE,
            f"{FROZEN_CARRIED} (stop-rule, <YYYY-MM-DD>)",
            "a freeze is recognized only in full, because the date in the "
            "cell is the date THIS row was frozen and the header's single "
            "freeze field cannot supply it for a second occasion",
        )
    return False, None


def complete_literal(
    row: Row,
    pattern: re.Pattern[str],
    shape: str,
    why: str,
) -> tuple[bool, str | None]:
    """Terminality of a status recognized only under its COMPLETE literal.

    Both statuses the round CONTRACT brings close a finding without a live
    signature, so neither is allowed to close it by its opening words: the
    full shape carries the reference (`NG-<n>`) and the date that make the
    closure auditable months later. A partial match is NON-terminal with a
    diagnostic, never a structural error — the row is simply not yet closed.
    """
    m = pattern.search(row["terminal"])
    if m is None:
        return False, f"{row['id']}: expected the complete literal `{shape}` — {why}"
    try:
        date.fromisoformat(m.group(1))
    except ValueError:
        return False, (
            f"{row['id']}: date {m.group(1)!r} in `{shape}` is not a "
            f"calendar date (YYYY-MM-DD)"
        )
    return True, None


def severity_line(rows: list[Row], open_ids: set[str]) -> str:
    """Return the severity distribution line (severity x terminal status).

    Severity is cell index 1 in the 7-, 8- and 9-cell schemas alike, so
    this is computed for v1, v2 and v3 ledgers with no schema detection.
    The three canonical classes are always named — a ledger with no blocker
    is a fact worth printing — and any other value found in the cell is
    reported after them under its own name.
    """
    counts: dict[str, list[int]] = {s: [0, 0] for s in SEVERITY_ORDER}
    for r in rows:
        key = r["severity"].strip().lower() or "(blank)"
        bucket = counts.setdefault(key, [0, 0])
        bucket[0] += 1
        if r["id"] not in open_ids:
            bucket[1] += 1
    names = list(SEVERITY_ORDER) + sorted(k for k in counts if k not in SEVERITY_ORDER)
    body = " | ".join(f"{n} {counts[n][1]}/{counts[n][0]}" for n in names)
    return f"severity distribution (terminal/rows): {body}"


def upheld_line(rows: list[Row]) -> str:
    """Return the upheld/refuted split, or why it cannot be computed.

    UPHELD: the criterion cell is not the literal em-dash, OR the terminal
    cell begins with `refused` (the claim stood and the owner refused to
    act — not the same thing as a refuted claim). The split needs the
    criterion column, so a 7-cell legacy ledger reports `n/a` instead of
    guessing: a legacy row has no cell to read, not an empty one.
    """
    if any(r["criterion"] is None for r in rows):
        return "upheld/refuted: n/a (v1 ledger — no criterion column)"
    upheld = sum(1 for r in rows if is_upheld(r))
    return f"upheld/refuted: {upheld} upheld, {len(rows) - upheld} refuted"


def not_adjudicated_lines(rows: list[Row]) -> list[str]:
    """Report the rows whose `verdict` cell is still empty, or [].

    A STATE, not a defect: the finding is transcribed and the adjudicator
    has not reached it. Such a row is non-terminal anyway, so it holds the
    round open through the ordinary open-rows route and this line changes
    no exit code. A ledger with every verdict filled prints nothing here,
    which is what keeps every ledger written before this recount unchanged.
    """
    n = sum(1 for r in rows if not r["verdict"].strip())
    if not n:
        return []
    return [
        (
            f"not adjudicated: {n} rows — the `verdict` cell is empty, which "
            f"is the state before adjudication and not a structural error; "
            f"the security lens's backstop does not read an empty cell"
        ),
    ]


def is_upheld(row: Row) -> bool:
    """Whether a finding stood: a real criterion, or a signed refusal."""
    refused = row["terminal"].strip().lower().startswith("refused")
    return row["criterion"] != NOT_NEEDED or refused


def class_groups(rows: list[Row]) -> dict[str, list[str]]:
    """Map each `class:` slug to the ids of the UPHELD rows carrying it.

    Only upheld rows count: a refuted claim is not a recurrence of
    anything. On a 7-cell legacy ledger `is_upheld` has no criterion cell
    to read and treats every row as upheld — legacy ledgers predate the
    tag and carry none, so the two never meet in practice.
    """
    groups: dict[str, list[str]] = {}
    for r in rows:
        if not is_upheld(r):
            continue
        # dict.fromkeys: one row naming the same class twice is one row.
        for slug in dict.fromkeys(CLASS_TAG_RE.findall(r["verdict"])):
            groups.setdefault(slug, []).append(r["id"])
    return groups


def lens_default_class(row: Row, slug: str, prefix: str | None) -> bool:
    """Whether this `class:` tag is the security lens's DEFAULT, not a call.

    True for exactly one shape: the reserved `security-pii` slug, on a row
    of the DECLARED security lens, with no `class-origin:adjudicator` in
    the same cell. Everything else is a class somebody chose — another
    slug, another lens's row, a ledger declaring no security lens, or the
    written statement that the adjudicator meant this one — and a class
    somebody chose is what a recurrence is made of.
    """
    if slug != SECURITY_PII_SLUG or prefix is None:
        return False
    if row["id"].rsplit("-", 1)[0] != prefix:
        return False
    return CLASS_ORIGIN_ADJUDICATOR_RE.search(row["verdict"]) is None


def kill_groups(
    rows: list[Row],
    prefix: str | None,
) -> dict[str, list[str]]:
    """`class_groups` minus the tags no adjudicator chose.

    The census counts every tag; the KILL counts defect classes. The two
    differ only where the security lens's default is in play, and where
    they differ the report says so on its own line rather than leaving a
    reader to work out why two upheld rows raised no kill.
    """
    groups: dict[str, list[str]] = {}
    for r in rows:
        if not is_upheld(r):
            continue
        for slug in dict.fromkeys(CLASS_TAG_RE.findall(r["verdict"])):
            if lens_default_class(r, slug, prefix):
                continue
            groups.setdefault(slug, []).append(r["id"])
    return groups


def kill_in_flight_lines(rows: list[Row]) -> list[str]:
    """`kill in flight: <slug> (<id>)` for every OPEN class-kill row.

    The class-kill warning speaks of "a 3rd recurrence with no kill in
    flight", and until now nothing said whether one was in flight or not.
    A row carrying `class-kill:<slug>` IS the gate's ledger row for that
    class; while it is not terminal, the kill is being built and the
    report names it and its id. Report-only, like every other line here.
    """
    out: list[str] = []
    for r in rows:
        if terminal_status(r)[0]:
            continue
        out.extend(
            f"  kill in flight: {slug} ({r['id']})"
            for slug in dict.fromkeys(CLASS_KILL_TAG_RE.findall(r["verdict"]))
        )
    return out


def class_kill_lines(rows: list[Row], prefix: str | None = None) -> list[str]:
    """Return the class-recurrence report, or [] when no row is tagged.

    A ledger with no `class:` and no `class-kill:` tag prints nothing here,
    which is what keeps an untagged ledger recounting exactly as it did
    before. `prefix` is the declared security lens, and it is what tells
    the lens's DEFAULT class apart from a class the adjudicator chose.
    """
    groups = class_groups(rows)
    out: list[str] = []
    if groups:
        body = " | ".join(f"{s} {len(groups[s])}" for s in sorted(groups))
        out.append(f"class recurrences (upheld rows per class tag): {body}")
        kills = kill_groups(rows, prefix)
        for slug in sorted(groups):
            counted = kills.get(slug, [])
            if len(counted) < len(groups[slug]):
                out.append(
                    f"  class-kill count for {slug}: {len(counted)} of "
                    f"{len(groups[slug])} upheld rows — the rest carry the "
                    f"declared security lens's DEFAULT class, which is a "
                    f"signature mode and not a defect class; an adjudicator "
                    f"who means the class itself writes "
                    f"`{CLASS_ORIGIN_ADJUDICATOR}` in the same cell",
                )
            if len(counted) >= CLASS_KILL_THRESHOLD:
                out.append(
                    f"  CLASS-KILL DUE: {slug} ({len(counted)} upheld: "
                    f"{', '.join(counted)}) — the next step for this class "
                    f"is a mechanical gate or a convention that kills it, "
                    f"logged as its own class-kill ledger row, not one more "
                    f"fix; a 3rd recurrence with no kill in flight escalates "
                    f"to the user. The 2nd-recurrence trigger is OURS, "
                    f"Tricorder-shaped — no standard supplies it.",
                )
    out.extend(kill_in_flight_lines(rows))
    return out


def awaits_a_batch(row: Row) -> bool:
    """Whether a row's fix was, or was to be, applied by a fix batch.

    Refuted rows were never fixed and residue/refusal rows were fixed by
    nobody on purpose; none of them belongs to a batch, so none of them is
    evidence that a batch could not be identified. A row in either named
    wait is on the same footing: a nominee is residue that has not been
    signed yet, and a row logged as no-action — waiting for that act or
    closed by it — was never handed to a fixer.
    The two statuses the round contract brings sit there for the same
    reason: a row the contract put out of scope, and a row the stop rule
    froze and carried, were never handed to a fixer either.
    """
    t = row["terminal"].strip().lower()
    return is_upheld(row) and not t.startswith(
        (
            "accepted-residue",
            "refused",
            AWAITING_SIGNATURE,
            AWAITING_LOGGED_NO_ACTION,
            LOGGED_NO_ACTION,
            OUT_OF_SCOPE,
            FROZEN_CARRIED,
        ),
    )


def injection_lines(rows: list[Row]) -> list[str]:
    """Return the per-batch injection rate, or [] when no row is tagged.

    DENOMINATOR — batch membership: the rows one batch fixed all carry
    that batch's identifier in their `fix` cell (the per-batch commit
    hash, or the snapshot name where no commit sanction exists), grouped
    by literal match. The ledger's "Batch deltas" prose is a historical
    snapshot and is deliberately not parsed. NUMERATOR — the carrier of
    the "finding <- the batch that produced it" link: the `from:<batch>`
    reference inside an `origin:fix-application` tag, and nothing else. A
    tagged row with no readable `from:` is listed as unattributed rather
    than lowering the share in silence.
    """
    tagged = [r for r in rows if FIX_APPLICATION_TAG in r["verdict"]]
    if not tagged:
        return []
    batches: dict[str, list[str]] = {}
    unidentified: list[str] = []
    for r in rows:
        key = r["fix"].strip()
        if key in NO_BATCH:
            if awaits_a_batch(r):
                unidentified.append(r["id"])
            continue
        batches.setdefault(key, []).append(r["id"])
    charged: dict[str, list[str]] = {}
    unattributed: list[str] = []
    for r in tagged:
        m = FROM_TAG_RE.search(r["verdict"])
        if m is None:
            unattributed.append(r["id"])
            continue
        charged.setdefault(m.group(1), []).append(r["id"])
    out = [
        (
            "injection rate (findings caused by a batch's own fix / rows "
            f"that batch fixed; {INJECTION_HIGH_PCT:g}% and "
            f"{INJECTION_FLOOR_PCT:g}% are LITERATURE reference points — "
            "undisciplined and disciplined floor — not our measurement):"
        ),
    ]
    # Batches in first-appearance order, which is the order the run of
    # consecutive high batches is read in.
    run = 0
    for key, ids in batches.items():
        num = len(charged.get(key, []))
        pct = PERCENT * num / len(ids)
        out.append(f"  {key}: {num}/{len(ids)} = {pct:.1f}%")
        run = run + 1 if pct >= INJECTION_HIGH_PCT else 0
        if run >= INJECTION_HIGH_RUN:
            out.append(
                f"  INJECTION RATE HIGH: {key}, {pct:.1f}% — "
                f"{INJECTION_HIGH_RUN} consecutive batches at or above "
                f"{INJECTION_HIGH_PCT:g}%: recommend stopping the batching "
                f"and forking to the user, whose call the stop is. Advisory "
                f"— this metric never stops the round by itself.",
            )
    if unattributed:
        out.append("  INJECTION UNATTRIBUTED: " + ", ".join(unattributed))
    orphans = sorted(k for k in charged if k not in batches)
    if orphans:
        out.append(
            "  injection: no batch in the fix column is named by from:"
            + ", from:".join(orphans),
        )
    if unidentified:
        out.append(
            "  injection rate: n/a (batch not identifiable) for "
            + ", ".join(unidentified),
        )
    return out


def lens_prefixes(lines: list[str]) -> list[str]:
    """Return the lens id prefixes declared in the header's `Lenses:` field.

    ONE source, and it is this one. The field's machine part is a run of
    lines directly under it, each ` - <PREFIX> | <lens name> | <model>`;
    reading stops at the first line that does not take that shape, so
    nothing further down the header can drift into the count. A prefix is
    counted once however many times it is written.

    What this deliberately does NOT do is count distinct id prefixes in the
    findings table: verifier passes write their rows under `V1`, `V2`, … by
    the same id contract as a lens, so that count would grow with every
    verification pass. Verifier prefixes are declared in their own header
    field and never in this one.
    """
    out: list[str] = []
    seen: set[str] = set()
    for n, raw in enumerate(lines):
        if not LENSES_FIELD_RE.match(raw.rstrip("\n")):
            continue
        for follower in lines[n + 1 :]:
            m = LENS_LINE_RE.match(follower.rstrip("\n"))
            if m is None:
                break
            if m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(m.group(1))
        break
    return out


def security_lens(lines: list[str]) -> tuple[str | None, str | None]:
    """Return (the declared security lens's prefix, error-or-None).

    The field is `Security lens: <PREFIX> | none`, in the same alphabet as
    the `Lenses:` prefixes. `none` and an ABSENT field both mean there is no
    security lens and no backstop — the absent case is what makes every
    ledger written before this field recount unchanged. A field that is
    present but reads as neither is a STRUCTURAL error rather than a silent
    "no backstop": this field arms a gate, and a gate that disarms itself on
    a typo is worse than no gate.
    """
    for raw in lines:
        m = SECURITY_LENS_RE.match(raw.rstrip("\n"))
        if m is None:
            continue
        value = m.group(1).strip()
        if value.lower() == NO_SECURITY_LENS:
            return None, None
        if LENS_PREFIX_RE.fullmatch(value):
            return value, None
        return None, (
            f"header field `Security lens:` reads {value!r} — it must be a "
            f"lens prefix ([A-Z][A-Z0-9]{{0,3}}, the `Lenses:` alphabet) or "
            f"the literal `{NO_SECURITY_LENS}`"
        )
    return None, None


def process_prefixes(lines: list[str]) -> tuple[list[str], str | None]:
    """Return (the declared process-row prefixes, error-or-None).

    The field is `Process prefixes: <PREFIX>[, <PREFIX>…]` or the literal
    `none`, in the same alphabet as the `Lenses:` prefixes and read by this
    field's OWN anchored pattern. It is a declaration of what is NOT a lens:
    the fixer's `NOTICED OUTSIDE BATCH` channel and a class-kill gate write
    rows under a prefix of the same shape as a lens's, and a reader with no
    such field cannot tell the two apart machine-side.

    `none` and an ABSENT field both mean no process prefix was declared, and
    the absent case is what makes every ledger written before this field
    recount unchanged — `k` in particular is untouched either way, because
    this parse never feeds `lens_prefixes`. A field that is present but reads
    as neither is a STRUCTURAL error rather than a silent "none", for the
    same reason the security-lens field is: a declaration that disarms itself
    on a typo is worse than no declaration. PRESENCE is read off the field
    NAME, so a line that ends AT THE COLON is a present field with an empty
    value and not an absent one: a gate whose arming hangs on a trailing
    space an editor may strip is not armed at all. And the field is ONE per
    ledger — two such lines are a STRUCTURAL error, never "take the first
    and say nothing".
    """
    found: list[str] = []
    for raw in lines:
        m = PROCESS_PREFIXES_RE.match(raw.rstrip("\n"))
        if m:
            found.append(m.group(1).strip())
    if not found:
        return [], None
    if len(found) > 1:
        return [], (
            f"the header carries {len(found)} `Process prefixes:` fields — "
            f"the field is declared ONCE per ledger; a second declaration is "
            f"an overwrite, never a silent replacement"
        )
    value = found[0]
    if value.lower() == NO_PROCESS_PREFIXES:
        return [], None
    parts = [p.strip() for p in value.split(",")]
    if all(LENS_PREFIX_RE.fullmatch(p) for p in parts) and parts:
        return list(dict.fromkeys(parts)), None
    return [], (
        f"header field `Process prefixes:` reads {value!r} — it must be "
        f"comma-separated prefixes ([A-Z][A-Z0-9]{{0,3}}, the `Lenses:` "
        f"alphabet) or the literal `{NO_PROCESS_PREFIXES}`"
    )


def process_prefix_errors(declared: list[str], lenses: list[str]) -> list[str]:
    """Reject a process prefix that is also declared as a lens.

    The whole point of the field is that a process row is tellable from a
    lens's row; a prefix written in both places tells them apart nowhere,
    and it would put the process's rows inside `k`'s own lens.
    """
    collisions = [p for p in declared if p in lenses]
    if not collisions:
        return []
    return [
        (
            f"header field `Process prefixes:` names {', '.join(collisions)}, "
            f"which the `Lenses:` field also declares — a process prefix is "
            f"what is NOT a lens, so it must be distinct from every lens "
            f"prefix"
        ),
    ]


def security_lens_errors(rows: list[Row], prefix: str | None) -> list[str]:
    """Reject a security-lens row that carries neither the class nor a declass.

    The DEFAULT is the point: a finding raised by the lens the owner declared
    the security lens IS of the security/PII class, and the adjudicator marks
    it without deciding the question again. Removing the default is allowed —
    the adjudicator is the one who knows — but only IN WRITING and in the
    same row: `declassed:security-pii — <reason>`, the reason free prose and
    never empty. Silence is what this closes: an unmarked row on a security
    lens used to walk past every gate keyed on the class.

    An EMPTY verdict cell is not that silence. It is the state "not
    adjudicated" — a stage-5 layout the adjudicator has not reached yet —
    and it is reported by its own line rather than refused here. The
    relaxation is exactly the empty case: a FILLED cell that leaves the
    class out is a judgment that was made and left the class out, and it
    stays the structural error it always was.
    """
    if prefix is None:
        return []
    out: list[str] = []
    for r in rows:
        if r["id"].rsplit("-", 1)[0] != prefix:
            continue
        if not r["verdict"].strip():
            continue
        if SECURITY_PII_SLUG in class_slugs(r):
            continue
        if DECLASSED_TAG in r["verdict"]:
            if DECLASSED_RE.search(r["verdict"]) is None:
                out.append(
                    f"line {r['line']}: {r['id']} carries "
                    f"`{DECLASSED_TAG}` with an empty reason — removing the "
                    f"security lens's default class takes a written reason "
                    f"in the same cell, `{DECLASSED_TAG} — <reason>`",
                )
            continue
        out.append(
            f"line {r['line']}: {r['id']} was raised by the declared security "
            f"lens {prefix} and carries neither `class:{SECURITY_PII_SLUG}` "
            f"nor `{DECLASSED_TAG} — <reason>` — a finding of the security "
            f"lens takes the class by DEFAULT, and the default is removed in "
            f"writing or not at all",
        )
    return out


def stop_rule_freeze(
    lines: list[str],
) -> tuple[tuple[date, str] | None, str | None]:
    """Return ((freeze date, carried-to), error-or-None) from the header.

    ONE field per ledger, written ONCE by whichever freeze occasion came
    first. The field has two independent writers — the contract's stop rule
    firing, and the one-off freeze of an exhausted blocker — so a second one
    finding the field already filled must not overwrite it, and the shape
    that overwrite would take in the file is a SECOND field line. That is
    what is rejected here: two lines are a structural error, never "take the
    first and say nothing".
    """
    found = [raw.rstrip("\n") for raw in lines if FREEZE_FIELD_RE.match(raw)]
    if not found:
        return None, None
    if len(found) > 1:
        return None, (
            f"the header carries {len(found)} `Stop-rule freeze:` fields — "
            f"the field is ONE per ledger and is written ONCE, by the first "
            f"freeze occasion; a later occasion keeps the first date and "
            f"dates its own row instead. Overwriting it is a structural "
            f"error, not a silent replacement"
        )
    m = FREEZE_VALUE_RE.match(found[0])
    if m is None:
        return None, (
            f"header field `Stop-rule freeze:` does not take its literal "
            f"shape `Stop-rule freeze: <YYYY-MM-DD> | carried-to: <next run "
            f"id | pending>`: {found[0].strip()!r}"
        )
    try:
        when = date.fromisoformat(m.group(1))
    except ValueError:
        return None, (
            f"header field `Stop-rule freeze:` carries date {m.group(1)!r} — "
            f"not a calendar date (YYYY-MM-DD)"
        )
    return (when, m.group(2)), None


def frozen_carried_ids(rows: list[Row]) -> list[str]:
    """The ids the stop rule's freeze carried — valid literal or not.

    Membership is read off the status word alone, so a row whose literal is
    incomplete still counts as a carry for the header check below: a
    malformed freeze must not be able to hide the missing header field.
    """
    return [
        r["id"]
        for r in rows
        if r["terminal"].strip().lower().startswith(FROZEN_CARRIED)
    ]


def round_started(lines: list[str]) -> date | None:
    """Return the ledger's `Round-started:` date, or None if it is not read.

    A date that is absent, unparseable or not a calendar-valid one is None:
    the chronology of a window of ledgers is DERIVED from this field, and a
    field that cannot be read never becomes a guess.
    """
    for raw in lines:
        m = ROUND_STARTED_RE.match(raw.rstrip("\n"))
        if m is None:
            continue
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def capture_sets(rows: list[Row], prefixes: list[str]) -> tuple[int, int]:
    """Return (D, f1) — distinct findings RAISED, and those raised by one lens.

    The capture-recapture sets are PER-LENS, so only rows whose id prefix is
    one of the declared lenses take part: a row a verifier raised was found
    by no lens at all and would inflate both counts.

    Findings are counted BEFORE adjudication (a refuted claim was still
    raised) and cross-lens duplicates are collapsed by the existing `=id`
    convention: a duplicate row's criterion cell opens with `=<primary-id>`,
    so its row joins the primary's group and the group's lens set is the
    union of the prefixes of every row in it. `D` is the number of groups,
    `f1` the number of groups exactly one lens contributed to.
    """
    groups: dict[str, set[str]] = {}
    for r in rows:
        prefix = r["id"].rsplit("-", 1)[0]
        if prefix not in prefixes:
            continue
        criterion = r["criterion"] or ""
        dup = DUPLICATE_OF_RE.match(criterion.strip())
        key = dup.group(1) if dup else r["id"]
        groups.setdefault(key, set()).add(prefix)
    return len(groups), sum(1 for s in groups.values() if len(s) == 1)


def estimate_lines(lines: list[str], rows: list[Row]) -> list[str]:
    """Return the residual-defect ESTIMATE block — report-only, always.

    `N-hat = D + ((k-1)/k) * f1`, the Jackknife capture-recapture estimator,
    printed ONLY at `k >= 4` and otherwise as the named `n/a` form. It never
    reaches an exit code and it is not part of any stop rule: it is an
    ADVISORY number, and the caveat printed beside it says whose caution it
    carries.
    """
    prefixes = lens_prefixes(lines)
    k = len(prefixes)
    if k == 0:
        return [
            (
                "residual-defect ESTIMATE: n/a: k not derived from the header "
                "(no `Lenses:` field with machine-readable "
                "` - <PREFIX> | <lens> | <model>` lines) — k is never guessed "
                "from the id prefixes in the table."
            ),
        ]
    if k < JACKKNIFE_MIN_LENSES:
        return [
            (
                f"residual-defect ESTIMATE: n/a: k<4 (k={k}; the Jackknife "
                f"estimator is applied from four lenses up)."
            ),
        ]
    d, f1 = capture_sets(rows, prefixes)
    n_hat = d + ((k - 1) / k) * f1
    return [
        (
            f"residual-defect ESTIMATE (Jackknife capture-recapture): "
            f"N-hat {n_hat:.1f} | D {d} raised | f1 {f1} single-lens | k {k} "
            f"({', '.join(prefixes)})"
        ),
        (
            "  ESTIMATE is ADVISORY, reported and never acted on: it enters no "
            "stop rule and no exit code. Lens diversity does not invalidate it "
            "(the source measured little or no impact on the estimate), but the "
            "caution that remains is OURS and is named as ours: our four field "
            "measurements put the single-lens share at 75-94% and N-hat near "
            "2*D, and they count D as distinct CONFIRMED findings where this "
            "line counts distinct RAISED ones, so comparability is not "
            "established. Treat the number as advice, not as a target."
        ),
    ]


def plateau_count(rows: list[Row]) -> int:
    """Return a ledger's major+blocker row count — the plateau's quantity."""
    return sum(1 for r in rows if r["severity"].strip().lower() in PLATEAU_SEVERITIES)


def plateau_line(counts: list[int]) -> str:
    """Return the severity-weighted plateau line for an ORDERED window.

    `counts` is oldest-first and holds exactly `PLATEAU_WINDOW` entries, so
    the window yields two deltas and the moving average is their mean. The
    caller has already ordered them by `Round-started`; this function never
    reorders and never checks chronology.
    """
    deltas = [counts[i + 1] - counts[i] for i in range(len(counts) - 1)]
    average = sum(deltas) / len(deltas)
    return (
        f"severity plateau ({PLATEAU_WINDOW}-round moving average of "
        f"major+blocker deltas): {average:+.1f} | major+blocker per round "
        f"(oldest first): {' -> '.join(str(c) for c in counts)} | deltas "
        f"{', '.join(f'{d:+d}' for d in deltas)} — reported beside the "
        f"binary streak, never instead of it."
    )


def shelf_slugs(row: Row) -> list[str]:
    """Return the `shelf:` slugs a verdict cell carries (usually none)."""
    return SHELF_TAG_RE.findall(row["verdict"])


def sustained_lines(
    prefixes: list[str],
    window: list[tuple[str, list[Row]]],
) -> list[str]:
    """Return the per-lens sustained rate with the shelf share beside it.

    The rate is upheld over RAISED, per declared lens, over the whole
    window — this ledger plus the `--prev` ledgers that parsed — which is
    what makes it SUSTAINED rather than one round's rate. The shelf share
    beside it is the share of that lens's REFUTATIONS carrying a `shelf:`
    tag, and the two are printed together on purpose: a lens below the
    baseline has its framing tightened in the next round, never dropped,
    and that call is PAIRED — the rate alone never triggers it, because
    refutations the contract's shelf closed were cheap to refute rather
    than wrong to raise.

    Report-only in every branch: nothing here reaches an exit code, and a
    figure that cannot be computed is `n/a: <reason>` and never `0`. The
    prefixes come from the header's machine-form `Lenses:` lines — the same
    single source `k` uses — so a header that declares none yields one
    `n/a` line rather than a count guessed off the findings table.
    """
    if not prefixes:
        return [
            (
                "per-lens sustained rate: n/a: no machine-form `Lenses:` lines "
                "in the header — the rate is never counted off the id prefixes "
                "in the findings table, where verification passes write rows too"
            ),
        ]
    rows = [r for _, ledger_rows in window for r in ledger_rows]
    if any(r["criterion"] is None for r in rows):
        return [
            (
                "per-lens sustained rate: n/a: a v1 (7-cell) ledger in the "
                "window has no criterion column, so upheld and refuted cannot "
                "be split"
            ),
        ]
    shelf_in_use = any(shelf_slugs(r) for r in rows)
    out = [
        (
            f"per-lens sustained rate (upheld/raised over the window: this "
            f"ledger and {len(window) - 1} previous), shelf share beside it:"
        ),
    ]
    for prefix in prefixes:
        # A row's prefix is everything before the FINAL `-<n>` (the id
        # contract at the top of this file), which is the same reading
        # `security_lens_errors` and `capture_sets` use. It matters only
        # for a composite id such as `V-CIT-1`, whose prefix is `V-CIT`
        # and never the leading `V`; for every single-segment id the two
        # readings are the same string.
        mine = [r for r in rows if r["id"].rsplit("-", 1)[0] == prefix]
        if not mine:
            out.append(
                f"  {prefix}: n/a: no rows raised under this prefix in the window",
            )
            continue
        upheld = [r for r in mine if is_upheld(r)]
        refuted = [r for r in mine if not is_upheld(r)]
        rate = PERCENT * len(upheld) / len(mine)
        if not shelf_in_use:
            shelf = (
                "shelf n/a: no `shelf:` tag anywhere in the window — the tag "
                "is optional and was never set, which is not a share of zero"
            )
        elif not refuted:
            shelf = "shelf n/a: no refutation for a contract shelf to close"
        else:
            shelved = sum(1 for r in refuted if shelf_slugs(r))
            shelf = (
                f"shelf {shelved}/{len(refuted)} = "
                f"{PERCENT * shelved / len(refuted):.1f}%"
            )
        out.append(
            f"  {prefix}: sustained {len(upheld)}/{len(mine)} = {rate:.1f}% | {shelf}",
        )
        if rate < SUSTAINED_BASELINE_PCT:
            out.append(
                f"  {prefix}: BELOW THE {SUSTAINED_BASELINE_PCT:.0f}% BASELINE "
                f"— that baseline is OURS, one measured round, not a "
                f"literature figure. The next round TIGHTENS this lens's "
                f"framing rather than dropping the lens, and only when the "
                f"shelf share beside this rate agrees: the rate alone is "
                f"never the trigger.",
            )
    return out


def resolve_register(ledger_path: str, explicit: str | None) -> tuple[Path | None, str]:
    """Return (the residue register's path, reason-when-None).

    With `--register` the path is taken as given, whatever it is. Without
    the flag it is DERIVED from the layout convention the docstring states
    as this script's contract: the register sits beside the run folders, in
    the `.critic-ledger/` directory that CONTAINS the ledger. Walking the
    ledger's ancestors for that directory name serves both the ordinary
    address and an archived one nested further down, without either being
    special-cased. A ledger outside such a directory derives nothing.
    """
    if explicit is not None:
        return Path(explicit), ""
    for parent in Path(ledger_path).resolve().parents:
        if parent.name == RUN_ROOT_DIR:
            return parent / REGISTER_NAME, ""
    return None, (
        f"path not derived — the ledger is outside a {RUN_ROOT_DIR}/ directory"
    )


def register_row_error(cells: list[str], n: int) -> str | None:
    """Return the first structural defect of one register row, or None.

    Fail-closed, exactly like the ledger's own row parsing: the register is
    the durable record of accepted risk, and a row nobody can read is a
    risk nobody re-counts. A blank `rationale` or `compensating-control` is
    a defect and not a gap to be filled later — the whole point of the two
    cells is that the acceptance was argued when it was made.
    """
    rid, severity, _hook, rationale, control, review_by, status = cells[:7]
    if severity.strip().lower() == BLOCKER:
        return (
            f"line {n}: {rid} is severity {BLOCKER} — a blocker is "
            f"categorically non-nominable and may not appear in the register"
        )
    if rationale.strip() in REGISTER_BLANK:
        return f"line {n}: {rid} has a blank `rationale` — a mandatory field"
    if control.strip() in REGISTER_BLANK:
        return (
            f"line {n}: {rid} has a blank `compensating-control` — the "
            f"literal 'none — direct risk accepted' is allowed, a blank cell "
            f"is not"
        )
    try:
        date.fromisoformat(review_by.strip())
    except ValueError:
        return (
            f"line {n}: {rid} has `review-by` {review_by.strip()!r} — it must "
            f"be a calendar-valid ISO date (YYYY-MM-DD)"
        )
    m = REGISTER_STATUS_RE.match(status.strip())
    if m is None:
        return (
            f"line {n}: {rid} has `status` {status.strip()!r} — it must be "
            f"one of {', '.join(REGISTER_STATUSES)}, each followed by an ISO "
            f"date, the last optionally by its cycle counter '(#<n>)'"
        )
    try:
        date.fromisoformat(m.group(2))
    except ValueError:
        return (
            f"line {n}: {rid} has status date {m.group(2)!r} — not a calendar "
            f"date (YYYY-MM-DD)"
        )
    return None


def parse_register(lines: list[str]) -> tuple[list[RegisterRow], list[str]]:
    """Return (rows, errors) for the residue register's single table.

    The table is the FIRST one whose header's first cell is
    `run-qualified id`; rows are read up to the next markdown heading. The
    width is fixed at eight — the register is a new file with one schema,
    so it has no legacy width to accept.
    """
    rows: list[RegisterRow] = []
    errors: list[str] = []
    in_table = False
    for n, raw in enumerate(lines, 1):
        stripped = raw.rstrip("\n").strip()
        if not in_table:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and cells[0].lower() == REGISTER_HEADER_FIRST:
                in_table = True
                if len(cells) != REGISTER_WIDTH:
                    errors.append(
                        f"line {n}: register header has {len(cells)} cells; "
                        f"the table is {REGISTER_WIDTH}-cell",
                    )
                    break
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("|") or re.fullmatch(r"\|[-| :]+\|", stripped):
            continue
        cells = split_row(stripped)
        if cells is None or len(cells) != REGISTER_WIDTH:
            errors.append(
                f"line {n}: malformed register row "
                f"({0 if cells is None else len(cells)} cells, need "
                f"{REGISTER_WIDTH} — unescaped pipe?): {stripped[:80]}",
            )
            continue
        problem = register_row_error(cells, n)
        if problem:
            errors.append(problem)
            continue
        m = REGISTER_STATUS_RE.match(cells[6].strip())
        if m is None:
            # Unreachable: `register_row_error` above returns a message for
            # exactly this case and the row was skipped there. The guard
            # narrows the type without an assert, and a future edit that
            # loosens that check drops the row instead of raising.
            continue
        rows.append(
            {
                "rid": cells[0],
                "severity": cells[1],
                "review_by": date.fromisoformat(cells[5].strip()),
                "status": m.group(1),
                "status_date": date.fromisoformat(m.group(2)),
                "cycle": int(m.group(3)) if m.group(3) else 1,
                "line": n,
            },
        )
    seen: set[str] = set()
    for r in rows:
        if r["rid"] in seen:
            errors.append(
                f"line {r['line']}: DUPLICATE REGISTER ID {r['rid']} — one "
                f"row per nominee",
            )
        seen.add(r["rid"])
    return rows, errors


def register_lines(
    reg: list[RegisterRow],
    nominated: list[str],
    today: date,
) -> list[str]:
    """Return the register's aggregate and its escalation lines.

    REPORT-ONLY, always: no line here reaches an exit code. The aggregate is
    the anti-normalization measure — accepted risk that nobody re-counts
    stops being felt as risk — and the escalations are what keep a row from
    sitting in the queue forever. What the report canNOT do is drain the
    queue; the docstring's register bullet states that boundary in full.
    """
    counts = dict.fromkeys(REGISTER_STATUSES, 0)
    for r in reg:
        counts[r["status"]] += 1
    body = " | ".join(f"{s} {counts[s]}" for s in REGISTER_STATUSES)
    if reg:
        oldest = min(r["status_date"] for r in reg)
        oldest_row = next(r for r in reg if r["status_date"] == oldest)
        age = f"oldest {(today - oldest).days} days ({oldest}, {oldest_row['rid']})"
    else:
        age = "oldest n/a (empty register)"
    out = [f"rows: {len(reg)} | {body} | {age}"]
    for r in reg:
        held = (today - r["status_date"]).days
        if r["status"] == "nominated" and held > NOMINATION_MAX_DAYS:
            out.append(
                f"NOMINATION OVERDUE: {r['rid']} (nominated "
                f"{r['status_date']}, {held} days; the "
                f"{NOMINATION_MAX_DAYS}-day limit on an UNRATIFIED "
                f"nomination is OURS, no standard supplies it) — put it to "
                f"the owner as its own fork: ratify it, withdraw the "
                f"nomination (the row goes back to adjudication as an open "
                f"finding), or set a new date on the owner's explicit word. "
                f"A permanently `nominated` row is banned.",
            )
        if r["status"] == "ratified" and r["review_by"] < today:
            out.append(
                f"REVIEW-BY EXPIRED: {r['rid']} (review-by {r['review_by']}, "
                f"{(today - r['review_by']).days} days ago) — expiry RE-OPENS "
                f"by default and is never a silent renewal: the row enters "
                f"the next round on this object as a re-opened finding.",
            )
        if r["status"] == "expired-reopened" and r["cycle"] >= SECOND_CYCLE:
            out.append(
                f"SECOND CYCLE — OWNER FORK REQUIRED: {r['rid']} "
                f"(expired-reopened {r['status_date']}, cycle #{r['cycle']}) "
                f"— a second expiry is never carried by a batch ratification "
                f"and never renewed in silence: it needs a FRESH "
                f"justification put to the owner, and until that fork is "
                f"decided the row counts as an open finding of the round.",
            )
    missing = [
        i
        for i in nominated
        if not any(r["rid"] == i or r["rid"].endswith("/" + i) for r in reg)
    ]
    if missing:
        out.append(
            "NOMINATION WITHOUT A REGISTER ROW: "
            + ", ".join(missing)
            + " — every nomination carries one register row (rationale, "
            "compensating control, review-by); ids are matched on the "
            "register's run-qualified form, `<run>/<id>`.",
        )
    out.append(
        "the queue drains only through the owner's ratification cadence and "
        "the escalations above: this report is visibility, not traction, and "
        "the register is append-only in this release.",
    )
    return out


def residue_report(
    ledger_path: str,
    register_arg: str | None,
    nominated: list[str],
) -> tuple[list[str], bool]:
    """Return (the residue-register block, register-is-well-formed).

    The block is produced only when the register is IN PLAY, and it is in
    play under exactly three conditions: `--register` was given, the derived
    file exists, or the ledger carries a nomination that a register must
    account for. Under none of them the block is EMPTY — which is what keeps
    a ledger with no register and no nomination recounting byte for byte as
    it did before residue existed (the compatibility promise).

    The second element is False only for a structurally broken register:
    the caller turns that into exit 2, by the same fail-closed rule as a
    malformed ledger row. Everything else here is report-only.
    """
    path, reason = resolve_register(ledger_path, register_arg)
    exists = path is not None and path.is_file()
    if not (register_arg is not None or exists or nominated):
        return [], True
    if path is None:
        return [f"residue register: n/a ({reason})"], True
    if not exists:
        return [f"residue register: n/a (not found at {path})"], True
    reg_lines, load_error = load(str(path))
    if reg_lines is None:
        return [f"residue register: n/a ({load_error})"], True
    reg, errors = parse_register(reg_lines)
    if errors:
        return (
            [f"residue register: {path}", "RESIDUE REGISTER STRUCTURAL ERRORS:"]
            + ["  " + e for e in errors],
            False,
        )
    today = datetime.now(UTC).date()
    return (
        [f"residue register: {path}"]
        + ["  " + line for line in register_lines(reg, nominated, today)],
        True,
    )


def passes_table(lines: list[str]) -> tuple[list[PassRow], bool]:
    """Return (rows, has_time_columns) for the verification-passes table.

    Binds to the FIRST table whose first header cell is `#`, exactly as
    before. The new-findings column is located BY NAME when the header
    names it and by index 3 otherwise, so every passes-table width already
    in the wild keeps reading the same cell. `started`/`ended` are read
    only when the header carries both: their absence is a v1 table, never
    an error.
    """
    rows: list[PassRow] = []
    header: list[str] = []
    in_table = False
    for raw in lines:
        stripped = raw.strip()
        if not in_table:
            cells = split_row(stripped) if stripped.startswith("|") else None
            if cells and cells[0] == "#":
                in_table = True
                header = [c.strip().lower() for c in cells]
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("|") or re.fullmatch(r"\|[-| :]+\|", stripped):
            continue
        cells = split_row(stripped)
        if not cells:
            continue
        idx = (
            header.index(NEW_FINDINGS_NAME)
            if NEW_FINDINGS_NAME in header
            else NEW_FINDINGS_INDEX
        )
        new: int | None = None
        if len(cells) > idx:
            m = re.search(r"\d+", cells[idx])
            if m:
                new = int(m.group())
        rows.append(
            {
                "ordinal": cells[0] if cells[0].isdigit() else str(len(rows) + 1),
                "new": new,
                "started": cell_by_name(cells, header, STARTED_NAME),
                "ended": cell_by_name(cells, header, ENDED_NAME),
            },
        )
    has_time = STARTED_NAME in header and ENDED_NAME in header
    return rows, has_time


def cell_by_name(cells: list[str], header: list[str], name: str) -> str | None:
    """Return a row's cell for a named column, or None if there is no column.

    None means "this table has no such column" (a v1 passes table); the
    empty string means the column exists and the cell is empty, which is a
    v2 cell that cannot be read — the two are deliberately not merged.
    """
    if name not in header:
        return None
    i = header.index(name)
    return cells[i] if i < len(cells) else ""


def parse_ts(cell: str) -> datetime | None:
    """Parse an ISO-8601 UTC timestamp at seconds resolution, or None."""
    if not TS_RE.fullmatch(cell.strip()):
        return None
    try:
        return datetime.strptime(cell.strip(), TS_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def time_axis_lines(rows: list[PassRow], *, has_time: bool) -> list[str]:
    """Return the time-axis lines that accompany the ordinal curve.

    REPORT-ONLY, always: nothing here reaches an exit code. A table without
    the two columns is a v1 table and says so in one line; a timestamp that
    is present but unparseable is named by row and column and the time axis
    is suppressed, leaving the ordinal curve above untouched.
    """
    if not has_time:
        return ["time axis: n/a (no started/ended columns — v1 passes table)"]
    bad: list[str] = []
    parsed: list[tuple[PassRow, datetime, datetime]] = []
    for p in rows:
        started, ended = parse_ts(p["started"] or ""), parse_ts(p["ended"] or "")
        for name, value in ((STARTED_NAME, started), (ENDED_NAME, ended)):
            if value is None:
                bad.append(
                    f"passes: row {p['ordinal']} '{name}' unparseable "
                    f"— time axis suppressed",
                )
        if started is not None and ended is not None:
            parsed.append((p, started, ended))
    if bad:
        return bad
    # Unreachable while the caller prints the axis only when the ordinal
    # curve is non-empty: a curve value comes from a row, so `rows` — and
    # with no `bad` entries, `parsed` — cannot be empty here. The guard is
    # kept deliberately, so a future caller that drops that gate gets a
    # printed line instead of an IndexError on `parsed[0]`.
    if not parsed:
        return ["time axis: n/a (passes table has no rows)"]
    origin = parsed[0][1]
    axis = " | ".join(
        f"+{int((s - origin).total_seconds())}s -> "
        f"{'?' if p['new'] is None else p['new']}"
        for p, s, _ in parsed
    )
    wall = " | ".join(
        f"{p['ordinal']}: {int((e - s).total_seconds())}s" for p, s, e in parsed
    )
    return [
        f"time-indexed curve (from {origin.strftime(TS_FORMAT)}): {axis}",
        f"pass wall-clock: {wall}",
    ]


def trace_line(path: str) -> str:
    """Return the one report-only line about the round's trace file.

    Nothing about a trace can change an exit code: a missing file, a
    directory, an undecodable file and a corrupt line are all reported and
    counted, never raised. The trace is not the ledger.
    """
    p = Path(path)
    try:
        with p.open(encoding="utf-8") as fh:
            raw = fh.readlines()
    except FileNotFoundError:
        return "trace: none"
    except (OSError, UnicodeDecodeError):
        return f"trace: unreadable ({p.name})"
    records, unreadable = 0, 0
    for line in raw:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            unreadable += 1
            continue
        if isinstance(obj, dict):
            records += 1
        else:
            unreadable += 1
    if unreadable:
        return f"trace: {records} records, {unreadable} unreadable lines skipped"
    return f"trace: {records} records"


def load(path: str) -> tuple[list[str] | None, str | None]:
    """Read a ledger file: return (lines, None), or (None, message).

    An input that cannot be opened or decoded is a STRUCTURAL error
    (exit 2 at the call site), never an uncaught traceback that the shell
    reports as exit 1 — the code that means "open rows remain".
    """
    try:
        with Path(path).open(encoding="utf-8") as fh:
            return fh.readlines(), None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except UnicodeDecodeError as exc:
        return None, f"cannot decode {path} as UTF-8: {exc}"


def main() -> int:
    """Recount the ledger named on the command line and return the exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    prev_paths: list[str] = []
    while "--prev" in args:
        i = args.index("--prev")
        if i + 1 >= len(args):
            print("--prev needs a path")
            print(__doc__)
            return 2
        prev_paths.append(args[i + 1])
        del args[i : i + 2]
    if len(prev_paths) > MAX_PREV:
        print(
            f"--prev takes at most {MAX_PREV} paths (the plateau window is "
            f"{PLATEAU_WINDOW} ledgers: this one and two previous)",
        )
        print(__doc__)
        return 2
    trace_path = None
    if "--trace" in args:
        i = args.index("--trace")
        if i + 1 >= len(args):
            print("--trace needs a path")
            print(__doc__)
            return 2
        trace_path = args[i + 1]
        del args[i : i + 2]
    register_arg = None
    if "--register" in args:
        i = args.index("--register")
        if i + 1 >= len(args):
            print("--register needs a path")
            print(__doc__)
            return 2
        register_arg = args[i + 1]
        del args[i : i + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    lines, load_error = load(args[0])
    if lines is None:
        print(load_error)
        return 2

    frozen = [
        raw
        for raw in lines
        if raw.strip().lower().startswith(("- ledger state:", "ledger state:"))
        and "frozen" in raw.lower()
    ]
    if frozen:
        print("LEDGER IS FROZEN (superseded by a rewrite) — not closable:")
        print("  " + frozen[0].strip())
        return 3

    rows, errors = parse_findings(lines)
    if not rows and not errors:
        print("no ledger rows found — wrong file or broken table?")
        return 2
    seen: set[str] = set()
    for r in rows:
        if r["id"] in seen:
            errors.append(f"line {r['line']}: DUPLICATE ROW ID {r['id']}")
        seen.add(r["id"])
    # The header fields the round CONTRACT adds. Both are absent from every
    # ledger written before it, and absence is silence here: a ledger with
    # neither field, and no row using either status, recounts exactly as it
    # did before this script learned about contracts at all.
    schema_error = row_schema_error(lines, findings_header_width(lines))
    if schema_error:
        errors.append(schema_error)
    lens_prefix, lens_field_error = security_lens(lines)
    if lens_field_error:
        errors.append(lens_field_error)
    errors += security_lens_errors(rows, lens_prefix)
    process, process_field_error = process_prefixes(lines)
    if process_field_error:
        errors.append(process_field_error)
    errors += process_prefix_errors(process, lens_prefixes(lines))
    freeze, freeze_error = stop_rule_freeze(lines)
    if freeze_error:
        errors.append(freeze_error)
    carried = frozen_carried_ids(rows)
    if carried and freeze is None and freeze_error is None:
        errors.append(
            f"{', '.join(carried)}: `{FROZEN_CARRIED}` with no "
            f"`Stop-rule freeze:` field in the header — a freeze that names "
            f"no carry is a transfer into nowhere",
        )
    if errors:
        print("STRUCTURAL ERRORS — no count is trustworthy until fixed:")
        for e in errors:
            print("  " + e)
        return 2

    open_rows: list[str] = []
    sig_rows: list[str] = []
    z3_rows: list[str] = []
    problems: list[str] = []
    for r in rows:
        ok, problem = terminal_status(r)
        if ok:
            continue
        if problem:
            problems.append(problem)
        wait, wait_problem = waiting_state(r)
        if wait_problem:
            problems.append(wait_problem)
        if wait == AWAITING_SIGNATURE:
            sig_rows.append(r["id"])
        elif wait == AWAITING_LOGGED_NO_ACTION:
            z3_rows.append(r["id"])
        else:
            open_rows.append(r["id"])
    non_terminal = open_rows + sig_rows + z3_rows
    pending = freeze is not None and freeze[1].strip().lower() == CARRIED_TO_PENDING
    if carried and not non_terminal and pending:
        print("STRUCTURAL ERRORS — no count is trustworthy until fixed:")
        print(
            f"  `Stop-rule freeze:` still reads `carried-to: "
            f"{CARRIED_TO_PENDING}` while the round closes over "
            f"{len(carried)} carried row(s) — the round they are carried "
            f"into is named before the carry is believed, never after",
        )
        return 2
    print(
        f"rows: {len(rows)} | terminal: {len(rows) - len(non_terminal)} | "
        f"non-terminal: {len(non_terminal)}",
    )
    for p in problems:
        print("  CONSISTENCY: " + p)
    print(severity_line(rows, set(non_terminal)))
    print(upheld_line(rows))
    for line in not_adjudicated_lines(rows):
        print(line)
    for line in class_kill_lines(rows, lens_prefix):
        print(line)
    for line in injection_lines(rows):
        print(line)
    for line in estimate_lines(lines, rows):
        print(line)
    report, register_ok = residue_report(args[0], register_arg, sig_rows)
    for line in report:
        print(line)
    if not register_ok:
        return 2

    pass_rows, has_time = passes_table(lines)
    c = [p["new"] for p in pass_rows if p["new"] is not None]
    if c:
        print("new-findings curve:", " -> ".join(map(str, c)))
        if len(c) >= KILL_CRITERION_WINDOW and c[-1] >= c[-2] >= c[-3] and c[-3] > 0:
            print(
                "  KILL-CRITERION WARNING: curve has not decayed for "
                "three consecutive passes — stop and fork to the user.",
            )
        for line in time_axis_lines(pass_rows, has_time=has_time):
            print("  " + line)
    if trace_path:
        print(trace_line(trace_path))

    if prev_paths:
        # Every `--prev` ledger is loaded before anything is ordered: the
        # window's chronology is DERIVED from the ledgers themselves.
        loaded: list[tuple[str, list[Row], bool]] = []
        prev_starts: list[date | None] = []
        for path in prev_paths:
            prev_lines, prev_load_error = load(path)
            if prev_lines is None:
                print(prev_load_error)
                return 2
            prev_rows, prev_errors = parse_findings(prev_lines)
            loaded.append((path, prev_rows, not prev_errors))
            prev_starts.append(round_started(prev_lines))
        plateau_reason: str | None = None
        if len(loaded) < MAX_PREV:
            plateau_reason = (
                f"n/a: {len(loaded)} previous ledger given; the "
                f"{PLATEAU_WINDOW}-round window needs two"
            )
        elif (
            round_started(lines) is None
            or prev_starts[0] is None
            or prev_starts[1] is None
            or prev_starts[0] == prev_starts[1]
        ):
            # Positional trust in the argument order is banned outright: with
            # no readable, distinct `Round-started` the window has no order,
            # so the plateau is not computed and the ordinary delta stands.
            plateau_reason = (
                "n/a: the order of the previous ledgers is not derived "
                "(Round-started missing, unreadable or the same in both)"
            )
        elif prev_starts[0] < prev_starts[1]:
            loaded = [loaded[1], loaded[0]]
            print("prev order: reordered by Round-started")
        prev_path, prev_rows, prev_ok = loaded[0]
        if plateau_reason is None and not all(ok for _, _, ok in loaded):
            plateau_reason = "n/a: a --prev ledger has structural errors"
        if not prev_ok:
            print("--prev ledger has structural errors; delta skipped.")
        else:
            prev = {r["id"]: terminal_status(r)[0] for r in prev_rows}
            cur = {r["id"]: terminal_status(r)[0] for r in rows}
            newly = sorted(i for i, t in cur.items() if t and not prev.get(i, False))
            regressed = sorted(
                i for i, t in cur.items() if not t and prev.get(i, False)
            )
            still = sorted(
                i for i, t in cur.items() if not t and i in prev and not prev[i]
            )
            new_open = sorted(i for i, t in cur.items() if not t and i not in prev)
            print(
                f"DELTA vs {prev_path}: newly-terminal {newly or '[]'} | "
                f"regressed {regressed or '[]'} | still-open "
                f"{still or '[]'} | new-open {new_open or '[]'}",
            )
            # Unreachable while the three predicates above stay exhaustive:
            # an open id is either absent from `prev` (-> new_open) or
            # present with a truthy (-> regressed) / falsy (-> still) value,
            # so `uncovered` is always empty. The guard is kept deliberately:
            # it makes a future edit to the bucket predicates fail loudly
            # instead of silently dropping ids from the delta.
            uncovered = (
                {i for i, t in cur.items() if not t}
                - set(regressed)
                - set(still)
                - set(new_open)
            )
            if uncovered:
                print(
                    "  DELTA COMPLETENESS ERROR — open ids missing from every bucket:",
                    ", ".join(sorted(uncovered)),
                )
                return 2
        # The per-lens sustained rate is a BETWEEN-ROUNDS report like the
        # delta above it, so it lives here and not in the single-ledger
        # block: the window is this ledger plus every `--prev` that parsed.
        window: list[tuple[str, list[Row]]] = [(args[0], rows)]
        window += [(p, prs) for p, prs, ok in loaded if ok]
        for line in sustained_lines(lens_prefixes(lines), window):
            print(line)
        # The plateau follows the delta it is the severity-weighted form of,
        # so a single `--prev` still prints exactly the 0.2.0 delta and then
        # one line naming why the moving average could not be computed.
        if plateau_reason is None:
            print(
                plateau_line(
                    [
                        plateau_count(loaded[1][1]),
                        plateau_count(loaded[0][1]),
                        plateau_count(rows),
                    ],
                ),
            )
        else:
            print("severity plateau: " + plateau_reason)

    # The four buckets, in the order the docstring fixes. Every list that
    # has members is printed; exactly ONE state line follows, that of the
    # first bucket that matches.
    if open_rows:
        print("non-terminal ids:", ", ".join(open_rows))
    if sig_rows:
        print("awaiting-signature ids:", ", ".join(sig_rows))
    if z3_rows:
        print("awaiting-logged-no-action ids:", ", ".join(z3_rows))
        for line in z3_overdue_lines(rows, z3_rows, datetime.now(UTC).date()):
            print("  " + line)
    if open_rows:
        print(f"ROUND NOT CLOSABLE: {len(open_rows)} open rows.")
        return 1
    if sig_rows:
        print(
            f"ROUND AWAITING RATIFICATION: {len(sig_rows)} rows await the "
            f"owner's signature.",
        )
        return 1
    if z3_rows:
        print(
            f"ROUND AWAITING Z3 CLOSURE: {len(z3_rows)} rows await the owner's act.",
        )
        return 1
    if carried and freeze is not None:
        print(f"FROZEN CARRIED: {len(carried)} rows → {freeze[1]}")
    print("ROUND CLOSABLE: zero non-terminal rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
