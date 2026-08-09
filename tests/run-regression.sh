#!/bin/sh
# Regression suite for recount.py's ledger contract (28 cases, c01-c28).
# Builds every edge case in a temp dir and runs recount.py against each.
# Expected exit codes are in the case names: e0 / e1 / e2 / e3.
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
fail=0
for f in "$T"/c*-e*.md; do
  b=$(basename "$f"); want=$(printf '%s' "$b" | sed 's/.*-e\([0-9]\)\.md/\1/')
  if [ "$b" = "c14-cur-e1.md" ]; then out=$(python3 "$R" "$f" --prev "$T/c14-prev-old.md" 2>&1); else out=$(python3 "$R" "$f" 2>&1); fi
  got=$?
  ok=ok; [ "$got" = "$want" ] || { ok=FAIL; fail=1; }
  printf '%-28s want=%s got=%s %s\n' "$b" "$want" "$got" "$ok"
  case "$b" in c14-cur-e1.md) printf '  %s\n' "$out" | grep DELTA;; esac
done
[ $fail -eq 0 ] && echo "ALL FIXTURES PASS" || echo "FIXTURE FAILURES PRESENT"
exit $fail
