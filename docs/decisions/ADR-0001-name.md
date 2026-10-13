# ADR-0001: Name the project `upfront`

## Context
The tool measures what a coding agent loads *before* the first prompt. The maintainer's other
tools use short compound names that say what they do (verdrift, layerdelta, lastgreen).

## Decision
`upfront`. Candidates checked on 2026-10-13 (GitHub `thanatchon36/<name>`, PyPI JSON API, GitHub
repo search, web search):

| Name | GitHub (own) | PyPI | Notable clash |
|---|---|---|---|
| **upfront** | free | free | none (largest same-name repo: 11★, unrelated) |
| ctxweigh | free | free | none, but hard to say aloud |
| toolweight | free | free | none, but ignores skills and instruction files |
| mcpweigh | free | free | none, but ties the name to MCP only |
| contextload | free | free | phillipclapham/contextload (1★) |

## Consequences
"upfront" is a common English word, so web search for it alone is noisy. The README, PyPI
keywords and GitHub topics pair it with "mcp" and "context window".
