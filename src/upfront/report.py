"""Assemble discovery, fetch, token counts and compat findings into one report."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from upfront import compat, tokens
from upfront.discover import HARNESSES, Discovery, Harness, ServerSpec, discover
from upfront.fetch import ServerResult, Status, fetch_all


@dataclass
class ToolUsage:
    name: str
    tokens: int


@dataclass
class ServerUsage:
    name: str
    scope: str
    transport: str
    target: str
    source: str
    status: Status
    error: str | None = None
    tools: list[ToolUsage] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return sum(t.tokens for t in self.tools)


@dataclass
class FileUsage:
    path: str
    tokens: int


@dataclass
class HarnessReport:
    harness: Harness
    servers: list[ServerUsage] = field(default_factory=list)
    skills_count: int = 0
    skills_metadata_tokens: int = 0
    skills_body_tokens: int = 0
    instructions: list[FileUsage] = field(default_factory=list)
    findings: list[compat.Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Tokens loaded before the first prompt: tools + skill metadata + instruction files."""
        servers = sum(s.tokens for s in self.servers if s.status == "ok")
        return servers + self.skills_metadata_tokens + sum(f.tokens for f in self.instructions)

    @property
    def empty(self) -> bool:
        return not (self.servers or self.skills_count or self.instructions or self.errors)


@dataclass
class Report:
    root: str
    tokenizer: str
    harnesses: list[HarnessReport]

    def to_dict(self) -> dict[str, Any]:
        def harness(h: HarnessReport) -> dict[str, Any]:
            d = asdict(h)
            d["total"] = h.total
            for s, raw in zip(h.servers, d["servers"], strict=True):
                raw["tokens"] = s.tokens
            return d

        return {
            "root": self.root,
            "tokenizer": self.tokenizer,
            "harnesses": [harness(h) for h in self.harnesses],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def _server_usage(result: ServerResult, harness: str) -> tuple[ServerUsage, list[compat.Finding]]:
    spec = result.spec
    usage = ServerUsage(
        spec.name, spec.scope, spec.transport, spec.target, str(spec.source),
        result.status, result.error,
        sorted((ToolUsage(str(t.get("name", "")), tokens.tool_tokens(t)) for t in result.tools),
               key=lambda t: -t.tokens),
    )  # fmt: skip
    findings = compat.check_tools(harness, spec.name, result.tools) if result.status == "ok" else []
    return usage, findings


def build_report(discovery: Discovery, results: Iterable[ServerResult]) -> Report:
    by_spec = {id(r.spec): r for r in results}
    out: list[HarnessReport] = []
    for name, ctx in discovery.harnesses.items():
        h = HarnessReport(name, errors=list(ctx.errors))
        for spec in ctx.servers:
            r = by_spec.get(id(spec)) or ServerResult(spec, "skipped")
            usage, findings = _server_usage(r, name)
            h.servers.append(usage)
            h.findings += findings
        h.servers.sort(key=lambda s: -s.tokens)
        h.skills_count = len(ctx.skills)
        for s in ctx.skills:
            meta, body = tokens.skill_tokens(s)
            h.skills_metadata_tokens += meta
            h.skills_body_tokens += body
        h.findings += compat.check_skills(name, ctx.skills)
        h.instructions = [FileUsage(str(f.path), tokens.count(f.text)) for f in ctx.instructions]
        out.append(h)
    return Report(str(discovery.root), tokens.tokenizer_name(), out)


def servers_to_launch(discovery: Discovery) -> list[ServerSpec]:
    return [s for ctx in discovery.harnesses.values() for s in ctx.servers]


def profile(
    root: Path | str = ".",
    *,
    home: Path | None = None,
    launch: bool = False,
    only: Iterable[str] | None = None,
    timeout: float = 20,
) -> Report:
    """Library entry point: discover configs under ``root`` and measure them.

    ``launch=False`` (the default) never starts a process or opens a connection; servers are
    reported as ``skipped``. See ADR-0004.
    """
    d = discover(Path(root), home=home, only=only)
    results = fetch_all(servers_to_launch(d), timeout=timeout) if launch else []
    return build_report(d, results)


def profile_tools_file(path: Path, *, only: Iterable[str] | None = None) -> Report:
    """Measure a saved ``tools/list`` JSON (``{"tools": [...]}`` or a list) for each client."""
    data = json.loads(path.read_text(encoding="utf-8"))
    tools = data["tools"] if isinstance(data, dict) else data
    wanted = [h for h in HARNESSES if only is None or h in set(only)]
    name = path.stem
    out = []
    for harness in wanted:
        spec = ServerSpec(harness, name, "project", path, "stdio", command="(tools file)")
        usage, findings = _server_usage(ServerResult(spec, "ok", tools), harness)
        out.append(HarnessReport(harness, servers=[usage], findings=findings))
    return Report(str(path), tokens.tokenizer_name(), out)
