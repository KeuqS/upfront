# upfront — Mission

> See how many tokens each MCP server, skill and instruction file costs your coding agent before you type a word, and which tools will break in Claude Code, Codex, Gemini CLI or OpenCode.

Status: in development (v0.1.0 target)

## Problem

Coding agents load a lot before your first prompt: every connected MCP server's tool schemas, the name and description of every installed skill, and every AGENTS.md / CLAUDE.md / GEMINI.md. Users notice it as a usage meter that climbs too fast or tools that silently disappear. The harnesses show little of it: Claude Code has `/context`, but only for itself, and OpenCode declined to build a breakdown. When the same MCP server moves between agents, schemas that work in one client fail in another.

- [HN: Claude Code sends 33k tokens before reading the prompt; OpenCode sends 7k](https://news.ycombinator.com/item?id=48883275) — 706 points, 2026-07-12. Users had to put a logging proxy in front of the agent to find out.
- [openai/codex#19679 — Make skills metadata context budget configurable instead of hardcoded 2%](https://github.com/openai/codex/issues/19679) — 👍40, open. Skill descriptions are shortened or dropped once the list passes 2% of the window, and users can't see when that happens.
- [openai/codex#44308 — Agent Plugin MCP tools are silently hidden after the global schema budget is exhausted](https://github.com/openai/codex/issues/44308) — 👍6, open.
- [anomalyco/opencode#11995 — Tool descriptions consume excessive tokens in system prompt](https://github.com/anomalyco/opencode/issues/11995) — 👍17, closed *not planned*.
- [openai/codex#26234 — Flatten MCP namespace tools for non-OpenAI Responses API providers](https://github.com/openai/codex/issues/26234) — 👍49, open.
- [anthropics/claude-code#18260 — MCP tool parameters with $ref schemas are incorrectly serialized as string](https://github.com/anthropics/claude-code/issues/18260) — 👍9, open.

The full evidence and gap check are in the pain-point report and `decision.md` in the research workspace.

## Target user

A developer who uses one or more coding agents (Claude Code, Codex CLI, Gemini CLI, OpenCode) with several MCP servers and skills installed. They hit usage limits sooner than expected, or see tools go missing, and want to know which server or skill to cut. A second user is the **MCP server author** who wants to know what their server costs agents and whether its schemas work in every client, from CI.

## Before / after

**Before:** route the agent through a logging proxy (mitmproxy or a custom one), capture the first request, and count tokens by hand. Or install and remove servers one at a time and watch the usage meter. For schema compatibility: connect the server to each agent and wait for a 400.

**After** (illustrative; real output is in the README):
```console
$ upfront --yes
claude-code   ≈ 24,180 tokens before your first prompt
  mcp  github        41 tools   ≈ 18,920
  mcp  playwright    21 tools   ≈  3,140
  skills  12 (metadata)          ≈  1,320   (bodies ≈ 21,400, loaded on demand)
  CLAUDE.md                      ≈    800
compat  ⚠ gemini-cli  github.create_issue  uses $ref/$defs   (gemini-cli#13326)
```

## Non-goals (v0.1)

- **Measuring the harness's own system prompt.** It's vendor-internal and changes every release. upfront measures only what *you* add (servers, skills, instruction files).
- **Exact token counts for every model.** v0.1 uses one tokenizer (`o200k_base`) as a stated estimate. Calling vendor token-count APIs would need keys and network, so it's on the roadmap.
- **Rewriting schemas (a "fix" proxy).** v0.1 reports problems and doesn't change traffic.
- **Runtime token usage of conversations.** That's already solved by ccusage, codeburn and others.
- **OAuth flows for remote servers.** Servers that need auth are reported as "auth required, not measured".
- **Cursor, Windsurf and other IDE agents.** Four CLI harnesses first.

## Architecture

```text
configs on disk ──► discover ──► [Server specs, skills, instruction files]
                                        │
                          (consent) ──► fetch  ──► tools/list via MCP SDK (stdio / Streamable HTTP)
                                        │
                                        ▼
                        tokens (o200k_base) + compat rules
                                        │
                                        ▼
                         Report ──► table (rich) / JSON / exit code
```

- `upfront/discover.py` — reads Claude Code (`.mcp.json`, `~/.claude.json`), Codex (`.codex/config.toml`, `~/.codex/config.toml`), Gemini CLI (`.gemini/settings.json`, `~/.gemini/settings.json`) and OpenCode (`opencode.json[c]`, `~/.config/opencode/opencode.json`). Also finds skills dirs and instruction files.
- `upfront/fetch.py` — launches or connects to each server with the official `mcp` SDK, with a per-server timeout, and paginates `tools/list`. Failures are recorded, never raised.
- `upfront/tokens.py` — counts tokens for each tool's wire JSON (name, description, input/output schema), each skill's metadata and body, and each instruction file. Falls back to a chars/4 estimate if the tokenizer can't load offline.
- `upfront/compat.py` — static rules, each linked to the public issue it comes from.
- `upfront/report.py` + `upfront/cli.py` — rendering, JSON, budget exit codes.

External deps: `mcp` (official SDK), `tiktoken` (tokenizer), `typer` (CLI, brings `rich`). No LLM calls, no API keys.

**Safety:** project-level config files can name arbitrary commands, so upfront only launches servers after confirmation (`--yes` for non-interactive use). Without consent it reports static data only.

## MVP features → acceptance tests

| # | Feature | Acceptance test | Closes use case in |
|---|---|---|---|
| F1 | Discover MCP servers, skills and instruction files for 4 harnesses, project + user scope | `tests/test_discover.py::test_discovers_all_four_harnesses` — a fixture project with all four config formats yields the expected servers, skills and files per harness | HN 33k-tokens thread |
| F2 | Fetch every tool from stdio and Streamable HTTP servers (paginated, timeout, failures recorded) | `tests/test_fetch.py::test_fetches_paginated_tools_over_stdio_and_http` + `::test_failing_server_is_recorded_not_raised` | codex#44308 |
| F3 | Count tokens per tool, server, skill (metadata vs body) and instruction file | `tests/test_tokens.py::test_counts_scale_with_schema_and_skill_metadata_is_separate_from_body` | opencode#11995, codex#19679 |
| F4 | Compatibility rules per client, each linked to its source issue, plus the Codex 2% skills-list budget | `tests/test_compat.py::test_flags_each_known_breaker_and_passes_clean_tools` | codex#26234, claude-code#18260, codex#19679 |
| F5 | CLI: ranked table, `--json`, `--budget N` exit code, `--tools-file` offline mode, launch only with consent | `tests/test_cli.py::test_budget_exit_code_and_json_and_consent` | CI use for server authors |

## Success metrics

- Each cited issue's scenario reproduces as a passing example in `examples/` (yes/no per link): codex#19679, opencode#11995, codex#26234 / claude-code#18260.
- CI green on Python 3.11–3.13 × Linux/macOS, and coverage ≥ 85%.
- In 30 days: at least one issue or PR from someone other than the author, and one MCP server repo using `upfront --budget` in CI. Stars don't count as a goal.

## Roadmap

- **v0.2** — exact counts via vendor token-count endpoints (opt-in, with key); `--fix` stdio proxy that rewrites schemas per client (inline `$ref`, shorten names), from report theme #1; Cursor/Windsurf configs.
- **v0.3** — diff mode (`upfront diff main..HEAD` for MCP server PRs); a GitHub Action wrapper; per-model tokenizers.
