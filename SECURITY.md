# Security policy

upfront reads agent configuration files (`.mcp.json`, `~/.claude.json`, `.codex/config.toml`,
`~/.codex/config.toml`, `.gemini/settings.json`, `~/.gemini/settings.json`, `opencode.json[c]`,
`~/.config/opencode/opencode.json`), skill folders and instruction files. It writes nothing to them.

**It can start processes.** To measure an MCP server, upfront launches the command named in the
config (stdio servers) or connects to the URL (HTTP servers), exactly as your agent would. A
config file inside a cloned repository can name any command, so upfront never launches or
connects without consent: it lists every command and URL and asks first, and in non-interactive
use it requires `--yes`. Without consent it reports only what it can read from disk.

It sends the `env` and `headers` from your config only to the server they are configured for. It
calls `tools/list` and nothing else: it never calls tools, reads resources or runs prompts. The
tokenizer may download its vocabulary file from OpenAI's public CDN on first use (`tiktoken`);
if that fails, upfront falls back to an offline estimate. It has no telemetry.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub: open the **Security** tab of this
repository and choose **Report a vulnerability**. Do not open a public issue.

You can expect an acknowledgement within a week. Fixes are released as a new patch version
and noted in [CHANGELOG.md](CHANGELOG.md).

## Supported versions

Only the latest release receives fixes.
