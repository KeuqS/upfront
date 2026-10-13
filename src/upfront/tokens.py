"""Token estimates for what a client sends: tool definitions, skill metadata, instruction files.

One tokenizer (``o200k_base``) is used for every harness; numbers are estimates (ADR-0003).
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any

import tiktoken

from upfront.discover import Skill

ENCODING = "o200k_base"

# Fields of an MCP Tool that clients forward to the model. `_meta` and `icons` are client-side.
WIRE_FIELDS = ("name", "title", "description", "inputSchema", "outputSchema", "annotations")


@lru_cache(maxsize=1)
def _encoder() -> tiktoken.Encoding | None:
    try:
        return tiktoken.get_encoding(ENCODING)
    except Exception:  # offline, blocked CDN, corrupt cache: fall back to an estimate
        return None


def tokenizer_name() -> str:
    return ENCODING if _encoder() is not None else "chars/4 estimate (tokenizer unavailable)"


def count(text: str) -> int:
    enc = _encoder()
    if enc is None:
        return math.ceil(len(text) / 4)
    return len(enc.encode(text, disallowed_special=()))


def tool_tokens(tool: dict[str, Any]) -> int:
    """Tokens for one tool definition as compact JSON of its wire fields."""
    wire = {k: tool[k] for k in WIRE_FIELDS if k in tool}
    return count(json.dumps(wire, separators=(",", ":"), ensure_ascii=False))


def skill_tokens(skill: Skill) -> tuple[int, int]:
    """(metadata loaded up front, body loaded when the skill is used)."""
    return count(f"{skill.name}: {skill.description}"), count(skill.body)
