from __future__ import annotations

from pathlib import Path
from typing import Any

from upfront.compat import RULES, check_skills, check_tools
from upfront.discover import Skill


def t(name: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"name": name, "description": "d", "inputSchema": schema or {"type": "object"}}


CLEAN = t("search_issues", {"type": "object", "properties": {"q": {"type": "string"}}})


def rules_for(harness: str, tool: dict[str, Any], server: str = "srv") -> set[str]:
    return {f.rule for f in check_tools(harness, server, [tool])}


def test_flags_each_known_breaker_and_passes_clean_tools() -> None:
    for harness in ("claude-code", "codex", "gemini-cli", "opencode"):
        assert rules_for(harness, CLEAN) == set(), harness

    # OpenAI function names: [a-zA-Z0-9_-], max 64 -> Codex
    assert "openai-tool-name" in rules_for("codex", t("x" * 65))
    assert "openai-tool-name" in rules_for("codex", t("files.read"))
    # Anthropic: ^[a-zA-Z0-9_-]{1,128}$ after Claude Code's mcp__<server>__ prefix
    assert "anthropic-tool-name" in rules_for("claude-code", t("x" * 120), server="github")
    assert "anthropic-tool-name" not in rules_for("claude-code", t("x" * 100), server="gh")
    assert "anthropic-tool-name" in rules_for("claude-code", t("files.read"))
    # Gemini: must start with a letter or underscore; dots and colons allowed
    assert "gemini-tool-name" in rules_for("gemini-cli", t("1password_get"))
    assert rules_for("gemini-cli", t("files.read")) == set()
    # Claude Code serializes $ref parameters as strings (open issue)
    ref = t(
        "create",
        {
            "type": "object",
            "$defs": {"P": {"type": "object"}},
            "properties": {"p": {"$ref": "#/$defs/P"}},
        },
    )
    assert "claude-ref-params" in rules_for("claude-code", ref)
    assert "claude-ref-params" not in rules_for("codex", ref)
    # OpenCode logs warnings for non-standard JSON Schema formats
    fmt = t(
        "schedule",
        {
            "type": "object",
            "properties": {"every": {"type": "string", "format": "google-duration"}},
        },
    )
    assert "opencode-unknown-format" in rules_for("opencode", fmt)
    std = t(
        "at", {"type": "object", "properties": {"when": {"type": "string", "format": "date-time"}}}
    )
    assert rules_for("opencode", std) == set()


def test_every_rule_cites_a_source() -> None:
    for rule in RULES.values():
        assert rule.source.startswith("https://"), rule.id


def test_codex_skills_budget() -> None:
    few = [Skill("a", "short", "", Path("a/SKILL.md"))]
    many = [Skill(f"skill_{i}", "d" * 300, "", Path(f"s{i}/SKILL.md")) for i in range(40)]
    assert check_skills("codex", few) == []
    (finding,) = check_skills("codex", many)
    assert finding.rule == "codex-skills-budget"
    assert check_skills("claude-code", many) == []


def test_server_name_characters_do_not_cause_claude_name_errors() -> None:
    # Clients normalize the server segment; only the tool's own name and the total length count.
    assert rules_for("claude-code", CLEAN, server="issue-scenarios.tools") == set()
    assert "anthropic-tool-name" in rules_for("claude-code", t("files.read"), server="a.b")
