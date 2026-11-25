"""Offline zero-trust bundle verifier (`attesta-verify`)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from verify_coc.verifier import BundleVerificationReport, verify_bundle

app = typer.Typer(add_completion=False, help="Offline zero-trust Chain-of-Custody bundle verifier.")
console = Console()


@app.command()
def main(bundle: Path = typer.Argument(..., help="Path to exported Attesta .zip bundle")) -> None:
    """Verify an exported Attesta evidence bundle offline."""
    report: BundleVerificationReport = verify_bundle(bundle)
    table = Table(title="Attesta Offline Chain-of-Custody Verification")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Bundle", str(bundle))
    table.add_row("Case ID", report.case_id or "-")
    table.add_row("Asset ID", report.asset_id or "-")
    table.add_row("Events Verified", str(report.event_count))
    table.add_row("Status", "[green]PASS[/green]" if report.valid else "[red]FAIL[/red]")
    console.print(table)

    if not report.valid:
        for err in report.errors:
            console.print(f"[red]• {err}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
