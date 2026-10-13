"""A minimal MCP server that serves a fixed `tools/list` read from a JSON file.

The examples and the test suite use it to stand up real MCP servers (stdio or
Streamable HTTP) whose tool schemas match the scenarios reported in public issues.

    python replay_server.py TOOLS.json                 # stdio
    python replay_server.py TOOLS.json --http 8765     # Streamable HTTP at /mcp
    python replay_server.py TOOLS.json --page-size 10  # paginate tools/list
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import anyio
import mcp_types as types
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server


def build_server(tools: list[dict[str, Any]], page_size: int) -> Server[Any]:
    parsed = [types.Tool.model_validate(t) for t in tools]

    async def list_tools(
        _ctx: Any, params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        start = int(params.cursor) if params and params.cursor else 0
        end = start + page_size
        return types.ListToolsResult(
            tools=parsed[start:end],
            next_cursor=str(end) if end < len(parsed) else None,
        )

    return Server("replay", on_list_tools=list_tools)


async def _run_stdio(server: Server[Any]) -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tools", type=Path)
    ap.add_argument("--http", type=int, metavar="PORT")
    ap.add_argument("--page-size", type=int, default=1000)
    args = ap.parse_args()
    data = json.loads(args.tools.read_text())
    server = build_server(data["tools"] if isinstance(data, dict) else data, args.page_size)
    if args.http:
        import uvicorn

        uvicorn.run(
            server.streamable_http_app(), host="127.0.0.1", port=args.http, log_level="warning"
        )
    else:
        anyio.run(_run_stdio, server)


if __name__ == "__main__":
    main()
