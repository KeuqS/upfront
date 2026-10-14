from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from upfront import __version__, profile
from upfront.cli import app, render
from upfront.report import FileUsage, HarnessReport, Report, ServerUsage, ToolUsage

runner = CliRunner()


def run(args: list[str], home: Path) -> tuple[int, str]:
    result = runner.invoke(app, args, env={"HOME": str(home), "API_BASE": ""})
    return result.exit_code, result.output


def test_budget_exit_code_and_json_and_consent(workspace: tuple[Path, Path]) -> None:
    root, home = workspace
    local = ["-H", "claude-code", "-H", "gemini-cli"]  # their remote servers are on 127.0.0.1

    # Not a TTY and no --yes: nothing is launched, and the output says how to measure.
    code, out = run([str(root), *local], home)
    assert code == 0
    assert "not measured" in out
    assert "--yes" in out
    assert "CLAUDE.md" in out

    code, out = run([str(root), *local, "--yes", "--json"], home)
    assert code == 0
    data = json.loads(out)
    claude = next(h for h in data["harnesses"] if h["harness"] == "claude-code")
    replay = next(s for s in claude["servers"] if s["name"] == "replay")
    assert replay["status"] == "ok"
    assert len(replay["tools"]) == 5
    assert replay["tokens"] == sum(t["tokens"] for t in replay["tools"]) > 0
    assert claude["total"] >= replay["tokens"]
    refused = next(s for s in claude["servers"] if s["name"] == "remote")
    assert refused["status"] == "error"

    code, out = run([str(root), *local, "--yes", "--budget", "1"], home)
    assert code == 1
    assert "over budget" in out
    code, _ = run([str(root), *local, "--yes", "--budget", "10000000"], home)
    assert code == 0


def test_tools_file_mode_checks_every_client_without_launching(tmp_path: Path) -> None:
    tools = {
        "tools": [
            {"name": "files.read", "description": "Read a file.", "inputSchema": {"type": "object"}}
        ]
    }
    f = tmp_path / "tools.json"
    f.write_text(json.dumps(tools))
    code, out = run(["--tools-file", str(f), "--strict"], tmp_path)
    assert code == 1  # error-severity finding with --strict
    assert "openai-tool-name" in out
    assert "anthropic-tool-name" in out
    assert "gemini-tool-name" not in out  # dots are valid for Gemini


def test_library_api_and_version(workspace: tuple[Path, Path]) -> None:
    root, home = workspace
    report = profile(root, home=home, launch=False, only=["codex"])
    (codex,) = report.harnesses
    assert codex.skills_count == 1
    assert all(s.status == "skipped" for s in codex.servers)
    code, out = run(["--version"], home)
    assert code == 0
    assert __version__ in out


def test_empty_project_says_so(tmp_path: Path) -> None:
    code, out = run([str(tmp_path)], tmp_path / "home")
    assert code == 0
    assert "nothing" in out.lower()


def test_header_hides_the_home_directory(workspace: tuple[Path, Path]) -> None:
    root, _home = workspace
    result = runner.invoke(app, [str(root), "-H", "codex"], env={"HOME": str(root.parent)})
    assert result.exit_code == 0
    assert str(root.parent) not in result.output.splitlines()[0]
    assert "~/project" in result.output.splitlines()[0]


def test_render_shows_server_share_only_for_measured_servers() -> None:
    measured = ServerUsage(
        "measured", "project", "stdio", "target", "source", "ok", tools=[ToolUsage("tool", 40)]
    )
    skipped = ServerUsage("skipped", "project", "stdio", "target", "source", "skipped")
    failed = ServerUsage("failed", "project", "stdio", "target", "source", "error", "timeout")
    report = Report(
        "/vault",
        "test",
        [
            HarnessReport(
                "claude-code",
                servers=[measured, skipped, failed],
                instructions=[FileUsage("AGENTS.md", 60)],
            )
        ],
    )

    output = render(report, top=3)

    lines = output.splitlines()
    measured_line = next(line for line in lines if "mcp measured" in line)
    skipped_line = next(line for line in lines if "mcp skipped" in line)
    failed_line = next(line for line in lines if "mcp failed" in line)
    assert measured_line.endswith("≈ 40  40% of total")
    assert skipped_line.endswith("-  not measured: no consent")
    assert failed_line.endswith("-  not measured: timeout")
    assert "of total" not in skipped_line
    assert "of total" not in failed_line
