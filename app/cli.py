"""
CLI Entry point for junior-engineer-bot.
Allows running the webhook server or running local code audits directly from the command line.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """🤖 junior-engineer-bot: Autonomous Junior Engineering Agent for your codebases."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host interface to bind.")
@click.option("--port", "-p", default=8000, help="Port to listen for GitHub webhooks.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload for development.")
def serve(host: str, port: int, reload: bool):
    """Start the FastAPI GitHub App webhook listener."""
    import uvicorn
    console.print(
        Panel.fit(
            f"[bold cyan]🤖 Junior Engineering Agent Webhook Server[/bold cyan]\n"
            f"[dim]Listening on:[/dim] [green]http://{host}:{port}/webhook[/green]",
            border_style="cyan",
        )
    )
    # Ensure app directory is in sys.path
    app_dir = Path(__file__).resolve().parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


@cli.command()
@click.argument("target_path", default=".", type=click.Path(exists=True))
@click.option("--min-severity", "-s", default="LOW", help="Minimum severity to display (CRITICAL, HIGH, MEDIUM, LOW, INFO).")
@click.option("--output", "-o", default="JUNIOR_AUDIT_REPORT.md", help="Markdown audit report output file.")
def audit(target_path: str, min_severity: str, output: str):
    """Audit any codebase path for vulnerabilities, bugs, and missing tests."""
    try:
        from app.junior_engineer import JuniorEngineer, Severity
    except ImportError:
        from junior_engineer import JuniorEngineer, Severity
    from rich.table import Table

    target = Path(target_path).resolve()
    console.print(f"[bold cyan]🔍 Scanning codebase:[/bold cyan] {target}")

    engineer = JuniorEngineer(repo_path=str(target))
    report = engineer.scan_repository(target_path=str(target))

    score = report.health_score
    color = "green" if score >= 80 else ("yellow" if score >= 60 else "red")
    console.print(f"\n[bold]Repository Health Score:[/bold] [{color}]{score}/100[/{color}]")
    console.print(f"[dim]Files Scanned: {report.total_files_scanned} | Total LOC: {report.total_loc:,}[/dim]\n")

    table = Table(title=f"Findings ({len(report.issues)} issues)")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Rule", style="dim", width=10)
    table.add_column("Location", style="cyan", width=25)
    table.add_column("Issue & Suggestion", style="white")

    for issue in report.issues[:25]:
        table.add_row(issue.severity.value, issue.rule_id, f"{issue.file_path}:{issue.line_number}", f"{issue.title}\n[italic green]↳ Fix: {issue.suggestion}[/italic green]")

    console.print(table)
    md_content = engineer.generate_markdown_report(report)
    Path(output).write_text(md_content, encoding="utf-8")
    console.print(f"\n[bold green]✓ Full Audit Report written to:[/bold green] {output}\n")


@cli.command()
@click.option("--repo", "-r", envvar="GITHUB_REPOSITORY", help="GitHub repository name (owner/repo).")
@click.option("--run-id", type=int, help="GitHub Actions run ID of failing CI.")
@click.option("--branch", "-b", default="main", help="Target branch name.")
@click.option("--issue-number", type=int, default=0, help="Issue number if triggered from an issue.")
@click.option("--issue-text", default="", help="Error description or issue body.")
def fix(repo: str, run_id: int | None, branch: str, issue_number: int, issue_text: str):
    """Run the automated bug fixer on a failing CI run or issue (serverless mode)."""
    try:
        from app.orchestrator import run_job
    except ImportError:
        from orchestrator import run_job

    if not repo:
        console.print("[bold red]Error:[/bold red] --repo (or GITHUB_REPOSITORY env var) is required.")
        sys.exit(1)

    if run_id:
        job = {"kind": "ci", "repo": repo, "run_id": run_id, "branch": branch}
    else:
        job = {"kind": "issue", "repo": repo, "number": issue_number, "text": issue_text}

    console.print(f"[bold green]🚀 Running autonomous fixer for:[/bold green] {repo} (kind={job['kind']})")
    run_job(job)
    console.print("[bold green]✓ Pipeline finished execution.[/bold green]")


if __name__ == "__main__":
    cli()
