# ADR-0002: Python, the official MCP SDK, and no LLM calls

## Context
The brief prefers Python and asks for a provider abstraction (OpenAI-compatible, Anthropic,
Ollama) *if the tool touches LLMs*. upfront talks to MCP servers, not to models.

## Decision
- Python ≥ 3.11 (stdlib `tomllib` reads Codex's TOML config).
- The official `mcp` SDK (v2.x) for stdio and Streamable HTTP, so the tool connects and
  paginates `tools/list` exactly like a real client.
- **No provider layer in v0.1.** Token counts come from a local tokenizer (ADR-0003). Exact,
  per-vendor counts via token-count APIs are a v0.2 opt-in; that is where the provider
  interface will live.

## Consequences
No API keys and no paid calls on the core path. `mcp` is a large dependency (it pulls
httpx, pydantic, starlette, uvicorn), but it is the reference implementation and it is
maintained by the spec authors. A hand-written JSON-RPC client would drift from the spec.
