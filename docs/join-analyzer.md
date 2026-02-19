# JOIN Analyzer

## Module

`sql_analyzer/join_analyzer.py`

## Purpose

When a multi-JOIN `SELECT` query returns **0 rows**, it can be difficult to tell which table is empty or which JOIN condition eliminates all matches. The JOIN analyzer automatically decomposes the query to pinpoint the root cause.

## Strategy

1. **Parse** — Extract the `FROM` table and every `JOIN`ed table, along with aliases and `ON` conditions.
2. **Count** — Run `SELECT COUNT(*)` on each individual table to find any that are empty.
3. **Step** — Incrementally reconstruct the JOIN chain, checking the row count after each additional `JOIN`. The first step that drops the count to 0 is the culprit.
4. **WHERE** — If all JOIN steps produce rows, re-run the final step _with_ the `WHERE` clause to see if filtering is the cause.

## When It Triggers

The diagnostic runs automatically during normal (non-batch) analysis when **all three** conditions are met:

- The query type is `SELECT`
- The result has `rows_affected == 0`
- The query contains at least one `JOIN` keyword

No CLI flag is needed — it activates only when relevant.

## Data Structures

### `TableInfo`

```python
@dataclass
class TableInfo:
    table_name: str      # e.g. "orders"
    alias: str           # e.g. "o" (equals table_name when no alias)
    join_type: str       # "FROM", "JOIN", "LEFT JOIN", etc.
    on_condition: str    # Raw ON clause text
```

### `TableCount`

```python
@dataclass
class TableCount:
    table_name: str
    alias: str
    row_count: int           # Result of SELECT COUNT(*)
    error: Optional[str]     # Database error, if any
```

### `JoinStepResult`

```python
@dataclass
class JoinStepResult:
    step: int                # 1-based step number
    tables_joined: List[str] # Tables included so far
    join_sql: str            # The SQL fragment used
    row_count: int           # Result of COUNT(*) at this step
    error: Optional[str]
```

### `JoinDiagnostic`

The top-level result attached to `QueryResult.join_diagnostic`:

```python
@dataclass
class JoinDiagnostic:
    original_query: str
    tables: List[TableInfo]
    table_counts: List[TableCount]
    join_steps: List[JoinStepResult]
    culprit_table: Optional[str]   # Table or "WHERE clause"
    culprit_reason: str            # Human-readable explanation
```

## Public Functions

### `has_joins(query: str) -> bool`

Quick regex check for the presence of a `JOIN` keyword. Used by the pipeline to decide whether to run the full diagnostic.

### `diagnose_empty_join(connector, query) -> Optional[JoinDiagnostic]`

Main entry point. Requires an active `DatabaseConnector` and the original SQL query. Returns `None` if the query involves fewer than 2 tables.

## Example Output

### Rich (colored) mode

```
╭───────────────────── JOIN Diagnostic ──────────────────────╮
│ JOIN Diagnostic — 0 rows returned                          │
│                                                            │
│ Individual Table Row Counts:                               │
╰────────────────────────────────────────────────────────────╯
  Table          Alias    Rows    Status
  orders         o          35    ✓
  users          u          10    ✓
  order_items    oi         12    ✓
  products       p          15    ✓

Incremental JOIN Analysis:
  Step    Tables Joined                              Rows    Status
     1    orders → users                               35    ✓
     2    orders → users → order_items                 12    ✓
     3    orders → users → order_items → products      12    ✓

╭────────────────────────────────────────────────────────────╮
│ Root Cause: The full JOIN produces 12 rows, but the WHERE  │
│ clause (o.status = 'nonexistent') filters all of them out. │
╰────────────────────────────────────────────────────────────╯
```

### Plain text mode

```
============================================================
JOIN Diagnostic — 0 rows returned
============================================================

Individual Table Row Counts:
  orders (o): 35 rows [OK]
  users (u): 10 rows [OK]
  order_items (oi): 12 rows [OK]
  products (p): 15 rows [OK]

Incremental JOIN Analysis:
  Step 1: orders -> users = 35 rows [OK]
  Step 2: orders -> users -> order_items = 12 rows [OK]
  Step 3: orders -> users -> order_items -> products = 12 rows [OK]

Root Cause: The full JOIN produces 12 rows, but the WHERE clause
(o.status = 'nonexistent') filters all of them out.
============================================================
```

## Possible Root Causes

| Scenario | `culprit_table` | Explanation |
|----------|-----------------|-------------|
| A table has 0 rows | Table name (e.g. `orders`) | Any JOIN involving an empty table produces 0 results |
| A JOIN condition has no matches | Table name added at that step | The ON condition doesn't match any rows across the two sides |
| WHERE filters everything | `"WHERE clause"` | The full JOIN produces rows, but the WHERE eliminates all of them |
| Multiple factors | First table to drop to 0 | The diagnostic reports the first step that causes the drop |

## Internal Helpers

- `_extract_tables_from_query(query)` — Regex-based parser for FROM/JOIN clauses.
- `_count_table(connector, table_name)` — Runs `SELECT COUNT(*)` on one table.
- `_count_join_step(connector, tables, up_to_index, where_clause)` — Builds incremental JOIN SQL and counts rows.
- `_extract_where_clause(query)` — Extracts the WHERE clause text from the query.
