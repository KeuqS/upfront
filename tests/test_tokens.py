from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from upfront import tokens
from upfront.discover import Skill


def tool(n_props: int) -> dict[str, Any]:
    return {
        "name": "search",
        "description": "Search the index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                f"field_{i}": {"type": "string", "description": "A field."} for i in range(n_props)
            },
        },
    }


def test_counts_scale_with_schema_and_skill_metadata_is_separate_from_body() -> None:
    small, big = tokens.tool_tokens(tool(1)), tokens.tool_tokens(tool(20))
    assert 0 < small < big
    assert tokens.tool_tokens(tool(20)) == big  # deterministic

    long_body = "Step one: read the docs.\n" * 200
    s = Skill("deploy", "Deploy the app to staging.", long_body, Path("SKILL.md"))
    meta, body = tokens.skill_tokens(s)
    assert 0 < meta < 30
    assert body > 20 * meta

    assert tokens.tokenizer_name() == "o200k_base"


def test_only_wire_fields_are_counted() -> None:
    base = tool(3)
    noisy = {**base, "_meta": {"internal": "x" * 5000}, "icons": [{"src": "data:" + "A" * 5000}]}
    assert tokens.tool_tokens(noisy) == tokens.tool_tokens(base)


def test_falls_back_to_char_estimate_when_tokenizer_cannot_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_name: str) -> None:
        raise OSError("no network")

    tokens._encoder.cache_clear()
    monkeypatch.setattr(tokens.tiktoken, "get_encoding", boom)
    try:
        assert tokens.count("x" * 40) == 10
        assert tokens.count("x" * 41) == 11
        assert "estimate" in tokens.tokenizer_name()
    finally:
        tokens._encoder.cache_clear()
