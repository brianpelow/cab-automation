"""CAB CLI — change advisory board automation commands."""

from __future__ import annotations

import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cab.core.config import CABConfig
from cab.models.change import ServiceContext
from cab.scorer.risk import score_change
from cab.generator.package import generate_cab_package
from cab.servicenow.client import ServiceNowClient

app = typer.Typer(name="cab", help="Change Advisory Board automation CLI.")
console = Console()


def _mock_service_context(service_name: str) -> ServiceContext:
    """Mock service context for CLI use without live Service Registry."""
    return ServiceContext(
        service_id=f"SVC-{hash(service_name) % 99999:05d}",
        service_name=service_name,
        owner=f"team-{service_name.split('-')[0]}@example.com",
        tier=1 if any(k in service_name for k in ["payment", "auth", "gateway"]) else 2,
        downstream_services=["mobile-app", "web-frontend"] if "payment" in service_name else ["reporting-service"],
        error_budget_remaining=72.5,
        recent_incident_count=1,
    )


@app.command("submit")
def submit(
    service: str = typer.Option(..., "--service", "-s", help="Service name"),
    env: str = typer.Option("production", "--env", "-e", help="Target environment"),
    change_type: str = typer.Option("standard", "--type", "-t", help="standard/emergency/hotfix/dependency-update"),
    diff: str = typer.Option("", "--diff", help="Path to git diff file"),
    summary: str = typer.Option("", "--summary", help="Change summary"),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Generate and submit a CAB change request."""
    config = CABConfig.from_env()

    diff_content = ""
    diff_lines = 0
    if diff:
        from pathlib import Path
        diff_path = Path(diff)
        if diff_path.exists():
            diff_content = diff_path.read_text(errors="ignore")
            diff_lines = len(diff_content.splitlines())

    diff_summary = summary or diff_content[:500] or f"Production deployment of {service} to {env}"

    svc = _mock_service_context(service)
    risk = score_change(svc, change_type, diff_lines, config)
    request = generate_cab_package(svc, diff_summary, risk, env, change_type, config)

    snow_client = ServiceNowClient(config)
    ticket = snow_client.submit_change(request)
    request.snow_ticket = ticket
    request.status = "submitted"

    if output_json:
        print(json.dumps(request.model_dump(), indent=2))
        return

    risk_color = {"low": "green", "medium": "yellow", "high": "orange3", "critical": "red"}.get(risk.level, "white")

    console.print(Panel.fit(
        f"Request ID: [cyan]{request.request_id}[/cyan]\n"
        f"ServiceNow: [cyan]{ticket}[/cyan]\n"
        f"Risk: [{risk_color}]{risk.level.upper()} ({risk.total}/100)[/{risk_color}]\n"
        f"Status: [yellow]{request.status}[/yellow]",
        title=f"CAB Request Submitted — {service}",
        border_style="blue",
    ))

    table = Table(border_style="dim", show_header=False)
    table.add_column("Factor", style="dim")
    table.add_column("Detail")
    for r in risk.rationale:
        parts = r.split(": +")
        table.add_row(parts[0] if len(parts) > 1 else r, f"+{parts[1]}" if len(parts) > 1 else "")
    console.print(table)

    if risk.level in ("high", "critical"):
        console.print(f"\n[yellow]⚠[/yellow] {risk.level.title()} risk — CAB chair review required before deployment.")
    else:
        console.print(f"\n[green]✓[/green] Standard CAB review. Check status: [cyan]cab status --ticket {ticket}[/cyan]")


@app.command("status")
def status(
    ticket: str = typer.Option(..., "--ticket", "-t", help="ServiceNow ticket number"),
) -> None:
    """Check approval status of a CAB change request."""
    config = CABConfig.from_env()
    client = ServiceNowClient(config)
    approval = client.get_approval_status(ticket)

    status_color = {"approved": "green", "rejected": "red", "pending": "yellow"}.get(
        approval.status, "white"
    )

    console.print(Panel.fit(
        f"Ticket: [cyan]{ticket}[/cyan]\n"
        f"Status: [{status_color}]{approval.status.upper()}[/{status_color}]\n"
        f"Approved by: {approval.approved_by or 'pending'}\n"
        f"Approved at: {approval.approved_at or 'pending'}",
        title="CAB Approval Status",
        border_style="blue",
    ))

    if approval.status == "approved":
        console.print("[green]✓ Deployment authorized. Proceed with orbit-platform Step 6.[/green]")
    elif approval.status == "rejected":
        console.print(f"[red]✗ Deployment blocked: {approval.rejection_reason}[/red]")
    else:
        console.print("[yellow]⏳ Awaiting CAB review. Deployment is blocked.[/yellow]")


@app.command("emergency")
def emergency(
    service: str = typer.Option(..., "--service", "-s", help="Service name"),
    incident: str = typer.Option(..., "--incident", "-i", help="Incident ID (e.g. INC0098765)"),
    summary: str = typer.Option("", "--summary", help="Brief description of emergency change"),
) -> None:
    """Submit an emergency change request for a P0 incident."""
    config = CABConfig.from_env()
    svc = _mock_service_context(service)
    svc.recent_incident_count += 1

    risk = score_change(svc, "emergency", 0, config)
    diff_summary = summary or f"Emergency change to restore {service} — linked to {incident}"
    request = generate_cab_package(svc, diff_summary, risk, "production", "emergency", config)
    request.compliance_notes += f" Emergency change linked to incident {incident}. Post-hoc documentation required within 24 hours per SOX ITGC CC7.2."

    snow_client = ServiceNowClient(config)
    ticket = snow_client.submit_change(request)
    request.snow_ticket = ticket
    request.status = "submitted"

    console.print(Panel.fit(
        f"[red]EMERGENCY CHANGE[/red]\n"
        f"Request: [cyan]{request.request_id}[/cyan]\n"
        f"ServiceNow: [cyan]{ticket}[/cyan]\n"
        f"Incident: [yellow]{incident}[/yellow]\n"
        f"Risk: [red]{risk.level.upper()} ({risk.total}/100)[/red]\n\n"
        f"[yellow]Post-hoc documentation required within 24 hours.[/yellow]\n"
        f"[yellow]CAB chair notified automatically.[/yellow]",
        title=f"Emergency CAB — {service}",
        border_style="red",
    ))


def main() -> None:
    app()


if __name__ == "__main__":
    main()