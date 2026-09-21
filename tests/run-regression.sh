#!/bin/sh
# Regression suite for recount.py's ledger contract (77 cases, c01-c77).
# Builds every edge case in a temp dir and runs recount.py against each.
# Expected exit codes are in the case names: e0 / e1 / e2 / e3; the cases
# added for 0.2.0 observability also assert the LINES those cases fix,
# because "reported, never fatal" is a claim about output.
# Lives in tests/ (moved from the round's fixtures dir at publication).
set -u
R="$(dirname "$0")/../skills/critic-ledger/scripts/recount.py"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
H='| id | sev | claim | verdict | fix | verified | terminal |
|---|---|---|---|---|---|---|'
# 8-cell schema (readiness-criterion column after `verdict`); the 7-cell
# cases below stay as they are — legacy ledgers must keep recounting.
H8='| id | sev | claim | verdict | criterion | fix | verified | terminal |
|---|---|---|---|---|---|---|---|'
w(){ printf '%s\n%s\n' "$H" "$2" > "$T/$1"; }
w8(){ printf '%s\n%s\n' "$H8" "$2" > "$T/$1"; }
w c01-digit-prefix-e0.md      '| L1-3 | major | c | v | f | LANDED | verified-landed |'
w c02-unescaped-pipe-e2.md    '| DA-1 | major | a|b broken | v | f | LANDED | verified-landed |'
w c03-escaped-pipe-e0.md      '| DA-1 | major | a \| b fine | v | f | LANDED | verified-landed |'
w c04-short-row-e2.md         '| DA-1 | major | short | v | LANDED | verified-landed |'
w c05-inconsistent-e1.md      '| DA-1 | major | c | v | f | NOT LANDED | verified-landed |'
printf '%s\n%s\n\n## Appendix\n%s\n%s\n' "$H" '| DA-1 | major | c | v | f | LANDED | verified-landed |' "$H" '| DX-9 | minor | inherited | i | - | - | open |' > "$T/c06-appendix-excluded-e0.md"
w c07-residue-unsigned-e1.md  '| DA-1 | minor | c | v | f | x | accepted-residue (no signature) |'
w c08-residue-signed-e0.md    '| DA-1 | minor | c | v | f | x | accepted-residue user-signed 2026-08-05 |'
w c09-bare-aliases-e1.md      '| DA-1 | minor | c | v | f | x | refuted |
| DA-2 | minor | c | v | f | LANDED | closed-verified |'
w c10-superseded-row-e1.md    '| DA-1 | minor | c | v | f | x | superseded-by-rewrite |'
printf -- '- Ledger state: FROZEN (superseded-by-rewrite, fixture)\n%s\n%s\n' "$H" '| DA-1 | major | c | v | f | LANDED | verified-landed |' > "$T/c11-frozen-e3.md"
printf '%s\n%s\n\n## Verification passes\n| # | pass | verdicts | new findings | notes |\n|---|---|---|---|---|\n| 1 | a | L | 3 | - |\n| 2 | b | L | 4 | - |\n| 3 | c | L | 5 | - |\n' "$H" '| DA-1 | major | c | v | f | LANDED | verified-landed |' > "$T/c12-kill-warning-e0.md"
w c13-duplicate-id-e2.md      '| DA-1 | major | c | v | f | LANDED | verified-landed |
| DA-1 | minor | dup | v | f | LANDED | verified-landed |'
# VE-1 regression: brand-new open id must appear in the new-open bucket
w c14-prev-old.md             '| DA-1 | major | c | v | f | x | open |'
w c14-cur-e1.md               '| DA-1 | major | c | v | f | LANDED | verified-landed |
| VE-1 | major | brand new open | confirmed | f | x | open |'
# 8-cell schema and the outcomes added with it
w8 c15-eight-cell-e0.md       '| DA-1 | major | c | v | grep -c TODO = 0 | f | LANDED | verified-landed |'
w8 c16-otherwise-desc-e0.md   '| DA-1 | major | c | v | quotes before/after | f | LANDED OTHERWISE (section rewritten instead of deleted) | verified-landed |'
w8 c17-otherwise-nodesc-e1.md '| DA-1 | major | c | v | quotes before/after | f | LANDED OTHERWISE | verified-landed |
| DA-2 | major | c | v | quotes before/after | f | LANDED OTHERWISE () | verified-landed |'
w8 c18-refused-signed-e0.md   '| SE-1 | major | pii | refused | — | f | x | refused-user-signed 2026-08-09 |'
w8 c19-refused-bare-e1.md     '| SE-1 | major | pii | refused | — | f | x | refused |'
w8 c20-criterion-empty-e2.md  '| DA-1 | major | c | v |  | f | LANDED | verified-landed |'
w8 c21-criterion-set-e2.md    '| DA-1 | major | c | v | grep -c TODO = 0 | f | x | refuted-with-reason |'
w c22-six-cell-row-e2.md      '| DA-1 | major | c | v | LANDED | verified-landed |'
# HA-1 regression: an owner signature without a date is not a signature
w8 c23-residue-nodate-e1.md   '| DA-1 | minor | c | v | keep as is | f | x | accepted-residue user-signed |'
w8 c24-residue-parens-e1.md   '| DA-1 | minor | c | v | keep as is | f | x | accepted-residue (user-signed) |'
w8 c25-refused-nodate-e1.md   '| SE-1 | major | pii | refused | — | f | x | refused-user-signed |'
# HD-1 regression: accepted-residue is UPHELD — its criterion cell must stay
w8 c26-residue-nocrit-e2.md   '| DA-1 | minor | c | v |  | f | x | accepted-residue user-signed 2026-08-09 |'
w8 c27-residue-dashcrit-e2.md '| DA-1 | minor | c | v | — | f | x | accepted-residue user-signed 2026-08-09 |'
w8 c28-residue-crit-e0.md     '| DA-1 | minor | c | v | leak-gate stays red | f | x | accepted-residue user-signed 2026-08-09 |'
# --- 0.2.0 observability (c29-c36) -----------------------------------------
# The v1 passes table (5 columns, as c12) and the v2 one, which appends
# `started`/`ended` as its LAST two columns so that `new findings` stays at
# cell index 3 for every reader, new or old.
P1='| # | pass | verdicts | new findings | notes |
|---|---|---|---|---|
| 1 | a | L | 5 | - |
| 2 | b | L | 3 | - |
| 3 | c | L | 1 | - |'
P2='| # | pass | verdicts | new findings | notes | started | ended |
|---|---|---|---|---|---|---|
| 1 | a | L | 5 | - | 2026-08-10T10:00:00Z | 2026-08-10T10:30:00Z |
| 2 | b | L | 3 | - | 2026-08-10T11:00:00Z | 2026-08-10T11:15:00Z |
| 3 | c | L | 1 | - | 2026-08-10T12:00:00Z | 2026-08-10T12:10:00Z |'
P2BAD='| # | pass | verdicts | new findings | notes | started | ended |
|---|---|---|---|---|---|---|
| 1 | a | L | 5 | - | 2026-08-10T10:00:00Z | 2026-08-10T10:30:00Z |
| 2 | b | L | 3 | - | 2026-08-10T11:00:00Z | yesterday |
| 3 | c | L | 1 | - | 2026-08-10T12:00:00Z | 2026-08-10T12:10:00Z |'
ROW8='| DA-1 | major | c | v | crit | f | LANDED | verified-landed |'
# c29 — v1 7-cell ledger, no passes table: distribution printed, split n/a.
w c29-v1-seven-cell-e0.md     '| L1-3 | major | c | v | f | LANDED | verified-landed |'
# c30 — v1 8-cell ledger, 5-column passes table: the curve as it is today.
printf '%s\n%s\n\n## Verification passes\n%s\n' "$H8" "$ROW8" "$P1" > "$T/c30-v1-five-col-passes-e0.md"
# c31 — v2 passes table: time-indexed curve and per-pass wall-clock.
printf '%s\n%s\n\n## Verification passes\n%s\n' "$H8" "$ROW8" "$P2" > "$T/c31-v2-passes-e0.md"
# c32 — v2 passes table with a malformed `ended` (Amendment 13, user-signed
# 2026-08-10): named by row, time axis suppressed, EXIT CODE UNCHANGED.
printf '%s\n%s\n\n## Verification passes\n%s\n' "$H8" "$ROW8" "$P2BAD" > "$T/c32-v2-bad-ended-e0.md"
# c33 — the same v2 ledger read by the PREVIOUS RELEASE's recount (the
# byte-compatibility claim, tested rather than asserted). Not in the loop
# below: it needs a second interpreter of the file.
printf '%s\n%s\n\n## Verification passes\n%s\n' "$H8" "$ROW8" "$P2" > "$T/c33-v2-for-old-recount.md"
# c34 — the SHIPPED ledger TEMPLATE, instantiated (B9). Every fixture above
# is a hand-written table; this one lifts the two table headers out of
# `templates/ledger.md` itself and fills them, so an edit to the shipped
# template that breaks the recount's contract fails HERE instead of in a
# live round. It is not redundant with c31: the template's passes table is
# EIGHT columns wide — `(scope)`, `bundled`, `second-pass-skipped` and, from
# 0.3.0, `verifiers` as the last column — and carries no timestamp columns,
# so it exercises the lookup BY NAME (`new findings` at index 3) on a wider
# header than c31's seven-column fixture, and the recount must print NO
# time axis for it.
TPL="$(dirname "$0")/../skills/critic-ledger/templates/ledger.md"
FH=$(awk '/^\| id \| sev \|/{print;getline;print;exit}' "$TPL")
PH=$(awk '/^\| # \| pass \(scope\)/{print;getline;print;exit}' "$TPL")
# The shipped `Row schema:` field is lifted too: the template must DECLARE
# the width its own findings header has, or every row written from it is a
# structural error of the recount.
RS=$(awk '/^- Row schema:/{print;exit}' "$TPL")
{ printf '%s\n' "$RS"
  printf '%s\n' "$FH"
  printf '%s\n' '| DA-1 | major | Z1 | c | v | crit | f | LANDED | verified-landed |'
  printf '%s\n' '| DA-2 | minor | Z3 | c | v | — | f | x | refuted-with-reason |'
  printf '\n## Verification passes\n'
  printf '%s\n' "$PH"
  printf '%s\n' '| 1 | a | L | 5 | no | no | - | 5 |'
  printf '%s\n' '| 2 | b | L | 3 | no | no | - | 1 |'
  printf '%s\n' '| 3 | c | L | 1 | yes | no | - | 1 |'
} > "$T/c34-template-instantiated-e0.md"
# --- 0.3.0 residue: the named waits and the register (c35-c41) -------------
# A nomination is neither open nor terminal: it WAITS, named, and the round
# is reported as awaiting ratification instead of closed. Blockers are
# categorically non-nominable. The register cases assert the report lines,
# which is where "expiry re-opens, never renews in silence" is observable.
w8 c35-blocker-nominee-e2.md  '| DA-1 | blocker | c | v | crit | f | x | awaiting-signature (nominated 2026-08-29) |'
w8 c36-nomination-e1.md       '| DA-1 | major | c | v | crit | f | LANDED | verified-landed |
| DA-2 | minor | c | v | crit | f | x | awaiting-signature (nominated 2026-08-29) |'
w8 c37-ratified-e0.md         '| DA-1 | major | c | v | crit | f | LANDED | verified-landed |
| DA-2 | minor | c | v | crit | f | x | accepted-residue user-signed 2026-08-29 |'
w8 c38-logged-no-action-e1.md '| DA-1 | major | c | v | crit | f | LANDED | verified-landed |
| DA-2 | minor | c | v | crit | f | x | awaiting-logged-no-action |'
# c39-c41 — the durable register. Not in the loop below: they take an option.
w8 c39-register-ledger.md     '| DA-1 | major | c | v | crit | f | LANDED | verified-landed |'
RH='| run-qualified id | severity | claim-hook | rationale | compensating-control | review-by | status | origin-run |
|---|---|---|---|---|---|---|---|'
printf '%s\n%s\n%s\n%s\n' "$RH" \
 '| run1/DA-2 | minor | hook | argued when it was made | a leak gate stays red | 2020-06-01 | ratified 2020-01-01 | run1 |' \
 '| run1/DA-3 | minor | hook | argued when it was made | none — direct risk accepted | 2099-01-01 | nominated 2020-01-01 | run1 |' \
 '| run1/DA-4 | major | hook | argued when it was made | a leak gate stays red | 2099-01-01 | expired-reopened 2026-01-01 (#2) | run1 |' > "$T/reg-overdue.md"
printf '%s\n%s\n' "$RH" '| run1/DA-5 | minor | hook |  | a gate | 2099-01-01 | nominated 2099-01-01 | run1 |' > "$T/reg-broken.md"
printf '%s\n%s\n%s\n' "$RH" \
 '| run1/DA-2 | minor | hook | argued when it was made | a leak gate stays red | 2099-01-01 | withdrawn 2020-01-01 | run1 |' \
 '| run1/DA-3 | minor | hook | argued when it was made | a leak gate stays red | 2099-01-01 | nominated 2099-01-01 | run1 |' > "$T/reg-withdrawn.md"
# --- 0.3.0 stopping metrics: the estimate and the plateau (c42-c47) --------
# k comes from the header's machine-form `Lenses:` lines and from nowhere
# else, so these fixtures carry a header. c42 is the applicability floor
# (k=3 -> no number at all); c43 pins the arithmetic against a hand-computed
# value; c44-c46 pin the plateau, its derived chronology and the unchanged
# single-`--prev` delta; c47 is the ledger that declares no lenses.
{ printf -- '- Lenses:\n  - AA | consistency | sonnet\n  - BB | correctness | sonnet\n  - CC | coverage | sonnet\n'
  printf '%s\n' "$H8"
  printf '%s\n' '| AA-1 | major | c | v | crit | f | LANDED | verified-landed |'
} > "$T/c42-k3-e0.md"
# k=5, five lens-raised findings, DD-1 a cross-lens duplicate of CC-1 and
# V1-1 raised by the verifier, not a lens. So D=4, f1=3 (AA-1, BB-1, EE-1)
# and N-hat = 4 + (4/5)*3 = 6.4, computed by hand here on purpose.
{ printf -- '- Lenses:\n  - AA | a | sonnet\n  - BB | b | sonnet\n  - CC | c | sonnet\n  - DD | d | sonnet\n  - EE | e | sonnet\n'
  printf '  timebox 15 min each; prose below the run is not counted.\n'
  printf -- '- Verifier passes: V\n'
  printf '%s\n' "$H8"
  printf '%s\n' '| AA-1 | major | c | v | crit | f | LANDED | verified-landed |'
  printf '%s\n' '| BB-1 | major | c | v | crit | f | LANDED | verified-landed |'
  printf '%s\n' '| CC-1 | major | c | v | crit | f | LANDED | verified-landed |'
  printf '%s\n' '| DD-1 | minor | c | v | =CC-1 | f | LANDED | verified-landed |'
  printf '%s\n' '| EE-1 | minor | c | v | crit | f | LANDED | verified-landed |'
  printf '%s\n' '| V1-1 | minor | c | v | crit | f | LANDED | verified-landed |'
} > "$T/c43-k5-e0.md"
# The plateau window: three ledgers, 7 -> 4 -> 2 major+blocker rows, so the
# deltas are -3 and -2 and the moving average is -2.5. Not in the loop —
# they take options.
plat(){ # plat <file> <round-started> <major-count>
  { printf -- '- Round-started: %s\n' "$2"
    printf '%s\n' "$H8"
    i=1; while [ "$i" -le "$3" ]; do
      printf '| PA-%s | major | c | v | crit | f | LANDED | verified-landed |\n' "$i"
      i=$((i + 1))
    done
  } > "$T/$1"
}
plat c44-cur.md   2026-08-29 2
plat c44-prev1.md 2026-08-20 4
plat c44-prev2.md 2026-08-10 7
# --- 0.3.0 round contract: the two statuses it brings (c48-c57) ------------
# `out-of-scope-by-contract` closes a finding on a signature given BEFORE the
# round, so it is recognized only under its COMPLETE literal, and never on a
# `class:security-pii` row without that row's own live signature.
# `frozen-carried` closes a row the stop rule froze: terminal, closability
# NOT blocked (the difference from `superseded-by-rewrite`), leaning on ONE
# header field that is written ONCE — the collision rule for its two
# independent writers. The last three are the security-lens backstop: the
# default class of a declared security lens is removed in writing or not at
# all.
w8 c48-out-of-scope-e0.md     '| DA-1 | major | c | v | crit | f | x | out-of-scope-by-contract (NG-2, signed 2026-08-29) |'
w8 c49-out-of-scope-bare-e1.md '| DA-1 | major | c | v | crit | f | x | out-of-scope-by-contract |'
w8 c50-out-of-scope-pii-e2.md '| SE-1 | major | c | upheld class:security-pii | crit | f | x | out-of-scope-by-contract (NG-2, signed 2026-08-29) |'
FREEZE='- Stop-rule freeze: 2026-08-29 | carried-to: 2026-09-01-120000-object'
printf -- '%s\n%s\n%s\n%s\n' "$FREEZE" "$H8" \
 '| DA-1 | blocker | c | v | crit | f | x | frozen-carried (stop-rule, 2026-08-29) |' \
 '| DA-2 | major | c | v | crit | f | x | frozen-carried (stop-rule, 2026-08-30) |' > "$T/c51-frozen-carried-e0.md"
w8 c52-frozen-no-field-e2.md  '| DA-1 | major | c | v | crit | f | x | frozen-carried (stop-rule, 2026-08-29) |'
printf -- '%s\n- Stop-rule freeze: 2026-08-30 | carried-to: r-other\n%s\n%s\n' "$FREEZE" "$H8" \
 '| DA-1 | major | c | v | crit | f | x | frozen-carried (stop-rule, 2026-08-29) |' > "$T/c53-freeze-twice-e2.md"
printf -- '- Stop-rule freeze: 2026-08-29 | carried-to: pending\n%s\n%s\n' "$H8" \
 '| DA-1 | major | c | v | crit | f | x | frozen-carried (stop-rule, 2026-08-29) |' > "$T/c54-carried-pending-e2.md"
printf -- '- Security lens: SE\n%s\n%s\n' "$H8" \
 '| SE-1 | major | c | upheld | crit | f | LANDED | verified-landed |' > "$T/c55-security-unmarked-e2.md"
printf -- '- Security lens: SE\n%s\n%s\n' "$H8" \
 '| SE-1 | major | c | upheld; declassed:security-pii — the path is a fixture, no real data | crit | f | LANDED | verified-landed |' > "$T/c56-security-declassed-e0.md"
printf -- '- Security lens: SE\n%s\n%s\n' "$H8" \
 '| SE-1 | major | c | upheld; declassed:security-pii — | crit | f | LANDED | verified-landed |' > "$T/c57-declass-no-reason-e2.md"
# --- 0.3.0 per-lens sustained rate and the `shelf:` tag (c59-c62) ----------
# The rate is a BETWEEN-ROUNDS report: it belongs to `--prev` and appears
# nowhere else (c62 is that compatibility claim). Its lens prefixes come from
# the header's machine-form `Lenses:` lines, the same single source `k` uses.
# The shelf share stands BESIDE the rate — never on a line of its own — and a
# window carrying no `shelf:` tag prints `n/a` with the reason, never `0`.
# c61 pins the tag's boundary: fail-closed like `class:`.
{ printf -- '- Round-started: 2026-08-29\n- Lenses:\n  - AA | a | sonnet\n  - BB | b | sonnet\n'
  printf '%s\n' "$H8"
  printf '%s\n' '| AA-1 | major | c | upheld | crit | f | LANDED | verified-landed |'
  printf '%s\n' '| AA-2 | minor | c | refuted; shelf:ng-2 | — | f | x | refuted-with-reason |'
  printf '%s\n' '| AA-3 | minor | c | refuted; shelf:ng-2 | — | f | x | refuted-with-reason |'
  printf '%s\n' '| BB-1 | minor | c | refuted | — | f | x | refuted-with-reason |'
} > "$T/c59-shelf-cur.md"
{ printf -- '- Round-started: 2026-08-20\n- Lenses:\n  - AA | a | sonnet\n  - BB | b | sonnet\n'
  printf '%s\n' "$H8"
  printf '%s\n' '| AA-9 | major | c | upheld | crit | f | LANDED | verified-landed |'
} > "$T/c59-shelf-prev.md"
sed 's/; shelf:ng-2//' "$T/c59-shelf-cur.md" > "$T/c60-noshelf-cur.md"
printf -- '- Lenses:\n  - AA | a | sonnet\n%s\n%s\n' "$H8" \
 '| AA-1 | minor | c | refuted; shelf:NG2 | — | f | x | refuted-with-reason |' > "$T/c61-shelf-slug-e2.md"
# --- 0.3.0 zones and the v3 nine-cell row (c63-c72) ------------------------
# The zone column is inserted THIRD, so `criterion`, `fix`, `verified` and
# `terminal` keep their addresses from the END of the row. c66/c67 are the
# pair that proves it: on a 9-cell row a hard `cells[4]` would read the
# VERDICT prose as the criterion, so c67's empty criterion would pass
# silently instead of failing closed. c68/c69 are the owner-act wait and its
# 30-day limit; c71/c72 the header's schema declaration.
H9='| id | sev | zone | claim | verdict | criterion | fix | verified | terminal |
|---|---|---|---|---|---|---|---|---|'
w9(){ printf '%s\n%s\n' "$H9" "$2" > "$T/$1"; }
w9 c63-v3-nine-cell-e0.md     '| DA-1 | major | Z2 | c | upheld | crit | f | LANDED | verified-landed |
| DA-2 | minor | Z3 | c | logged, no action taken | crit | f | x | logged-no-action |'
w9 c64-lna-wrong-zone-e2.md   '| DA-1 | minor | Z1 | c | v | crit | f | x | logged-no-action |'
w8 c65-lna-v2-row-e2.md       '| DA-1 | minor | c | v | crit | f | x | logged-no-action |'
w9 c66-v3-criterion-set-e0.md '| DA-1 | major | Z2 | c | upheld — the wording is ambiguous | grep -c TODO = 0 | f | LANDED | verified-landed |'
w9 c67-v3-criterion-empty-e2.md '| DA-1 | major | Z2 | c | upheld — the wording is ambiguous |  | f | LANDED | verified-landed |'
# c68/c69 — the owner-act wait. Not in the loop below: they assert LINES.
# c68 uses TODAY so it can never age into the overdue block; c69 pins a date
# far past the limit, so the block is asserted rather than hoped for.
TODAY=$(date -u '+%Y-%m-%d')
printf '%s\n%s\n' "$H9" \
 "| DA-1 | major | Z2 | c | upheld | crit | f | LANDED | verified-landed |
| DA-2 | minor | Z3 | c | logged | crit | f | x | awaiting-logged-no-action (listed $TODAY) |" > "$T/c68-z3-wait.md"
printf '%s\n%s\n' "$H9" \
 '| DA-1 | major | Z2 | c | upheld | crit | f | LANDED | verified-landed |
| DA-2 | minor | Z3 | c | logged | crit | f | x | awaiting-logged-no-action (listed 2020-01-01) |' > "$T/c69-z3-overdue.md"
w9 c70-lna-pii-e2.md          '| SE-1 | minor | Z3 | c | upheld class:security-pii | crit | f | x | logged-no-action |'
printf -- '- Row schema: v2\n%s\n%s\n' "$H9" \
 '| DA-1 | major | Z2 | c | upheld | crit | f | LANDED | verified-landed |' > "$T/c71-schema-mismatch-e2.md"
printf -- '- Row schema: v3\n%s\n%s\n' "$H9" \
 '| DA-1 | major | Z2 | c | upheld | crit | f | LANDED | verified-landed |' > "$T/c72-schema-agrees-e0.md"
# --- 0.3.0 closed ledger state (c73) ---------------------------------------
# Stage 9 now writes `Ledger state: closed <ISO-date>` into the header of a
# ledger the recount declared closable. `recount.py` is NOT changed for it:
# the FROZEN branch matches the substring `frozen`, which `closed` does not
# contain, so a closed ledger recounts as an open one does. c73 is the exact
# counterpart of c11 (the FROZEN header, exit 3) and pins that difference.
printf -- '- Ledger state: closed 2026-01-15\n%s\n%s\n' "$H" '| DA-1 | major | c | v | f | LANDED | verified-landed |' > "$T/c73-closed-state-e0.md"
# --- 0.3.0 the lens-split verification pass (c74) ---------------------------
# The lens-split rule names the mode in which ONE pass is executed by N fresh verifiers with
# non-overlapping id scopes, and gives the passes table a column carrying
# that count. `recount.py` is NOT changed for it: `new findings` is located
# BY NAME, and a column the header does not name is ignored by construction
# (`cell_by_name()` returns None for it), so the extra cell can neither shift
# a reading nor raise a structural error. c74 is the fixture that proves it
# instead of asserting it — the curve and the time axis are the ones c31
# gets from the same numbers.
PLENS='| # | pass (scope) | verdicts | new findings | bundled | second-pass-skipped | notes | verifiers | started | ended |
|---|---|---|---|---|---|---|---|---|---|
| 1 | a | L | 5 | no | no | lens-split | 5 | 2026-08-10T10:00:00Z | 2026-08-10T10:30:00Z |
| 2 | b | L | 3 | no | no | - | 1 | 2026-08-10T11:00:00Z | 2026-08-10T11:15:00Z |
| 3 | c | L | 1 | yes | no | - | 1 | 2026-08-10T12:00:00Z | 2026-08-10T12:10:00Z |'
printf '%s\n%s\n\n## Verification passes\n%s\n' "$H8" "$ROW8" "$PLENS" > "$T/c74-lens-split-passes-e0.md"
# --- 0.3.0 the fresh skeleton: an empty verdict cell (c75) ------------------
# A stage-5 layout has its findings transcribed and its `verdict` cells still
# blank. The security-lens backstop used to refuse exactly that as a
# structural error (exit 2), which made the recount unusable where it helps
# most — before adjudication. An empty cell is now the STATE "not
# adjudicated": no error, the rows are non-terminal like any unfinished row,
# and the round is reported as not closable (exit 1). c55 is the counterpart
# that did not move: a FILLED verdict leaving the class out is still exit 2.
printf -- '- Security lens: SE\n%s\n%s\n%s\n' "$H8" \
 '| SE-1 | major | c |  |  | f | x |  |' \
 '| SE-2 | minor | c |  |  | f | x |  |' > "$T/c75-fresh-skeleton-e1.md"
fail=0
# Cases that could not run at all — no reference, no fixture. Counted here so
# that the closing line can name them; the count never touches the exit code.
skipped=0
for f in "$T"/c*-e*.md; do
  b=$(basename "$f"); want=$(printf '%s' "$b" | sed 's/.*-e\([0-9]\)\.md/\1/')
  if [ "$b" = "c14-cur-e1.md" ]; then out=$(python3 "$R" "$f" --prev "$T/c14-prev-old.md" 2>&1); else out=$(python3 "$R" "$f" 2>&1); fi
  got=$?
  ok=ok; [ "$got" = "$want" ] || { ok=FAIL; fail=1; }
  printf '%-28s want=%s got=%s %s\n' "$b" "$want" "$got" "$ok"
  case "$b" in c14-cur-e1.md) printf '  %s\n' "$out" | grep DELTA;; esac
done
# --- content assertions ----------------------------------------------------
# The loop above checks exit codes only. The 0.2.0 cases are claims about
# OUTPUT ("reported, never fatal"), so each names the lines it requires and
# the lines it forbids. Nothing here may move an exit code.
case_run(){ # case_run <name> <want-exit> <argv...>
  cn=$1; want=$2; shift 2
  out=$(python3 "$R" "$@" 2>"$T/stderr.txt"); got=$?
  ok=ok; [ "$got" = "$want" ] || { ok=FAIL; fail=1; }
  printf '%-28s want=%s got=%s %s\n' "$cn" "$want" "$got" "$ok"
}
has(){ # has <substring>   — required in the last case's stdout
  if printf '%s\n' "$out" | grep -qF -- "$1"; then printf '    has: %s\n' "$1"
  else printf '    MISSING: %s\n' "$1"; fail=1; fi
}
hasnt(){ # hasnt <substring> — forbidden in the last case's stdout
  if printf '%s\n' "$out" | grep -qF -- "$1"; then printf '    UNEXPECTED: %s\n' "$1"; fail=1
  else printf '    absent: %s\n' "$1"; fi
}
skip(){ # skip <case> <reason> — a case that could not run at all. Never a
        # pass and never a failure, but COUNTED: the closing line names the
        # count, so a degraded run cannot read as a full one.
  skipped=$((skipped + 1))
  printf '%-28s SKIPPED — %s\n' "$1" "$2"
}
case_run c29-content 0 "$T/c29-v1-seven-cell-e0.md"
has 'severity distribution (terminal/rows): blocker 0/0 | major 1/1 | minor 0/0'
has 'upheld/refuted: n/a (v1 ledger'
hasnt 'new-findings curve'
hasnt 'time axis'
case_run c30-content 0 "$T/c30-v1-five-col-passes-e0.md"
has 'new-findings curve: 5 -> 3 -> 1'
has 'time axis: n/a (no started/ended columns'
hasnt 'time-indexed curve'
case_run c31-content 0 "$T/c31-v2-passes-e0.md"
has 'new-findings curve: 5 -> 3 -> 1'
has 'time-indexed curve (from 2026-08-10T10:00:00Z): +0s -> 5 | +3600s -> 3 | +7200s -> 1'
has 'pass wall-clock: 1: 1800s | 2: 900s | 3: 600s'
case_run c32-content 0 "$T/c32-v2-bad-ended-e0.md"
has "passes: row 2 'ended' unparseable — time axis suppressed"
has 'new-findings curve: 5 -> 3 -> 1'
hasnt 'time-indexed curve'
hasnt 'pass wall-clock'
# c33 — the previous release's recount reading a v2 ledger. The reference is
# the last tag (overridable with PREV_RECOUNT_REF); where no tag is reachable
# — a shallow clone, an export outside git — the case is SKIPPED out loud and
# never counted as a pass.
ref=${PREV_RECOUNT_REF:-$(git describe --tags --abbrev=0 2>/dev/null || true)}
if [ -n "$ref" ] && git show "$ref:./skills/critic-ledger/templates/recount.py" > "$T/old-recount.py" 2>/dev/null; then
  out=$(python3 "$T/old-recount.py" "$T/c33-v2-for-old-recount.md" 2>&1); got=$?
  ok=ok; [ "$got" = 0 ] || { ok=FAIL; fail=1; }
  printf '%-28s want=0 got=%s %s (ref %s)\n' "c33-old-recount" "$got" "$ok" "$ref"
  has 'new-findings curve: 5 -> 3 -> 1'
else
  skip "c33-old-recount" "no previous recount reachable (ref=${ref:-none})"
fi
# c34 — the instantiated shipped template. An empty header here means the
# template no longer carries the table this fixture is built from, which is
# itself the regression; say so rather than failing on a malformed fixture.
if [ -z "$FH" ] || [ -z "$PH" ]; then
  printf '%-28s MISSING: ledger.md table header(s) not found in the template\n' "c34-template"
  fail=1
fi
case_run c34-template-content 0 "$T/c34-template-instantiated-e0.md"
has 'rows: 2 | terminal: 2 | non-terminal: 0'
has 'severity distribution (terminal/rows): blocker 0/0 | major 1/1 | minor 1/1'
has 'new-findings curve: 5 -> 3 -> 1'
hasnt 'time-indexed curve'
hasnt 'pass wall-clock'
case_run c35-content 2 "$T/c35-blocker-nominee-e2.md"
has 'categorically non-nominable'
case_run c36-content 1 "$T/c36-nomination-e1.md"
has 'awaiting-signature ids: DA-2'
has "ROUND AWAITING RATIFICATION: 1 rows await the owner's signature."
has 'residue register: n/a (path not derived'
hasnt 'ROUND NOT CLOSABLE'
case_run c37-content 0 "$T/c37-ratified-e0.md"
has 'ROUND CLOSABLE: zero non-terminal rows.'
hasnt 'AWAITING'
hasnt 'residue register'
case_run c38-content 1 "$T/c38-logged-no-action-e1.md"
has "ROUND AWAITING Z3 CLOSURE: 1 rows await the owner's act."
hasnt 'ROUND AWAITING RATIFICATION'
case_run c39-register 0 "$T/c39-register-ledger.md" --register "$T/reg-overdue.md"
has 'rows: 3 | nominated 1 | ratified 1 | expired-reopened 1'
has 'REVIEW-BY EXPIRED: run1/DA-2'
has 'NOMINATION OVERDUE: run1/DA-3'
has 'SECOND CYCLE — OWNER FORK REQUIRED: run1/DA-4'
has 'visibility, not traction'
case_run c40-register-broken 2 "$T/c39-register-ledger.md" --register "$T/reg-broken.md"
has 'RESIDUE REGISTER STRUCTURAL ERRORS:'
has 'run1/DA-5 has a blank'
has 'a mandatory field'
# c41 — the compatibility claim: a ledger with neither a register nor a
# nomination prints not one line about residue.
case_run c41-no-register 0 "$T/c15-eight-cell-e0.md"
hasnt 'residue register'
hasnt 'AWAITING'
# c42-c47 — the two stopping metrics. Both are report-only: not one of these
# cases may move an exit code, and c42/c43 assert that the applicability
# condition is honoured rather than worked around.
case_run c42-content 0 "$T/c42-k3-e0.md"
has 'residual-defect ESTIMATE: n/a: k<4 (k=3;'
hasnt 'N-hat'
case_run c43-content 0 "$T/c43-k5-e0.md"
has 'N-hat 6.4 | D 4 raised | f1 3 single-lens | k 5 (AA, BB, CC, DD, EE)'
has 'ESTIMATE is ADVISORY'
has 'comparability is not established'
case_run c44-plateau 0 "$T/c44-cur.md" --prev "$T/c44-prev1.md" --prev "$T/c44-prev2.md"
has 'severity plateau (3-round moving average of major+blocker deltas): -2.5'
has 'major+blocker per round (oldest first): 7 -> 4 -> 2 | deltas -3, -2'
hasnt 'prev order: reordered'
case_run c45-plateau-reordered 0 "$T/c44-cur.md" --prev "$T/c44-prev2.md" --prev "$T/c44-prev1.md"
has 'prev order: reordered by Round-started'
has 'major+blocker per round (oldest first): 7 -> 4 -> 2 | deltas -3, -2'
has "DELTA vs $T/c44-prev1.md"
case_run c46-single-prev 0 "$T/c44-cur.md" --prev "$T/c44-prev1.md"
has "DELTA vs $T/c44-prev1.md"
has 'severity plateau: n/a: 1 previous ledger given'
hasnt 'moving average'
case_run c47-no-lenses 0 "$T/c15-eight-cell-e0.md"
has 'residual-defect ESTIMATE: n/a: k not derived from the header'
# c48-c57 — the round contract's two statuses and the security-lens backstop.
# The exit codes are checked by the loop above; these name the LINES, because
# "recognized only in full", "closability not blocked" and "written once" are
# claims about output as much as about codes.
case_run c48-content 0 "$T/c48-out-of-scope-e0.md"
has 'ROUND CLOSABLE: zero non-terminal rows.'
hasnt 'FROZEN CARRIED'
case_run c49-content 1 "$T/c49-out-of-scope-bare-e1.md"
has 'expected the complete literal'
has 'out-of-scope-by-contract (NG-<n>, signed <YYYY-MM-DD>)'
has 'ROUND NOT CLOSABLE'
case_run c50-content 2 "$T/c50-out-of-scope-pii-e2.md"
has 'with no live'
has 'does not reach a class both of whose outcomes'
case_run c51-content 0 "$T/c51-frozen-carried-e0.md"
has 'rows: 2 | terminal: 2 | non-terminal: 0'
has 'FROZEN CARRIED: 2 rows → 2026-09-01-120000-object'
has 'ROUND CLOSABLE: zero non-terminal rows.'
case_run c52-content 2 "$T/c52-frozen-no-field-e2.md"
has 'a freeze that names no carry is a transfer into nowhere'
case_run c53-content 2 "$T/c53-freeze-twice-e2.md"
has 'the header carries 2'
has 'the field is ONE per ledger and is written ONCE'
hasnt 'FROZEN CARRIED'
case_run c54-content 2 "$T/c54-carried-pending-e2.md"
has 'still reads'
has 'while the round closes over 1 carried row(s)'
case_run c55-content 2 "$T/c55-security-unmarked-e2.md"
has 'raised by the declared security lens SE'
case_run c56-content 0 "$T/c56-security-declassed-e0.md"
has 'ROUND CLOSABLE: zero non-terminal rows.'
case_run c57-content 2 "$T/c57-declass-no-reason-e2.md"
has 'with an empty reason'
# c58 — the compatibility claim of this batch: a ledger declaring neither
# header field and using neither status prints not one line about either.
case_run c58-no-contract 0 "$T/c15-eight-cell-e0.md"
hasnt 'FROZEN CARRIED'
hasnt 'security lens'
hasnt 'Stop-rule freeze'
case_run c59-shelf-share 0 "$T/c59-shelf-cur.md" --prev "$T/c59-shelf-prev.md"
has 'AA: sustained 2/4 = 50.0% | shelf 2/2 = 100.0%'
has 'BB: sustained 0/1 = 0.0% | shelf 0/1 = 0.0%'
has 'the rate alone is never the trigger'
case_run c60-no-shelf-tag 0 "$T/c60-noshelf-cur.md" --prev "$T/c59-shelf-prev.md"
has 'tag anywhere in the window'
has 'which is not a share of zero'
hasnt 'shelf 0/'
case_run c61-shelf-slug 2 "$T/c61-shelf-slug-e2.md"
has 'AA-1 carries a'
has 'tag whose slug is not 1-32 characters'
# c62 — the compatibility claim of this batch: with no `--prev` the rate is
# not printed at all, so a single-ledger recount is what it always was.
case_run c62-no-prev 0 "$T/c15-eight-cell-e0.md"
hasnt 'per-lens sustained rate'
hasnt 'shelf'
# c63/c68/c69 — the v3 row and the owner-act wait, asserted as LINES: the
# upheld split needs the criterion cell read from the END of a 9-cell row,
# and the third bucket must print its own state line and its own overdue
# block without moving an exit code.
case_run c63-v3-content 0 "$T/c63-v3-nine-cell-e0.md"
has 'rows: 2 | terminal: 2 | non-terminal: 0'
has 'upheld/refuted: 2 upheld, 0 refuted'
has 'ROUND CLOSABLE'
case_run c68-z3-wait 1 "$T/c68-z3-wait.md"
has 'awaiting-logged-no-action ids: DA-2'
has "ROUND AWAITING Z3 CLOSURE: 1 rows await the owner's act."
hasnt 'ROUND NOT CLOSABLE'
hasnt 'ROUND CLOSABLE'
hasnt 'Z3 CLOSURE OVERDUE'
case_run c69-z3-overdue 1 "$T/c69-z3-overdue.md"
has 'Z3 CLOSURE OVERDUE: DA-2 (listed 2020-01-01'
has 'the 30-day limit is the residue queue'
has "ROUND AWAITING Z3 CLOSURE: 1 rows await the owner's act."
# c73 — a closed header is not a frozen one: the closable report is printed
# and the frozen branch stays silent.
case_run c73-closed-state 0 "$T/c73-closed-state-e0.md"
has 'ROUND CLOSABLE: zero non-terminal rows.'
hasnt 'LEDGER IS FROZEN'
# c74 — the lens-split pass's `verifiers` column: an unnamed column is
# ignored by construction, so the curve and the time axis are unmoved by it.
case_run c74-lens-split 0 "$T/c74-lens-split-passes-e0.md"
has 'new-findings curve: 5 -> 3 -> 1'
has 'pass wall-clock: 1: 1800s | 2: 900s | 3: 600s'
hasnt 'time axis: n/a'
# c75 — the fresh skeleton. The exit code is checked by the loop above; the
# LINES are the claim: the state is named and the structural error is gone.
case_run c75-fresh-skeleton 1 "$T/c75-fresh-skeleton-e1.md"
has 'not adjudicated: 2 rows'
has 'ROUND NOT CLOSABLE: 2 open rows.'
hasnt 'STRUCTURAL ERRORS'
hasnt 'raised by the declared security lens'
# c76 — the README's recount block against a live run of the shipped example.
# The block is published as captured output, and its own caption names the
# command that reproduces it, so the case RUNS that command and diffs the two
# byte for byte. A change to the example that nobody re-ran the command after
# turns the README into an illustration again, and this is what notices.
EXDIR="$(dirname "$0")/../examples/worked-round"
RDME="$(dirname "$0")/../README.md"
(cd "$EXDIR" && python3 ../../skills/critic-ledger/scripts/recount.py \
  fix-ledger.md) > "$T/c76-live.txt" 2> "$T/c76-err.txt"
got=$?
# The published block, carved out by its CAPTION and not by its content: the
# first fenced section after the sentence that names the reproducing command.
# Locking on to "the first fence whose first line is `rows: `" instead would
# follow any future block that happened to start that way, and would report a
# spurious DESYNC rather than the defect this case exists to catch.
# The backticks below are LITERAL caption text, not a command substitution.
# shellcheck disable=SC2016
CAP='Live `recount.py` output'
caps=$(grep -c -F "$CAP" "$RDME")
awk -v cap="$CAP" \
    'index($0, cap) { seen=1; next }
     seen && /^```/ { if (inb) exit; inb=1; next }
     inb { print }' \
  "$RDME" > "$T/c76-readme.txt"
ok=ok; [ "$got" = 0 ] || { ok=FAIL; fail=1; }
# The anchor must be UNIQUE: zero matches or several mean the carve-out could
# have taken the wrong block, so the case fails loudly instead of comparing.
[ "$caps" = 1 ] || { ok=FAIL; fail=1; }
# Fail-closed: an empty carve-out is a broken case, never a passing one.
[ -s "$T/c76-readme.txt" ] || { ok=FAIL; fail=1; }
# The comparison runs BEFORE the case line is printed and folds into $ok: a
# DESYNC must show as a FAIL on the case line itself, not as an "ok" line
# contradicted only by the suite's trailing failure summary.
if diff -u "$T/c76-readme.txt" "$T/c76-live.txt" > "$T/c76-diff.txt"; then
  desync=0
else
  desync=1; ok=FAIL; fail=1
fi
printf '%-28s want=0 got=%s %s\n' "c76-readme-recount" "$got" "$ok"
[ "$caps" = 1 ] || printf '    ERROR: README caption anchor matched %s times, expected exactly 1: %s\n' "$caps" "$CAP"
if [ "$desync" = 0 ]; then
  printf '    has: README block identical to the live run\n'
else
  printf '    DESYNC: README block != live recount output\n'
  cat "$T/c76-diff.txt"; cat "$T/c76-err.txt"
fi
# c77 — a withdrawn nomination is a register status of its own: it parses,
# it is counted in the aggregate, and it is never printed as overdue.
case_run c77-register-withdrawn 0 "$T/c39-register-ledger.md" --register "$T/reg-withdrawn.md"
has 'rows: 2 | nominated 1 | ratified 0 | expired-reopened 0 | withdrawn 1'
hasnt 'NOMINATION OVERDUE'
hasnt 'STRUCTURAL ERRORS'
# The closing line names any case that could not run. A consumer that reads
# only this line would otherwise take a degraded run for a full one. The
# prefix is unchanged — CONTRIBUTING promises `ALL FIXTURES PASS` on green —
# and so is the exit code: a skip was never a failure and still is not.
if [ $fail -eq 0 ]; then
  if [ "$skipped" -gt 0 ]; then echo "ALL FIXTURES PASS ($skipped skipped)"
  else echo "ALL FIXTURES PASS"; fi
else
  echo "FIXTURE FAILURES PRESENT"
fi
exit $fail
