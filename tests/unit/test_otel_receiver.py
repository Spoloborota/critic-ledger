"""Characterization tests for templates/otel/otel-receiver.py.

The receiver is the only shipped script that opens a listening socket, so
these cases pin exactly the properties that make that acceptable: it binds
loopback and refuses anything else, it appends one line per accepted body
and invents nothing for a body it cannot read, and `install` writes a user
service file AND loads it through the platform's own manager — the two
managers are stubbed on PATH, so the difference between "executed" and
"printed" is a marker file rather than a claim. `--no-load` is the switch
that keeps a test from touching the real managers, and its own case
asserts the marker stays absent.

Everything lives under `tmp_path`, and `HOME` is redirected there by
`hardened_env`, so the service files a run writes are thrown away with the
temporary directory.
"""

from __future__ import annotations

import gzip
import http.client
import importlib.util
import json
import os
import plistlib
import re
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta

import pytest

from conftest import hardened_env

SCRIPT = "otel/otel-receiver.py"
LISTEN_RE = re.compile(r"127\.0\.0\.1:(\d+)")
# The name a rotated file carries: the live stem, then the UTC instant of
# the rotation, then the same suffix.
# A second rotation within the same second takes a `-<n>` suffix rather than
# overwriting the first: the stamp is a second, the suffix keeps the name unique.
ROTATED_RE = re.compile(r"^otel\.\d{8}T\d{6}Z(?:-\d+)?\.jsonl$")
LOOPBACK = "127.0.0.1"

HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_TOO_LARGE = 413
HTTP_SERVER_ERROR = 500

# The two service managers `install`/`uninstall`/`status` drive. A stub of
# each is put on PATH and leaves a marker file when it runs, so a case can
# assert either half: that the loader WAS executed, or that `--no-load`
# left the managers alone.
SERVICE_COMMANDS = ("launchctl", "systemctl")


@pytest.fixture
def script_path(templates_dir):
    """The receiver, resolved under the repository's own templates directory.

    It ships among the templates rather than the scripts, and a redirected
    scripts directory does not move the templates.
    """
    path = templates_dir / SCRIPT
    assert path.is_file(), path
    return path


@pytest.fixture
def receiver_module(script_path):
    """Import the receiver as a module, the one case subprocess cannot cover.

    Every other case here drives the script through subprocess, which is
    the right shape for a program. The interpreter the installer records
    is read from `sys.executable` OF THE RUNNING PROCESS, and a child
    process reports its own — so no subprocess run can substitute a
    prepared interpreter path. Importing is safe: the script defines
    names at import time and does nothing else, all work happens under
    `main()`, which is not called here.
    """
    spec = importlib.util.spec_from_file_location(
        "otel_receiver_under_test", script_path
    )
    assert spec is not None and spec.loader is not None, script_path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stub_bin(tmp_path):
    """A PATH directory whose `launchctl`/`systemctl` only leave a marker."""
    stub_dir = tmp_path / "stub-bin"
    stub_dir.mkdir()
    marker = tmp_path / "service-command-was-run"
    for name in SERVICE_COMMANDS:
        stub = stub_dir / name
        stub.write_text(
            "#!/bin/sh\n"
            f'echo "$0 $@" >> "{marker}"\n'
            "exit 0\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
    return stub_dir, marker


@pytest.fixture
def run_receiver(script_path, sandbox_home, tmp_path, stub_bin):
    """Invoke the receiver once and return the CompletedProcess."""
    stub_dir, _marker = stub_bin
    env = hardened_env(sandbox_home)
    env["PATH"] = f"{stub_dir}:{env['PATH']}"
    cwd = tmp_path / "cwd"
    cwd.mkdir(exist_ok=True)

    def _run(*args: object) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(script_path), *map(str, args)]
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    return _run


@pytest.fixture
def serving(script_path, sandbox_home, tmp_path):
    """Start `serve` on an ephemeral port; yield its port and output file."""
    env = hardened_env(sandbox_home)
    started = []

    def _start(name: str = "otel.jsonl", *extra: str):
        out = tmp_path / name
        proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            [
                sys.executable,
                str(script_path),
                "serve",
                "--out",
                str(out),
                *extra,
                "--port",
                "0",
            ],
            cwd=str(tmp_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        started.append(proc)
        first = proc.stdout.readline() if proc.stdout is not None else ""
        match = LISTEN_RE.search(first)
        assert match, f"no listening line: {first!r}"
        return int(match.group(1)), out

    # The processes are reachable by name so a case that needs the
    # receiver's own stderr can stop it and read what it printed.
    _start.started = started
    yield _start

    for proc in started:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            proc.kill()


def post(port: int, path: str, body: bytes, headers: dict | None = None) -> int:
    """POST one body to the receiver and return the status code."""
    conn = http.client.HTTPConnection(LOOPBACK, port, timeout=10)
    sent = {"Content-Type": "application/json"}
    sent.update(headers or {})
    try:
        conn.request("POST", path, body=body, headers=sent)
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


def post_on(conn, path: str, body: bytes) -> int:
    """POST one body over an ALREADY OPEN connection and keep it open."""
    conn.request(
        "POST", path, body=body, headers={"Content-Type": "application/json"}
    )
    response = conn.getresponse()
    response.read()
    return response.status


def get(port: int, path: str) -> int:
    """GET one path from the receiver and return the status code."""
    conn = http.client.HTTPConnection(LOOPBACK, port, timeout=10)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


def lines_of(path, expected: int) -> list[dict]:
    """Read the JSONL file once it holds `expected` lines."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            rows = [line for line in text.splitlines() if line.strip()]
            if len(rows) >= expected:
                return [json.loads(line) for line in rows]
        time.sleep(0.05)
    text = path.read_text(encoding="utf-8") if path.exists() else "<absent>"
    raise AssertionError(f"expected {expected} line(s), file holds: {text!r}")


# --- the three signals -----------------------------------------------------


def test_each_signal_path_appends_one_parsed_line(serving):
    """Three POSTs, three lines, each naming its own signal."""
    port, out = serving()
    bodies = {
        "/v1/logs": {"resourceLogs": [{"n": 1}]},
        "/v1/metrics": {"resourceMetrics": [{"n": 2}]},
        "/v1/traces": {"resourceSpans": [{"n": 3}]},
    }
    for path, body in bodies.items():
        assert post(port, path, json.dumps(body).encode("utf-8")) == HTTP_OK

    rows = lines_of(out, 3)
    assert [row["signal"] for row in rows] == ["logs", "metrics", "traces"]
    assert [row["body"] for row in rows] == list(bodies.values())
    for row in rows:
        assert set(row) == {"v", "received_at", "signal", "body"}
        assert row["received_at"].endswith("Z")


def test_every_appended_line_carries_the_envelope_version(serving):
    """K7c: every receiver line is stamped `"v": 1`, whichever signal it names."""
    port, out = serving()
    body = {"resourceSpans": [{"n": 1}]}
    assert post(port, "/v1/traces", json.dumps(body).encode("utf-8")) == HTTP_OK

    (row,) = lines_of(out, 1)
    assert row["v"] == 1
    assert set(row) == {"v", "received_at", "signal", "body"}

    payload = b"\x1f\x8b not json at all"
    assert post(port, "/v1/logs", payload) == HTTP_OK
    (not_json_row,) = lines_of(out, 2)[1:]
    assert not_json_row["v"] == 1


def test_a_body_that_is_not_json_is_recorded_by_length_only(serving):
    """No content is invented for a body the receiver could not read."""
    port, out = serving()
    payload = b"\x1f\x8b not json at all"
    assert post(port, "/v1/traces", payload) == HTTP_OK

    (row,) = lines_of(out, 1)
    assert row["signal"] == "traces"
    assert "body" not in row
    assert row["body_raw_len"] == len(payload)


def test_a_gzip_body_is_decompressed_before_it_is_parsed(serving):
    """A compressed export is data, not an unreadable blob."""
    port, out = serving()
    body = {"resourceSpans": [{"n": 7}]}
    payload = gzip.compress(json.dumps(body).encode("utf-8"))
    assert post(port, "/v1/traces", payload,
                {"Content-Encoding": "gzip"}) == HTTP_OK

    (row,) = lines_of(out, 1)
    assert row["body"] == body
    assert set(row) == {"v", "received_at", "signal", "body"}


def test_an_unreadable_body_names_the_encoding_it_declared(serving):
    """The fallback line says WHY it could not be read, not just how long."""
    port, out = serving()
    payload = b"\x1f\x8b not gzip either"
    assert post(port, "/v1/logs", payload,
                {"Content-Encoding": "gzip"}) == HTTP_OK

    (row,) = lines_of(out, 1)
    assert "body" not in row
    assert row["body_raw_len"] == len(payload)
    assert row["encoding"] == "gzip"


def test_a_corrupt_gzip_stream_is_recorded_like_any_unreadable_body(serving):
    """A valid gzip header over a corrupt stream is a line, not a traceback.

    Decompression fails HERE with `zlib.error`, which is not an `OSError`
    and not the `BadGzipFile` a broken header raises: uncaught, it would
    leave the exporter with a torn connection, no answer and no line at
    all, which is the one thing the receiver promises never to do.
    """
    port, out = serving()
    # The first ten bytes of a real gzip stream are its whole header, so
    # the magic and the deflate method byte are genuine and only the
    # compressed payload behind them is garbage.
    valid = gzip.compress(json.dumps({"resourceSpans": [{"n": 1}]}).encode("utf-8"))
    payload = valid[:10] + b"not a deflate stream at all"
    assert post(port, "/v1/traces", payload,
                {"Content-Encoding": "gzip"}) == HTTP_OK

    (row,) = lines_of(out, 1)
    assert "body" not in row
    assert row["body_raw_len"] == len(payload)
    assert row["encoding"] == "gzip"

    proc = serving.started[-1]
    proc.terminate()
    _stdout, stderr = proc.communicate(timeout=10)
    assert "Traceback" not in stderr, stderr


def test_an_unknown_path_is_a_404_and_writes_nothing(serving):
    """Only the three OTLP paths are recorded at all."""
    port, out = serving()
    assert post(port, "/v1/something-else", b"{}") == HTTP_NOT_FOUND
    assert get(port, "/") == HTTP_NOT_FOUND
    assert post(port, "/v1/traces", b"{}") == HTTP_OK
    (row,) = lines_of(out, 1)
    assert row["signal"] == "traces"


def test_a_get_on_a_signal_path_is_refused(serving):
    """The receiver writes; it serves nothing back."""
    port, out = serving()
    assert get(port, "/v1/traces") == HTTP_METHOD_NOT_ALLOWED
    assert not out.exists() or out.read_text(encoding="utf-8") == ""


def test_the_out_file_is_created_0600(serving):
    """The data is readable by its owner and by nobody else.

    Every record carries identity attributes, so the file is private and
    so is the directory the receiver makes for it. The modes are set
    explicitly rather than left to the umask; the bits themselves are a
    POSIX property and mean nothing on a platform without them.
    """
    port, out = serving("sub/otel.jsonl")
    assert post(port, "/v1/traces", b"{}") == HTTP_OK
    lines_of(out, 1)

    assert out.stat().st_mode & 0o777 == 0o600
    assert out.parent.stat().st_mode & 0o777 == 0o700


def test_a_pre_existing_out_file_is_narrowed_to_0600_at_serve_start(
    serving, tmp_path
):
    """A file left world-readable by an earlier run does not stay that way.

    The mode of a new file is now carried by the syscall that creates it,
    so nothing on the writing path ever looks at a file that already
    exists: one created before that rule, or left wide by a process killed
    between an open and a chmod, would keep the umask's default for the
    life of the file. `serve` narrows it once, at startup, and the next
    appended line lands in a private file.
    """
    out = tmp_path / "otel.jsonl"
    out.write_text("", encoding="utf-8")
    out.chmod(0o644)

    port, served = serving()
    assert served == out
    assert post(port, "/v1/traces", b"{}") == HTTP_OK
    lines_of(out, 1)

    assert out.stat().st_mode & 0o777 == 0o600


# --- a write that fails, and a body that is too large ----------------------


def test_a_write_failure_answers_500_and_keeps_the_connection(serving, tmp_path):
    """A file it cannot write to is answered, not hung up on.

    The exporter keeps its connections: a dropped one costs it the whole
    batch and tells it nothing. Note the mode is only honoured for a
    non-root run, so the case is skipped as root.

    The file is created 0o444 and `serve` narrows an existing out file at
    startup, so the mode in force during the POSTs below is 0o400: the
    startup only ever REMOVES group and world bits, and the owner's write
    bit was never there. Either way the file is unwritable, which is what
    this case is about.
    """
    if os.geteuid() == 0:
        pytest.skip("a read-only mode does not stop root from writing")
    blocked = tmp_path / "readonly.jsonl"
    blocked.write_text("", encoding="utf-8")
    blocked.chmod(0o444)
    port, _out = serving("readonly.jsonl")
    body = json.dumps({"resourceSpans": [{"n": 1}]}).encode("utf-8")

    conn = http.client.HTTPConnection(LOOPBACK, port, timeout=10)
    try:
        assert post_on(conn, "/v1/traces", body) == HTTP_SERVER_ERROR
        assert post_on(conn, "/v1/traces", body) == HTTP_SERVER_ERROR
    finally:
        conn.close()

    proc = serving.started[-1]
    proc.terminate()
    _stdout, stderr = proc.communicate(timeout=10)
    assert "write failed:" in stderr


def test_a_body_over_the_limit_is_413(serving):
    """A body larger than the receiver's ceiling is refused and not stored.

    The literal is the receiver's own `MAX_BODY_BYTES`, sixteen mebibytes.
    """
    port, out = serving()
    oversized = 16 * 2**20 + 1
    before = len(out.read_text(encoding="utf-8").splitlines()) if out.exists() else 0

    assert post(port, "/v1/traces", b"x" * oversized) == HTTP_TOO_LARGE

    after = len(out.read_text(encoding="utf-8").splitlines()) if out.exists() else 0
    assert after == before


# --- rotation --------------------------------------------------------------


def test_rotation_happens_between_lines_and_keeps_every_line_whole(
    serving, tmp_path
):
    """A rotation is taken BETWEEN two lines, under the write's own lock.

    Nothing here runs on a timer: the size is looked at while the lock
    that appends is already held, so no line can ever be split across the
    old file and the new one, and no line can be lost between them.
    """
    port, out = serving("otel.jsonl", "--rotate-mb", "0.001")
    for index in range(20):
        body = {"resourceSpans": [{"n": index, "pad": "x" * 100}]}
        assert post(port, "/v1/traces", json.dumps(body).encode("utf-8")) == HTTP_OK

    deadline = time.monotonic() + 10
    rows: list[str] = []
    while time.monotonic() < deadline:
        files = sorted(tmp_path.glob("otel*.jsonl"))
        rows = [
            line
            for path in files
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(rows) >= 20:
            break
        time.sleep(0.05)

    files = sorted(tmp_path.glob("otel*.jsonl"))
    assert len(files) >= 2, [path.name for path in files]
    assert len(rows) == 20, rows
    for line in rows:
        json.loads(line)
    assert out.exists()
    rotated = [path.name for path in files if path != out]
    for name in rotated:
        assert ROTATED_RE.match(name), name


def test_rotate_mb_zero_disables_rotation(serving, tmp_path):
    """Zero means one file forever: the setting can be turned off."""
    port, out = serving("otel.jsonl", "--rotate-mb", "0")
    for index in range(20):
        body = {"resourceSpans": [{"n": index, "pad": "x" * 100}]}
        assert post(port, "/v1/traces", json.dumps(body).encode("utf-8")) == HTTP_OK
    lines_of(out, 20)

    files = sorted(tmp_path.glob("otel*.jsonl"))
    assert [path.name for path in files] == ["otel.jsonl"]
    assert len(out.read_text(encoding="utf-8").splitlines()) == 20


# --- loopback only ---------------------------------------------------------


def test_a_host_that_is_not_loopback_is_refused(run_receiver, tmp_path):
    """The refusal is the mechanism, not a warning in a comment."""
    out = tmp_path / "never-written.jsonl"
    result = run_receiver("serve", "--out", str(out), "--host", "0.0.0.0")
    assert result.returncode != 0, result.stdout
    assert "refused" in result.stdout
    assert not out.exists()


def test_a_busy_port_is_refused_with_exit_3(run_receiver, tmp_path):
    """A port already in use is named and refused, never retried in silence.

    Under a service manager an unreported bind failure is a restart loop:
    the daemon dies every few seconds and says nothing about why.
    """
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.bind((LOOPBACK, 0))
    holder.listen(1)
    busy = holder.getsockname()[1]
    try:
        out = tmp_path / "never-written.jsonl"
        result = run_receiver("serve", "--out", str(out), "--port", str(busy))
    finally:
        holder.close()

    assert result.returncode == 3, result.stdout + result.stderr
    assert "cannot bind" in result.stdout


def test_the_server_is_constructed_on_the_loopback_address(script_path):
    """The accepted host is bound literally, and only loopback is accepted."""
    text = script_path.read_text(encoding="utf-8")
    assert 'BIND_HOST = "127.0.0.1"' in text
    assert "server_class(host)((host, port)" in text
    assert '"0.0.0.0"' not in text
    # `::1` cannot be bound by an AF_INET server, so accepting it and
    # binding IPv4 anyway would be a silent lie about what is listening.
    assert "address_family = socket.AF_INET6" in text
    assert 'LOOPBACK_HOSTS = ("127.0.0.1", "localhost", IPV6_LOOPBACK)' in text


# --- install / uninstall write the files AND drive the manager -------------


def unit_of(sandbox_home):
    """The systemd unit path under the redirected HOME."""
    return (
        sandbox_home / ".config" / "systemd" / "user"
        / "critic-ledger-otel-receiver.service"
    )


def test_install_writes_a_launchagent_and_loads_it(
    run_receiver, sandbox_home, tmp_path, stub_bin
):
    """The plist starts at login, and `launchctl` is actually invoked."""
    _stub_dir, marker = stub_bin
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    result = run_receiver(
        "install", "--out", str(out), "--port", "4318", "--service", "launchd"
    )
    assert result.returncode == 0, result.stderr

    plist_path = (
        sandbox_home / "Library" / "LaunchAgents"
        / "com.critic-ledger.otel-receiver.plist"
    )
    assert plist_path.is_file(), result.stdout
    plist = plistlib.loads(plist_path.read_bytes())
    assert plist["RunAtLoad"] is True
    assert plist["KeepAlive"] == {"Crashed": True, "SuccessfulExit": False}
    argv = plist["ProgramArguments"]
    assert argv[0].startswith("/")
    assert argv[1].startswith("/")
    assert "serve" in argv
    assert str(out.resolve()) in argv
    # The service runs the COPY beside `--out`, never the installed
    # plugin directory, which is version stamped and moves on refresh.
    assert argv[1] == str(out.resolve().parent / "otel-receiver.py")
    assert (out.parent / "otel-receiver.py").is_file()
    assert marker.exists(), result.stdout
    assert "launchctl" in marker.read_text(encoding="utf-8")


def test_install_writes_a_systemd_unit_and_loads_it(
    run_receiver, sandbox_home, tmp_path, stub_bin
):
    """The unit is wanted by the default target, and systemctl is invoked."""
    _stub_dir, marker = stub_bin
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    result = run_receiver(
        "install", "--out", str(out), "--service", "systemd"
    )
    assert result.returncode == 0, result.stderr

    unit = unit_of(sandbox_home)
    assert unit.is_file(), result.stdout
    text = unit.read_text(encoding="utf-8")
    assert "WantedBy=default.target" in text
    assert "ExecStart=/" in text
    assert str(out.resolve()) in text
    assert "serve --out" in text
    assert str(out.resolve().parent / "otel-receiver.py") in text
    assert (out.parent / "otel-receiver.py").is_file()

    ran = marker.read_text(encoding="utf-8")
    assert "daemon-reload" in ran
    assert "enable --now" in ran


def test_install_with_no_load_writes_the_unit_and_runs_nothing(
    run_receiver, sandbox_home, tmp_path, stub_bin
):
    """`--no-load` is the switch a test uses: files written, manager untouched."""
    _stub_dir, marker = stub_bin
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    result = run_receiver(
        "install", "--out", str(out), "--service", "systemd", "--no-load"
    )
    assert result.returncode == 0, result.stderr
    assert unit_of(sandbox_home).is_file()
    assert not marker.exists(), marker.read_text(encoding="utf-8")


def test_install_writes_log_paths_beside_out(
    run_receiver, sandbox_home, tmp_path
):
    """The service keeps a log, and it lands beside the data it writes.

    Without those two keys a crash of the receiver goes to nowhere and
    the only symptom left is a file that stopped growing. The path is
    derived from the out file, never from the environment.
    """
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    log = out.parent / "otel-receiver.log"
    result = run_receiver(
        "install", "--out", str(out), "--service", "launchd", "--no-load",
        "--rotate-mb", "12.5",
    )
    assert result.returncode == 0, result.stderr

    plist_path = (
        sandbox_home / "Library" / "LaunchAgents"
        / "com.critic-ledger.otel-receiver.plist"
    )
    plist = plistlib.loads(plist_path.read_bytes())
    assert plist["StandardOutPath"] == str(log)
    assert plist["StandardErrorPath"] == str(log)
    assert f"log: {log}" in result.stdout
    # The rotation setting reaches the service, not just the shell that
    # typed it: the installed unit carries the flag and its value.
    argv = plist["ProgramArguments"]
    assert argv[argv.index("--rotate-mb") + 1] == "12.5"


def test_install_writes_log_lines_into_the_systemd_unit(
    run_receiver, sandbox_home, tmp_path
):
    """The systemd half of the same rule: both streams append to one file."""
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    log = out.parent / "otel-receiver.log"
    result = run_receiver(
        "install", "--out", str(out), "--service", "systemd", "--no-load"
    )
    assert result.returncode == 0, result.stderr

    text = unit_of(sandbox_home).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert f"StandardOutput=append:{log}" in lines
    assert f"StandardError=append:{log}" in lines
    assert f"log: {log}" in result.stdout
    exec_start = next(line for line in lines if line.startswith("ExecStart="))
    assert "--rotate-mb" in exec_start


def test_install_keepalive_is_the_dictionary_form(
    run_receiver, sandbox_home, tmp_path
):
    """Restart after a crash, stay down after a clean exit.

    `KeepAlive: true` restarts the service whatever happened, so a
    receiver that refused to start is started again every few seconds
    forever; the dictionary form asks for the restart only when it helps.
    """
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    result = run_receiver(
        "install", "--out", str(out), "--service", "launchd", "--no-load"
    )
    assert result.returncode == 0, result.stderr

    plist_path = (
        sandbox_home / "Library" / "LaunchAgents"
        / "com.critic-ledger.otel-receiver.plist"
    )
    plist = plistlib.loads(plist_path.read_bytes())
    assert plist["KeepAlive"] == {"Crashed": True, "SuccessfulExit": False}
    assert plist["ThrottleInterval"] == 10

    result = run_receiver(
        "install", "--out", str(out), "--service", "systemd", "--no-load"
    )
    assert result.returncode == 0, result.stderr
    text = unit_of(sandbox_home).read_text(encoding="utf-8")
    assert "Restart=on-failure" in text
    assert "RestartSec=10" in text
    assert "Restart=always" not in text


def test_install_does_not_resolve_the_interpreter_symlink(
    receiver_module, tmp_path, monkeypatch
):
    """The stable symlink is recorded, never the file it points at today.

    A resolved interpreter names a version-stamped directory that the
    next upgrade of that interpreter deletes, and the service then runs
    a path that no longer exists.
    """
    real = tmp_path / "real-python"
    real.write_text("", encoding="utf-8")
    link = tmp_path / "python3.14"
    link.symlink_to(real)
    monkeypatch.setattr(receiver_module.sys, "executable", str(link))

    python = receiver_module.resolve_interpreter()

    assert python == link
    assert python != real.resolve()


def test_install_refuses_a_cellar_interpreter_without_python_option(
    receiver_module, sandbox_home, tmp_path, monkeypatch, capsys
):
    """Under a version-stamped directory the installer asks, never guesses."""
    sandbox_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(sandbox_home))
    cellar = (
        tmp_path / "Cellar" / "python@3.14" / "3.14.6" / "bin" / "python3.14"
    )
    monkeypatch.setattr(receiver_module.sys, "executable", str(cellar))
    out = tmp_path / "o" / "claude-otel.jsonl"
    unit = unit_of(sandbox_home)

    code = receiver_module.install(
        out=out, port=4318, choice="systemd", load=False, python=None
    )

    assert code != 0
    assert "pass --python" in capsys.readouterr().out
    assert not unit.exists()

    link = tmp_path / "python3.14-symlink"
    link.symlink_to(tmp_path / "real-python")
    code = receiver_module.install(
        out=out, port=4318, choice="systemd", load=False, python=link
    )

    assert code == 0
    assert f"ExecStart={link}" in unit.read_text(encoding="utf-8")


def test_uninstall_unloads_the_service_then_removes_what_was_written(
    run_receiver, sandbox_home, tmp_path, stub_bin
):
    """The unit and the script copy both go, and the manager is told first."""
    _stub_dir, marker = stub_bin
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    run_receiver("install", "--out", str(out), "--service", "systemd", "--no-load")
    unit = unit_of(sandbox_home)
    copy = out.parent / "otel-receiver.py"
    assert unit.is_file()
    assert copy.is_file()

    result = run_receiver("uninstall", "--service", "systemd")
    assert result.returncode == 0, result.stderr
    assert not unit.exists()
    assert not copy.exists()
    assert "disable --now" in marker.read_text(encoding="utf-8")


def test_uninstall_with_no_load_removes_the_files_and_runs_nothing(
    run_receiver, sandbox_home, tmp_path, stub_bin
):
    """Removal never depends on a manager being reachable."""
    _stub_dir, marker = stub_bin
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    run_receiver("install", "--out", str(out), "--service", "systemd", "--no-load")

    result = run_receiver("uninstall", "--service", "systemd", "--no-load")
    assert result.returncode == 0, result.stderr
    assert not unit_of(sandbox_home).exists()
    assert not (out.parent / "otel-receiver.py").exists()
    assert not marker.exists(), marker.read_text(encoding="utf-8")


# --- status ----------------------------------------------------------------


def test_status_reports_the_absent_unit_and_the_answering_port(
    run_receiver, serving
):
    """Both halves are reported: the file that is not there, the port that is."""
    port, _out = serving()
    result = run_receiver(
        "status", "--port", str(port), "--service", "systemd", "--no-load"
    )
    assert result.returncode == 0, result.stderr
    assert "absent" in result.stdout
    assert "answers" in result.stdout
    assert "loaded: not checked" in result.stdout


def test_status_asks_the_manager_and_samples_the_out_file(
    run_receiver, sandbox_home, tmp_path, stub_bin
):
    """Loaded state comes from the manager; growth from two line counts."""
    _stub_dir, marker = stub_bin
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    run_receiver("install", "--out", str(out), "--service", "systemd", "--no-load")
    assert unit_of(sandbox_home).is_file()
    out.write_text('{"signal": "traces"}\n', encoding="utf-8")

    # No `--out`: the path is read back from the unit that `install` wrote.
    result = run_receiver("status", "--port", "1", "--service", "systemd")
    assert result.returncode == 0, result.stderr
    assert "installed" in result.stdout
    # The stub exits 0, so the manager's answer is "loaded".
    assert "loaded: yes" in result.stdout
    assert "is-active" in marker.read_text(encoding="utf-8")
    assert str(out.resolve()) in result.stdout
    assert "idle (1 -> 1 lines)" in result.stdout


def test_status_prints_the_age_of_the_last_line(
    run_receiver, tmp_path, stub_bin
):
    """How old the newest line is, and how large the file has grown.

    A receiver with nothing to record writes nothing, so two equal line
    counts say very little; the age of the last line is what separates a
    quiet receiver from a dead one.
    """
    _stub_dir, _marker = stub_bin
    out = tmp_path / "otel-data" / "claude-otel.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    stamp = (datetime.now(tz=UTC) - timedelta(seconds=5)).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")
    line = json.dumps(
        {"v": 1, "received_at": stamp, "signal": "traces", "body": {"n": 1}}
    )
    out.write_text(line + "\n", encoding="utf-8")

    result = run_receiver(
        "status", "--out", str(out), "--port", "1", "--service", "systemd",
        "--no-load",
    )
    assert result.returncode == 0, result.stderr

    age = float(
        re.search(r"last line age: ([0-9.]+) s", result.stdout).group(1)
    )
    assert 5 <= age <= 7, result.stdout
    size = int(re.search(r"size: ([0-9]+) bytes", result.stdout).group(1))
    assert size == out.stat().st_size


def test_status_reports_an_absent_out_file_as_absent(run_receiver, tmp_path):
    """A named file that does not exist is `absent`, never `static`."""
    out = tmp_path / "otel-data" / "never-written.jsonl"
    result = run_receiver(
        "status", "--out", str(out), "--port", "1", "--service", "systemd",
        "--no-load",
    )
    assert result.returncode == 0, result.stderr
    assert f"out {out}: absent" in result.stdout
