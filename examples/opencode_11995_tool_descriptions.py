"""anomalyco/opencode#11995: "Tool descriptions consume excessive tokens in system prompt".

OpenCode closed this as not planned. This measures three official MCP reference servers (from
saved tools/list snapshots, so nothing is launched) and splits each tool's cost into its
description and the rest of its definition (name and JSON schemas).

    uv run python examples/opencode_11995_tool_descriptions.py
"""

import json
from pathlib import Path

from upfront.tokens import count, tool_tokens

servers = Path(__file__).parent / "servers"
rows = []
for name in ("filesystem", "memory", "everything"):
    for tool in json.loads((servers / f"{name}.tools.json").read_text())["tools"]:
        total = tool_tokens(tool)
        rows.append((total, count(tool.get("description", "")), f"{name}.{tool['name']}"))

rows.sort(reverse=True)
grand = sum(r[0] for r in rows)
described = sum(r[1] for r in rows)
share = described / grand
print(f"{len(rows)} tools ≈ {grand:,} tokens; descriptions are ≈ {described:,} ({share:.0%})")
print(f"{'tool':<38} {'total':>7} {'description':>12}")
for total, desc, name in rows[:8]:
    print(f"{name:<38} {total:>7,} {desc:>12,}")
