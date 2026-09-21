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
  (`scripts/transcribe.py` leaves the placeholder `·` there, since
  transcription is literal copying and the zone is a judgment). A zone
  changes the PAPER and the CLOSURE ROUTE of a row and nothing else: it
  never lowers a severity, never relaxes a check, and never weakens the
  fresh-verifier rule. The one mechanical consequence read here is the
  terminal status `logged-no-action`, which no row outside `Z3` may take.
- The ROW SCHEMA IS DECLARED IN THE HEADER, and a declaration that
  disagrees with the table is a STRUCTURAL error. The optional header
  field `Row schema: v1 | v2 | v3` is what tells a reader — this script,
  `scripts/transcribe.py`, a verifier — which form the table takes
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
  code; a ledger carrying no such tag prints nothing here. The SAME
  knowledge decides the threshold line itself: the kill is DUE only where
  the class has no kill row at all, `CLASS-KILL IN FLIGHT: <slug>` where
  one is open and `CLASS-KILL DONE: <slug>` where one is terminal. Telling
  an adjudicator to open a row he has already opened is a false statement
  the eye learns to skip, and skipping it is how a real DUE goes unread.
- The INJECTION RATE per fix batch: the findings tagged
  `origin:fix-application from:<batch>` over the number of rows that batch
  fixed. Both sides come from machine-readable cells. DENOMINATOR: the
  rows a batch fixed all carry that batch's identifier in their `fix`
  cell, grouped by literal match — the ledger's "Batch deltas" prose is a
  historical snapshot and is deliberately NOT parsed. NUMERATOR: the
  `from:<batch>` reference, which alone says whose fix produced the
  finding. The batch KEY of a `fix` cell is the first HASH-LIKE token in
  it, whatever precedes it: `F3 c447822 (touch-up)` and a bare `c447822`
  name one batch, as the round's own prose does. A cell carrying no
  hash-like token keeps its whole literal as the key (a snapshot name), so
  nothing that used to group still splits. A tagged row without a readable
  `from:` is listed as
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
- The SEVERITY-WEIGHTED PLATEAU, printed on TWO lines — the numbers, then
  one line saying in its own words that they are advisory. It sits beside
  the binary streak rule and never instead of it: the moving average of the
  major+blocker deltas over a window of THREE ledgers — this one and two
  `--prev` — which is two deltas, averaged. The quantity per ledger is the
  count of rows whose severity cell reads `major` or `blocker`; the severity
  cell is index 1 in all three schemas, so a 7-cell ledger takes part like
  any other.
  With fewer inputs the line is `severity plateau: n/a: <reason>` and the
  ordinary delta is unaffected.
- The new-findings CURVE from the "Verification passes" table (header
  starting `| # |`): the first integer of each "new findings" cell.
  Kill-criterion warning when the curve has not decayed for three
  consecutive passes. Under the curve, on its OWN line, the standing of the
  binary signal: `stop criterion (verdict streak): met | not met — <why>`,
  read from the NOT-LANDED and new-findings cells of the last two passes.
  It is SEVERITY-AWARE, as the rule it reports is: new findings the cell
  names as MINOR leave a pass clean, new major or blocker ones do not, and
  a count whose severity the cell does not name leaves it dirty (an unread
  severity is never read as minor).
  The curve and the criterion were one line once, and a first-time reader
  took "the curve is falling" for "the criterion is met" — they are
  different claims, so they are different lines. Report-only: the criterion
  line changes no exit code, exactly like the curve above it. The "new
  findings" column is located BY NAME when the passes header names it and by
  index 3 otherwise, so the positional behaviour of older ledgers is
  preserved exactly.
  When that table carries `started` and `ended` as its last two columns the
  curve is ALSO printed on a time axis, with the wall-clock of each pass;
  when it does not, one line says why there is no time axis. A timestamp
  that is present but unparseable is REPORTED BY NAME and the time axis is
  suppressed — it NEVER changes the exit code, because those two columns
  are optional and a measurement must not be able to fail a round.
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
  `nominated <date>`, `ratified <date>`, `expired-reopened <date>` or
  `withdrawn <date>`, the third optionally carrying its cycle counter as
  `(#<n>)`; a blocker may not
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
  withdrawn | age of the oldest`; `NOMINATION OVERDUE` for a `nominated` row past 30
  days, that limit being OURS and marked as ours; `REVIEW-BY EXPIRED` for a
  `ratified` row whose `review-by` has passed, since expiry RE-OPENS by
  default and is never a silent renewal; `SECOND CYCLE — OWNER FORK
  REQUIRED` for a row re-opened a second time, which no batch ratification
  may carry; and `NOMINATION WITHOUT A REGISTER ROW` for an
  `awaiting-signature` ledger id that no register row accounts for (ids are
  matched on the register's run-qualified form, `<run>/<id>`; a `withdrawn`
  row accounts for none).
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

Usage:  recount.py <ledger.md> [--prev <old-ledger.md>]...
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

import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

# The row grammar, the header-field grammar and the escaping live in ONE
# place — `scripts/ledger_md.py`, beside this script — so that a row is
# read the same way by everything that touches a ledger. The import is
# resolved from THIS script's own directory: the payload ships loose files
# and there is no installed package (see `pyproject.toml`), so a copy of
# these scripts without `ledger_md.py` beside them does not run.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The import sits below the path insert above, which is what makes it work.
from ledger_md import (
    EXIT_FROZEN,
    EXIT_NOT_CLOSABLE,
    EXIT_OK,
    EXIT_STRUCTURAL,
    findings_header_width,
    row_schema_error,
)

# The ledger's reading, its checks, its statuses, its metrics and its report
# lines live in five modules beside this script, imported the same way; this
# file keeps the argument handling, the phases and the order of printing.
from ledger_model import (
    CARRIED_TO_PENDING,
    Ledger,
    Row,
    load,
    parse_findings,
    read_ledger,
    round_started,
)
from metrics import (
    MAX_PREV,
    PLATEAU_WINDOW,
    plateau_count,
)
from report import (
    class_kill_lines,
    estimate_lines,
    injection_lines,
    not_adjudicated_lines,
    plateau_line,
    residue_report,
    severity_line,
    stop_criterion_line,
    sustained_lines,
    time_axis_lines,
    upheld_line,
    z3_overdue_lines,
)
from statuses import (
    AWAITING_LOGGED_NO_ACTION,
    AWAITING_SIGNATURE,
    FROZEN_CARRIED,
    frozen_carried_ids,
    terminal_status,
    waiting_state,
)
from structural_checks import (
    process_prefix_errors,
    security_lens_errors,
)

# Length of the window the kill criterion looks at.
KILL_CRITERION_WINDOW = 3


@dataclass(frozen=True)
class Tally:
    """The non-terminal ids by bucket, and the ids the stop rule carried."""

    open_rows: list[str]
    sig_rows: list[str]
    z3_rows: list[str]
    carried: list[str]


def structure_phase(
    ledger_path: str,
    register_arg: str | None,
) -> tuple[list[str], Ledger | None, list[str], int]:
    """Phase 1: load the ledger and refuse what no count can be trusted on.

    Returns (the ledger's lines, the ledger or None, the lines to print, the
    exit code). The ledger is None exactly when the run stops here with that
    code; otherwise there is nothing to print and the code is unused. The
    four stops keep their order: an unreadable file, a frozen ledger (before
    the findings table's errors are consulted), a file with no rows at all,
    and the accumulated structural errors.
    """
    lines, load_error = load(ledger_path)
    if lines is None:
        return [], None, [str(load_error)], EXIT_STRUCTURAL
    ledger, errors = read_ledger(
        lines, ledger_path=ledger_path, register_arg=register_arg
    )
    if ledger.ledger_state:
        frozen = [
            "LEDGER IS FROZEN (superseded by a rewrite) — not closable:",
            "  " + ledger.ledger_state[0].strip(),
        ]
        return lines, None, frozen, EXIT_FROZEN

    rows = ledger.rows
    if not rows and not errors:
        empty = [
            (
                "no ledger rows found — wrong file or broken table? (a "
                "fresh ledger before scripts/transcribe.py has run also "
                "prints this; run transcribe.py first)"
            )
        ]
        return lines, None, empty, EXIT_STRUCTURAL
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
    if ledger.security_lens_error:
        errors.append(ledger.security_lens_error)
    errors += security_lens_errors(rows, ledger.security_lens)
    if ledger.process_prefixes_error:
        errors.append(ledger.process_prefixes_error)
    errors += process_prefix_errors(ledger.process_prefixes, ledger.lens_prefixes)
    freeze, freeze_error = ledger.stop_rule_freeze, ledger.stop_rule_freeze_error
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
        block = ["STRUCTURAL ERRORS — no count is trustworthy until fixed:"]
        block += ["  " + e for e in errors]
        return lines, None, block, EXIT_STRUCTURAL
    return lines, ledger, [], EXIT_OK


def count_phase(ledger: Ledger) -> tuple[Tally, list[str], int | None]:
    """Phase 2: sort the rows into buckets and report the counts.

    Returns (the buckets, the lines to print, an exit code or None). The one
    stop here, a pending carry at closure, needs the buckets, so it cannot
    sit in phase 1; it comes before the counts.
    """
    rows = ledger.rows
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
    freeze = ledger.stop_rule_freeze
    pending = freeze is not None and freeze[1].strip().lower() == CARRIED_TO_PENDING
    carried = frozen_carried_ids(rows)
    tally = Tally(
        open_rows=open_rows, sig_rows=sig_rows, z3_rows=z3_rows, carried=carried
    )
    if carried and not non_terminal and pending:
        carry_error = (
            f"  `Stop-rule freeze:` still reads `carried-to: "
            f"{CARRIED_TO_PENDING}` while the round closes over "
            f"{len(carried)} carried row(s) — the round they are carried "
            f"into is named before the carry is believed, never after"
        )
        block = ["STRUCTURAL ERRORS — no count is trustworthy until fixed:"]
        block.append(carry_error)
        return tally, block, EXIT_STRUCTURAL
    out = [
        (
            f"rows: {len(rows)} | terminal: {len(rows) - len(non_terminal)} | "
            f"non-terminal: {len(non_terminal)}"
        ),
    ]
    out += ["  CONSISTENCY: " + p for p in problems]
    out += [severity_line(rows, set(non_terminal)), upheld_line(rows)]
    return tally, out, None


def report_phase(ledger: Ledger, tally: Tally) -> tuple[list[str], int | None]:
    """Phase 3: the single-ledger reports, in their printing order.

    Returns (the lines to print, an exit code or None). A structurally broken
    residue register stops the run after its own lines and before the curve.
    """
    rows = ledger.rows
    out: list[str] = []
    out += not_adjudicated_lines(rows)
    out += class_kill_lines(rows, ledger.security_lens)
    out += injection_lines(rows)
    out += estimate_lines(ledger.lens_prefixes, rows)
    report, register_ok = residue_report(
        ledger.ledger_path, ledger.register_arg, tally.sig_rows
    )
    out += report
    if not register_ok:
        return out, EXIT_STRUCTURAL

    pass_rows = ledger.pass_rows
    c = [p["new"] for p in pass_rows if p["new"] is not None]
    if c:
        out.append("new-findings curve: " + " -> ".join(map(str, c)))
        if len(c) >= KILL_CRITERION_WINDOW and c[-1] >= c[-2] >= c[-3] and c[-3] > 0:
            out.append(
                "  KILL-CRITERION WARNING: curve has not decayed for "
                "three consecutive passes — stop and fork to the user.",
            )
        axis = time_axis_lines(pass_rows, has_time=ledger.has_time)
        out += ["  " + line for line in axis]
        # The binary signal, on its OWN line and in its own words: the curve
        # above says which way the numbers move, this says whether the round
        # may stop. Neither is the other, and one line saying both was read
        # as the second when it meant the first.
        out.append(stop_criterion_line(pass_rows))
    return out, None


def between_rounds_phase(
    lines: list[str],
    ledger: Ledger,
    prev_paths: list[str],
) -> tuple[list[str], int | None]:
    """Phase 4: the between-rounds reports, produced only under `--prev`.

    Returns (the lines to print, an exit code or None). `lines` are this
    ledger's own lines, consulted for its `Round-started:` date alone.
    """
    rows = ledger.rows
    out: list[str] = []
    if prev_paths:
        # Every `--prev` ledger is loaded before anything is ordered: the
        # window's chronology is DERIVED from the ledgers themselves.
        loaded: list[tuple[str, list[Row], bool]] = []
        prev_starts: list[date | None] = []
        for path in prev_paths:
            prev_lines, prev_load_error = load(path)
            if prev_lines is None:
                out.append(str(prev_load_error))
                return out, EXIT_STRUCTURAL
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
            # WHICH ledger costs the metric is NAMED: a reason that only
            # said the order was underivable sent every reader back to
            # re-deriving three headers by hand.
            dated = list(
                zip(
                    [ledger.ledger_path, *(p for p, _, _ in loaded)],
                    [round_started(lines), *prev_starts],
                    strict=True,
                )
            )
            undated = [path for path, start in dated if start is None]
            detail = (
                "no readable Round-started in " + ", ".join(undated)
                if undated
                else "the same Round-started in "
                + ", ".join(path for path, _ in dated[1:])
            )
            plateau_reason = (
                f"n/a: the order of the previous ledgers is not derived ({detail})"
            )
        elif prev_starts[0] < prev_starts[1]:
            loaded = [loaded[1], loaded[0]]
            out.append("prev order: reordered by Round-started")
        prev_path, prev_rows, prev_ok = loaded[0]
        if plateau_reason is None and not all(ok for _, _, ok in loaded):
            plateau_reason = "n/a: a --prev ledger has structural errors"
        if not prev_ok:
            out.append("--prev ledger has structural errors; delta skipped.")
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
            out.append(
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
                missing = ", ".join(sorted(uncovered))
                out.append(
                    "  DELTA COMPLETENESS ERROR — open ids missing from every "
                    f"bucket: {missing}",
                )
                return out, EXIT_STRUCTURAL
        # The per-lens sustained rate is a BETWEEN-ROUNDS report like the
        # delta above it, so it lives here and not in the single-ledger
        # block: the window is this ledger plus every `--prev` that parsed.
        window: list[tuple[str, list[Row]]] = [(ledger.ledger_path, rows)]
        window += [(p, prs) for p, prs, ok in loaded if ok]
        out += sustained_lines(ledger.lens_prefixes, window)
        # The plateau follows the delta it is the severity-weighted form of,
        # so a single `--prev` still prints exactly the 0.2.0 delta and then
        # one line naming why the moving average could not be computed.
        if plateau_reason is None:
            out += plateau_line(
                [
                    plateau_count(loaded[1][1]),
                    plateau_count(loaded[0][1]),
                    plateau_count(rows),
                ],
            )
        else:
            out.append("severity plateau: " + plateau_reason)
    return out, None


def verdict_phase(ledger: Ledger, tally: Tally) -> tuple[list[str], int]:
    """Phase 5: the id buckets, then exactly one state line and its exit code."""
    rows = ledger.rows
    open_rows, sig_rows, z3_rows = tally.open_rows, tally.sig_rows, tally.z3_rows
    out: list[str] = []
    # The four buckets, in the order the docstring fixes. Every list that
    # has members is printed; exactly ONE state line follows, that of the
    # first bucket that matches.
    if open_rows:
        out.append("non-terminal ids: " + ", ".join(open_rows))
    if sig_rows:
        out.append("awaiting-signature ids: " + ", ".join(sig_rows))
    if z3_rows:
        out.append("awaiting-logged-no-action ids: " + ", ".join(z3_rows))
        today = datetime.now(UTC).date()
        out += ["  " + line for line in z3_overdue_lines(rows, z3_rows, today)]
    if open_rows:
        out.append(f"ROUND NOT CLOSABLE: {len(open_rows)} open rows.")
        return out, EXIT_NOT_CLOSABLE
    if sig_rows:
        out.append(
            f"ROUND AWAITING RATIFICATION: {len(sig_rows)} rows await the "
            f"owner's signature.",
        )
        return out, EXIT_NOT_CLOSABLE
    if z3_rows:
        out.append(
            f"ROUND AWAITING Z3 CLOSURE: {len(z3_rows)} rows await the owner's act.",
        )
        return out, EXIT_NOT_CLOSABLE
    freeze = ledger.stop_rule_freeze
    if tally.carried and freeze is not None:
        out.append(f"FROZEN CARRIED: {len(tally.carried)} rows → {freeze[1]}")
    out.append("ROUND CLOSABLE: zero non-terminal rows.")
    return out, EXIT_OK


def main() -> int:
    """Recount the ledger named on the command line and return the exit code."""
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return EXIT_OK
    prev_paths: list[str] = []
    while "--prev" in args:
        i = args.index("--prev")
        if i + 1 >= len(args):
            print("--prev needs a path")
            print(__doc__)
            return EXIT_STRUCTURAL
        prev_paths.append(args[i + 1])
        del args[i : i + 2]
    if len(prev_paths) > MAX_PREV:
        print(
            f"--prev takes at most {MAX_PREV} paths (the plateau window is "
            f"{PLATEAU_WINDOW} ledgers: this one and two previous)",
        )
        print(__doc__)
        return EXIT_STRUCTURAL
    register_arg = None
    if "--register" in args:
        i = args.index("--register")
        if i + 1 >= len(args):
            print("--register needs a path")
            print(__doc__)
            return EXIT_STRUCTURAL
        register_arg = args[i + 1]
        del args[i : i + 2]
    if len(args) != 1:
        print(__doc__)
        return EXIT_STRUCTURAL
    lines, ledger, out, exit_code = structure_phase(args[0], register_arg)
    for line in out:
        print(line)
    if ledger is None:
        return exit_code

    tally, out, stop = count_phase(ledger)
    for line in out:
        print(line)
    if stop is not None:
        return stop

    out, stop = report_phase(ledger, tally)
    for line in out:
        print(line)
    if stop is not None:
        return stop

    out, stop = between_rounds_phase(lines, ledger, prev_paths)
    for line in out:
        print(line)
    if stop is not None:
        return stop

    out, exit_code = verdict_phase(ledger, tally)
    for line in out:
        print(line)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
