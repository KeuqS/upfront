"""Command-line interface: ``upfront [PATH]``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from upfront import __version__
from upfront.discover import HARNESSES, discover
from upfront.fetch import fetch_all
from upfront.report import Report, build_report, profile_tools_file, servers_to_launch

app = typer.Typer(add_completion=False, rich_markup_mode=None)


LABEL_WIDTH = 46


def _n(x: int) -> str:
    return f"≈ {x:,}"


def _row(label: str, value: str = "", note: str = "") -> str:
    if len(label) > LABEL_WIDTH:
        label = label[: LABEL_WIDTH - 1] + "…"
    return f"{label:<{LABEL_WIDTH}} {value:>9}  {note}".rstrip()


def _tidy(text: str, root: str) -> str:
    """Shorten paths so pasted output doesn't leak the home directory."""
    for prefix in (str(Path(root).resolve()), str(Path(root))):
        if prefix not in ("", "."):
            text = text.replace(prefix + "/", "")
    return text.replace(str(Path.home()), "~")


def render(report: Report, top: int) -> str:
    root = report.root
    header = root if root not in ("", ".") else _tidy(str(Path(root).resolve()), "/")
    lines = [f"upfront {__version__} · {header} · tokens {report.tokenizer}"]
    shown = [h for h in report.harnesses if not h.empty]
    if not shown:
        lines += ["", "Nothing configured: no MCP servers, skills or instruction files found."]
    for h in shown:
        lines += ["", _row(h.harness, _n(h.total), "before your first prompt")]
        for s in h.servers:
            label = f"  mcp {s.name} ({s.scope})"
            if s.status == "ok":
                lines.append(
                    _row(f"  mcp {s.name} ({len(s.tools)} tools, {s.scope})", _n(s.tokens))
                )
                lines += [_row(f"      {t.name}", _n(t.tokens)) for t in s.tools[:top]]
            elif s.status == "skipped":
                lines.append(_row(label, "-", "not measured: no consent"))
            else:
                lines.append(_row(label, "-", f"not measured: {_tidy(s.error or '', root)}"))
        if h.skills_count:
            label = f"  skills ({h.skills_count}, name + description)"
            body = f"bodies {_n(h.skills_body_tokens)} load on demand"
            lines.append(_row(label, _n(h.skills_metadata_tokens), body))
        for file in h.instructions:
            lines.append(_row(f"  {_tidy(file.path, root)}", _n(file.tokens)))
        lines += [f"  ! {_tidy(e, root)}" for e in h.errors]
    findings = [f for h in report.harnesses for f in h.findings]
    if findings:
        lines += ["", "compatibility"]
        for f in findings:
            where = ".".join(x for x in (f.server, f.tool) if x) or "-"
            lines.append(f"  {f.severity:<7} {f.harness:<11} {where}: {f.message}")
            lines.append(f"          [{f.rule}] {f.source}")
    if any(s.status == "skipped" for h in shown for s in h.servers):
        lines += [
            "",
            "Servers were not started. Run with --yes to launch them and measure their tools.",
        ]
    return "\n".join(lines)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"upfront {__version__}")
        raise typer.Exit()


@app.command()
def main(
    path: Annotated[Path, typer.Argument(help="Project directory.")] = Path("."),
    harness: Annotated[
        list[str] | None,
        typer.Option("--harness", "-H", help=f"Only these harnesses: {', '.join(HARNESSES)}."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Start/connect to configured servers without asking."),
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the report as JSON.")] = False,
    budget: Annotated[
        int | None, typer.Option(help="Exit 1 if any harness loads more tokens than this.")
    ] = None,
    strict: Annotated[
        bool, typer.Option(help="Exit 1 on error-level compatibility findings.")
    ] = False,
    tools_file: Annotated[
        Path | None, typer.Option(help="Measure a saved tools/list JSON instead of configs.")
    ] = None,
    top: Annotated[int, typer.Option(help="Heaviest tools to list per server.")] = 3,
    timeout: Annotated[float, typer.Option(help="Seconds per server.")] = 20,
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version.")
    ] = False,
) -> None:
    """See what your coding agents load before your first prompt."""
    unknown = set(harness or []) - set(HARNESSES)
    if unknown:
        raise typer.BadParameter(f"unknown harness {', '.join(sorted(unknown))}", param_hint="-H")

    if tools_file:
        report = profile_tools_file(tools_file, only=harness)
    else:
        d = discover(path, only=harness)
        specs = servers_to_launch(d)
        launch = yes
        if specs and not yes and sys.stdin.isatty():
            typer.echo("upfront will start or connect to these MCP servers to read their tools:")
            for s in specs:
                typer.echo(f"  [{s.harness}] {s.name}: {s.target}")
            launch = typer.confirm("Continue?", default=False)
        report = build_report(d, fetch_all(specs, timeout=timeout) if launch else [])

    typer.echo(report.to_json() if as_json else render(report, top))

    failed = False
    if budget is not None:
        for h in report.harnesses:
            if h.total > budget:
                failed = True
                if not as_json:
                    typer.echo(
                        f"{h.harness}: {h.total:,} tokens is over budget ({budget:,})", err=True
                    )
    if strict and any(f.severity == "error" for h in report.harnesses for f in h.findings):
        failed = True
    if failed:
        raise typer.Exit(1)
