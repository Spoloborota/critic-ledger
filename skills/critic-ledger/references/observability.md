Every path in this file is given relative to the skill directory ${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/ — the router SKILL.md carries the substituted absolute prefix; the paths below are relative to that directory.

## The OpenTelemetry receiver (optional)

The block below was written for the round's own trace, which no longer
exists; it is kept byte-for-byte because it is the plugin's privacy
commitment. Read "trace" as "the receiver's file" for locality and
non-upload: nothing is sent anywhere, no endpoint, no aggregation, a file
reaches another person only if its owner hands it over. Two sentences do NOT
carry over: there is no on-by-default flag any more (the receiver is
installed by an explicit act, or not at all), and the receiver's OTLP file
DOES carry identity attributes on every record — it is not free of free text
and is not shown to anyone without a review of its own.

**The privacy invariant.** Everything observability produces is a LOCAL
file the person who ran the round owns. Nothing is sent anywhere. There is
no endpoint, no opt-in-to-share, no aggregation service, and no extension
point where one could be added later without re-opening this discipline
through a round of its own. Numbers reach THIS PLUGIN's author only from
the author's own machine. A trace written on anyone else's machine stays
on that machine: the flag is on by default and any user can switch it off, and
either way nothing here moves a file anywhere — a trace reaches another
person only if its owner hands it over themselves. The trace
carries no free-text field at all — every value is an enumeration or an
anchored, length-bounded pattern — which is why it needs no sanitization
pass before it can be shown to anyone, unlike the salvaged reports.

**How to install the receiver.** The receiver writes a LOCAL file — the
plugin never opens a connection and never starts one. Two capture paths get
you that file; pick either: the bundled receiver's own JSON-lines wrapper
(`{"received_at", "signal", "body"}`) and the collector's file exporter,
which writes the bare OTLP envelope itself, one per line, with no wrapper
at all.

**(1) DEFAULT — the bundled receiver as a user service.**
`templates/otel/otel-receiver.py install --out <path outside any
repository>` installs and starts it — a LaunchAgent on macOS, a systemd
`--user` unit on Linux — so it runs whenever you log in; `status` reports
whether it is loaded and whether the file is growing, and `uninstall`
removes it. It listens on `127.0.0.1` only, needs no Docker and no
third-party dependency. `status` also prints the file's size and the age
of its last line, so a quiet receiver is not mistaken for a dead one; and
`--rotate-mb` (default 256) moves the file aside between two lines, into
`<stem>.<UTC stamp>.jsonl` beside the live one.

`serve` creates the directory `0700` and the file `0600` — and the file
sits inside your home: exclude it from backups if your backup tool
copies it, because it carries identity attributes on every record.

**(2) ALTERNATIVE — the OpenTelemetry Collector in Docker,** for anyone who
already runs Docker: `export CRITIC_LEDGER_OTEL_DIR=<path outside any
repository>` then `docker compose -f templates/otel/compose.yaml up -d`.
Both `collector.yaml` and `compose.yaml` are configuration, not code, and
the collector image is pinned to a version rather than `latest`.

Either way, set these environment variables (the three content flags
appear only as explicit zeros, and none of them is needed — the reader
never touches a prompt, a response or a tool argument):
`CLAUDE_CODE_ENABLE_TELEMETRY=1`,
`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, `OTEL_METRICS_EXPORTER=otlp`,
`OTEL_LOGS_EXPORTER=otlp`, `OTEL_TRACES_EXPORTER=otlp`,
`OTEL_EXPORTER_OTLP_PROTOCOL=http/json`,
`OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318`,
`OTEL_METRIC_EXPORT_INTERVAL=10000`, `OTEL_LOGS_EXPORT_INTERVAL=5000`,
`CLAUDE_CODE_OTEL_DIAG_STDERR=1` (exporter diagnostics to stderr, not
content; a CLI of 2.1.179 or later), and `OTEL_LOG_USER_PROMPTS=0`,
`OTEL_LOG_ASSISTANT_RESPONSES=0`, `OTEL_LOG_TOOL_DETAILS=0` — explicit
zeros, so an inherited shell environment cannot turn them on. The
environment is read at startup — restart Claude Code once, and have the
receiver or the collector up BEFORE that start.

Do not enable `rotation:` in `collector.yaml`: the file exporter's rotation
splits records at the file boundary (`opentelemetry-collector-contrib`
issue 22747) and breaks the JSON.

**Liveness.** Before you rely on the receiver, run the liveness command of
the capture path in use and expect its literal — `running` for the receiver
service on macOS, `active` on Linux, and the service name `otel-collector`
for the Docker collector; anything else means the file is not being written.

```
launchctl print gui/$(id -u)/com.critic-ledger.otel-receiver 2>/dev/null | awk '/^\tstate = /{print $3; exit}'   # macOS receiver -> running
systemctl --user is-active critic-ledger-otel-receiver.service                                           # Linux receiver -> active
docker compose -f "${CLAUDE_PLUGIN_ROOT}/skills/critic-ledger/templates/otel/compose.yaml" ps --status running --services   # Docker collector -> otel-collector
```

The plugin itself reads nothing from that file today; a reader is the
subject of a separate specification.
