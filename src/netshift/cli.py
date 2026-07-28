"""CLI entry point.

This is the only place where the object graph is assembled: which adapter goes
behind which port. In .NET that is Program.cs and the IServiceCollection
registrations. The architectural term is composition root -- the single spot
that knows about both the interfaces and the implementations.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from netshift import __version__
from netshift.adapters.csproj_reader import CsprojReader
from netshift.adapters.memory_store import InMemoryReportStore, SystemClock
from netshift.config import Settings, load_settings
from netshift.domain import ProjectReport, Severity
from netshift.ports import Clock, ProjectSource, ReportStore

app = typer.Typer(
    name="netshift",
    help="Inspect legacy .NET projects and plan their migration.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_SEVERITY_STYLE = {
    Severity.INFO: "cyan",
    Severity.WARNING: "yellow",
    Severity.BLOCKER: "bold red",
}


def build_source() -> ProjectSource:
    return CsprojReader()


def build_clock() -> Clock:
    return SystemClock()


def build_store(settings: Settings) -> ReportStore:
    """Pick the store implementation. The only branch of its kind in the app."""
    if settings.netshift_store == "postgres":
        from netshift.adapters.postgres_store import PostgresReportStore

        return PostgresReportStore(settings.postgres_dsn)
    return InMemoryReportStore()


def _tool_version(executable: str, *args: str) -> str | None:
    """First line of `executable args`, or None when it is not installed."""
    path = shutil.which(executable)
    if path is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 - fixed command list, not user input
            [path, *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else "installed"


@app.command()
def version() -> None:
    """Print the netshift version."""
    console.print(f"netshift {__version__}")


@app.command()
def doctor() -> None:
    """Check the environment: tooling, configuration, store availability."""
    settings = load_settings()

    table = Table(title="netshift doctor", show_lines=False)
    table.add_column("Check", style="bold")
    table.add_column("Status", width=8, justify="center")
    table.add_column("Details", overflow="fold")

    ok = "[green]ok[/green]"
    missing = "[red]missing[/red]"
    warn = "[yellow]note[/yellow]"

    for label, executable, args in (
        ("git", "git", ("--version",)),
        ("uv", "uv", ("--version",)),
        ("docker", "docker", ("--version",)),
    ):
        detail = _tool_version(executable, *args)
        table.add_row(label, ok if detail else missing, detail or "not found in PATH")

    env_file = Path(".env")
    table.add_row(
        ".env",
        ok if env_file.exists() else warn,
        "found" if env_file.exists() else "absent -- copy .env.example to .env",
    )

    table.add_row("store", ok, settings.netshift_store)

    if settings.netshift_store == "postgres":
        try:
            store = build_store(settings)
            table.add_row("postgres", ok, f"connected, {len(store.list_names())} report(s)")
        except Exception as exc:  # noqa: BLE001 - doctor must survive any failure
            table.add_row("postgres", missing, str(exc).strip().splitlines()[0])

    provider = settings.netshift_llm_provider
    if provider == "none":
        table.add_row("llm", warn, "no provider selected (phase 3)")
    else:
        table.add_row(
            "llm",
            ok if settings.llm_key_present else missing,
            f"{provider}/{settings.netshift_llm_model}"
            + ("" if settings.llm_key_present else " -- key not set in .env"),
        )

    console.print(table)
    console.print(f"[dim]checked at {build_clock().now_iso()}[/dim]")


@app.command()
def inspect(
    path: Annotated[Path, typer.Argument(help="Path to a .csproj file")],
    save: Annotated[bool, typer.Option("--save", help="Store the report")] = False,
) -> None:
    """Parse a .csproj and print what stands in the way of migrating it."""
    source = build_source()

    try:
        report = source.load(path)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    _print_report(report)

    if save:
        build_store(load_settings()).save(report)
        console.print(f"[dim]stored as '{report.name}'[/dim]")

    # Non-zero exit when blockers are present, so the command can sit in a
    # pipeline and honestly fail it.
    raise typer.Exit(code=0 if report.is_migratable else 1)


@app.command(name="list")
def list_reports() -> None:
    """List stored reports."""
    names = build_store(load_settings()).list_names()
    if not names:
        console.print("[dim]empty -- store one: netshift inspect <file> --save[/dim]")
        return
    for name in names:
        console.print(name)


def _print_report(report: ProjectReport) -> None:
    console.print(f"\n[bold]{report.name}[/bold]  ({report.style})")
    console.print(f"frameworks:   {', '.join(report.target_frameworks) or '-'}")
    console.print(f"dependencies: {len(report.packages)}\n")

    if not report.findings:
        console.print("[green]no findings[/green]")
        return

    table = Table(show_lines=False)
    table.add_column("Code", width=6)
    table.add_column("Severity", width=9)
    table.add_column("Finding", overflow="fold")
    table.add_column("What to do", overflow="fold", style="dim")

    for finding in report.findings:
        style = _SEVERITY_STYLE[finding.severity]
        table.add_row(
            finding.code,
            f"[{style}]{finding.severity}[/{style}]",
            finding.message,
            finding.hint or "",
        )

    console.print(table)

    verdict = (
        "[green]no blockers[/green]"
        if report.is_migratable
        else f"[bold red]blockers: {len(report.blockers)}[/bold red]"
    )
    console.print(f"\n{verdict}")


if __name__ == "__main__":
    app()
