# Architecture

## Overview

SQL Analyzer is a modular Python CLI tool that analyzes SQL file performance. It follows a **linear pipeline** architecture — each stage processes data and passes results to the next.

## Pipeline Flow

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
                                                          │    Report    │
                                                          │              │
                                                          │ Rich console │
                                                          │ JSON / CSV   │
                                                          └──────────────┘
```

## Module Dependency Graph

```
sql_analyzer.py  (entry point)
├── sql_analyzer/config.py        ← no internal deps
├── sql_analyzer/sql_parser.py    ← no internal deps (uses sqlparse)
├── sql_analyzer/db_connector.py  ← depends on config.py
├── sql_analyzer/executor.py      ← depends on db_connector.py, sql_parser.py
├── sql_analyzer/plan_analyzer.py ← no internal deps
├── sql_analyzer/suggestions.py   ← depends on plan_analyzer.py, sql_parser.py
├── sql_analyzer/ai_advisor.py    ← no internal deps (lazy imports)
└── sql_analyzer/report.py        ← depends on executor.py (QueryResult), sql_parser.py
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

## Design Decisions

1. **Lazy imports for drivers** — `psycopg2`, `pyodbc`, `openai`, `ollama`, `groq` are imported inside functions, not at module level. This avoids `ImportError` when a user only needs one backend.

2. **Separate EXPLAIN execution** — EXPLAIN runs as a second query after the main execution, in its own cursor. This keeps timing measurement clean and avoids side effects from EXPLAIN ANALYZE.

3. **DB-specific plan parsers** — Each database returns EXPLAIN output in a different format (PostgreSQL JSON, SQL Server text, SQLite tree). Each has a dedicated parser function rather than trying to unify formats.

4. **Scoring is heuristic** — The 1-10 performance score uses simple point deductions (e.g., -2 for sequential scan, -1 for missing index). This is intentional — it gives a quick visual signal without claiming false precision.

5. **AI is always optional** — The AI advisor functions return `None` gracefully on any failure. The pipeline never depends on AI being available.

6. **Line number tracking** — Statements are correlated back to the original file by searching for the first meaningful line of each parsed statement in the raw file content. This survives comment stripping and whitespace normalization.
