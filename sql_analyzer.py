"""SQL Analyzer — Main CLI entry point.

Usage:
    python sql_analyzer.py --file script.sql --db postgres
    python sql_analyzer.py --file script.sql --db sqlite --sqlite-path database.db
    python sql_analyzer.py --file script.sql --db sqlserver --explain-analyze
    python sql_analyzer.py --file script.sql --db postgres --json --csv --ai
"""

import argparse
import logging
import sys
from typing import List

from rich.console import Console

from sql_analyzer.ai_advisor import (
    get_ai_suggestions,
    get_groq_suggestions,
    get_ollama_suggestions,
)
from sql_analyzer.config import AnalyzerConfig, DatabaseConfig, setup_logging
from sql_analyzer.db_connector import DatabaseConnector
from sql_analyzer.executor import QueryResult, execute_all_queries
from sql_analyzer.plan_analyzer import analyze_query_plan
from sql_analyzer.report import (
    print_query_result,
    print_summary,
    save_csv_report,
    save_json_report,
)
from sql_analyzer.sql_parser import get_query_type, load_sql_file, split_queries
from sql_analyzer.suggestions import generate_suggestions

console = Console()
logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="sql_analyzer",
        description="Production-ready SQL performance analyzer with EXPLAIN plan parsing.",
    )

    # Required arguments
    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to the .sql file to analyze.",
    )

    # Database settings
    parser.add_argument(
        "--db",
        choices=["postgres", "sqlserver", "sqlite"],
        default="postgres",
        help="Database type (default: postgres).",
    )

    # SQLite connection
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Path to SQLite database file (default: database.db).",
    )

    # PostgreSQL connection
    parser.add_argument("--pg-host", default=None, help="PostgreSQL host.")
    parser.add_argument("--pg-port", type=int, default=None, help="PostgreSQL port.")
    parser.add_argument("--pg-database", default=None, help="PostgreSQL database name.")
    parser.add_argument("--pg-user", default=None, help="PostgreSQL user.")
    parser.add_argument("--pg-password", default=None, help="PostgreSQL password.")

    # SQL Server connection
    parser.add_argument("--mssql-server", default=None, help="SQL Server host.")
    parser.add_argument("--mssql-database", default=None, help="SQL Server database.")
    parser.add_argument("--mssql-user", default=None, help="SQL Server user.")
    parser.add_argument("--mssql-password", default=None, help="SQL Server password.")
    parser.add_argument(
        "--mssql-trusted",
        action="store_true",
        help="Use Windows trusted connection for SQL Server.",
    )

    # Analysis settings
    parser.add_argument(
        "--explain-analyze",
        action="store_true",
        help="Use EXPLAIN ANALYZE (actually runs query in EXPLAIN).",
    )
    parser.add_argument(
        "--slow-threshold",
        type=float,
        default=500.0,
        help="Slow query threshold in ms (default: 500).",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop execution on first query error.",
    )

    # Output settings
    parser.add_argument(
        "--json",
        dest="save_json",
        action="store_true",
        help="Save report to performance_report.json.",
    )
    parser.add_argument(
        "--json-path",
        default="performance_report.json",
        help="Path for JSON report output.",
    )
    parser.add_argument(
        "--csv",
        dest="save_csv",
        action="store_true",
        help="Save report to performance_report.csv.",
    )
    parser.add_argument(
        "--csv-path",
        default="performance_report.csv",
        help="Path for CSV report output.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output.",
    )

    # AI settings
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Enable OpenAI-powered optimization suggestions.",
    )
    parser.add_argument(
        "--openai-key",
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var).",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o).",
    )

    # Ollama settings (local LLM — no login/API key needed)
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Use local Ollama LLM for AI suggestions (no API key needed).",
    )
    parser.add_argument(
        "--ollama-model",
        default="llama3",
        help="Ollama model name (default: llama3). Run 'ollama list' to see available models.",
    )
    parser.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434).",
    )

    # Groq settings (fast cloud inference — free tier available)
    parser.add_argument(
        "--groq",
        action="store_true",
        help="Use Groq for fast AI suggestions (free tier available).",
    )
    parser.add_argument(
        "--groq-key",
        default=None,
        help="Groq API key (or set GROQ_API_KEY env var). Get one at https://console.groq.com/keys",
    )
    parser.add_argument(
        "--groq-model",
        default="llama-3.3-70b-versatile",
        help="Groq model name (default: llama-3.3-70b-versatile).",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Logging verbosity level (default: WARNING).",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to log file.",
    )

    return parser


def build_configs(args: argparse.Namespace) -> tuple[DatabaseConfig, AnalyzerConfig]:
    """Build configuration objects from CLI args and environment variables.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Tuple of (DatabaseConfig, AnalyzerConfig).
    """
    # Start from environment, then override with CLI args
    db_config = DatabaseConfig.from_env(db_type=args.db)
    analyzer_config = AnalyzerConfig.from_env()

    # Override DB config with CLI args
    if args.pg_host:
        db_config.pg_host = args.pg_host
    if args.pg_port:
        db_config.pg_port = args.pg_port
    if args.pg_database:
        db_config.pg_database = args.pg_database
    if args.pg_user:
        db_config.pg_user = args.pg_user
    if args.pg_password:
        db_config.pg_password = args.pg_password

    if args.mssql_server:
        db_config.mssql_server = args.mssql_server
    if args.mssql_database:
        db_config.mssql_database = args.mssql_database
    if args.mssql_user:
        db_config.mssql_user = args.mssql_user
    if args.mssql_password:
        db_config.mssql_password = args.mssql_password
    if args.mssql_trusted:
        db_config.mssql_trusted_connection = True

    if args.sqlite_path:
        db_config.sqlite_path = args.sqlite_path

    # Override analyzer config with CLI args
    analyzer_config.explain_analyze = args.explain_analyze
    analyzer_config.slow_query_threshold_ms = args.slow_threshold
    analyzer_config.continue_on_error = not args.stop_on_error
    analyzer_config.save_json = args.save_json
    analyzer_config.json_output_path = args.json_path
    analyzer_config.save_csv = args.save_csv
    analyzer_config.csv_output_path = args.csv_path
    analyzer_config.colored_output = not args.no_color
    analyzer_config.log_level = args.log_level
    analyzer_config.log_file = args.log_file

    if args.ai:
        analyzer_config.openai_enabled = True
    if args.openai_key:
        analyzer_config.openai_api_key = args.openai_key
    if args.openai_model:
        analyzer_config.openai_model = args.openai_model

    # Ollama settings
    if args.ollama:
        analyzer_config.ollama_enabled = True
        analyzer_config.ai_backend = "ollama"
    if args.ollama_model:
        analyzer_config.ollama_model = args.ollama_model
    if args.ollama_host:
        analyzer_config.ollama_host = args.ollama_host

    # Groq settings
    if args.groq:
        analyzer_config.groq_enabled = True
        analyzer_config.ai_backend = "groq"
    if args.groq_key:
        analyzer_config.groq_api_key = args.groq_key
    if args.groq_model:
        analyzer_config.groq_model = args.groq_model

    # If Groq is enabled but no API key, prompt interactively
    if analyzer_config.groq_enabled and not analyzer_config.groq_api_key:
        analyzer_config.groq_api_key = _prompt_for_api_key(
            provider="Groq",
            url="https://console.groq.com/keys",
            env_var="GROQ_API_KEY",
        )

    # If OpenAI AI is enabled but no API key is available, prompt interactively
    if (
        analyzer_config.openai_enabled
        and not analyzer_config.ollama_enabled
        and not analyzer_config.groq_enabled
        and not analyzer_config.openai_api_key
    ):
        analyzer_config.openai_api_key = _prompt_for_api_key(
            provider="OpenAI",
            url="https://platform.openai.com/api-keys",
            env_var="OPENAI_API_KEY",
        )

    return db_config, analyzer_config


def _prompt_for_api_key(
    provider: str = "OpenAI",
    url: str = "https://platform.openai.com/api-keys",
    env_var: str = "OPENAI_API_KEY",
) -> str:
    """Interactively prompt the user for an API key.

    Offers to save the key to a .env file for future use.

    Args:
        provider: Name of the AI provider (e.g. "OpenAI", "Groq").
        url: URL where the user can get their API key.
        env_var: Environment variable name to save the key as.

    Returns:
        The API key entered by the user, or empty string if skipped.
    """
    import getpass
    from pathlib import Path

    console.print(
        f"\n[bold yellow]{provider} API key required for AI suggestions.[/bold yellow]"
    )
    console.print(
        f"[dim]Get your key at: {url}[/dim]\n"
    )

    api_key = getpass.getpass(f"Paste your {provider} API key (hidden): ").strip()

    if not api_key:
        console.print("[yellow]No API key entered. AI suggestions will be skipped.[/yellow]\n")
        return ""

    # Offer to save to .env
    console.print()
    save = input("Save key to .env file for future use? [Y/n]: ").strip().lower()

    if save in ("", "y", "yes"):
        env_path = Path(".env")
        existing = ""
        if env_path.exists():
            existing = env_path.read_text(encoding="utf-8")

        if env_var in existing:
            # Replace existing key
            import re
            updated = re.sub(
                rf"{env_var}=.*",
                f"{env_var}={api_key}",
                existing,
            )
            env_path.write_text(updated, encoding="utf-8")
        else:
            # Append to file
            with open(env_path, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write(f"{env_var}={api_key}\n")

        console.print("[green]API key saved to .env — you won't be asked again.[/green]\n")
    else:
        console.print("[dim]Key not saved. You'll be prompted again next time.[/dim]\n")

    return api_key


def run_analysis(
    db_config: DatabaseConfig,
    analyzer_config: AnalyzerConfig,
    sql_file: str,
) -> List[QueryResult]:
    """Execute the full analysis pipeline.

    Args:
        db_config: Database connection configuration.
        analyzer_config: Analyzer settings.
        sql_file: Path to the SQL file.

    Returns:
        List of QueryResult objects.
    """
    colored = analyzer_config.colored_output

    # Step 1: Load and parse SQL file
    console.print(f"\n[bold]Loading SQL file:[/bold] {sql_file}")
    sql_content = load_sql_file(sql_file)
    queries = split_queries(sql_content)
    console.print(f"[bold]Found {len(queries)} executable statements.[/bold]\n")

    if not queries:
        console.print("[yellow]No executable SQL statements found.[/yellow]")
        return []

    # Step 2: Connect to database
    connector = DatabaseConnector(db_config)
    try:
        connector.connect()
        if db_config.db_type == "postgres":
            conn_info = db_config.pg_host
        elif db_config.db_type == "sqlserver":
            conn_info = db_config.mssql_server
        else:
            conn_info = db_config.sqlite_path
        console.print(
            f"[green]Connected to {db_config.db_type} ({conn_info})[/green]\n"
        )
    except (ConnectionError, ImportError) as e:
        console.print(f"[red]Connection failed: {e}[/red]")
        sys.exit(1)

    try:
        # Step 3: Execute queries
        results = execute_all_queries(
            connector=connector,
            queries=queries,
            explain_analyze=analyzer_config.explain_analyze,
            continue_on_error=analyzer_config.continue_on_error,
        )

        # Step 4: Analyze plans and generate suggestions
        for result in results:
            if result.success:
                # Analyze EXPLAIN plan
                metrics = analyze_query_plan(
                    explain_output=result.explain_output,
                    execution_time_ms=result.execution_time_ms,
                    slow_threshold_ms=analyzer_config.slow_query_threshold_ms,
                    db_type=db_config.db_type,
                )

                # Mark slow queries
                if result.execution_time_ms > analyzer_config.slow_query_threshold_ms:
                    result.is_slow = True

                # Generate suggestions
                warnings, suggestions = generate_suggestions(
                    query=result.query_text,
                    metrics=metrics,
                    slow_threshold_ms=analyzer_config.slow_query_threshold_ms,
                )
                result.warnings = warnings
                result.suggestions = suggestions
                result.performance_score = metrics.performance_score

                # AI suggestions (if enabled)
                if result.query_type == "SELECT":
                    ai_advice = None

                    if analyzer_config.groq_enabled:
                        ai_advice = get_groq_suggestions(
                            query=result.query_text,
                            explain_output=result.explain_output,
                            api_key=analyzer_config.groq_api_key,
                            model=analyzer_config.groq_model,
                        )
                    elif analyzer_config.ollama_enabled:
                        ai_advice = get_ollama_suggestions(
                            query=result.query_text,
                            explain_output=result.explain_output,
                            model=analyzer_config.ollama_model,
                            host=analyzer_config.ollama_host,
                        )
                    elif (
                        analyzer_config.openai_enabled
                        and analyzer_config.openai_api_key
                    ):
                        ai_advice = get_ai_suggestions(
                            query=result.query_text,
                            explain_output=result.explain_output,
                            api_key=analyzer_config.openai_api_key,
                            model=analyzer_config.openai_model,
                        )

                    if ai_advice:
                        result.suggestions.append(f"[AI] {ai_advice}")

            # Print individual result
            print_query_result(result, colored=colored)

        # Step 5: Print summary
        print_summary(results, colored=colored)

        return results

    finally:
        connector.close()


def main() -> None:
    """Main entry point for the SQL Analyzer CLI."""
    parser = build_arg_parser()
    args = parser.parse_args()

    # Build configurations
    db_config, analyzer_config = build_configs(args)

    # Setup logging
    setup_logging(analyzer_config)

    # Run analysis
    results = run_analysis(db_config, analyzer_config, args.file)

    # Save reports if requested
    if analyzer_config.save_json:
        save_json_report(results, analyzer_config.json_output_path)

    if analyzer_config.save_csv:
        save_csv_report(results, analyzer_config.csv_output_path)


if __name__ == "__main__":
    main()
