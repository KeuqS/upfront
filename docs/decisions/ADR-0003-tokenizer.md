# ADR-0003: One tokenizer, stated as an estimate, with an offline fallback

## Context
Each vendor tokenizes differently, and Anthropic's and Google's tokenizers are not available
offline. Users need relative weight ("which server is heavy?") more than exact counts.

## Decision
Count with `tiktoken`'s `o200k_base` for every harness and label numbers with "≈". Count what
the client sends: each tool's wire JSON (`name`, `title`, `description`, `inputSchema`,
`outputSchema`, `annotations`), skill metadata (frontmatter `name` + `description`), skill
bodies separately, and instruction files whole. If the vocabulary file can't be loaded
(offline, blocked CDN), fall back to `ceil(chars / 4)` and say so in the output.

## Consequences
Absolute numbers can differ from a vendor's count, and harnesses wrap tools
in their own framing, which upfront does not add. Rankings and budgets stay useful. Exact
counts are on the roadmap (ADR-0002).
