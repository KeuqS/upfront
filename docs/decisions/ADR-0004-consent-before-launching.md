# ADR-0004: Ask before launching or connecting to any server

## Context
To measure a stdio MCP server, upfront has to run the command in its config. Project-scoped
configs (`.mcp.json`, `.codex/config.toml`, `.gemini/settings.json`, `opencode.json`) come with
cloned repositories, so they can name arbitrary commands. Claude Code asks before starting
project servers, and Codex reads project config only for trusted projects.

## Decision
upfront lists every command and URL it would start or contact, then asks. When stdin is not a
TTY it launches nothing unless `--yes` is passed. Without consent it still reports skills,
instruction files and the server list, marking servers as "not measured (no consent)".
`--tools-file` measures a saved `tools/list` JSON without launching anything.

## Consequences
CI usage needs `--yes` (or `--tools-file`). That is one more flag, and a deliberate one.
