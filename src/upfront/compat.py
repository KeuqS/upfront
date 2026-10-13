"""Static compatibility checks for MCP tool definitions, per client.

Every rule cites the documentation or the *open* issue it comes from. Problems that clients
have already fixed (several old ``$defs``/64-character reports) are deliberately not rules:
a false "this breaks" is worse than no warning.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from upfront.discover import Skill

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Rule:
    id: str
    harnesses: tuple[str, ...]
    severity: Severity
    summary: str
    source: str


@dataclass(frozen=True)
class Finding:
    rule: str
    harness: str
    severity: Severity
    server: str
    tool: str
    message: str
    source: str


RULES: dict[str, Rule] = {
    r.id: r
    for r in (
        Rule(
            "openai-tool-name",
            ("codex",),
            "error",
            "OpenAI function names allow a-z, A-Z, 0-9, _ and -, up to 64 characters",
            "https://github.com/openai/openai-python/blob/main/src/openai/types/shared_params/function_definition.py",
        ),
        Rule(
            "anthropic-tool-name",
            ("claude-code",),
            "error",
            "Claude tool names must match ^[a-zA-Z0-9_-]{1,128}$ after the mcp__<server>__ prefix",
            "https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools",
        ),
        Rule(
            "gemini-tool-name",
            ("gemini-cli",),
            "error",
            "Gemini function names start with a letter or _; then a-zA-Z0-9_.:-, up to 128",
            "https://github.com/googleapis/python-genai/blob/main/google/genai/types.py",
        ),
        Rule(
            "claude-ref-params",
            ("claude-code",),
            "warning",
            "Parameters defined through $ref are sent to the server as JSON strings",
            "https://github.com/anthropics/claude-code/issues/18260",
        ),
        Rule(
            "opencode-unknown-format",
            ("opencode",),
            "info",
            "Non-standard JSON Schema 'format' values make OpenCode log warnings",
            "https://github.com/anomalyco/opencode/issues/15161",
        ),
        Rule(
            "codex-skills-budget",
            ("codex",),
            "warning",
            "Codex caps the initial skills list at 2% of the context window (8,000 characters "
            "when the window is unknown) and shortens or drops skills beyond it",
            "https://learn.chatgpt.com/docs/build-skills",
        ),
    )
}

_OPENAI_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_ANTHROPIC_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
_GEMINI_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.:-]{0,127}$")

# JSON Schema 2020-12 defined formats (validation vocabulary, section 7.3).
STANDARD_FORMATS = frozenset(
    {
        "date-time",
        "date",
        "time",
        "duration",
        "email",
        "idn-email",
        "hostname",
        "idn-hostname",
        "ipv4",
        "ipv6",
        "uri",
        "uri-reference",
        "iri",
        "iri-reference",
        "uuid",
        "uri-template",
        "json-pointer",
        "relative-json-pointer",
        "regex",
    }
)

CODEX_SKILLS_FALLBACK_CHARS = 8000


def _walk(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _finding(rule_id: str, harness: str, server: str, tool: str, message: str) -> Finding:
    r = RULES[rule_id]
    return Finding(rule_id, harness, r.severity, server, tool, message, r.source)


def check_tools(harness: str, server: str, tools: list[dict[str, Any]]) -> list[Finding]:
    """Findings for one server's tools as seen by ``harness``."""
    out: list[Finding] = []
    for tool in tools:
        name = str(tool.get("name", ""))
        schema = tool.get("inputSchema") or {}
        nodes = list(_walk(schema))
        if harness == "codex" and not _OPENAI_NAME.match(name):
            out.append(
                _finding(
                    "openai-tool-name",
                    harness,
                    server,
                    name,
                    f"'{name}' ({len(name)} chars) is not a valid OpenAI function name",
                )
            )
        if harness == "claude-code":
            full = f"mcp__{server}__{name}"
            if not _ANTHROPIC_NAME.match(full):
                out.append(
                    _finding(
                        "anthropic-tool-name",
                        harness,
                        server,
                        name,
                        f"'{full}' ({len(full)} chars) is not a valid Claude tool name",
                    )
                )
            if any("$ref" in n for n in nodes):
                out.append(
                    _finding(
                        "claude-ref-params",
                        harness,
                        server,
                        name,
                        "uses $ref; Claude Code may send those arguments as strings",
                    )
                )
        if harness == "gemini-cli" and not _GEMINI_NAME.match(name):
            out.append(
                _finding(
                    "gemini-tool-name",
                    harness,
                    server,
                    name,
                    f"'{name}' is not a valid Gemini function name",
                )
            )
        if harness == "opencode":
            odd = sorted(
                {
                    str(n["format"])
                    for n in nodes
                    if isinstance(n.get("format"), str) and n["format"] not in STANDARD_FORMATS
                }
            )
            if odd:
                out.append(
                    _finding(
                        "opencode-unknown-format",
                        harness,
                        server,
                        name,
                        f"non-standard format: {', '.join(odd)}",
                    )
                )
    return out


def codex_skills_chars(skills: list[Skill]) -> int:
    """Approximate size of Codex's initial skills list: name, description and path per skill."""
    return sum(len(s.name) + len(s.description) + len(str(s.path)) for s in skills)


def check_skills(harness: str, skills: list[Skill]) -> list[Finding]:
    if harness != "codex":
        return []
    chars = codex_skills_chars(skills)
    if chars <= CODEX_SKILLS_FALLBACK_CHARS:
        return []
    return [
        _finding(
            "codex-skills-budget",
            harness,
            "",
            "",
            f"{len(skills)} skills ≈ {chars:,} characters of metadata, over Codex's "
            f"{CODEX_SKILLS_FALLBACK_CHARS:,}-character fallback budget",
        )
    ]
