# Technical Documentation

Developer reference for the SQL Analyzer codebase. Each page covers one module in depth.

## Pages

| Page | Module | Description |
|------|--------|-------------|
| [Architecture](architecture.md) | — | System overview, data flow, and design decisions |
| [CLI & Entry Point](cli.md) | `sql_analyzer.py` | Argument parsing, config building, pipeline orchestration |
| [Configuration](config.md) | `sql_analyzer/config.py` | Dataclasses, environment variables, logging setup |
| [Credential Manager](credential-manager.md) | `sql_analyzer/credential_manager.py` | Password encryption, secure storage, interactive prompts |
| [SQL Parser](parser.md) | `sql_analyzer/sql_parser.py` | File loading, query splitting, line number tracking |
| [Database Connector](database.md) | `sql_analyzer/db_connector.py` | Connection management, transactions, cursor lifecycle |
| [Query Executor](executor.md) | `sql_analyzer/executor.py` | Execution timing, EXPLAIN plans, error handling |
| [Plan Analyzer](plan-analyzer.md) | `sql_analyzer/plan_analyzer.py` | EXPLAIN parsing for PostgreSQL, SQL Server, SQLite |
| [Suggestion Engine](suggestions.md) | `sql_analyzer/suggestions.py` | Rule-based performance warnings and recommendations |
| [AI Advisor](ai-advisor.md) | `sql_analyzer/ai_advisor.py` | OpenAI, Groq, and Ollama integration |
| [Report Output](report.md) | `sql_analyzer/report.py` | Rich console output, JSON/CSV export |
