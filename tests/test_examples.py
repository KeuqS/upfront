"""The examples reproduce the scenarios of the issues they are named after; keep them working."""

from __future__ import annotations

import subprocess
import sys

import pytest

from .conftest import REPO

EXPECT = {
    "codex_19679_skills_budget.py": "fallback budget",
    "opencode_11995_tool_descriptions.py": "descriptions are",
    "claude_code_18260_ref_params.py": "claude-code/issues/18260",  # the $ref warning cites it
}


@pytest.mark.parametrize("script", sorted(EXPECT))
def test_example_runs(script: str) -> None:
    out = subprocess.run(
        [sys.executable, str(REPO / "examples" / script)],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    ).stdout
    assert EXPECT[script] in out
