"""Connect to MCP servers and collect their full ``tools/list``, exactly as a client would."""

from __future__ import annotations

import tempfile
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Literal

import anyio
import httpx2
from mcp import Client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from upfront.discover import ServerSpec

Status = Literal["ok", "error", "skipped"]


@dataclass
class ServerResult:
    spec: ServerSpec
    status: Status
    tools: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def _key(spec: ServerSpec) -> tuple[Any, ...]:
    return (
        spec.transport,
        spec.command,
        tuple(spec.args),
        tuple(sorted(spec.env.items())),
        spec.cwd,
        spec.url,
        tuple(sorted(spec.headers.items())),
    )


def _transport(
    spec: ServerSpec, errlog: Any, statuses: list[int]
) -> AbstractAsyncContextManager[Any]:
    async def record(response: httpx2.Response) -> None:
        statuses.append(response.status_code)

    if spec.transport == "stdio":
        params = StdioServerParameters(
            command=spec.command or "", args=spec.args, env=spec.env or None, cwd=spec.cwd
        )
        return stdio_client(params, errlog=errlog)
    if spec.transport == "sse":
        return sse_client(spec.url or "", headers=dict(spec.headers) or None)
    client = httpx2.AsyncClient(
        headers=spec.headers, follow_redirects=True, event_hooks={"response": [record]}
    )
    return streamable_http_client(spec.url or "", http_client=client)


def _describe(exc: BaseException, statuses: list[int], url: str | None = None) -> str:
    """Turn nested anyio/httpx exception groups into one short, actionable line."""
    auth = [c for c in statuses if c in (401, 403)]
    if auth:
        return f"auth required (HTTP {auth[0]}); not measured"
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    text = f"{type(exc).__name__}: {exc}".strip().rstrip(":")
    if url and isinstance(exc, (httpx2.ConnectError, httpx2.ConnectTimeout)):
        return f"could not connect to {url} ({type(exc).__name__})"
    if isinstance(exc, FileNotFoundError):
        return f"command not found: {exc.filename or exc}"
    return text


async def _list_tools(
    spec: ServerSpec, timeout: float, statuses: list[int], errlog: Any
) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    with anyio.fail_after(timeout):
        transport = _transport(spec, errlog, statuses)
        async with Client(transport, read_timeout_seconds=timeout) as client:
            cursor: str | None = None
            while True:
                page = await client.list_tools(cursor=cursor)
                tools += [t.model_dump(by_alias=True, exclude_none=True) for t in page.tools]
                cursor = page.next_cursor
                if not cursor:
                    return tools


async def fetch_one(spec: ServerSpec, timeout: float = 20) -> ServerResult:
    """Fetch one server's tools. Never raises: failures become ``status="error"``."""
    statuses: list[int] = []
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as errlog:
        try:
            return ServerResult(spec, "ok", await _list_tools(spec, timeout, statuses, errlog))
        except TimeoutError:
            error = f"timed out after {timeout:g}s"
        except Exception as e:
            error = _describe(e, statuses, spec.url)
        errlog.seek(0)
        stderr = [line.strip() for line in errlog.read().splitlines() if line.strip()]
    if stderr:  # a server that exits early usually says why on stderr
        error += f"; server said: {stderr[-1][:200]}"
    return ServerResult(spec, "error", error=error)


def fetch_all(
    specs: list[ServerSpec], *, timeout: float = 20, concurrency: int = 4
) -> list[ServerResult]:
    """Fetch every server, launching each distinct command/URL once. Order matches ``specs``."""
    unique: dict[tuple[Any, ...], ServerSpec] = {}
    for s in specs:
        unique.setdefault(_key(s), s)
    done: dict[tuple[Any, ...], ServerResult] = {}

    async def run() -> None:
        limiter = anyio.CapacityLimiter(concurrency)

        async def one(key: tuple[Any, ...], spec: ServerSpec) -> None:
            async with limiter:
                done[key] = await fetch_one(spec, timeout)

        async with anyio.create_task_group() as tg:
            for key, spec in unique.items():
                tg.start_soon(one, key, spec)

    anyio.run(run)
    results = []
    for s in specs:
        shared = done[_key(s)]
        results.append(ServerResult(s, shared.status, shared.tools, shared.error))
    return results
