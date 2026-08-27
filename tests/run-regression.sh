#!/bin/sh
# Regression suite for recount.py's ledger contract (38 cases, c01-c37).
# Builds every edge case in a temp dir and runs recount.py against each.
# Expected exit codes are in the case names: e0 / e1 / e2 / e3; the cases
# added for 0.2.0 observability also assert the LINES those cases fix,
# because "reported, never fatal" is a claim about output.
# Lives in tests/ (moved from the round's fixtures dir at publication).
set -u
R="$(dirname "$0")/../skills/critic-ledger/templates/recount.py"
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
# c34-c36 — the `--trace` line. Not in the loop below: they take an option.
printf '%s\n%s\n\n## Verification passes\n%s\n' "$H8" "$ROW8" "$P2" > "$T/c34-v2-trace.md"
printf '%s\n%s\n' '{"v":1,"kind":"span","round":"r","span":"s1.00"}' '{"v":1,"kind":"open","round":"r","span":"s2.01"}' > "$T/trace-ok.jsonl"
printf '%s\n%s\n%s\n%s\n%s\n' '{"v":1,"kind":"span","round":"r","span":"s1.00"}' 'not json at all' '{"v":1,' '[]' '{"v":1,"kind":"open","round":"r","span":"s2.01"}' > "$T/trace-corrupt.jsonl"
mkdir "$T/trace-dir.jsonl"
# c37 — the SHIPPED ledger TEMPLATE, instantiated (B9). Every fixture above
# is a hand-written table; this one lifts the two table headers out of
# `templates/ledger.md` itself and fills them, so an edit to the shipped
# template that breaks the recount's contract fails HERE instead of in a
# live round. It is not redundant with c31: the template's passes table is
# NINE columns wide and carries `started`/`ended` at indices 7 and 8, so it
# exercises the lookup BY NAME rather than the last-two-by-position shape
# c31's seven-column fixture happens to have.
TPL="$(dirname "$0")/../skills/critic-ledger/templates/ledger.md"
FH=$(awk '/^\| id \| sev \|/{print;getline;print;exit}' "$TPL")
PH=$(awk '/^\| # \| pass \(scope\)/{print;getline;print;exit}' "$TPL")
{ printf '%s\n' "$FH"
  printf '%s\n' '| DA-1 | major | c | v | crit | f | LANDED | verified-landed |'
  printf '%s\n' '| DA-2 | minor | c | v | — | f | x | refuted-with-reason |'
  printf '\n## Verification passes\n'
  printf '%s\n' "$PH"
  printf '%s\n' '| 1 | a | L | 5 | no | no | - | 2026-08-10T10:00:00Z | 2026-08-10T10:30:00Z |'
  printf '%s\n' '| 2 | b | L | 3 | no | no | - | 2026-08-10T11:00:00Z | 2026-08-10T11:15:00Z |'
  printf '%s\n' '| 3 | c | L | 1 | yes | no | - | 2026-08-10T12:00:00Z | 2026-08-10T12:10:00Z |'
} > "$T/c37-template-instantiated-e0.md"
fail=0
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
  printf '%-28s SKIPPED — no previous recount reachable (ref=%s)\n' "c33-old-recount" "${ref:-none}"
fi
case_run c34-trace-absent 0 "$T/c34-v2-trace.md" --trace "$T/no-such-trace.jsonl"
has 'trace: none'
case_run c35-trace-corrupt 0 "$T/c34-v2-trace.md" --trace "$T/trace-corrupt.jsonl"
has 'trace: 2 records, 3 unreadable lines skipped'
case_run c36-trace-directory 0 "$T/c34-v2-trace.md" --trace "$T/trace-dir.jsonl"
has 'trace: unreadable (trace-dir.jsonl)'
if [ -s "$T/stderr.txt" ]; then printf '    UNEXPECTED: stderr from the directory case\n'; fail=1
else printf '    absent: stderr (no traceback)\n'; fi
case_run c36b-trace-ok 0 "$T/c34-v2-trace.md" --trace "$T/trace-ok.jsonl"
has 'trace: 2 records'
# c37 — the instantiated shipped template. An empty header here means the
# template no longer carries the table this fixture is built from, which is
# itself the regression; say so rather than failing on a malformed fixture.
if [ -z "$FH" ] || [ -z "$PH" ]; then
  printf '%-28s MISSING: ledger.md table header(s) not found in the template\n' "c37-template"
  fail=1
fi
case_run c37-template-content 0 "$T/c37-template-instantiated-e0.md"
has 'rows: 2 | terminal: 2 | non-terminal: 0'
has 'severity distribution (terminal/rows): blocker 0/0 | major 1/1 | minor 1/1'
has 'new-findings curve: 5 -> 3 -> 1'
has 'time-indexed curve (from 2026-08-10T10:00:00Z): +0s -> 5 | +3600s -> 3 | +7200s -> 1'
has 'pass wall-clock: 1: 1800s | 2: 900s | 3: 600s'
[ $fail -eq 0 ] && echo "ALL FIXTURES PASS" || echo "FIXTURE FAILURES PRESENT"
exit $fail
