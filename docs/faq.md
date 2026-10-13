# FAQ

**Why does my agent use so many tokens before I've typed anything?**
Usually MCP tool schemas. Run `upfront --yes --top 10` and look at the heaviest servers and
tools. The [HN thread](https://news.ycombinator.com/item?id=48883275) that measured "Claude Code
sends 33k tokens before reading the prompt; OpenCode sends 7k" needed a logging proxy to find
this out; upfront reads it from the servers directly (it doesn't measure the vendor's own
system prompt).

**Are tool descriptions the problem?**
Often not. In the three official reference servers in `examples/servers`, descriptions are
about a sixth of the tool tokens; the JSON schemas are the rest (run
`examples/opencode_11995_tool_descriptions.py`). That's the case
[opencode#11995](https://github.com/anomalyco/opencode/issues/11995) describes, closed as not
planned.

**Codex dropped or shortened some of my skills.**
Codex caps its initial skills list at 2% of the context window, or 8,000 characters when it
doesn't know the window ([docs](https://learn.chatgpt.com/docs/build-skills)). upfront warns
when your skills' metadata is over the 8,000-character figure; see
[codex#19679](https://github.com/openai/codex/issues/19679) and
`examples/codex_19679_skills_budget.py`.

**Some plugin MCP tools never show up in Codex.**
[codex#44308](https://github.com/openai/codex/issues/44308) reports tools hidden after a global
schema budget is exhausted. upfront shows each server's schema tokens so you can see which
servers are pushing you over; it can't predict Codex's exact cutoff, which isn't documented.

**My server works in Claude Code but its object parameters arrive as strings.**
If the parameter is defined through `$ref`, that's
[claude-code#18260](https://github.com/anthropics/claude-code/issues/18260) (open). upfront
flags `$ref` in tools for Claude Code (`claude-ref-params`); inlining the definition avoids it.
See `examples/claude_code_18260_ref_params.py`.

**My MCP tools fail with Ollama / LM Studio in Codex.**
[codex#26234](https://github.com/openai/codex/issues/26234) and
[codex#23186](https://github.com/openai/codex/issues/23186): Codex wraps MCP tools in a
`namespace` type that non-OpenAI providers don't accept. That depends on the provider, not the
schema, so upfront can't detect it from the tools; it does check that names are valid OpenAI
function names, which those providers also expect.

**Why doesn't upfront warn about `$defs` for Gemini, or 64-character names for Claude?**
Those were real reports, and they're closed as completed
([gemini-cli#13326](https://github.com/google-gemini/gemini-cli/issues/13326),
[claude-code#21136](https://github.com/anthropics/claude-code/issues/21136)). The Gemini API also
takes plain JSON Schema through `parameters_json_schema`
([google-genai](https://github.com/googleapis/python-genai/blob/main/google/genai/types.py)), and
Claude tool names may now be up to 128 characters
([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)). upfront
only reports what still breaks.

**Does upfront send my tokens or config anywhere?**
No. It reads local files, starts or contacts only the servers in your config (after you agree),
calls `tools/list` on them, and may download the tokenizer's vocabulary once. No telemetry.
See [SECURITY.md](../SECURITY.md).
