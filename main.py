"""
Main CLI Entry Point for AI Resume Screening & Ranking System.
Supports CLI batch execution, formatted terminal summaries, and FastAPI server launching.
"""

import sys
import argparse
import asyncio
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.pipeline import ScreeningPipeline
from src.config import settings
from src.api import app

# Configure UTF-8 encoding for Windows console compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True)


def display_results_in_terminal(report):
    """Render beautiful, structured terminal output using Rich."""
    # Summary panel
    summary = report.summary
    summary_text = (
        f"[bold cyan]Total Resumes Ingested:[/bold cyan] {summary.total_resumes} | "
        f"[bold green]Eligible Candidates:[/bold green] {summary.eligible} | "
        f"[bold red]Rejected Candidates:[/bold red] {summary.rejected} | "
        f"[bold yellow]Failed/Unreadable:[/bold yellow] {summary.failed_unreadable}\n"
        f"[dim]Total Processing Time: {summary.execution_time_seconds}s | LLM Provider: {settings.llm_provider}[/dim]"
    )
    console.print(Panel(summary_text, title="[SUMMARY] AI Resume Screeening and Ranking System (Kasparro assignment)", border_style="cyan"))

    # Eligible Candidates Table
    if report.ranked_candidates:
        table = Table(title="[SHORTLIST] Ranked Eligible Candidates Shortlist (100 Pts Rubric)", border_style="green", header_style="bold green")
        table.add_column("Rank", justify="center", style="bold yellow")
        table.add_column("Candidate Name", style="bold white")
        table.add_column("Total Score", justify="center", style="bold green")
        table.add_column("AI Depth (40)", justify="center")
        table.add_column("Python (30)", justify="center")
        table.add_column("Cloud (15)", justify="center")
        table.add_column("GitHub (10)", justify="center")
        table.add_column("Eng (5)", justify="center")
        table.add_column("Key Highlights & Strengths", style="cyan")

        for c in report.ranked_candidates:
            b = c.score_breakdown
            highlights = "; ".join(c.strengths[:2])
            if c.applied_penalties:
                highlights += f" [red]({len(c.applied_penalties)} penalty)[/red]"

            table.add_row(
                str(c.rank),
                c.candidate_name,
                f"{c.total_score}/100",
                str(b.ai_project_depth),
                str(b.python_backend),
                str(b.cloud_fullstack),
                str(b.github),
                str(b.engineering_depth),
                highlights
            )
        console.print(table)
    else:
        console.print("[yellow]No candidates met hard eligibility criteria.[/yellow]")

    # Rejected Candidates Table
    if report.rejected_candidates:
        rej_table = Table(title="[REJECTED] Candidates (Failed Hard Filters)", border_style="red", header_style="bold red")
        rej_table.add_column("Candidate Name", style="bold white")
        rej_table.add_column("Rejection Reasons", style="bold red")
        rej_table.add_column("Matched Skills Present", style="dim")

        for r in report.rejected_candidates:
            rej_table.add_row(
                r.candidate,
                "\n".join(f"* {reason}" for reason in r.rejection_reasons),
                ", ".join(r.matched_skills[:8]) if r.matched_skills else "[dim]None[/dim]"
            )
        console.print(rej_table)

    # Failed files notice
    if report.failed_files:
        fail_table = Table(title="[FAILED] Corrupted / Unreadable Files", border_style="yellow")
        fail_table.add_column("File Name", style="yellow")
        fail_table.add_column("Error Details", style="dim")
        for f in report.failed_files:
            fail_table.add_row(f.get("file_name", "Unknown"), f.get("error", "Parsing error"))
        console.print(fail_table)


async def run_cli(args):
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        console.print(f"[bold red]Error: Input directory does not exist: {input_path}[/bold red]")
        sys.exit(1)

    console.print(f"[bold cyan]>> Starting screening on resumes directory:[/bold cyan] {input_path}")
    pipeline = ScreeningPipeline(max_concurrency=args.concurrency)

    report = await pipeline.run(input_path)

    # Export outputs
    pipeline.export_json(report, output_path)
    console.print(f"[bold green][OK] JSON Results exported to:[/bold green] {output_path}")

    if args.csv:
        csv_path = Path(args.csv)
        pipeline.export_csv(report, csv_path)
        console.print(f"[bold green][OK] CSV Results exported to:[/bold green] {csv_path}")

    display_results_in_terminal(report)


def main():
    parser = argparse.ArgumentParser(
        description="AI Resume Screeening and Ranking System (Kasparro assignment)"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="./resumes",
        help="Path to folder containing resumes (PDF, DOCX, TXT)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./output/results.json",
        help="Path to save the resulting JSON report"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional path to save CSV results for spreadsheet analysis"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=5,
        help="Maximum concurrent file processing tasks (default: 5)"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Launch the FastAPI server instead of running the CLI"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind FastAPI server if --serve is specified (default: 8000)"
    )

    args = parser.parse_args()

    if args.serve:
        import uvicorn
        console.print(f"[bold green]Starting FastAPI Server on http://localhost:{args.port}...[/bold green]")
        uvicorn.run("src.api:app", host="0.0.0.0", port=args.port, reload=True)
    else:
        asyncio.run(run_cli(args))


if __name__ == "__main__":
    main()
