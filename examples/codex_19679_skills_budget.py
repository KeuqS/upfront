"""openai/codex#19679: "Make skills metadata context budget configurable instead of hardcoded 2%".

Codex lists every installed skill's name, description and path up front, capped at 2% of the
context window (8,000 characters when the window is unknown); beyond that it shortens
descriptions and drops skills. This builds a project with 40 skills in .agents/skills and shows
how much metadata Codex has to fit, before you find out from a missing skill.

    uv run python examples/codex_19679_skills_budget.py
"""

import tempfile
from pathlib import Path

from upfront import profile

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for i in range(40):
        skill = root / ".agents" / "skills" / f"team-skill-{i:02d}"
        skill.mkdir(parents=True)
        description = (
            f"Use when working on service {i}: runs the service's checklist for migrations, "
            "feature flags, on-call handoff and release notes, and links the relevant runbooks."
        )
        skill.joinpath("SKILL.md").write_text(
            f"---\nname: team-skill-{i:02d}\ndescription: {description}\n---\n\nSteps...\n"
        )

    (codex,) = profile(root, home=root / "empty-home", only=["codex"]).harnesses
    print(f"{codex.skills_count} skills, ≈ {codex.skills_metadata_tokens:,} tokens of metadata")
    for finding in codex.findings:
        print(f"{finding.severity}: {finding.message}\n  {finding.source}")
