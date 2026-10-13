"""anthropics/claude-code#18260: "MCP tool parameters with $ref schemas are incorrectly
serialized as string".

The reporter's Notion MCP server defined `parent` through $ref, and Claude Code sent it as a
JSON string. examples/servers/issue-scenarios.tools.json reproduces that schema (plus the
Firebase-style `google-duration` format from opencode#15161 and a dotted tool name). This
checks it against every client's rules without starting a server.

    uv run python examples/claude_code_18260_ref_params.py
"""

from pathlib import Path

from upfront import profile_tools_file

report = profile_tools_file(Path(__file__).parent / "servers" / "issue-scenarios.tools.json")
for harness in report.harnesses:
    for f in harness.findings:
        print(f"{f.harness:<11} {f.severity:<7} {f.tool:<16} {f.message}")
        print(f"{'':<11} {'':<7} {'':<16} {f.source}")
