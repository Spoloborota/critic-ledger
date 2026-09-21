#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Local OTLP `http/json` receiver: one request body per JSONL line.

The plugin NEVER starts this receiver: the user installs it once, on
purpose, with `install`; it listens on loopback only and opens no
outbound connection of any kind, and the plugin itself only ever READS
the file it writes.

What it is for
--------------
Level 3 of the telemetry design needs a parseable file of the
OpenTelemetry stream Claude Code exports. The `console` exporter does
not write JSON, and there is no file exporter in the product, so the
stream has to be received. Two receivers can capture it: this one
(stdlib only, no container runtime) and the OpenTelemetry Collector in
Docker (`collector.yaml` + `compose.yaml` beside this file). The two
files are NOT identical: this receiver wraps every request in the
envelope described below, while the collector's file exporter writes the
bare OTLP envelope itself, one per line, with no `v`, `received_at` or
`signal` around it. The reader accepts both and tells them apart by
shape: a wrapped line carries `body`, a bare line carries
`resourceSpans`, `resourceLogs` or `resourceMetrics` at the top level.

The file format, one line per request
-------------------------------------
    {"v": 1,
     "received_at": "<UTC ISO 8601, milliseconds, Z>",
     "signal": "logs" | "metrics" | "traces",
     "body": <the request body, parsed, exactly as it arrived>}

`v` is the envelope's own version: the reader accepts the versions it
knows and reads a line written without it as version 1.

A `Content-Encoding: gzip` body is decompressed before it is parsed. A
body that is still not JSON (a truncated payload, a corrupted compressed
stream, an encoding this receiver does not implement) is recorded as the
same line WITHOUT `body` and with `"body_raw_len": <bytes>` plus
`"encoding": <the header, or "identity">` instead: the line count stays
honest, the reason is named, and nothing unreadable is invented. Bodies
are never filtered, never rewritten and never printed — all the reading
discipline lives in the reader, not here.

The file is moved aside once it reaches `--rotate-mb` (256 by default,
0 disables it). The move is taken between two lines, under the same lock
as the write, so no line is ever split or lost across it. A rotated file
is named `<stem>.<UTC yyyymmddThhmmssZ>.jsonl` beside the live one, which
keeps name order and time order the same: a reader takes the files in
name order, the live file last.

Subcommands
-----------
    serve      --out <file> [--port 4318] [--host 127.0.0.1]
    install    --out <file> [--port 4318] [--service auto|launchd|systemd]
               [--no-load]
    uninstall  [--out <file>] [--service auto|launchd|systemd] [--no-load]
    status     [--out <file>] [--port 4318] [--service auto|launchd|systemd]
               [--no-load]

`serve` exits 2 when the host it was given is not loopback and 3 when
the port cannot be bound (already in use, or not permitted): a bind that
failed is named, never retried in silence under a service manager.

An accepted request is answered 200, an unknown path 404 and a read 405.
Two more answers exist: 413 when the declared body is larger than
`MAX_BODY_BYTES` (drained, never stored), and 500 when the file could
not be written (the reason goes to stderr and the connection stays
open, so the exporter can retry rather than lose the batch).

`serve` refuses any host that is not loopback and executes nothing at
all: every line that may run a command lives BELOW the
`# --- service management ---` marker, and the published suite holds the
file to that split. `install` writes the user service file AND loads it
through the platform's own manager (`launchctl bootstrap gui/<uid>`,
falling back to `launchctl load -w`; `systemctl --user daemon-reload`
then `systemctl --user enable --now`); `uninstall` unloads it and then
removes what was written. `--no-load` writes or removes the files and
runs no manager command at all — that is what the tests use.

`install` COPIES this script next to `--out` and points the service at
the copy: the installed plugin directory is version stamped and moves on
every refresh, so a service pointing into it would silently run a
deleted file. `uninstall` removes that copy again.

`status` reports whether the unit file is present, whether the manager
reports the service loaded, whether the port answers, whether the
`--out` file grows (two line counts one second apart, `grows` or
`idle` — a receiver with nothing to record is quiet, not dead), its size
in bytes, and how long ago its last line was received. The `--out` path
is taken from the flag or read back from the unit.

The path given to `--out` belongs OUTSIDE any repository: it is machine
local data, and it is named once, at install time.

Before changing anything here read `references/observability.md`, section "Before you change telemetry".
"""  # noqa: E501  # the pointer sentence is one unbreakable line

from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import plistlib
import shlex
import shutil
import socket
import subprocess  # service management only, see the marker below
import sys
import threading
import time
import zlib  # the exception a corrupt deflate stream raises, nothing else
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_PORT = 4318
BIND_HOST = "127.0.0.1"
IPV6_LOOPBACK = "::1"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", IPV6_LOOPBACK)

# The three OTLP HTTP paths the exporter posts to, and the signal name
# each one is recorded under. Anything else is a 404: a receiver that
# accepted unknown paths would be recording something it cannot name.
SIGNAL_PATHS = {
    "/v1/logs": "logs",
    "/v1/metrics": "metrics",
    "/v1/traces": "traces",
}
# The envelope's own version, written on every appended line. A reader
# that does not know this number reads the line as version 1.
ENVELOPE_VERSION = 1

EMPTY_JSON = b"{}"
# An OTLP export batch is kilobytes; a body past this ceiling is not
# telemetry, so it is refused rather than read into memory.
MAX_BODY_BYTES = 16 * 2**20
DRAIN_CHUNK_BYTES = 64 * 2**10
# The size at which the out file is moved aside, in mebibytes, and the
# lock that makes the move happen between two lines and not inside one.
DEFAULT_ROTATE_MB = 256.0
ROTATE_LOCK = threading.Lock()
# Every group and world bit. The out file carries identity attributes on
# every record, so a new one is created 0600 and an existing one has these
# bits taken off it at startup; no bit is ever added back.
SHARED_MODE_BITS = 0o077
STATUS_TIMEOUT_S = 0.5
# Two line counts this far apart decide `grows` against `idle`. One
# second is the shortest gap that outlives the exporter's own jitter and
# still keeps `status` an interactive command.
GROWTH_SAMPLE_S = 1.0
# How much of the tail `status` reads to find the last whole line. It
# doubles until one fits: the file itself is never read whole.
TAIL_WINDOW_BYTES = 64 * 2**10

LAUNCHD_LABEL = "com.critic-ledger.otel-receiver"
SYSTEMD_UNIT = "critic-ledger-otel-receiver.service"
# The name the installed copy of this script carries beside `--out`.
SCRIPT_COPY_NAME = "otel-receiver.py"
# The name of the log file the installed service writes, also beside it.
LOG_NAME = "otel-receiver.log"

SERVICE_AUTO = "auto"
SERVICE_LAUNCHD = "launchd"
SERVICE_SYSTEMD = "systemd"


def utc_now() -> str:
    """Return the current UTC instant as an ISO 8601 string ending in Z."""
    stamp = datetime.now(tz=UTC).isoformat(timespec="milliseconds")
    return stamp.replace("+00:00", "Z")


def rotate_if_needed(out: Path, rotate_bytes: int) -> None:
    """Move a grown out file aside, keeping its name in time order.

    The caller holds `ROTATE_LOCK`, so this runs between two appended
    lines and never inside one. The stamp has a one-second resolution:
    two rotations within the same second would land on the same name, so
    a numbered suffix is added, and only then.
    """
    if rotate_bytes <= 0:
        return
    try:
        size = out.stat().st_size
    except OSError:
        return
    if size < rotate_bytes:
        return
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    target = out.with_name(f"{out.stem}.{stamp}{out.suffix}")
    attempt = 0
    while target.exists():
        attempt += 1
        target = out.with_name(f"{out.stem}.{stamp}-{attempt}{out.suffix}")
    out.rename(target)


def tighten_existing(out: Path) -> None:
    """Clear the group and world bits of an out file that already exists.

    The mode of a NEW file is set by the syscall that creates it, so the
    writing path never revisits a file already on disk: one written before
    that rule, or left wide by a process killed between an open and a
    chmod, would keep its broader mode for the life of the file. Bits are
    only ever removed here, never added, so a file deliberately made
    read-only stays read-only, and an absent file is simply nothing to do.
    """
    try:
        mode = out.stat().st_mode & 0o777
    except OSError:
        return
    if mode & SHARED_MODE_BITS:
        out.chmod(mode & ~SHARED_MODE_BITS)


def append_record(out: Path, record: dict[str, object], rotate_bytes: int = 0) -> None:
    """Append one JSON object to the output file as a single line."""
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    # One lock over both halves: the size is judged and the line is
    # written without another thread appending in between, which is what
    # keeps every line whole on either side of a rotation.
    with ROTATE_LOCK:
        rotate_if_needed(out, rotate_bytes)
        # A rotation renames the old file away, so the next line creates a
        # new one: the mode is carried by the CREATING syscall itself, not
        # by a `chmod` after the write. Between those two calls a killed
        # process used to leave the identity-carrying file at the umask's
        # wider default, and nothing ever narrowed it again.
        descriptor = os.open(out, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def make_handler(out: Path, rotate_bytes: int = 0) -> type[BaseHTTPRequestHandler]:
    """Build the request handler bound to one output file."""

    class Handler(BaseHTTPRequestHandler):
        """One accepted request, one appended line, one empty 200."""

        protocol_version = "HTTP/1.1"
        server_version = "critic-ledger-otel-receiver"
        sys_version = ""

        def reply(self, status: HTTPStatus, payload: bytes = EMPTY_JSON) -> None:
            """Answer with a JSON body of a known length."""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def signal_of(self) -> str | None:
            """Return the signal name of the request path, or None."""
            return SIGNAL_PATHS.get(self.path.split("?")[0])

        def append(self, record: dict[str, object]) -> bool:
            """Append one record; answer 500 instead of dropping the caller.

            A file that cannot be written is the receiver's problem, not
            the exporter's: it is told so, over a connection that stays
            open, and the reason is printed once on stderr.
            """
            try:
                append_record(out, record, rotate_bytes)
            except OSError as exc:
                print(
                    f"write failed: {exc.strerror or exc}", file=sys.stderr, flush=True
                )
                self.reply(HTTPStatus.INTERNAL_SERVER_ERROR)
                return False
            return True

        def do_POST(self) -> None:  # http.server dispatch name
            """Record one exported body and acknowledge it."""
            # The body is drained BEFORE the path is judged: an unread
            # body would be read as the next request on a kept-alive
            # connection, and the exporter keeps its connections.
            declared = self.headers.get("Content-Length")
            try:
                length = int(declared) if declared else 0
            except ValueError:
                length = 0
            if length > MAX_BODY_BYTES:
                # Drained in pieces, never held whole: the connection
                # must stay usable, and an oversized body is refused
                # without ever being kept in memory.
                left = length
                while left > 0:
                    chunk = self.rfile.read(min(DRAIN_CHUNK_BYTES, left))
                    if not chunk:
                        break
                    left -= len(chunk)
                self.reply(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            raw = self.rfile.read(length) if length > 0 else b""
            declared_encoding = self.headers.get("Content-Encoding")
            encoding = declared_encoding.strip() if declared_encoding else "identity"
            transfer = self.headers.get("Transfer-Encoding") or ""
            chunked = "chunked" in transfer.lower() and not declared
            signal = self.signal_of()
            if signal is None:
                self.reply(HTTPStatus.NOT_FOUND)
                return
            record: dict[str, object] = {
                "v": ENVELOPE_VERSION,
                "received_at": utc_now(),
                "signal": signal,
            }
            if chunked:
                # Chunked framing is not implemented here: without a
                # Content-Length nothing was read, and the line says so
                # by name rather than looking like an empty body.
                record["body_raw_len"] = 0
                record["encoding"] = "chunked-unsupported"
                if not self.append(record):
                    return
                self.reply(HTTPStatus.OK)
                return
            body = raw
            if encoding.lower() == "gzip":
                try:
                    body = gzip.decompress(raw)
                except (OSError, EOFError, zlib.error):
                    # A valid gzip header over a corrupted deflate stream
                    # raises `zlib.error`, which is NOT an `OSError`: left
                    # uncaught it would tear the connection down and lose
                    # the batch. The raw body falls through to the record
                    # below and is counted like any other unreadable one.
                    body = raw
            try:
                record["body"] = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Never echo, never guess: the length and the declared
                # encoding are the whole record of a body this receiver
                # could not read.
                record["body_raw_len"] = len(raw)
                record["encoding"] = encoding
            if not self.append(record):
                return
            self.reply(HTTPStatus.OK)

        def do_GET(self) -> None:  # http.server dispatch name
            """Refuse a read: the receiver has nothing to serve back."""
            if self.signal_of() is not None:
                self.reply(HTTPStatus.METHOD_NOT_ALLOWED)
                return
            self.reply(HTTPStatus.NOT_FOUND)

    return Handler


class LoopbackServerV4(ThreadingHTTPServer):
    """The IPv4 loopback server: `127.0.0.1` and `localhost`."""

    address_family = socket.AF_INET


class LoopbackServerV6(ThreadingHTTPServer):
    """The IPv6 loopback server: `::1`, which AF_INET cannot bind."""

    address_family = socket.AF_INET6


def server_class(host: str) -> type[ThreadingHTTPServer]:
    """Return the server class whose address family can bind `host`.

    Binding the accepted host literally is the point: `::1` used to be
    accepted and then silently served over IPv4.
    """
    if host == IPV6_LOOPBACK:
        return LoopbackServerV6
    return LoopbackServerV4


def serve(out: Path, host: str, port: int, rotate_bytes: int = 0) -> int:
    """Listen on loopback and append every accepted body to `out`."""
    if host not in LOOPBACK_HOSTS:
        print(f"refused: host {host} is not loopback; use {BIND_HOST}")
        return 2
    out = out.expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    # `mkdir`'s own mode is masked by the umask, so the directory is set
    # explicitly: every record carries identity attributes.
    out.parent.chmod(0o700)
    # A file that already exists is narrowed once, here: the mode of a NEW
    # file belongs to the syscall that creates it, so nothing on the
    # writing path ever revisits a file written before this rule.
    tighten_existing(out)
    try:
        server = server_class(host)((host, port), make_handler(out, rotate_bytes))
    except OSError as exc:
        # A bind that failed is a fact worth printing: under a service
        # manager the alternative is a process that dies every few
        # seconds and leaves no reason anywhere.
        print(f"refused: cannot bind {host}:{port}: {exc.strerror or exc}")
        return 3
    bound = int(server.socket.getsockname()[1])
    print(f"listening on http://{host}:{bound} writing {out}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    finally:
        server.server_close()
    return 0


def resolve_interpreter(python: Path | None = None) -> Path | None:
    """Return the interpreter the installed service should run, or None.

    `sys.executable` is taken as it stands, WITHOUT `.resolve()`: the
    symlink a package manager keeps (`.../bin/python3.14`) survives an
    upgrade, while the file it points at today lives in a directory
    stamped with the exact version and is deleted by the next one.

    When the running interpreter is ITSELF inside such a directory the
    answer is None and the caller refuses: the correct symlink is a
    choice only the user can make. Only the literal `Cellar` layout is
    recognised here; nothing else is guessed at, and no lookup of the
    environment's PATH is attempted.
    """
    if python is not None:
        return python
    candidate = Path(sys.executable)
    if "Cellar" in candidate.parts:
        return None
    return candidate


# --- service management ---
#
# Everything BELOW this marker may run a command; nothing above it ever
# does. `subprocess` is imported for `install`, `uninstall` and `status`
# only — the receiving path (`serve`, `make_handler` and the handler)
# executes nothing at all, and `plugin/tests/unit/test_payload_invariants.py`
# holds this file to that split by reading the marker line.


def run_command(argv: list[str]) -> int:
    """Run one service-manager command, printing it and its exit code.

    Never fatal: a manager that is absent or refuses is reported, not
    raised, because `status` must answer even on a machine where the
    service was never installed.
    """
    print(f"    $ {' '.join(shlex.quote(part) for part in argv)}")
    try:
        completed = subprocess.run(  # noqa: S603 - list argv, no shell
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as error:
        print(f"    ! not run: {error}")
        return 127
    for stream in (completed.stdout, completed.stderr):
        for line in stream.splitlines():
            print(f"    | {line}")
    print(f"    exit {completed.returncode}")
    return completed.returncode


def service_kind(choice: str) -> str:
    """Resolve `auto` to the user-service manager of this machine."""
    if choice != SERVICE_AUTO:
        return choice
    if platform.system().lower() == "darwin":
        return SERVICE_LAUNCHD
    return SERVICE_SYSTEMD


def unit_path(kind: str) -> Path:
    """Return the path of the user-service file for one manager."""
    if kind == SERVICE_LAUNCHD:
        return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
    return Path.home() / ".config" / "systemd" / "user" / SYSTEMD_UNIT


def log_path(out: Path) -> Path:
    """Return the log file of the installed service, beside `--out`.

    One file carries both streams: the service writes little, and a
    crash is easier to read next to the lines that preceded it. The path
    is derived from `--out` and from nothing else.
    """
    return out.parent / LOG_NAME


def launchd_plist(
    python: Path,
    script: Path,
    out: Path,
    port: int,
    rotate_mb: float = DEFAULT_ROTATE_MB,
) -> bytes:
    """Build the LaunchAgent property list, started at login."""
    plist: dict[str, object] = {
        "Label": LAUNCHD_LABEL,
        "ProgramArguments": [
            str(python),
            str(script),
            "serve",
            "--out",
            str(out),
            "--port",
            str(port),
            "--rotate-mb",
            str(rotate_mb),
        ],
        "RunAtLoad": True,
        # Restart after a crash, stay down after a clean exit: the plain
        # `True` form would restart a receiver that refused to start,
        # every ThrottleInterval seconds, for as long as the user is
        # logged in.
        "KeepAlive": {"Crashed": True, "SuccessfulExit": False},
        "ThrottleInterval": 10,
        "ProcessType": "Background",
        # Both streams go to one file beside the data: a traceback that
        # goes nowhere leaves a file that merely stopped growing.
        "StandardOutPath": str(log_path(out)),
        "StandardErrorPath": str(log_path(out)),
    }
    return plistlib.dumps(plist)


def systemd_unit(
    python: Path,
    script: Path,
    out: Path,
    port: int,
    rotate_mb: float = DEFAULT_ROTATE_MB,
) -> str:
    """Build the systemd user unit, started at login."""
    # Every element is quoted: launchd takes a list, systemd takes one
    # line, and an unquoted space in a path produces an invalid unit.
    parts = [
        str(python),
        str(script),
        "serve",
        "--out",
        str(out),
        "--port",
        str(port),
        "--rotate-mb",
        str(rotate_mb),
    ]
    command = " ".join(shlex.quote(part) for part in parts)
    log = log_path(out)
    # `on-failure`, not `always`: after a clean exit the service stays
    # down, which is the same rule the launchd KeepAlive dictionary
    # states, and a refused start is not retried every ten seconds
    # forever. Both streams append to one file beside the data.
    return (
        "[Unit]\n"
        "Description=critic-ledger local OTLP receiver (loopback only)\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={command}\n"
        "Restart=on-failure\n"
        "RestartSec=10\n"
        f"StandardOutput=append:{log}\n"
        f"StandardError=append:{log}\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def script_copy_path(out: Path) -> Path:
    """Return the copy of this script the installed service runs.

    It lives beside `--out`, outside every repository. The installed
    plugin directory is version stamped and is replaced on every
    refresh, so a unit pointing into it would run a deleted file.
    """
    return out.parent / SCRIPT_COPY_NAME


def unit_argv(target: Path) -> list[str]:
    """Return the argv an installed unit runs, or an empty list."""
    if not target.is_file():
        return []
    if target.suffix == ".plist":
        try:
            plist = plistlib.loads(target.read_bytes())
        except (OSError, ValueError):
            return []
        argv = plist.get("ProgramArguments")
        if not isinstance(argv, list):
            return []
        return [str(item) for item in argv]
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return []
    prefix = "ExecStart="
    for line in text.splitlines():
        if line.startswith(prefix):
            return shlex.split(line[len(prefix) :])
    return []


def unit_option(argv: list[str], flag: str) -> str | None:
    """Return the value that follows `flag` in an installed unit's argv."""
    if flag in argv:
        index = argv.index(flag)
        if index + 1 < len(argv):
            return argv[index + 1]
    return None


def load_service(kind: str, target: Path) -> int:
    """Load the freshly written user service through its own manager."""
    if kind == SERVICE_LAUNCHD:
        domain = f"gui/{os.getuid()}"
        code = run_command(["launchctl", "bootstrap", domain, str(target)])
        if code != 0:
            print("    bootstrap refused; trying the legacy loader")
            code = run_command(["launchctl", "load", "-w", str(target)])
        return code
    run_command(["systemctl", "--user", "daemon-reload"])
    return run_command(["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT])


def unload_service(kind: str, target: Path) -> int:
    """Unload the user service before its file is removed."""
    if kind == SERVICE_LAUNCHD:
        domain = f"gui/{os.getuid()}"
        return run_command(["launchctl", "bootout", domain, str(target)])
    return run_command(["systemctl", "--user", "disable", "--now", SYSTEMD_UNIT])


def service_loaded(kind: str) -> bool:
    """Return whether the manager reports the service as loaded."""
    if kind == SERVICE_LAUNCHD:
        return run_command(["launchctl", "list", LAUNCHD_LABEL]) == 0
    return run_command(["systemctl", "--user", "is-active", SYSTEMD_UNIT]) == 0


def install(  # noqa: PLR0913  # one argument per unit field the human may set
    out: Path,
    port: int,
    choice: str,
    *,
    load: bool,
    python: Path | None = None,
    rotate_mb: float = DEFAULT_ROTATE_MB,
) -> int:
    """Write the user service file, then load it through its manager."""
    kind = service_kind(choice)
    interpreter = resolve_interpreter(python)
    if interpreter is None:
        print(
            "install: interpreter under a versioned directory - "
            "pass --python <symlink path>"
        )
        return 2
    print(f"interpreter: {interpreter}")
    out = out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve()
    script = script_copy_path(out)
    if script == source:
        print(f"already in place {script}")
    else:
        shutil.copyfile(source, script)
        print(f"copied {source}")
        print(f"    -> {script}")
    target = unit_path(kind)
    target.parent.mkdir(parents=True, exist_ok=True)
    if kind == SERVICE_LAUNCHD:
        target.write_bytes(launchd_plist(interpreter, script, out, port, rotate_mb))
    else:
        target.write_text(
            systemd_unit(interpreter, script, out, port, rotate_mb),
            encoding="utf-8",
        )
    print(f"written {target}")
    print(f"log: {log_path(out)}")
    if not load:
        print("--no-load: the service file is written and NOT loaded")
        return 0
    print("loading the service:")
    load_service(kind, target)
    return 0


def uninstall(choice: str, out: Path | None, *, load: bool) -> int:
    """Unload the user service, then remove the unit and the copy."""
    kind = service_kind(choice)
    target = unit_path(kind)
    argv = unit_argv(target)
    if load:
        print("unloading the service:")
        unload_service(kind, target)
    else:
        print("--no-load: the service is NOT unloaded")
    copy: Path | None = None
    if out is not None:
        copy = script_copy_path(out.expanduser().resolve())
    elif len(argv) > 1:
        copy = Path(argv[1])
    if target.exists():
        target.unlink()
        print(f"removed {target}")
    else:
        print(f"absent {target}")
    if (
        copy is not None
        and copy.name == SCRIPT_COPY_NAME
        and copy.is_file()
        and copy != Path(__file__).resolve()
    ):
        copy.unlink()
        print(f"removed {copy}")
    return 0


def port_answers(port: int) -> bool:
    """Return whether something accepts a loopback connection on `port`."""
    try:
        with socket.create_connection((BIND_HOST, port), STATUS_TIMEOUT_S):
            return True
    except OSError:
        return False


def line_count(path: Path) -> int | None:
    """Return the number of lines in `path`, or None if it is unreadable."""
    try:
        with path.open("rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return None


def growth(path: Path) -> str:
    """Sample the line count twice, a second apart, and name the verdict."""
    first = line_count(path)
    if first is None:
        return "absent"
    time.sleep(GROWTH_SAMPLE_S)
    second = line_count(path)
    if second is None:
        return "absent"
    # `idle`, not `static`: a receiver with nothing to record writes
    # nothing, and one quiet second says nothing about its health.
    verdict = "grows" if second > first else "idle"
    return f"{verdict} ({first} -> {second} lines)"


def last_line_age_s(path: Path) -> float | None:
    """Return how many seconds ago the last line was received, or None.

    The file may be hundreds of megabytes, so only its tail is read:
    the seek window doubles until a whole line is inside it. Exactly one
    key of the parsed object is looked at, `received_at`; nothing else
    is extracted from it, and any failure at all answers None.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size == 0:
        return None
    window = TAIL_WINDOW_BYTES
    last = ""
    try:
        with path.open("rb") as handle:
            while True:
                start = max(0, size - window)
                handle.seek(start)
                chunk = handle.read(size - start)
                rows = [row for row in chunk.split(b"\n") if row.strip()]
                if not rows:
                    return None
                if len(rows) > 1 or start == 0:
                    last = rows[-1].decode("utf-8")
                    break
                if window >= size:
                    return None
                window *= 2
    except (OSError, UnicodeDecodeError):
        return None
    try:
        received_at = json.loads(last)["received_at"]
        stamp = datetime.fromisoformat(str(received_at))
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        return None
    if stamp.tzinfo is None:
        return None
    return (datetime.now(tz=UTC) - stamp).total_seconds()


def status(port: int, choice: str, out: Path | None, *, load: bool) -> int:
    """Report the unit, its load state, the port and the file's growth."""
    kind = service_kind(choice)
    target = unit_path(kind)
    present = "installed" if target.exists() else "absent"
    print(f"service {kind}: {present} {target}")
    argv = unit_argv(target)
    if load:
        print("asking the service manager:")
        print(f"loaded: {'yes' if service_loaded(kind) else 'no'}")
    else:
        print("loaded: not checked (--no-load)")
    answers = "answers" if port_answers(port) else "silent"
    print(f"port {BIND_HOST}:{port}: {answers}")
    recorded = unit_option(argv, "--out")
    if out is not None:
        chosen: Path | None = out.expanduser()
    elif recorded is not None:
        chosen = Path(recorded)
    else:
        chosen = None
    if chosen is None:
        print("out: unknown (no --out given, none recorded in the unit)")
        return 0
    print(f"out {chosen}: {growth(chosen)}")
    try:
        size = chosen.stat().st_size
    except OSError:
        print("size: n/a")
    else:
        print(f"size: {size} bytes")
    age = last_line_age_s(chosen)
    print("last line age: n/a" if age is None else f"last line age: {age:.1f} s")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser of the four subcommands."""
    parser = argparse.ArgumentParser(
        prog="otel-receiver.py",
        description="Local OTLP http/json receiver, loopback only.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    serve_parser = subcommands.add_parser("serve", help="run the receiver")
    serve_parser.add_argument("--out", required=True, help="JSONL file to append to")
    serve_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_parser.add_argument("--host", default=BIND_HOST)
    rotate_help = (
        "rotate the out file aside at this size in MB, between lines; 0 disables"
    )
    serve_parser.add_argument(
        "--rotate-mb", type=float, default=DEFAULT_ROTATE_MB, help=rotate_help
    )

    no_load_help = "write or remove the files and run no manager command"

    install_parser = subcommands.add_parser(
        "install", help="write the user service file and load it"
    )
    install_parser.add_argument("--out", required=True)
    install_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    install_parser.add_argument(
        "--service",
        choices=(SERVICE_AUTO, SERVICE_LAUNCHD, SERVICE_SYSTEMD),
        default=SERVICE_AUTO,
    )
    install_parser.add_argument(
        "--rotate-mb", type=float, default=DEFAULT_ROTATE_MB, help=rotate_help
    )
    install_parser.add_argument(
        "--python",
        type=Path,
        default=None,
        help="interpreter to run the service; give the symlink, "
        "not the versioned target",
    )
    install_parser.add_argument("--no-load", action="store_true", help=no_load_help)

    uninstall_parser = subcommands.add_parser(
        "uninstall", help="unload the user service and remove its files"
    )
    uninstall_parser.add_argument("--out", default=None)
    uninstall_parser.add_argument(
        "--service",
        choices=(SERVICE_AUTO, SERVICE_LAUNCHD, SERVICE_SYSTEMD),
        default=SERVICE_AUTO,
    )
    uninstall_parser.add_argument("--no-load", action="store_true", help=no_load_help)

    status_parser = subcommands.add_parser(
        "status", help="report the unit, its load state, the port and the file"
    )
    status_parser.add_argument("--out", default=None)
    status_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    status_parser.add_argument(
        "--service",
        choices=(SERVICE_AUTO, SERVICE_LAUNCHD, SERVICE_SYSTEMD),
        default=SERVICE_AUTO,
    )
    status_parser.add_argument("--no-load", action="store_true", help=no_load_help)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one subcommand and return its exit code."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "serve":
        rotate_mb = float(args.rotate_mb)
        rotate_bytes = int(rotate_mb * 2**20) if rotate_mb > 0 else 0
        return serve(Path(args.out), str(args.host), int(args.port), rotate_bytes)
    load = not bool(args.no_load)
    chosen = Path(args.out) if args.out is not None else None
    if args.command == "install":
        return install(
            Path(args.out),
            int(args.port),
            str(args.service),
            load=load,
            python=Path(args.python) if args.python is not None else None,
            rotate_mb=float(args.rotate_mb),
        )
    if args.command == "uninstall":
        return uninstall(str(args.service), chosen, load=load)
    return status(int(args.port), str(args.service), chosen, load=load)


if __name__ == "__main__":
    sys.exit(main())
