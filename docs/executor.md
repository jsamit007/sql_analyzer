# Query Executor

**Module:** `sql_analyzer/executor.py`

Executes SQL statements sequentially with precise timing, captures results, and runs EXPLAIN plans.

## `QueryResult` Dataclass

The central data object that flows through the entire pipeline.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query_number` | `int` | — | Sequential index (1-based) |
| `query_text` | `str` | — | Full SQL text |
| `query_type` | `str` | — | `SELECT`, `INSERT`, `UPDATE`, etc. |
| `line_number` | `int` | `0` | Source file line (1-based) |
| `execution_time_ms` | `float` | `0.0` | Measured execution time |
| `rows_affected` | `int` | `0` | Row count |
| `success` | `bool` | `True` | Whether execution succeeded |
| `error_message` | `str \| None` | `None` | Error details on failure |
| `explain_output` | `str \| None` | `None` | Raw EXPLAIN plan text |
| `explain_data` | `list \| None` | `None` | Structured EXPLAIN data |
| `warnings` | `list[str]` | `[]` | Performance warnings (populated later) |
| `suggestions` | `list[str]` | `[]` | Optimization advice (populated later) |
| `performance_score` | `int \| None` | `None` | 1-10 score (populated later) |
| `is_slow` | `bool` | `False` | Exceeds threshold (populated later) |
| `join_diagnostic` | `Any \| None` | `None` | JoinDiagnostic if JOIN returned 0 rows (populated later) |

### `to_dict() → dict`

Serializes to a dictionary for JSON export. Rounds `execution_time_ms` to 2 decimal places.

## Functions

### `execute_query(connector, query, query_number, explain_analyze, line_number) → QueryResult`

Executes a single SQL statement and measures its performance.

**Sequence:**

```
1. Determine query type via get_query_type()
2. Create QueryResult with initial metadata
3. Execute the query:
   a. Open cursor
   b. Start timer: time.perf_counter()
   c. cur.execute(query)
   d. Stop timer: time.perf_counter()
   e. Calculate elapsed ms
   f. For SELECT: fetchall() and count rows
   g. For DML: read cur.rowcount
   h. Commit
4. On failure: capture error, rollback
5. For successful SELECTs: run _run_explain() separately
```

**Why timing only measures `execute()`:**
The timer wraps only `cur.execute()`, not `fetchall()`. This gives the server-side execution time, which is what matters for optimization.

**Why EXPLAIN is separate:**
EXPLAIN runs in its own cursor after the main query completes. This avoids contaminating timing measurements and handles the case where EXPLAIN might fail even if the query succeeds.

### `_run_explain(connector, query, analyze) → str | None`

Dispatches to the appropriate EXPLAIN implementation:

| DB Type | Function | Strategy |
|---------|----------|----------|
| PostgreSQL | `_run_explain_postgres()` | `EXPLAIN (FORMAT JSON, BUFFERS ON)` |
| SQL Server | `_run_explain_sqlserver()` | `SET SHOWPLAN_TEXT ON` |
| SQLite | `_run_explain_sqlite()` | `EXPLAIN QUERY PLAN` |

### `_run_explain_postgres(connector, query, analyze) → str | None`

```sql
EXPLAIN (FORMAT JSON, BUFFERS ON) SELECT ...
-- With analyze=True:
EXPLAIN (FORMAT JSON, BUFFERS ON, ANALYZE ON) SELECT ...
```

Returns the JSON plan as a formatted string. PostgreSQL returns the plan in the first column of the first row.

**Note:** `EXPLAIN ANALYZE` actually **executes** the query. This is why it's behind the `--explain-analyze` flag.

### `_run_explain_sqlserver(connector, query) → str | None`

```sql
SET SHOWPLAN_TEXT ON
<query>
-- Read all result sets (showplan returns multiple)
SET SHOWPLAN_TEXT OFF
```

Iterates through all result sets using `cur.nextset()` to capture the full plan text.

### `_run_explain_sqlite(connector, query) → str | None`

```sql
EXPLAIN QUERY PLAN SELECT ...
```

SQLite returns rows of `(id, parent, notused, detail)`. The function builds an indented tree from the parent-child relationships:

```
|--SCAN users
|--SEARCH orders USING INDEX idx_orders_user_id (user_id=?)
  |--USE TEMP B-TREE FOR ORDER BY
```

**Tree building algorithm:**
1. Collect all nodes as `(id, parent, detail)` tuples
2. Build a `node_map` of `{id: parent_id}`
3. Calculate depth by walking the parent chain
4. Indent each line by `depth * 2` spaces

### `execute_all_queries(connector, queries, explain_analyze, continue_on_error) → List[QueryResult]`

Iterates over all `(query, line_number)` tuples and calls `execute_query()` for each.

If `continue_on_error=False` and a query fails, execution stops immediately. Otherwise, failures are recorded and execution continues with the next query.

## `BatchResult` Dataclass

Used by `--batch` mode when the entire SQL file is executed as a single script.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether the script completed without error |
| `total_statements` | `int` | Number of statements in the file |
| `execution_time_ms` | `float` | Total script execution time |
| `rows_affected` | `int` | Total rows from `cursor.rowcount` |
| `error_message` | `str \| None` | Error details on failure |

### `execute_as_script(connector, sql_content, total_statements) → BatchResult`

Executes the full SQL file content as a single database call:

- **SQLite:** Uses `cursor.executescript()` which handles multiple statements natively
- **PostgreSQL / SQL Server:** Uses `cursor.execute()` with the full content (relies on the driver to handle multiple statements)

Timing wraps the entire execution. On failure, rolls back and captures the error.
