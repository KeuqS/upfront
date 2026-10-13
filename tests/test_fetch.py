from __future__ import annotations

import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from upfront.discover import ServerSpec
from upfront.fetch import fetch_all

from .conftest import REPLAY


def stdio_spec(*args: str, name: str = "replay") -> ServerSpec:
    return ServerSpec(
        "claude-code",
        name,
        "project",
        Path(".mcp.json"),
        "stdio",
        command=sys.executable,
        args=[*args],
    )


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def http_server(tools_file: Path) -> Iterator[str]:
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(REPLAY), str(tools_file), "--http", str(port)])
    deadline = time.time() + 15
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.1)
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_fetches_paginated_tools_over_stdio_and_http(tools_file: Path, http_server: str) -> None:
    paged = stdio_spec(str(REPLAY), str(tools_file), "--page-size", "2")
    http = ServerSpec("codex", "remote", "user", Path("config.toml"), "http", url=http_server)
    results = fetch_all([paged, http], timeout=20)
    assert [r.status for r in results] == ["ok", "ok"]
    for r in results:
        assert [t["name"] for t in r.tools] == [f"tool_{i}" for i in range(5)]
        assert r.tools[0]["inputSchema"]["properties"]["q"] == {"type": "string"}  # wire JSON


def test_failing_server_is_recorded_not_raised(tools_file: Path) -> None:
    missing = ServerSpec(
        "codex", "missing", "user", Path("c.toml"), "stdio", command="/nonexistent/upfront-mcp"
    )
    hangs = stdio_spec("-c", "import time; time.sleep(60)", name="hangs")
    ok = stdio_spec(str(REPLAY), str(tools_file))
    results = fetch_all([missing, hangs, ok], timeout=3)
    by = {r.spec.name: r for r in results}
    assert by["missing"].status == "error"
    assert by["missing"].error
    assert by["hangs"].status == "error"
    assert "timed out" in (by["hangs"].error or "")
    assert by["replay"].status == "ok"


def test_http_auth_failure_is_reported_as_auth_required() -> None:
    port = free_port()
    # A server that answers every request with 401, like a remote MCP server without a token.
    code = (
        "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
        "class H(BaseHTTPRequestHandler):\n"
        "    def do_POST(self):\n"
        "        self.send_response(401); self.send_header('WWW-Authenticate', 'Bearer');"
        " self.send_header('Content-Length', '0'); self.end_headers()\n"
        "    do_GET = do_POST\n"
        "    def log_message(self, *a): pass\n"
        f"HTTPServer(('127.0.0.1', {port}), H).serve_forever()\n"
    )
    proc = subprocess.Popen([sys.executable, "-c", code])
    try:
        time.sleep(0.5)
        spec = ServerSpec(
            "opencode", "jira", "user", Path("o.json"), "http", url=f"http://127.0.0.1:{port}/mcp"
        )
        (r,) = fetch_all([spec], timeout=10)
    finally:
        proc.terminate()
    assert r.status == "error"
    assert "auth" in (r.error or "").lower()


def test_identical_servers_are_fetched_once(tools_file: Path) -> None:
    a = stdio_spec(str(REPLAY), str(tools_file), name="a")
    b = ServerSpec("codex", "b", "user", Path("c.toml"), "stdio", command=a.command, args=a.args)
    ra, rb = fetch_all([a, b], timeout=20)
    assert ra.tools == rb.tools
    assert ra.tools is rb.tools  # one launch, shared result


def test_server_stderr_explains_an_early_exit() -> None:
    crash = stdio_spec(
        "-c", "import sys; sys.stderr.write('error: GITHUB_TOKEN is not set\\n'); sys.exit(1)"
    )
    (r,) = fetch_all([crash], timeout=10)
    assert r.status == "error"
    assert "GITHUB_TOKEN is not set" in (r.error or "")
