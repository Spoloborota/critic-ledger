# Coverage matrix — 0.2.0 observability regression cases and enforcement rows

**Generated 2026-08-11.**
This is a **point-in-time audit**, not a live artifact: every mapping below was
re-derived by opening `tests/run-regression.sh` and `tests/unit/*` at the commit
this file lands in. Line numbers age; the test *ids* are the durable half of
each row. Re-derive before relying on a line number.

Scope: the eight observability regression cases and enforcement rows
**1, 2, 3 and 3a**. Rows 4, 5 and 6 are audited at the end under
"Enforcement rows outside this file's test scope", with the reason each is not
a suite case.

Counts at the time of writing: **38 shell cases** (`c01`–`c37`) and **526**
pytest tests.

---

## 1. The eight regression cases

Every case is a shell case in `tests/run-regression.sh`; the exit-code half runs
in the glob loop at `:115`–`:122`, the output half in the `case_run` block.

| # | case | shell case id | run-regression.sh line | what the assertions pin |
|---|---|---|---|---|
| 1 | v1 7-cell ledger, no passes table | `c29-v1-seven-cell-e0` / `c29-content` | fixture `:77`, content `:141`–`:145` | exit 0; `severity distribution … major 1/1`; `upheld/refuted: n/a (v1 ledger`; **no** `new-findings curve`; **no** `time axis` |
| 2 | v1 8-cell ledger, 5-column passes table | `c30-v1-five-col-passes-e0` / `c30-content` | fixture `:79`, content `:146`–`:149` | exit 0; `new-findings curve: 5 -> 3 -> 1` unchanged; `time axis: n/a (no started/ended columns`; **no** `time-indexed curve` |
| 3 | v2 passes table with `started`/`ended` | `c31-v2-passes-e0` / `c31-content` | fixture `:81`, content `:150`–`:153` | exit 0; ordinal curve **and** `time-indexed curve (from …): +0s -> 5 \| +3600s -> 3 \| +7200s -> 1`; `pass wall-clock: 1: 1800s \| 2: 900s \| 3: 600s` |
| 4 | v2 passes table, `ended` malformed | `c32-v2-bad-ended-e0` / `c32-content` | fixture `:84`, content `:154`–`:158` | **exit 0 — unchanged**; `passes: row 2 'ended' unparseable — time axis suppressed`; ordinal curve still printed; **no** time-indexed curve, **no** wall-clock (whole-axis suppression) |
| 5 | v2 ledger read by the 0.1.0 recount | `c33-old-recount` | `:159`–`:171` | resolves `git describe --tags --abbrev=0` (override `PREV_RECOUNT_REF`), `git show <ref>:…/recount.py`, runs the OLD script on a v2 ledger: exit 0 + `new-findings curve: 5 -> 3 -> 1`. Prints a loud `SKIPPED` — never a pass — when no ref is reachable. **See section 3 for the empirical run and the CI decision.** |
| 6 | trace absent | `c34-trace-absent` | `:172`–`:173` | exit 0; `trace: none` |
| 7 | trace with 3 corrupt lines | `c35-trace-corrupt` | `:174`–`:175` | exit 0; `trace: 2 records, 3 unreadable lines skipped` |
| 8 | `--trace` pointed at a directory | `c36-trace-directory` | `:176`–`:179` | exit 0; `trace: unreadable (trace-dir.jsonl)`; **empty stderr** — the "no traceback" half is asserted, not assumed |

**Gaps found: none.** All eight rows already had a live case. Two
cases exist beyond the eight and are recorded here so the suite's shape is fully
accounted for:

- `c36b-trace-ok` (`:180`–`:181`) — the positive `--trace` case. Not one of the
  eight; added so that the three failure cases above are not the only evidence
  that `--trace` is read at all.
- `c37-template-instantiated` / `c37-template-content` (fixture `:102`–`:113`,
  content `:182`–`:194`) — added, see section 4b.

---

## 2. Enforcement rows 1, 2, 3, 3a

### Row 1 — no network primitive exists in the payload

| test id | file:line | covers |
|---|---|---|
| `tests/unit/test_payload_invariants.py::test_no_template_script_imports_a_network_primitive` | `tests/unit/test_payload_invariants.py:66` | **the whole `templates/*.py` directory**, with the gate's own token list (`urllib`, `requests`, `socket`, `ftplib`, `smtplib`, `http.client`) — the gate exactly as it is stated |
| `tests/unit/test_payload_invariants.py::test_the_gate_covers_every_python_file_that_ships` | `tests/unit/test_payload_invariants.py:77` | that the sweep above is not matching an empty glob, and that it reaches all eight shipped scripts by name |
| `tests/unit/test_trace.py::test_the_script_contains_no_network_primitive_and_no_subprocess` | `tests/unit/test_trace.py:968` | `trace.py` alone (pre-existing) |
| `tests/unit/test_rollup.py::test_the_script_contains_no_network_primitive_and_no_subprocess` | `tests/unit/test_rollup.py:1261` | `rollup.py` alone (pre-existing) |

**GAP FOUND AND FILLED.** Before this audit the gate existed only as two
per-script assertions. Row 1 says the property holds of *the payload*, and its
gate command is `grep -rEn … templates/*.py` — a network import landing
in `transcribe.py`, `validate-report.py`, `check-frontmatter.py`,
`cleanup-scratchpad.py`, `deleted-lines.py` or `recount.py` would have failed no
test. The directory-wide sweep is the fill.

Baseline re-derivation at the time of writing, per the "re-run that exact
command and state the delta" rule:

```
$ grep -rEn 'urllib|requests|socket|ftplib|smtplib|http\.client' \
       skills/critic-ledger/templates/*.py
(no output)   exit 1
```

Delta against the 2026-08-10 baseline reading: `hashlib` in `rollup.py`
(already recorded as the one known delta) — nothing else, and nothing the row-1
pattern matches.

### Row 2 — no shell-out that could reach a network

| test id | file:line | covers |
|---|---|---|
| `tests/unit/test_payload_invariants.py::test_the_named_scripts_contain_no_subprocess_at_all[trace.py]` | `tests/unit/test_payload_invariants.py:101` | `trace.py` |
| `…::test_the_named_scripts_contain_no_subprocess_at_all[rollup.py]` | `tests/unit/test_payload_invariants.py:101` | `rollup.py` |
| `…::test_the_named_scripts_contain_no_subprocess_at_all[recount.py]` | `tests/unit/test_payload_invariants.py:101` | **`recount.py`** — the "preserved property of the third" |
| `…::test_the_exempt_script_still_shells_out_only_through_a_fixed_argv[deleted-lines.py]` | `tests/unit/test_payload_invariants.py:110` | the exemption the row grants, pinned to a list argv (`shell=True` absent) rather than left implicit |

**GAP FOUND AND FILLED.** Row 2 names **three** scripts; only two had an
assertion. `recount.py` — the script that arbitrates round closure and the one
most likely to be extended — was unguarded. The parametrized test covers all
three, plus `os.system` / `os.popen` / `os.execv` / `os.spawn`, which the word
`subprocess` alone does not catch.

Re-derivation of the exemption claim (the exempted pair is `copy-project.sh`
and `deleted-lines.py`):

```
$ grep -ln subprocess skills/critic-ledger/templates/*.py
skills/critic-ledger/templates/deleted-lines.py
skills/critic-ledger/templates/cleanup-scratchpad.py
$ grep -n subprocess skills/critic-ledger/templates/cleanup-scratchpad.py
12:   directory descriptor), never by a shell: there is no `rm`, no `subprocess`, no
```

`cleanup-scratchpad.py`'s only match is a **docstring sentence denying** the use;
it imports no `subprocess`. The claim that `deleted-lines.py` is the sole Python
shell-out holds.

### Row 3 — the trace cannot carry content

| test id | file:line | covers |
|---|---|---|
| `tests/unit/test_trace.py::test_append_refuses_out_of_vocabulary_values` | `tests/unit/test_trace.py:358` | the closed enums on `append` (parametrized over the out-of-vocabulary values) |
| `tests/unit/test_trace.py::test_flags_are_a_closed_vocabulary` | `tests/unit/test_trace.py:477` | `flags` |
| `tests/unit/test_trace.py::test_id_tags_are_a_closed_vocabulary` | `tests/unit/test_trace.py:493` | `id_tags` |
| `tests/unit/test_trace.py::test_an_open_record_with_an_extra_key_is_refused` | `tests/unit/test_trace.py:787` | "refuses to write an unknown key" |
| `tests/unit/test_trace.py::test_a_span_record_missing_a_mandatory_field_is_refused` | `tests/unit/test_trace.py:795` | the other direction of the same schema |
| `tests/unit/test_trace.py::test_validate_refuses_a_wrong_type_as_firmly_as_a_wrong_word` | `tests/unit/test_trace.py:1138` | type confusion, not only bad vocabulary |
| `tests/unit/test_trace.py::test_poisoned_content_never_reaches_the_trace_or_the_output` | `tests/unit/test_trace.py:876` | **the row's named unit test**: poisoned fields through the token-capture path, absent from both the file and stdout |
| `tests/unit/test_trace.py::test_a_wrong_shape_with_poisoned_content_is_refused_without_an_echo` | `tests/unit/test_trace.py:932` | the refusal path with the same poison |
| `tests/unit/test_rollup.py::test_round_and_object_slug_are_derived_and_bounded` | `tests/unit/test_rollup.py:352` | `object_slug` — the summary-only field the row hands to `rollup.py` |
| `tests/unit/test_rollup.py::test_object_slug_stays_inside_its_pattern_for_a_hostile_folder_name` | `tests/unit/test_rollup.py:361` | the derivation that bounds the slug *before* it reaches a file |
| `tests/unit/test_rollup.py::test_mode_is_read_from_the_mode_line` / `…::test_a_mode_holding_neither_value_is_refused_not_written` | `tests/unit/test_rollup.py:392`, `:398` | `mode` — the other summary-only field |
| `tests/unit/test_rollup.py::test_ledger_prose_never_reaches_the_summary_or_the_table` | `tests/unit/test_rollup.py:1168` | free text from the *ledger* input |
| `tests/unit/test_rollup.py::test_a_poisoned_trace_value_is_refused_without_an_echo` | `tests/unit/test_rollup.py:1189` | free text from the *trace* input |

**No gap.** The fallback reader clause of the row ("where the fallback shipped,
through its reader") is vacuous: no `enrich` subcommand ships. Nothing to test,
and nothing missing.

### Row 3a — and neither can its failure output

| test id | file:line | covers |
|---|---|---|
| `tests/unit/test_trace.py::test_a_poisoned_path_cannot_widen_the_diagnostic` | `tests/unit/test_trace.py:900` | a poisoned *path* cannot smuggle content into the file-name slot |
| `tests/unit/test_trace.py::test_every_diagnostic_the_script_can_print_matches_the_closed_form` | `tests/unit/test_trace.py:945` | **the row's named form check**: every diagnostic the script can emit is driven and matched against the specified regex; the produced set is compared to the closed error-class vocabulary with `==` |
| `tests/unit/test_rollup.py::test_a_poisoned_unparseable_line_is_never_echoed` | `tests/unit/test_rollup.py:1201` | the malformed-JSON-line path |
| `tests/unit/test_rollup.py::test_a_poisoned_path_cannot_widen_the_diagnostic` | `tests/unit/test_rollup.py:1209` | as above, for `rollup.py` |
| `tests/unit/test_rollup.py::test_every_diagnostic_the_script_prints_matches_the_closed_form` | `tests/unit/test_rollup.py:1234` | the same form check on the second producer |

Both modules assert against the same regex, character for character
(`tests/unit/test_trace.py:33`–`:36`, `tests/unit/test_rollup.py:34`–`:37`).

**No gap.**

### Enforcement rows outside this file's test scope — audited, with reasons

- **Row 4 — nothing exists while the flag is off.** The row itself makes this a
  fresh-install check "with its `ls` output attached", i.e. an owner-run L1
  probe on a clean profile, not a suite case: the suite runs
  against the repository, never against an installed plugin, and a test that
  installed one would violate the fixtures' rule that nothing is written outside
  `tmp_path` (`tests/unit/conftest.py:15`–`:21`). Left to the release procedure.
- **Row 5 — the trace stays out of releases.** Mechanically checkable — a
  round's `.critic-ledger/` directory is excluded by the release process's own
  file-selection rules — and deliberately **not** added as a test: the script
  carrying those rules is itself excluded from releases, so such a test would
  pass in the development tree and fail in every released copy, and the suite
  ships. A gate that cannot run where the artifact lives is worse than none.
- **Row 6 — the T2 rollup carries no identity.** Already covered by
  the T2 projection tests in `tests/unit/test_rollup.py` (the identifier-free
  projection and the append-not-overwrite behavior). The "deletable in one
  step" half is a documentation claim about a path under
  `~`, verified by reading, not by a test that would have to write there.

---

## 3. Case c33 — the empirical run against the real v0.1.0, and the CI decision

This was left open: the development repository carries **no tags**, so c33
prints `SKIPPED` here and was only ever exercised against a commit standing in
for the previous release. This audit ran it against the real published tag
and then decided the public-CI posture.

### Transcript

Run read-only against a local clone of the published repository (`<released>`)
and a scratch directory (`<scratch>`); no fetch, no write to either tree.

```
$ git -C <released> tag -l
v0.1.0

$ git -C <released> describe --tags --abbrev=0
v0.1.0
$ git -C <released> rev-list --count v0.1.0..HEAD
2

$ git -C <released> show v0.1.0:skills/critic-ledger/templates/recount.py \
      > <scratch>/recount-v0.1.0.py
$ wc -l <scratch>/recount-v0.1.0.py
     415
$ shasum -a 256 <scratch>/recount-v0.1.0.py
2e6e443e3d1eb6e5467cfdae00bef719e3b06ec468db854deb64e8924fd7238f

# the c33 fixture, byte-for-byte as run-regression.sh builds it
$ python3 <scratch>/recount-v0.1.0.py <scratch>/c33-v2-for-old-recount.md
rows: 1 | terminal: 1 | non-terminal: 0
new-findings curve: 5 -> 3 -> 1
ROUND CLOSABLE: zero non-terminal rows.
exit=0
```

End-to-end replication through the case's own code path — the suite run with its
working directory inside the tagged clone, so `git describe` and `git show`
resolve exactly as they would on a CI runner (the script's `$R` still points at
the development tree's 0.2.0 `recount.py`, which is the comparison the case is
for):

```
$ cd <released>
$ sh <dev-tree>/tests/run-regression.sh
…
c33-old-recount              want=0 got=0 ok (ref v0.1.0)
    has: new-findings curve: 5 -> 3 -> 1
…
ALL FIXTURES PASS
```

The development-tree control, for the negative half of the claim:

```
$ git describe --tags --abbrev=0        # in the development tree
fatal: No names found, cannot describe anything.
exit=128
$ git tag -l | wc -l
0
```

### Decision — `fetch-depth: 0`, c33 runs in public CI

The case **passes** against the real v0.1.0 recount, so the contract's
pass-branch applies: the workflow is changed so c33 runs rather than skips.
`.github/workflows/tests.yml`, `tests` job checkout step, now carries
`fetch-depth: 0`.

Why `fetch-depth: 0` and not `fetch-tags: true`: `fetch-tags` adds tag refs to
the fetch, but `git describe --tags --abbrev=0` walks HEAD's **ancestry** for the
nearest tag, and the default `fetch-depth: 1` checkout has no ancestry to walk —
v0.1.0 is two commits behind the public HEAD (`rev-list --count` above). The tag
would be present and still undiscoverable. Full history makes both the tag ref
and the path to it available, which is what the case needs.

Cost accepted knowingly: a full-history fetch on the four-way test matrix. The
repository is small and the alternative is a compatibility claim that CI never
checks — the exact thing case 5 above exists to prevent ("tested rather than
asserted"). Only the `tests` job takes the change; the five other jobs keep the
default shallow checkout.

Residual risk, stated rather than glossed: the case is a **conditional** one. If
the published repository is ever cloned or exported without tags, c33 goes back
to printing `SKIPPED` and the suite still exits 0. That is a deliberate
choice (a missing previous release is not a defect of the current one), not
something `fetch-depth` changes.

---

## 4. Additional candidate items

### 4a. conftest `SCRIPT_NAMES` whitelist — NOT unified (record of why)

**Candidate:** `tests/unit/conftest.py:40`–`:47` whitelists six scripts;
`trace.py` and `rollup.py` are absent, and `tests/unit/test_trace.py:62` /
`tests/unit/test_rollup.py` drive their scripts through their own subprocess
fixtures. Unify only if the unification is a pure refactor with zero assertion
changes.

**It is not.** Three reasons, each checkable:

1. `SCRIPT_NAMES` is not only the `run` fixture's whitelist — it is also the
   **presence gate** of the `scripts_dir` fixture (`tests/unit/conftest.py:90`–
   `:92`: `pytest.fail(f"scripts missing from {directory}: …")`). Adding the two
   0.2.0 scripts makes the *entire suite* fail against any 0.1.x snapshot pointed
   at by `CRITIC_LEDGER_SCRIPTS_DIR` — the one capability conftest's own
   docstring names as the reason the indirection exists
   (`tests/unit/conftest.py:9`–`:13`). That is a behavior change, not a refactor.
2. The call shapes differ: `run("recount.py", …)` takes the script name as its
   first argument and accepts `cwd=` / `stdin=`; `trace(…)` and `rollup(…)` are
   bound to one script and take neither. Unifying means rewriting **83** call
   sites in `test_trace.py` and **89** in `test_rollup.py`
   (`grep -c` on the fixture names) — 172 edited lines whose only defense against
   a typo is the suite that is being edited.
3. The exclusion is already **deliberate and documented at both call sites**
   (`tests/unit/test_trace.py:10`–`:13`, `tests/unit/test_rollup.py:12`–`:14`:
   *"deliberately NOT added to conftest's `run` fixture (that whitelist belongs
   to the six 0.1.x scripts)"*). Both local fixtures reuse conftest's
   `hardened_env`, so the safety property the whitelist exists to guarantee — one
   hardened environment, everything inside `tmp_path` — is already shared. What
   is not shared is a name list, which is the part that carries the cost.

**Outcome: refuted, no change.** The duplication is ~18 lines of fixture body
against a suite-wide regression risk and a documented capability loss.

### 4b. A case pinning the instantiated ledger TEMPLATE — ADDED (`c37`)

**Candidate:** every regression fixture above is a hand-written table; nothing tested
that the **shipped** `skills/critic-ledger/templates/ledger.md` still produces a
ledger the recount can read.

**Added** as shell case `c37`, `tests/run-regression.sh:102`–`:113` (fixture) and
`:182`–`:194` (assertions). It lifts both table headers *out of the template
file itself* (`awk` on `| id | sev |` and `| # | pass (scope)`, header plus
separator), fills them with rows, and asserts the recount's full output. It is
not redundant with c31: the template's passes table is **nine** columns wide and
carries `started`/`ended` at indices **7 and 8**, so it exercises `recount.py`'s
lookup **by name** (`cell_by_name`, `skills/critic-ledger/templates/recount.py:479`)
rather than the last-two-of-seven shape c31's fixture happens to have. Asserted:

```
rows: 2 | terminal: 2 | non-terminal: 0
severity distribution (terminal/rows): blocker 0/0 | major 1/1 | minor 1/1
new-findings curve: 5 -> 3 -> 1
time-indexed curve (from 2026-08-10T10:00:00Z): +0s -> 5 | +3600s -> 3 | +7200s -> 1
pass wall-clock: 1: 1800s | 2: 900s | 3: 600s
```

The rows also exercise the criterion/terminal agreement rule in both directions:
a `verified-landed` row with a non-empty criterion and a `refuted-with-reason`
row carrying exactly `—`. A guard at `tests/run-regression.sh:185`–`:188` reports
a missing template header as its own failure, so a template rewrite cannot
silently degrade the case into a malformed fixture that passes.

### 4c. SKILL.md stage sentences — ADDED

**Candidate:** ten `**With observability on**` markers exist, one per
stage 0–9; nothing asserted it.

**Added**, `tests/unit/test_payload_invariants.py:146`, `:151`, `:160` — three
tests rather than one, because "ten markers in the file" is the weak version of
the claim:

- `test_the_stage_machine_has_ten_stages_numbered_zero_through_nine` — the
  stage machine is parsed out of `SKILL.md` and its numbering pinned.
- `test_every_stage_carries_exactly_one_observability_sentence` — the count is
  asserted **per stage** (`dict.fromkeys(range(10), 1)`), so two markers in one
  stage and none in another fails, which a total-count test would not catch.
- `test_the_file_carries_no_observability_marker_outside_the_stage_machine` —
  the total is ten and all ten are stage sentences.

Current state re-derived: markers at `skills/critic-ledger/SKILL.md:326`, `:350`,
`:404`, `:437`, `:458`, `:474`, `:543`, `:607`, `:657`, `:721`; stage starts at
`:312`, `:332`, `:361`, `:411`, `:443`, `:464`, `:479`, `:549`, `:612`, `:667`.

### 4d. "the two shell scripts in the tree" — REWORDED

**Candidate:** `.github/workflows/tests.yml:20` and `:109` said "the two
shell scripts in the tree". The claim is true of the **released** tree; in a
development checkout the same glob also matches additional paths under private
tooling directories that never ship, all covered by the release process's own
file-selection rules — reproduced here against the released tree only:

```
$ find . -name '*.sh' -not -path './.git/*'
./tests/run-regression.sh
./skills/critic-ledger/templates/copy-project.sh
```

Exactly the two the shellcheck step names.

**Reworded** in both places to say **SHIPPED** and to point at the two names the
step already lists, plus a sentence saying why the list is written out instead
of globbed (`*.sh` in a development checkout matches the excluded files). The
comment is now accurate read from either tree.

**`CONTRIBUTING.md:30` left as is** — "The third command lints both shell
scripts." Its antecedent is the command block sixteen lines above
(`CONTRIBUTING.md:13`–`:14`), which names both files explicitly; the sentence
makes no claim about what is or is not in the tree, so there is nothing to
correct. Changing it would be churn, not accuracy.

---

## 5. Suite counts, re-measured

Measured on the tree this file lands in, by collection rather than by hand.

| site | before | after | moved by |
|---|---|---|---|
| `tests/run-regression.sh:2` (header) | `37 cases, c01-c36b` | `38 cases, c01-c37` | `c37` |
| `CONTRIBUTING.md:21` | 37 | 38 | `c37` |
| `CONTRIBUTING.md:25` | 517 | 526 | `test_payload_invariants.py` (+9) |
| `.github/workflows/tests.yml:4` | 37-case | 38-case | `c37` |
| `.github/workflows/tests.yml:5` | 517-case | 526-case | +9 |
| `.github/workflows/tests.yml` step name (regression) | 37 cases | 38 cases | `c37` |
| `.github/workflows/tests.yml` step name (pytest) | 517 cases | 526 cases | +9 |

Measurements:

```
$ uvx pytest==9.1.1 tests/unit -q --collect-only | tail -1
526 tests collected

$ sh tests/run-regression.sh | tail -1
ALL FIXTURES PASS
```

The shell count is **distinct case ids**, not printed lines: `c01`–`c28` (28)
plus `c29`–`c37` (10, counting `c36b`) = 38. The run prints 43 result lines
because `c29`–`c32` and `c37` are checked twice — once for exit code in the glob
loop, once for output in the `case_run` block.

**One count site is knowingly left stale, because it is outside this audit's
file scope:** `CHANGELOG.md:55`–`:56` reads *"the shell regression suite goes
from 28 to 37 cases, the pytest characterization suite from 230 to 517
tests"*. The true 0.2.0 deltas are **28 → 38** and **230 → 526**. This audit's
scope was limited to `tests/**`, `.github/workflows/tests.yml` and
`CONTRIBUTING.md`; the stale count is a follow-up, not fixed here.
