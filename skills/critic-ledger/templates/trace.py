#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Reference trace writer and validator for a critic-ledger round —
the T1 carrier `.critic-ledger/<run>/trace.jsonl`, one JSON object per
line, UTF-8, LF, APPEND-ONLY. Observability is optional and ON by
default; nothing here runs, and no file is created, when the round
switched it off.

THIS SCRIPT NEVER FAILS CLOSED — its exit code is ALWAYS 0
----------------------------------------------------------
Every other gate in this project is fail-closed. This one is the
deliberate inverse: observability must never be able to fail a round
at all. A refused value, an unreadable file, a malformed line, a failed
write and a wrong invocation all exit 0. What a failure produces is ONE
diagnostic line built from a CLOSED error-class vocabulary:

    unreadable | unparseable-line | no-usage | id-not-found |
    schema-refused | write-failed

printed as `<class>: <file name>` or `<class>: <file name>:<line>` and
NOTHING else. The diagnostic NEVER echoes the bytes it failed to read or
parse: the natural debugging instinct on a malformed line is exactly the
thing forbidden here, because the trace must stay showable to anyone
without a sanitization pass. The file NAME is printed, never a path.
(`no-usage` has no producer while the transcript fallback does not ship.
The class stays in the vocabulary because the `outcome · script` error
strings reuse this same list.)

No `enrich` subcommand exists, and no transcript is ever opened. Tokens
come from the completed `Agent` tool result the orchestrator already
receives, handed to `append` on the command line.

There is deliberately NO free-text field
----------------------------------------
Every field is an enumeration or an anchored, length-bounded pattern. A
value that does not match is REFUSED rather than written — "collect
nothing", never "stop the round". `append` therefore writes a line only
when the complete record passes the same validator `validate` applies.

Two records per span
--------------------
- `--kind open` at the open: the smaller field set (`v`, `round`, `span`,
  `parent`, `stage`, `actor`, `unit`, `id_prefix`, `model_assigned`,
  `started`, and `agent_id` where the spawn already returned one), and no
  other key.
- `--kind span` at the close: the complete span record. Its `started` is
  COPIED from the open record already on disk (never re-read from a
  clock, never taken from an agent); a close with no open record on disk
  is refused with `id-not-found`. `ended` is this script's own clock.
- A `span` record supersedes the `open` record with the same id and the
  pair counts once. An `open` with no `span` is an UNCLOSED span: the
  round was interrupted. No reader may invent its end; `validate` reports
  the count as `trace: <n> unclosed spans (round interrupted)`, which is
  not an error class, widens no vocabulary and changes no exit code.

What `validate` reports
-----------------------
Per line, one diagnostic of the closed vocabulary above for a line that
cannot be parsed or that the schema refuses. Then REPORT-ONLY defects
(they too change no exit code), one per line, in the bounded form
`defect: <class> line <n>`, `<class>` being one of:

    duplicate-span              a second `span` record for one id
    unit-id-prefix-disagreement a critic span whose `unit` and
                                `id_prefix` differ
    wallclock-mismatch          `wallclock_s` disagrees with
                                `ended - started`
    total-tokens-mismatch       `tokens.total` (the tool result's
                                `totalTokens`) disagrees with the sum of
                                the four counters
    id-tags-orphan              `id_tags` names an id absent from `ids`

and a summary line. Under `tokens_source: agent-tool-result-total` the
`tokens` object carries `total` ALONE: the four counters never arrive
from that delivery, so the cross-check does not apply. Under every
other source the four counters are fixed and `tokens.total` is the one
optional key — where it is present, the cross-check against the tool
result's `totalTokens` is required, and that check needs the number on
disk to be re-derivable. Records without it are accepted unchanged.

Usage:  trace.py append <trace.jsonl> --kind open|span --round <run>
                --span <s3.01> --actor <actor> --unit <unit> [options]
        trace.py validate <trace.jsonl>
        trace.py -h | --help                        (this text)

Options for `append` (every one takes a value; `null` and the empty
string mean JSON null where the field is nullable):
        --kind --round --span --parent --stage --actor --unit
        --id-prefix --agent-id --ids --id-tags --flags
        --model-assigned --model-actual --model-source
        --tokens-in --tokens-out --cache-write --cache-read
        --total-tokens --tokens-source --commit
        --started --ended --outcome
`--ids` and `--flags` are comma-separated; `--id-tags` is a JSON object.
`--stage` defaults to the stage named by the span id; `--parent` to the
round span `s1.00` (and to null on `s1.00` itself); `--started` and
`--ended` default to this script's own clock.
A bare `--total-tokens` (no four counters) is written only alongside
`--tokens-source agent-tool-result-total`; with the four counters
present it stays the optional, cross-checked aggregate.

Exit code: ALWAYS 0 — see the second section above.
"""  # noqa: D205  # printed usage text; reflowing it would change output

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
ROUND_SPAN = "s1.00"

# The closed error-class vocabulary, reused verbatim by the
# `outcome · script` patterns: widening one widens both.
ERROR_CLASSES = (
    "unreadable",
    "unparseable-line",
    "no-usage",
    "id-not-found",
    "schema-refused",
    "write-failed",
)
DIAGNOSTIC_RE = re.compile(
    r"^(unreadable|unparseable-line|no-usage|id-not-found|schema-refused"
    r"|write-failed): [\w./-]+(:\d+)?$",
)

KINDS = ("open", "span")
ACTORS = (
    "orchestrator",
    "critic",
    "fixer",
    "verifier",
    "script",
    "subagent-observed",
)
# Actors that measure a spawn: `n/a` is never their observed model.
SPAWN_ACTORS = ("critic", "fixer", "verifier", "subagent-observed")
# Actors that measure no spawn: both model cells read `n/a`, and no
# `agent_id` exists to record.
NO_SPAWN_ACTORS = ("orchestrator", "script")

MODEL_SOURCES = ("resolvedModel", "self-report", "n/a")
# The same completed `Agent` tool result, reporting its AGGREGATE alone:
# where the result carries no four-counter breakdown, the `tokens` object
# carries the single key `total` and nothing else.
TOTAL_ONLY_SOURCE = "agent-tool-result-total"
TOKENS_SOURCES = (
    "agent-tool-result",
    TOTAL_ONLY_SOURCE,
    "subagent-transcript",
    "absent",
)
FLAG_VOCABULARY = (
    "respawn",
    "dropped-lens",
    "degraded",
    "bundled",
    "criterion-unworkable",
)
TAG_VOCABULARY = ("fix-application", "security-pii", "duplicate", "refuted")

# The payload's own scripts, a closed list. A new script joins it
# before it may open a span.
SCRIPT_UNITS = (
    "trace.py",
    "rollup.py",
    "recount.py",
    "transcribe.py",
    "deleted-lines.py",
    "validate-report.py",
    "copy-project.sh",
)
# `round` is the unit of the round span `s1.00` itself: the opening stage
# writes its `open` record and the closing stage its close, with the
# existing step outcome `closed`.
ORCHESTRATOR_UNITS = ("round", "scoping", "salvage", "closure")
ORCHESTRATOR_BATCH_RE = re.compile(r"^adjudication-batch-\d{1,4}$")
ORCHESTRATOR_STEP_OUTCOMES = ("scoped", "salvaged", "closed")
# Waiting for the owner is an orchestrator UNIT, not a new actor: the
# orchestrator writes the `open` when the question is put to the owner and
# the close on the owner's word. The reason is a closed vocabulary and so
# is the outcome; the longest name, `owner-wait-authorization`, is exactly
# MAX_ORCHESTRATOR_UNIT_LEN characters, so a seventh reason is a length
# decision as much as a vocabulary one.
OWNER_WAIT_RE = re.compile(
    r"^owner-wait-(signature|authorization|fork|amendment|ratification"
    r"|z3-closure)$",
)
OWNER_WAIT_OUTCOMES = ("answered", "refused", "abandoned")

ROUND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}-[a-z0-9][a-z0-9-]{0,39}$")
SPAN_RE = re.compile(r"^s[1-9]\.\d{2,4}$")
# The id contract of recount.py (its `ID_RE`), character for character: a
# prefix of one or more letter-led segments joined by dashes, then `-<n>`,
# so a span naming a composite id (`V-CIT-1`) is recorded, not refused.
FINDING_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)*-\d+$")
PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,7}$")
AGENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

MAX_ROUND_LEN = 58
MAX_SPAN_LEN = 8
MAX_FINDING_ID_LEN = 16
MAX_AGENT_ID_LEN = 64
MAX_MODEL_LEN = 32
MAX_COMMIT_LEN = 40
MIN_STAGE = 1
MAX_STAGE = 9
TAG_STAGE = 6
COMMIT_STAGE = 7

# `unit` per actor: an anchored pattern and a maximum length.
UNIT_PATTERNS = {
    "critic": (re.compile(r"^[A-Za-z][A-Za-z0-9]{0,7}$"), 8),
    "verifier": (re.compile(r"^P\d{1,4}$"), 5),
    "fixer": (re.compile(r"^[A-Z]{1,2}\d{1,3}[a-z]?$"), 6),
    "subagent-observed": (re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,31}$"), 32),
}
MAX_SCRIPT_UNIT_LEN = 20
MAX_ORCHESTRATOR_UNIT_LEN = 24

# `outcome` per actor.
OUTCOME_PATTERNS = {
    "critic": (re.compile(r"^(findings:\d{1,4}|dropped)$"), 16),
    # The fixer has THREE per-id outcomes, and the third one is countable
    # here: `notfound:<k>` carries `premise-not-found`. The two-part form is
    # kept beside the three-part one rather than replaced — every trace of a
    # closed round carries it, and those traces validate unchanged. The bound
    # is 48 and not 32 because `bounded` cuts by LENGTH independently of the
    # pattern: `fixed:10,unworkable:10,notfound:10` is 34 characters and the
    # four-digit worst case is 40, so a 32 would reject a matching outcome.
    "fixer": (
        re.compile(
            r"^fixed:\d{1,4},unworkable:\d{1,4}(?:,notfound:\d{1,4})?$",
        ),
        48,
    ),
    "verifier": (re.compile(r"^L:\d{1,4},P:\d{1,4},NOT:\d{1,4},new:\d{1,4}$"), 48),
    "script": (
        re.compile(r"^(ok|error:(" + "|".join(ERROR_CLASSES) + r"))$"),
        32,
    ),
    "subagent-observed": (re.compile(r"^observed:(tokens|no-tokens)$"), 20),
    "orchestrator": (
        re.compile(
            r"^(upheld:\d{1,4},refuted:\d{1,4}|"
            + "|".join(ORCHESTRATOR_STEP_OUTCOMES)
            + r")$",
        ),
        32,
    ),
}
# The orchestrator's SECOND closed outcome form, selected by `unit` — never
# merged into the entry above. A merged pattern would pass `scoped` on an
# owner-wait span and `answered` on `scoping`, and the check would stop
# telling the two units apart.
OWNER_WAIT_OUTCOME = (
    re.compile(r"^(" + "|".join(OWNER_WAIT_OUTCOMES) + r")$"),
    16,
)

OPEN_REQUIRED = (
    "v",
    "kind",
    "round",
    "span",
    "parent",
    "stage",
    "actor",
    "unit",
    "id_prefix",
    "model_assigned",
    "started",
)
OPEN_ALLOWED = (*OPEN_REQUIRED, "agent_id")
SPAN_REQUIRED = (
    *OPEN_REQUIRED,
    "agent_id",
    "ids",
    "id_tags",
    "flags",
    "model_actual",
    "model_source",
    "tokens",
    "tokens_source",
    "commit",
    "ended",
    "wallclock_s",
    "outcome",
)
TOKEN_KEYS = ("in", "out", "cache_write", "cache_read")
TOKEN_TOTAL_KEY = "total"  # noqa: S105  # a JSON key name, not a credential
# The `append` options carrying the four counters, in TOKEN_KEYS order.
COUNTER_OPTIONS = ("tokens_in", "tokens_out", "cache_write", "cache_read")

OPTION_NAMES = (
    "--kind",
    "--round",
    "--span",
    "--parent",
    "--stage",
    "--actor",
    "--unit",
    "--id-prefix",
    "--agent-id",
    "--ids",
    "--id-tags",
    "--flags",
    "--model-assigned",
    "--model-actual",
    "--model-source",
    "--tokens-in",
    "--tokens-out",
    "--cache-write",
    "--cache-read",
    "--total-tokens",
    "--tokens-source",
    "--commit",
    "--started",
    "--ended",
    "--outcome",
)
NULL_LITERALS = ("", "null")


# ---------------------------------------------------------------------------
# diagnostics — the only failure output, and it carries no content
# ---------------------------------------------------------------------------


def diagnostic(error_class: str, name: str, line: int | None = None) -> str:
    """Build the one diagnostic line: a closed class plus a file name.

    The name is reduced to its basename and every character outside
    `[A-Za-z0-9._-]` is replaced, so the result cannot carry content
    through a crafted path. A line that still fails the diagnostic form
    is replaced by a bounded last-resort line rather than printed.
    """
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", Path(name).name) or "trace"
    text = f"{error_class}: {safe}" if line is None else f"{error_class}: {safe}:{line}"
    if error_class not in ERROR_CLASSES or not DIAGNOSTIC_RE.match(text):
        return "schema-refused: trace"
    return text


# ---------------------------------------------------------------------------
# typed readers over decoded JSON (never trust the shape of a line)
# ---------------------------------------------------------------------------


def as_object(value: object) -> dict[str, object] | None:
    """Return a str-keyed mapping, or None when the value is not one."""
    if not isinstance(value, dict):
        return None
    out: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def as_str_list(value: object) -> list[str] | None:
    """Return a list of strings, or None when the value is not one."""
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        out.append(item)
    return out


def as_int(value: object) -> int | None:
    """Return an int, or None. `True` is a bool, not the integer 1."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def as_str(value: object) -> str | None:
    """Return a string, or None when the value is not one."""
    return value if isinstance(value, str) else None


def parse_timestamp(value: object) -> datetime | None:
    """Return the datetime of an ISO-8601 UTC second-resolution string."""
    text = as_str(value)
    if text is None or not TIMESTAMP_RE.match(text):
        return None
    try:
        return datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def bounded(value: object, pattern: re.Pattern[str], max_len: int) -> bool:
    """Report whether a value is a string matching an anchored, bounded pattern."""
    text = as_str(value)
    return text is not None and len(text) <= max_len and pattern.match(text) is not None


# ---------------------------------------------------------------------------
# the schema — one validator, used by `append` and `validate`
# ---------------------------------------------------------------------------


def valid_unit(actor: str, value: object) -> bool:
    """Check `unit` against the closed vocabulary or pattern of its actor."""
    text = as_str(value)
    if text is None:
        return False
    if actor == "script":
        return text in SCRIPT_UNITS and len(text) <= MAX_SCRIPT_UNIT_LEN
    if actor == "orchestrator":
        if len(text) > MAX_ORCHESTRATOR_UNIT_LEN:
            return False
        return (
            text in ORCHESTRATOR_UNITS
            or ORCHESTRATOR_BATCH_RE.match(text) is not None
            or OWNER_WAIT_RE.match(text) is not None
        )
    pattern, max_len = UNIT_PATTERNS[actor]
    return bounded(text, pattern, max_len)


def valid_outcome(actor: str, value: object, unit: object) -> bool:
    """Check `outcome` against the closed pattern of its actor and unit.

    The orchestrator has TWO closed forms, and the unit selects between
    them: an owner-wait span takes `OWNER_WAIT_OUTCOMES` and nothing else,
    every other orchestrator unit takes the step/adjudication form and
    nothing else. Every other actor keys on the actor alone.
    """
    if actor == "orchestrator" and OWNER_WAIT_RE.match(as_str(unit) or "") is not None:
        pattern, max_len = OWNER_WAIT_OUTCOME
    else:
        pattern, max_len = OUTCOME_PATTERNS[actor]
    return bounded(value, pattern, max_len)


def valid_head(rec: dict[str, object]) -> str | None:
    """Validate the fields both record kinds share; return the actor or None."""
    if as_int(rec.get("v")) != SCHEMA_VERSION:
        return None
    if not bounded(rec.get("round"), ROUND_RE, MAX_ROUND_LEN):
        return None
    span_id = as_str(rec.get("span"))
    if span_id is None or not bounded(span_id, SPAN_RE, MAX_SPAN_LEN):
        return None
    stage = as_int(rec.get("stage"))
    if stage is None or not MIN_STAGE <= stage <= MAX_STAGE:
        return None
    # The id names the stage that WROTE the span, and `stage: 0`
    # never appears in a valid trace.
    if span_id[1] != str(stage):
        return None
    parent = rec.get("parent")
    if span_id == ROUND_SPAN:
        if parent is not None:
            return None
    elif not bounded(parent, SPAN_RE, MAX_SPAN_LEN):
        return None
    actor = as_str(rec.get("actor"))
    if actor not in ACTORS:
        return None
    if not valid_unit(actor, rec.get("unit")):
        return None
    id_prefix = rec.get("id_prefix")
    if actor in ("critic", "verifier"):
        if not bounded(id_prefix, PREFIX_RE, MAX_SPAN_LEN):
            return None
    elif id_prefix is not None:
        return None
    agent_id = rec.get("agent_id")
    if agent_id is not None:
        if actor in NO_SPAWN_ACTORS:
            return None
        if not bounded(agent_id, AGENT_ID_RE, MAX_AGENT_ID_LEN):
            return None
    model_assigned = as_str(rec.get("model_assigned"))
    if model_assigned is None:
        return None
    if actor in NO_SPAWN_ACTORS:
        if model_assigned != "n/a":
            return None
    elif not bounded(model_assigned, MODEL_RE, MAX_MODEL_LEN):
        return None
    if parse_timestamp(rec.get("started")) is None:
        return None
    return actor


def valid_tokens(rec: dict[str, object], actor: str) -> bool:
    """Validate `tokens`, `tokens_source` and their pairing rules."""
    tokens = rec.get("tokens")
    source = as_str(rec.get("tokens_source"))
    if source not in TOKENS_SOURCES:
        return False
    if tokens is None:
        # `null` is the honest value, and it pairs with `absent`.
        return source == "absent"
    if source == "absent":
        return False
    # The main loop's spend is never separable per batch.
    if actor == "orchestrator":
        return False
    obj = as_object(tokens)
    if obj is None:
        return False
    if source == TOTAL_ONLY_SOURCE:
        # One measured aggregate and no breakdown: `total` ALONE. The four
        # counters never arrive from this delivery, so their form is not
        # admitted for it — the source names what was measured.
        if set(obj) != {TOKEN_TOTAL_KEY}:
            return False
    elif set(obj) - {TOKEN_TOTAL_KEY} != set(TOKEN_KEYS):
        return False
    for value in obj.values():
        number = as_int(value)
        if number is None or number < 0:
            return False
    return True


def valid_models(rec: dict[str, object], actor: str) -> bool:
    """Validate `model_actual` and `model_source` against the schema's rules."""
    if as_str(rec.get("model_source")) not in MODEL_SOURCES:
        return False
    model_actual = as_str(rec.get("model_actual"))
    if model_actual is None:
        return False
    if actor in NO_SPAWN_ACTORS:
        # The one permitted equality: no model assigned, none observed.
        return model_actual == "n/a"
    if model_actual == "n/a":
        # For an actor that measures a spawn, absence is `unknown`.
        return False
    if not bounded(model_actual, MODEL_RE, MAX_MODEL_LEN):
        return False
    # Never silently equal to `model_assigned` — an assignment copied
    # into an observation is not an observation.
    return model_actual != as_str(rec.get("model_assigned"))


def valid_close(rec: dict[str, object], actor: str) -> bool:
    """Validate the fields a `kind: "span"` record adds to the head."""
    ids = as_str_list(rec.get("ids"))
    if ids is None or any(
        len(i) > MAX_FINDING_ID_LEN or not FINDING_ID_RE.match(i) for i in ids
    ):
        return False
    tags = as_object(rec.get("id_tags"))
    if tags is None:
        return False
    stage = as_int(rec.get("stage"))
    if tags and stage != TAG_STAGE:
        return False
    for key, value in tags.items():
        if len(key) > MAX_FINDING_ID_LEN or not FINDING_ID_RE.match(key):
            return False
        tag_list = as_str_list(value)
        if tag_list is None or any(t not in TAG_VOCABULARY for t in tag_list):
            return False
    flags = as_str_list(rec.get("flags"))
    if flags is None or any(f not in FLAG_VOCABULARY for f in flags):
        return False
    if not valid_models(rec, actor) or not valid_tokens(rec, actor):
        return False
    commit = rec.get("commit")
    if commit is not None and (
        stage != COMMIT_STAGE or not bounded(commit, COMMIT_RE, MAX_COMMIT_LEN)
    ):
        return False
    started = parse_timestamp(rec.get("started"))
    ended = parse_timestamp(rec.get("ended"))
    if started is None or ended is None or ended < started:
        return False
    wallclock = as_int(rec.get("wallclock_s"))
    if wallclock is None or wallclock < 0:
        return False
    if not valid_outcome(actor, rec.get("outcome"), rec.get("unit")):
        return False
    return valid_observed_pairing(rec, actor)


def valid_observed_pairing(rec: dict[str, object], actor: str) -> bool:
    """Enforce the `subagent-observed` outcome/token pairing."""
    if actor != "subagent-observed":
        return True
    has_tokens = rec.get("tokens") is not None
    source = as_str(rec.get("tokens_source"))
    if rec.get("outcome") == "observed:tokens":
        return has_tokens and source == "subagent-transcript"
    return not has_tokens


def valid_record(value: object) -> bool:
    """Report whether a decoded line is a valid `open` or `span` record."""
    rec = as_object(value)
    if rec is None:
        return False
    kind = rec.get("kind")
    if kind not in KINDS:
        return False
    required = OPEN_REQUIRED if kind == "open" else SPAN_REQUIRED
    allowed = OPEN_ALLOWED if kind == "open" else SPAN_REQUIRED
    keys = set(rec)
    if not set(required) <= keys or not keys <= set(allowed):
        return False
    actor = valid_head(rec)
    if actor is None:
        return False
    return True if kind == "open" else valid_close(rec, actor)


# ---------------------------------------------------------------------------
# append — one span line, including the token capture
# ---------------------------------------------------------------------------


def parse_append(args: list[str]) -> tuple[str, dict[str, str]] | None:
    """Return (path, options) for `append`, or None on a usage error."""
    path: str | None = None
    opt: dict[str, str] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if token in OPTION_NAMES:
            if index + 1 >= len(args):
                return None
            opt[token[2:].replace("-", "_")] = args[index + 1]
            index += 2
            continue
        if token.startswith("-") or path is not None:
            return None
        path = token
        index += 1
    if path is None:
        return None
    return path, opt


def nullable(opt: dict[str, str], key: str) -> str | None:
    """Read an option that may be JSON null (absent, empty or `null`)."""
    value = opt.get(key)
    if value is None or value in NULL_LITERALS:
        return None
    return value


def build_tokens(opt: dict[str, str]) -> tuple[dict[str, int] | None, bool]:
    """Build the `tokens` object from the counters; the flag reports success."""
    given = [k for k in COUNTER_OPTIONS if k in opt]
    if not given:
        if "total_tokens" not in opt:
            return None, True
        # A bare `--total-tokens` has no four counters to cross-check, so it
        # is written ONLY under the source that names that delivery — the
        # aggregate alone, in the one shape `valid_tokens` admits for it.
        if opt.get("tokens_source") != TOTAL_ONLY_SOURCE:
            return None, False
        try:
            total = int(opt["total_tokens"])
        except ValueError:
            return None, False
        return {TOKEN_TOTAL_KEY: total}, True
    if len(given) != len(COUNTER_OPTIONS):
        # Zero is never a stand-in for a counter that was not captured.
        return None, False
    tokens: dict[str, int] = {}
    for key, option in zip(TOKEN_KEYS, COUNTER_OPTIONS, strict=True):
        try:
            tokens[key] = int(opt[option])
        except ValueError:
            return None, False
    if "total_tokens" in opt:
        try:
            tokens[TOKEN_TOTAL_KEY] = int(opt["total_tokens"])
        except ValueError:
            return None, False
    return tokens, True


def build_record(
    opt: dict[str, str],
    started: str,
    ended: str | None,
) -> dict[str, object] | None:
    """Assemble the record the options describe, or None on a shape error."""
    kind = opt.get("kind", "")
    span_id = opt.get("span", "")
    actor = opt.get("actor", "")
    no_spawn = actor in NO_SPAWN_ACTORS

    if "stage" in opt:
        try:
            stage: int = int(opt["stage"])
        except ValueError:
            return None
    elif len(span_id) > 1 and span_id[1].isdigit():
        stage = int(span_id[1])
    else:
        return None

    if "parent" in opt:
        parent: object = nullable(opt, "parent")
    else:
        parent = None if span_id == ROUND_SPAN else ROUND_SPAN

    rec: dict[str, object] = {
        "v": SCHEMA_VERSION,
        "kind": kind,
        "round": opt.get("round", ""),
        "span": span_id,
        "parent": parent,
        "stage": stage,
        "actor": actor,
        "unit": opt.get("unit", ""),
        "id_prefix": nullable(opt, "id_prefix"),
    }
    if kind != "open" or "agent_id" in opt:
        rec["agent_id"] = nullable(opt, "agent_id")
    if kind == "open":
        rec["model_assigned"] = opt.get("model_assigned", "n/a" if no_spawn else "")
        rec["started"] = started
        return rec

    ids = opt.get("ids", "")
    rec["ids"] = [i for i in ids.split(",") if i]
    try:
        tags: object = json.loads(opt["id_tags"]) if "id_tags" in opt else {}
    except ValueError:
        return None
    rec["id_tags"] = tags
    flags = opt.get("flags", "")
    rec["flags"] = [f for f in flags.split(",") if f]
    rec["model_assigned"] = opt.get("model_assigned", "n/a" if no_spawn else "")
    rec["model_actual"] = opt.get("model_actual", "n/a" if no_spawn else "unknown")
    # `resolvedModel` names an OBSERVATION; `unknown` is the absence of one,
    # and it pairs with `model_source: "n/a"`.
    observed = opt.get("model_actual") not in (None, "unknown")
    default_source = "resolvedModel" if observed and not no_spawn else "n/a"
    rec["model_source"] = opt.get("model_source", default_source)
    tokens, ok = build_tokens(opt)
    if not ok:
        return None
    rec["tokens"] = tokens
    rec["tokens_source"] = opt.get(
        "tokens_source",
        "agent-tool-result" if tokens is not None else "absent",
    )
    rec["commit"] = nullable(opt, "commit")
    rec["started"] = started
    rec["ended"] = ended
    start_dt = parse_timestamp(started)
    end_dt = parse_timestamp(ended)
    if start_dt is None or end_dt is None:
        return None
    rec["wallclock_s"] = int((end_dt - start_dt).total_seconds())
    rec["outcome"] = opt.get("outcome", "")
    return rec


def read_lines(path: Path) -> tuple[list[str] | None, str | None]:
    """Read a trace file: return (lines, None) or (None, error class)."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, "id-not-found"
    except OSError:
        return None, "unreadable"
    except UnicodeDecodeError:
        return None, "unreadable"
    return text.splitlines(), None


def open_started(
    path: Path, round_id: str, span_id: str
) -> tuple[str | None, str | None]:
    """Copy `started` from the span's own `open` record already on disk."""
    lines, error = read_lines(path)
    if lines is None:
        return None, error
    found: str | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            decoded: object = json.loads(stripped)
        except ValueError:
            continue
        rec = as_object(decoded)
        if rec is None:
            continue
        if (
            rec.get("kind") == "open"
            and rec.get("round") == round_id
            and rec.get("span") == span_id
        ):
            candidate = as_str(rec.get("started"))
            if candidate is not None:
                found = candidate
    if found is None:
        return None, "id-not-found"
    return found, None


def cmd_append(args: list[str]) -> int:
    """Append one record; print at most one diagnostic; always return 0."""
    parsed = parse_append(args)
    if parsed is None:
        print(__doc__)
        return 0
    path_text, opt = parsed
    path = Path(path_text)
    now = datetime.now(tz=UTC).strftime(TIMESTAMP_FORMAT)

    started: str = opt.get("started", now)
    ended: str | None = None
    if opt.get("kind") == "span":
        if "started" not in opt:
            # `started` is COPIED from the open record on
            # disk, never re-read from a clock and never asked of an agent.
            copied, error = open_started(
                path,
                opt.get("round", ""),
                opt.get("span", ""),
            )
            if copied is None:
                print(diagnostic(error or "id-not-found", path_text))
                return 0
            started = copied
        ended = opt.get("ended", now)

    rec = build_record(opt, started, ended)
    if rec is None or not valid_record(rec):
        print(diagnostic("schema-refused", path_text))
        return 0
    line = json.dumps(rec, separators=(",", ":"))
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
    except OSError:
        print(diagnostic("write-failed", path_text))
    return 0


# ---------------------------------------------------------------------------
# validate — schema, closed vocabularies, and the report-only defects
# ---------------------------------------------------------------------------


def token_defect(rec: dict[str, object]) -> bool:
    """Report whether `tokens.total` disagrees with the four counters."""
    obj = as_object(rec.get("tokens"))
    if obj is None or TOKEN_TOTAL_KEY not in obj:
        return False
    if not set(TOKEN_KEYS) <= set(obj):
        # The total-only form (`agent-tool-result-total`) carries no
        # breakdown for the total to disagree with: nothing to cross-check,
        # and indexing the absent counters here would raise on the very
        # records the source admits.
        return False
    total = as_int(obj[TOKEN_TOTAL_KEY])
    counters = [as_int(obj[k]) for k in TOKEN_KEYS]
    if total is None or any(c is None for c in counters):
        return False
    return total != sum(c for c in counters if c is not None)


def record_defects(rec: dict[str, object]) -> list[str]:
    """Return the report-only defect classes a single valid record carries."""
    found: list[str] = []
    if rec.get("actor") == "critic" and rec.get("unit") != rec.get("id_prefix"):
        found.append("unit-id-prefix-disagreement")
    if rec.get("kind") == "span":
        started = parse_timestamp(rec.get("started"))
        ended = parse_timestamp(rec.get("ended"))
        wallclock = as_int(rec.get("wallclock_s"))
        if (
            started is not None
            and ended is not None
            and wallclock is not None
            and int((ended - started).total_seconds()) != wallclock
        ):
            found.append("wallclock-mismatch")
        if token_defect(rec):
            found.append("total-tokens-mismatch")
        ids = set(as_str_list(rec.get("ids")) or [])
        tags = as_object(rec.get("id_tags")) or {}
        if set(tags) - ids:
            found.append("id-tags-orphan")
    return found


def cmd_validate(args: list[str]) -> int:
    """Validate a trace file; print diagnostics and defects; always return 0."""
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__)
        return 0
    path_text = args[0]
    lines, _error = read_lines(Path(path_text))
    if lines is None:
        print(diagnostic("unreadable", path_text))
        return 0

    opened: set[str] = set()
    closed: set[str] = set()
    refused = 0
    defects: list[str] = []
    for number, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            decoded: object = json.loads(stripped)
        except ValueError:
            print(diagnostic("unparseable-line", path_text, number))
            refused += 1
            continue
        if not valid_record(decoded):
            print(diagnostic("schema-refused", path_text, number))
            refused += 1
            continue
        rec = as_object(decoded) or {}
        span_id = as_str(rec.get("span")) or ""
        if rec.get("kind") == "open":
            opened.add(span_id)
        else:
            if span_id in closed:
                defects.append(f"defect: duplicate-span line {number}")
            closed.add(span_id)
        defects.extend(f"defect: {name} line {number}" for name in record_defects(rec))
    for defect in defects:
        print(defect)
    unclosed = len(opened - closed)
    if unclosed:
        print(f"trace: {unclosed} unclosed spans (round interrupted)")
    print(
        f"trace: {len(closed)} spans, {unclosed} unclosed, "
        f"{refused} refused lines, {len(defects)} defects",
    )
    return 0


def main() -> int:
    """Dispatch the subcommand. The return value is ALWAYS 0."""
    args = sys.argv[1:]
    if not args or any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return 0
    try:
        if args[0] == "append":
            return cmd_append(args[1:])
        if args[0] == "validate":
            return cmd_validate(args[1:])
    except Exception:  # noqa: BLE001  # never fail closed, and never echo
        # Deliberately not the argv token: an unforeseen failure must not
        # turn the diagnostic into an echo of whatever was passed in.
        print(diagnostic("write-failed", "trace"))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
