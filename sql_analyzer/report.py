"""Report generation — console output, JSON, and CSV.

Provides rich colored console output and file export for
query execution results and performance analysis.
"""

import csv
import json
import logging
from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .executor import QueryResult
from .sql_parser import truncate_query_text

logger = logging.getLogger(__name__)

console = Console()


def print_query_result(result: QueryResult, colored: bool = True) -> None:
    """Print a single query result to the console.

    Args:
        result: QueryResult to display.
        colored: Whether to use colored output.
    """
    if colored:
        _print_query_result_rich(result)
    else:
        _print_query_result_plain(result)


def print_query_result_compact(result: QueryResult, colored: bool = True) -> None:
    """Print a compact query result without execution plan or AI suggestions.

    Args:
        result: QueryResult to display.
        colored: Whether to use colored output.
    """
    if colored:
        _print_query_result_compact_rich(result)
    else:
        _print_query_result_compact_plain(result)


def print_query_detail(result: QueryResult, colored: bool = True) -> None:
    """Print execution plan and AI suggestions for a selected query.

    Args:
        result: QueryResult whose details to display.
        colored: Whether to use colored output.
    """
    if colored:
        _print_query_detail_rich(result)
    else:
        _print_query_detail_plain(result)


def _print_query_result_rich(result: QueryResult) -> None:
    """Print query result using Rich library for colored output."""
    # Determine panel color based on status
    if not result.success:
        border_style = "red"
        status_icon = "[red]✗ FAILED[/red]"
    elif result.is_slow:
        border_style = "yellow"
        status_icon = "[yellow]⚠ SLOW[/yellow]"
    elif result.performance_score is not None and result.performance_score <= 4:
        border_style = "yellow"
        status_icon = "[yellow]⚠ NEEDS OPTIMIZATION[/yellow]"
    else:
        border_style = "green"
        status_icon = "[green]✓ OK[/green]"

    # Build content
    lines = []
    line_info = f"  [magenta](line {result.line_number})[/magenta]" if result.line_number else ""
    lines.append(f"[bold]Query #{result.query_number}[/bold]{line_info}  {status_icon}")
    lines.append(f"[dim]{truncate_query_text(result.query_text, 120)}[/dim]")
    lines.append("")

    if result.success:
        lines.append(f"Execution Time: [cyan]{result.execution_time_ms:.2f} ms[/cyan]")
        lines.append(f"Rows Affected:  [cyan]{result.rows_affected}[/cyan]")
        lines.append(f"Query Type:     [cyan]{result.query_type}[/cyan]")

        if result.performance_score is not None:
            score = result.performance_score
            if score >= 8:
                score_color = "green"
            elif score >= 5:
                score_color = "yellow"
            else:
                score_color = "red"
            lines.append(
                f"Perf Score:     [{score_color}]{score}/10[/{score_color}]"
            )

        # Execution plan detail
        if result.explain_output:
            lines.append("")
            lines.append("[bold white]Execution Plan:[/bold white]")
            for plan_line in result.explain_output.splitlines():
                lines.append(f"  [dim]{plan_line}[/dim]")
    else:
        lines.append(f"[red]Error: {result.error_message}[/red]")

    # Warnings
    if result.warnings:
        lines.append("")
        lines.append("[bold yellow]Performance Warnings:[/bold yellow]")
        for w in result.warnings:
            lines.append(f"  [yellow]• {w}[/yellow]")

    # Suggestions
    if result.suggestions:
        lines.append("")
        lines.append("[bold cyan]Suggestions:[/bold cyan]")
        for s in result.suggestions:
            if s.startswith("[AI]"):
                lines.append(f"  [bright_green]{s}[/bright_green]")
            else:
                lines.append(f"  [bright_white]→ {s}[/bright_white]")

    content = "\n".join(lines)
    console.print(Panel(content, border_style=border_style, expand=True))


def _print_query_result_compact_rich(result: QueryResult) -> None:
    """Print compact query result using Rich (no execution plan or AI suggestions)."""
    if not result.success:
        border_style = "red"
        status_icon = "[red]\u2717 FAILED[/red]"
    elif result.is_slow:
        border_style = "yellow"
        status_icon = "[yellow]\u26a0 SLOW[/yellow]"
    elif result.performance_score is not None and result.performance_score <= 4:
        border_style = "yellow"
        status_icon = "[yellow]\u26a0 NEEDS OPTIMIZATION[/yellow]"
    else:
        border_style = "green"
        status_icon = "[green]\u2713 OK[/green]"

    lines = []
    line_info = f"  [magenta](line {result.line_number})[/magenta]" if result.line_number else ""
    lines.append(f"[bold]Query #{result.query_number}[/bold]{line_info}  {status_icon}")
    lines.append(f"[dim]{truncate_query_text(result.query_text, 120)}[/dim]")
    lines.append("")

    if result.success:
        lines.append(f"Execution Time: [cyan]{result.execution_time_ms:.2f} ms[/cyan]")
        lines.append(f"Rows Affected:  [cyan]{result.rows_affected}[/cyan]")
        lines.append(f"Query Type:     [cyan]{result.query_type}[/cyan]")

        if result.performance_score is not None:
            score = result.performance_score
            if score >= 8:
                score_color = "green"
            elif score >= 5:
                score_color = "yellow"
            else:
                score_color = "red"
            lines.append(
                f"Perf Score:     [{score_color}]{score}/10[/{score_color}]"
            )
    else:
        lines.append(f"[red]Error: {result.error_message}[/red]")

    # Warnings (still shown in compact view)
    if result.warnings:
        lines.append("")
        lines.append("[bold yellow]Performance Warnings:[/bold yellow]")
        for w in result.warnings:
            lines.append(f"  [yellow]\u2022 {w}[/yellow]")

    # Non-AI suggestions only (still shown in compact view)
    non_ai_suggestions = [s for s in result.suggestions if not s.startswith("[AI]")]
    if non_ai_suggestions:
        lines.append("")
        lines.append("[bold cyan]Suggestions:[/bold cyan]")
        for s in non_ai_suggestions:
            lines.append(f"  [bright_white]\u2192 {s}[/bright_white]")

    # Hint about available details
    has_plan = bool(result.explain_output)
    has_ai = any(s.startswith("[AI]") for s in result.suggestions)
    if has_plan or has_ai:
        lines.append("")
        detail_parts = []
        if has_plan:
            detail_parts.append("execution plan")
        if has_ai:
            detail_parts.append("AI recommendation")
        lines.append(
            f"[dim italic]\u2139 {' & '.join(detail_parts)} available — "
            f"enter query #{result.query_number} after summary to view[/dim italic]"
        )

    content = "\n".join(lines)
    console.print(Panel(content, border_style=border_style, expand=True))


def _print_query_result_compact_plain(result: QueryResult) -> None:
    """Print compact query result in plain text (no execution plan or AI)."""
    sep = "-" * 60
    print(sep)
    line_info = f" (line {result.line_number})" if result.line_number else ""
    print(f"Query #{result.query_number}{line_info}")
    print(f"SQL: {truncate_query_text(result.query_text, 120)}")

    if result.success:
        print(f"Execution Time: {result.execution_time_ms:.2f} ms")
        print(f"Rows Affected: {result.rows_affected}")
        print(f"Query Type: {result.query_type}")
        if result.performance_score is not None:
            print(f"Performance Score: {result.performance_score}/10")
    else:
        print(f"ERROR: {result.error_message}")

    if result.warnings:
        print("Performance Warnings:")
        for w in result.warnings:
            print(f"  - {w}")

    non_ai_suggestions = [s for s in result.suggestions if not s.startswith("[AI]")]
    if non_ai_suggestions:
        print("Suggestions:")
        for s in non_ai_suggestions:
            print(f"  - {s}")

    has_plan = bool(result.explain_output)
    has_ai = any(s.startswith("[AI]") for s in result.suggestions)
    if has_plan or has_ai:
        detail_parts = []
        if has_plan:
            detail_parts.append("execution plan")
        if has_ai:
            detail_parts.append("AI recommendation")
        print(f"  [i] {' & '.join(detail_parts)} available — enter query #{result.query_number} after summary to view")

    print(sep)


def _print_query_detail_rich(result: QueryResult) -> None:
    """Print execution plan and AI suggestions using Rich."""
    lines = []
    line_info = f"  [magenta](line {result.line_number})[/magenta]" if result.line_number else ""
    lines.append(f"[bold]Query #{result.query_number}[/bold]{line_info}")
    lines.append(f"[dim]{truncate_query_text(result.query_text, 120)}[/dim]")
    lines.append("")

    if result.explain_output:
        lines.append("[bold white]Execution Plan:[/bold white]")
        for plan_line in result.explain_output.splitlines():
            lines.append(f"  [dim]{plan_line}[/dim]")
    else:
        lines.append("[dim]No execution plan available for this query.[/dim]")

    ai_suggestions = [s for s in result.suggestions if s.startswith("[AI]")]
    if ai_suggestions:
        lines.append("")
        lines.append("[bold bright_green]AI Recommendations:[/bold bright_green]")
        for s in ai_suggestions:
            lines.append(f"  [bright_green]{s}[/bright_green]")

    content = "\n".join(lines)
    console.print(Panel(content, border_style="cyan", title="Query Detail", expand=True))


def _print_query_detail_plain(result: QueryResult) -> None:
    """Print execution plan and AI suggestions in plain text."""
    sep = "=" * 60
    print(sep)
    line_info = f" (line {result.line_number})" if result.line_number else ""
    print(f"Query #{result.query_number}{line_info} — Detail View")
    print(f"SQL: {truncate_query_text(result.query_text, 120)}")
    print()

    if result.explain_output:
        print("Execution Plan:")
        for plan_line in result.explain_output.splitlines():
            print(f"  {plan_line}")
    else:
        print("No execution plan available for this query.")

    ai_suggestions = [s for s in result.suggestions if s.startswith("[AI]")]
    if ai_suggestions:
        print("\nAI Recommendations:")
        for s in ai_suggestions:
            print(f"  {s}")

    print(sep)


def _print_query_result_plain(result: QueryResult) -> None:
    """Print query result in plain text format."""
    sep = "-" * 60
    print(sep)
    line_info = f" (line {result.line_number})" if result.line_number else ""
    print(f"Query #{result.query_number}{line_info}")
    print(f"SQL: {truncate_query_text(result.query_text, 120)}")

    if result.success:
        print(f"Execution Time: {result.execution_time_ms:.2f} ms")
        print(f"Rows Affected: {result.rows_affected}")
        print(f"Query Type: {result.query_type}")

        if result.performance_score is not None:
            print(f"Performance Score: {result.performance_score}/10")

        if result.explain_output:
            print("Execution Plan:")
            for plan_line in result.explain_output.splitlines():
                print(f"  {plan_line}")
    else:
        print(f"ERROR: {result.error_message}")

    if result.warnings:
        print("Performance Warnings:")
        for w in result.warnings:
            print(f"  - {w}")

    if result.suggestions:
        print("Suggestions:")
        for s in result.suggestions:
            print(f"  - {s}")

    print(sep)


def print_summary(results: List[QueryResult], colored: bool = True) -> None:
    """Print execution summary with total time and top slowest queries.

    Args:
        results: All query results.
        colored: Whether to use colored output.
    """
    total_time = sum(r.execution_time_ms for r in results)
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    slow_count = sum(1 for r in results if r.is_slow)

    # Top 3 slowest queries
    sorted_by_time = sorted(
        [r for r in results if r.success],
        key=lambda r: r.execution_time_ms,
        reverse=True,
    )
    top_slow = sorted_by_time[:3]

    if colored:
        console.print()
        console.print(
            Panel("[bold]Execution Summary[/bold]", border_style="cyan", expand=True)
        )

        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Total Queries", str(len(results)))
        summary_table.add_row("Successful", f"[green]{successful}[/green]")
        summary_table.add_row("Failed", f"[red]{failed}[/red]" if failed else "0")
        summary_table.add_row("Slow Queries", str(slow_count))
        summary_table.add_row("Total Execution Time", f"{total_time:.2f} ms")

        console.print(summary_table)

        # Top slowest
        if top_slow:
            console.print()
            console.print("[bold yellow]Top 3 Slowest Queries:[/bold yellow]")
            slow_table = Table()
            slow_table.add_column("#", style="bold")
            slow_table.add_column("Line", style="magenta")
            slow_table.add_column("Time (ms)", style="red")
            slow_table.add_column("Score", style="yellow")
            slow_table.add_column("Query", style="dim")

            for r in top_slow:
                score_str = f"{r.performance_score}/10" if r.performance_score else "N/A"
                slow_table.add_row(
                    str(r.query_number),
                    str(r.line_number) if r.line_number else "-",
                    f"{r.execution_time_ms:.2f}",
                    score_str,
                    truncate_query_text(r.query_text, 80),
                )
            console.print(slow_table)

        # Optimization summary
        all_suggestions = []
        for r in results:
            all_suggestions.extend(r.suggestions)
        unique_suggestions = list(dict.fromkeys(all_suggestions))

        if unique_suggestions:
            console.print()
            console.print("[bold cyan]Optimization Summary:[/bold cyan]")
            for idx, s in enumerate(unique_suggestions[:10], 1):
                if s.startswith("[AI]"):
                    console.print(f"  [bright_green]{idx}. {s}[/bright_green]")
                else:
                    console.print(f"  [bright_white]{idx}. {s}[/bright_white]")

    else:
        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total Queries:        {len(results)}")
        print(f"Successful:           {successful}")
        print(f"Failed:               {failed}")
        print(f"Slow Queries:         {slow_count}")
        print(f"Total Execution Time: {total_time:.2f} ms")

        if top_slow:
            print("\nTop 3 Slowest Queries:")
            for r in top_slow:
                score = f"{r.performance_score}/10" if r.performance_score else "N/A"
                line_info = f" (line {r.line_number})" if r.line_number else ""
                print(
                    f"  #{r.query_number}{line_info}: {r.execution_time_ms:.2f} ms "
                    f"(Score: {score}) — {truncate_query_text(r.query_text, 60)}"
                )

        print("=" * 60)


def save_json_report(results: List[QueryResult], output_path: str) -> None:
    """Save performance report as JSON file.

    Args:
        results: All query results.
        output_path: Path to the output JSON file.
    """
    total_time = sum(r.execution_time_ms for r in results)
    sorted_by_time = sorted(
        [r for r in results if r.success],
        key=lambda r: r.execution_time_ms,
        reverse=True,
    )

    report = {
        "summary": {
            "total_queries": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "slow_queries": sum(1 for r in results if r.is_slow),
            "total_execution_time_ms": round(total_time, 2),
            "top_3_slowest": [
                {
                    "query_number": r.query_number,
                    "execution_time_ms": round(r.execution_time_ms, 2),
                    "query_text": truncate_query_text(r.query_text, 200),
                }
                for r in sorted_by_time[:3]
            ],
        },
        "queries": [r.to_dict() for r in results],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("JSON report saved to: %s", output_path)
    console.print(f"[green]JSON report saved to: {output_path}[/green]")


def save_csv_report(results: List[QueryResult], output_path: str) -> None:
    """Save performance report as CSV file.

    Args:
        results: All query results.
        output_path: Path to the output CSV file.
    """
    fieldnames = [
        "query_number",
        "line_number",
        "query_type",
        "execution_time_ms",
        "rows_affected",
        "success",
        "error_message",
        "performance_score",
        "is_slow",
        "warnings",
        "suggestions",
        "query_text",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            row = {
                "query_number": r.query_number,
                "line_number": r.line_number,
                "query_type": r.query_type,
                "execution_time_ms": round(r.execution_time_ms, 2),
                "rows_affected": r.rows_affected,
                "success": r.success,
                "error_message": r.error_message or "",
                "performance_score": r.performance_score or "",
                "is_slow": r.is_slow,
                "warnings": "; ".join(r.warnings),
                "suggestions": "; ".join(r.suggestions),
                "query_text": truncate_query_text(r.query_text, 200),
            }
            writer.writerow(row)

    logger.info("CSV report saved to: %s", output_path)
    console.print(f"[green]CSV report saved to: {output_path}[/green]")
