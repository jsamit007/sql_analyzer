# Architecture

## Overview

SQL Analyzer is a modular Python CLI tool that analyzes SQL files. It supports two mutually exclusive modes selected via CLI flags:

- **`--time-queries`** — Full performance pipeline: execute, time, EXPLAIN, suggestions, AI
- **`--join-analyzer`** — JOIN diagnostic mode: filter to SELECT+JOIN queries, run table counts and incremental join step analysis

Both modes share the SQL parser, DB connector, and report modules.

## Pipeline Flow (`--time-queries`)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  SQL Parser  │───▶│  Executor   │───▶│Plan Analyzer │───▶│  Suggestions │
│              │    │             │    │              │    │              │
│ Load .sql    │    │ Run queries │    │ Parse EXPLAIN│    │ Generate     │
│ Split queries│    │ Measure time│    │ Detect issues│    │ warnings &   │
│ Track lines  │    │ Run EXPLAIN │    │ Score 1-10   │    │ advice       │
└─────────────┘    └─────────────┘    └──────────────┘    └──────┬───────┘
                         │                                       │
                         │                                       ▼
                   ┌─────┴───────┐                        ┌──────────────┐
                   │  DB Connect  │                        │  AI Advisor  │
                   │             │                        │  (optional)  │
                   │ PostgreSQL  │                        │ OpenAI/Groq/ │
                   │ SQL Server  │                        │ Ollama       │
                   │ SQLite      │                        └──────┬───────┘
                   └─────────────┘                               │
                                                                 ▼
                                                          ┌──────────────┐
                                                          │JOIN Analyzer │
                                                          │  (auto)      │
                                                          │ Diagnose     │
                                                          │ empty JOINs  │
                                                          └──────┬───────┘
                                                                 │
                                                                 ▼
                                                          ┌──────────────┐
                                                          │    Report    │
                                                          │              │
                                                          │ Rich console │
                                                          │ JSON / CSV   │
                                                          └──────────────┘
```

## Pipeline Flow (`--join-analyzer`)

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  SQL Parser  │───▶│  Filter to   │───▶│JOIN Analyzer │───▶│    Report    │
│              │    │  SELECT+JOIN │    │              │    │              │
│ Load .sql    │    │  queries     │    │ Table counts │    │ Rich console │
│ Split queries│    │  (skip rest) │    │ Incr. steps  │    │ diagnostics  │
│ Track lines  │    │              │    │ Root cause   │    │              │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                         │
                   ┌─────┴───────┐
                   │  DB Connect  │
                   │  PostgreSQL  │
                   │  SQL Server  │
                   │  SQLite      │
                   └─────────────┘
```

Skips: timing analysis, EXPLAIN plans, AI suggestions, performance scoring, interactive prompt.

## Module Dependency Graph

```
sql_analyzer.py  (entry point)
├── sql_analyzer/config.py              ← no internal deps
├── sql_analyzer/credential_manager.py  ← no internal deps (uses cryptography)
├── sql_analyzer/sql_parser.py          ← no internal deps (uses sqlparse)
├── sql_analyzer/db_connector.py        ← depends on config.py
├── sql_analyzer/executor.py            ← depends on db_connector.py, sql_parser.py
├── sql_analyzer/plan_analyzer.py       ← no internal deps
├── sql_analyzer/suggestions.py         ← depends on plan_analyzer.py, sql_parser.py
├── sql_analyzer/join_analyzer.py       ← depends on db_connector.py
├── sql_analyzer/ai_advisor.py          ← no internal deps (lazy imports)
└── sql_analyzer/report.py              ← depends on executor.py (QueryResult), join_analyzer.py, sql_parser.py
```

## Key Data Structures

### `QueryResult` (executor.py)

The central data object that flows through the pipeline. Created by the executor, enriched by the plan analyzer, suggestion engine, and AI advisor, then consumed by the report module.

```python
@dataclass
class QueryResult:
    query_number: int           # Sequential index (1-based)
    query_text: str             # Full SQL text
    query_type: str             # SELECT, INSERT, UPDATE, DELETE, DDL, etc.
    line_number: int            # Source file line (1-based)
    execution_time_ms: float    # Precise timing via time.perf_counter()
    rows_affected: int          # Row count from cursor
    success: bool               # Whether execution succeeded
    error_message: str | None   # Error details if failed
    explain_output: str | None  # Raw EXPLAIN text
    warnings: list[str]         # Performance warnings
    suggestions: list[str]      # Optimization recommendations
    performance_score: int | None  # 1-10 score
    is_slow: bool               # Exceeds threshold
    join_diagnostic: Any | None # JoinDiagnostic if JOIN returned 0 rows
```

### `PlanMetrics` (plan_analyzer.py)

Structured representation of an EXPLAIN plan's characteristics:

```python
@dataclass
class PlanMetrics:
    # Cost estimates, timing, row counts, buffer stats
    # Boolean flags: has_sequential_scan, has_nested_loop, has_large_sort, etc.
    # Lists: node_types, scan_types, join_types, tables_scanned
    # Final: performance_score (1-10)
```

### Config Dataclasses (config.py)

- `DatabaseConfig` — connection parameters for all three DB backends
- `AnalyzerConfig` — execution, output, AI, and logging settings

Both support `from_env()` class methods that read from environment variables / `.env` files.

### Credential Storage (.credentials)

Encrypted database passwords, stored as Fernet tokens in a JSON file. Machine-bound — the encryption key is derived from the hostname, OS, and MAC address. See [Credential Manager](credential-manager.md) for details.

## Design Decisions

1. **Lazy imports for drivers** — `psycopg2`, `pyodbc`, `openai`, `ollama`, `groq` are imported inside functions, not at module level. This avoids `ImportError` when a user only needs one backend.

2. **Separate EXPLAIN execution** — EXPLAIN runs as a second query after the main execution, in its own cursor. This keeps timing measurement clean and avoids side effects from EXPLAIN ANALYZE.

3. **DB-specific plan parsers** — Each database returns EXPLAIN output in a different format (PostgreSQL JSON, SQL Server text, SQLite tree). Each has a dedicated parser function rather than trying to unify formats.

4. **Scoring is heuristic** — The 1-10 performance score uses simple point deductions (e.g., -2 for sequential scan, -1 for missing index). This is intentional — it gives a quick visual signal without claiming false precision.

5. **AI is always optional** — The AI advisor functions return `None` gracefully on any failure. The pipeline never depends on AI being available.

6. **Line number tracking** — Statements are correlated back to the original file by searching for the first meaningful line of each parsed statement in the raw file content. This survives comment stripping and whitespace normalization.

7. **Secure password handling** — Database passwords are never stored in plain text. They are prompted with hidden input (`getpass`), encrypted with Fernet (AES-128-CBC + HMAC-SHA256), and saved to a machine-bound `.credentials` file. CLI args and env vars still work as overrides for scripted usage.

8. **JOIN decomposition** — When a multi-JOIN SELECT returns 0 rows, the analyzer automatically breaks the query apart, checks individual table row counts, and incrementally reconstructs the JOIN chain to pinpoint which table or condition causes the empty result. See [JOIN Analyzer](join-analyzer.md).

9. **Two analysis modes** — The CLI requires one of `--time-queries` (full performance pipeline) or `--join-analyzer` (JOIN diagnostic only). This keeps the two concerns separate — timing analysis is about performance, while JOIN analysis is about correctness and data availability.
