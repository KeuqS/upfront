from __future__ import annotations

from pathlib import Path

import pytest

from upfront.discover import HARNESSES, discover


def names(ctx_servers: list) -> set[str]:  # type: ignore[type-arg]
    return {s.name for s in ctx_servers}


def test_discovers_all_four_harnesses(workspace: tuple[Path, Path]) -> None:
    root, home = workspace
    d = discover(root, home=home, env={})
    assert set(d.harnesses) == set(HARNESSES)

    claude = d.harnesses["claude-code"]
    assert names(claude.servers) == {"replay", "remote", "user-wide", "local-only"}
    remote = next(s for s in claude.servers if s.name == "remote")
    assert remote.transport == "http"
    assert remote.url == "http://127.0.0.1:9/mcp"  # ${VAR:-default} expanded
    assert any("broken" in e and "type" in e for e in claude.errors)  # url without type
    assert {s.scope for s in claude.servers} == {"project", "user", "local"}
    assert [f.path.name for f in claude.instructions] == ["CLAUDE.md"]
    assert {s.name for s in claude.skills} == {"deploy", "review"}

    codex = d.harnesses["codex"]
    assert names(codex.servers) == {"replay", "figma"}  # enabled = false is skipped
    assert next(s for s in codex.servers if s.name == "figma").transport == "http"
    assert [f.path.name for f in codex.instructions] == ["AGENTS.md"]
    assert {s.name for s in codex.skills} == {"release"}

    gemini = d.harnesses["gemini-cli"]
    by_name = {s.name: s for s in gemini.servers}
    assert by_name["legacy-sse"].transport == "sse"
    assert by_name["streaming"].transport == "http"
    assert by_name["streaming"].headers == {"X-Key": "k"}
    assert by_name["replay"].cwd == str(root)
    assert [f.path.name for f in gemini.instructions] == ["GEMINI.md"]

    opencode = d.harnesses["opencode"]
    oc = {s.name: s for s in opencode.servers}
    assert set(oc) == {"replay"}  # "jira" has enabled: false
    assert oc["replay"].env == {"A": "1"}
    assert oc["replay"].args[-1].endswith("tools.json")
    # OpenCode also loads Claude-compatible and agent-compatible skill folders
    assert {s.name for s in opencode.skills} == {"triage", "deploy", "release", "review"}
    assert [f.path.name for f in opencode.instructions] == ["AGENTS.md"]


def test_claude_falls_back_to_agents_md_without_claude_md(workspace: tuple[Path, Path]) -> None:
    root, home = workspace
    (root / "CLAUDE.md").unlink()
    claude = discover(root, home=home, env={}).harnesses["claude-code"]
    assert [f.path.name for f in claude.instructions] == ["AGENTS.md"]


def test_invalid_config_is_reported_not_raised(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text("{not json")
    d = discover(tmp_path, home=tmp_path / "nohome", env={})
    assert d.harnesses["claude-code"].servers == []
    assert any(".mcp.json" in e for e in d.harnesses["claude-code"].errors)


def test_skill_metadata_and_body_are_split(workspace: tuple[Path, Path]) -> None:
    root, home = workspace
    s = next(x for x in discover(root, home=home, env={}).harnesses["codex"].skills)
    assert s.name == "release"
    assert s.description == "Cut a release."
    assert "Do the thing." in s.body
    assert "description:" not in s.body


@pytest.mark.parametrize("harness", ["codex", "gemini-cli"])
def test_only_filter(workspace: tuple[Path, Path], harness: str) -> None:
    root, home = workspace
    assert list(discover(root, home=home, env={}, only=[harness]).harnesses) == [harness]


def test_stdio_servers_start_in_the_project_directory(workspace: tuple[Path, Path]) -> None:
    root, home = workspace
    d = discover(root, home=home, env={})
    stdio = [s for ctx in d.harnesses.values() for s in ctx.servers if s.transport == "stdio"]
    assert stdio
    assert all(s.cwd == str(root) for s in stdio)  # like the agents, which run from the project
