# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-13

### Added

- `upfront [PATH]`: reports, per coding agent, the estimated tokens loaded before the first
  prompt by MCP tool definitions, skill metadata and instruction files.
- Config discovery for Claude Code (`.mcp.json`, `~/.claude.json` user and local scope),
  Codex (`.codex/config.toml`, `~/.codex/config.toml`), Gemini CLI (`.gemini/settings.json`)
  and OpenCode (`opencode.json[c]`), with skills folders and AGENTS/CLAUDE/GEMINI.md.
- `tools/list` over stdio, Streamable HTTP and SSE via the official MCP SDK, with pagination,
  per-server timeouts and per-server errors (including "auth required" and the server's last
  stderr line).
- Compatibility findings that cite their source: OpenAI, Anthropic and Gemini tool-name rules,
  `$ref` parameters in Claude Code (claude-code#18260), non-standard formats in OpenCode
  (opencode#15161), and Codex's skills-list budget.
- `--json`, `--budget`, `--strict`, `--tools-file`, `--top`, `--timeout`, `-H/--harness`.
- Servers are started only with consent (interactive prompt or `--yes`).
- Library API: `upfront.profile()` and `upfront.profile_tools_file()`.
- Examples reproducing codex#19679, opencode#11995 and claude-code#18260, and a demo project
  with tools/list snapshots of three official MCP reference servers.

[Unreleased]: https://github.com/thanatchon36/upfront/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thanatchon36/upfront/releases/tag/v0.1.0
