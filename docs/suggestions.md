# Suggestion Engine

**Module:** `sql_analyzer/suggestions.py`

Generates actionable performance warnings and improvement suggestions based on query type and EXPLAIN plan analysis.

## `generate_suggestions(query, metrics, slow_threshold_ms) → (list[str], list[str])`

Entry point. Returns a tuple of `(warnings, suggestions)`.

**Flow:**

```
1. Check for slow query (execution_time_ms > threshold)
2. Dispatch to query-type-specific analyzer:
   - SELECT  → _analyze_select()
   - INSERT/UPDATE/DELETE → _analyze_dml()
3. Run general plan analysis → _analyze_plan_metrics()
4. Return (warnings, suggestions)
```

## SELECT Analysis

### `_analyze_select(query, metrics, warnings, suggestions)`

Checks the query text and plan metrics for common SELECT performance issues.

| Check | Detection Method | Output |
|-------|-----------------|--------|
| **SELECT \*** | Regex: `SELECT\s+\*` | Suggestion: specify columns |
| **Missing WHERE** | String search: `WHERE` not in query (and no `JOIN`) | Suggestion: add filters |
| **Large result set** | `estimated_rows > 1000` or `actual_rows > 1000`, no `LIMIT`/`TOP` | Suggestion: use LIMIT |
| **Sequential scan** | `metrics.has_sequential_scan` | Warning per table in `tables_scanned` |
| **Missing index** | `metrics.missing_index_likely` | Warning |
| **High cost** | `metrics.total_cost > 10000` | Warning with cost value |
| **Filter columns** | Extracts WHERE columns → suggests indexes | Suggestion per column |

## DML Analysis

### `_analyze_dml(query, query_type, metrics, warnings, suggestions)`

| Query Type | Check | Output |
|------------|-------|--------|
| **INSERT** | Always | Suggest batch operations (multi-row VALUES or COPY) |
| **UPDATE/DELETE** | No WHERE clause | Warning: affects ALL rows |
| **UPDATE/DELETE** | Has WHERE clause | Suggest index on WHERE columns |
| **All DML** | Always | Suggest checking triggers |
| **All DML** | Always | Suggest reviewing FK constraints |

## Plan-Level Analysis

### `_analyze_plan_metrics(metrics, warnings, suggestions)`

Generates warnings from boolean flags in `PlanMetrics`:

| Flag | Warning | Suggestion |
|------|---------|------------|
| `has_nested_loop` | "Nested Loop Join detected" | "Verify join conditions have indexes" |
| `has_hash_join` | "Hash Join detected — uses more memory" | — |
| `has_large_sort` | "Large sort operation (possibly spilling to disk)" | "Add index on ORDER BY / GROUP BY columns" |
| `has_bitmap_heap_scan` | "Bitmap Heap Scan — partial index usage" | "Consider more selective index" |
| `has_temp_disk_usage` | "Temporary disk usage — work_mem may be too low" | "Increase work_mem or optimize query" |

## WHERE Column Extraction

### `_extract_where_columns(query) → list[str]`

Heuristic extraction of column names from WHERE clauses using regex.

**Algorithm:**

```
1. Find WHERE clause content (text between WHERE and GROUP/ORDER/LIMIT/HAVING/end)
2. Match patterns: column = value, column > value, column IN (...), column LIKE ...
3. Filter out SQL keywords (AND, OR, NOT, NULL, TRUE, FALSE, etc.)
4. Return column names (may include table.column format)
```

**Regex pattern:**
```python
r"(\b[\w]+(?:\.[\w]+)?)\s*(?:=|!=|<>|>=|<=|>|<|\bIN\b|\bLIKE\b|\bBETWEEN\b|\bIS\b)"
```

**Limitations:**
- This is a heuristic parser, not a full SQL parser
- May miss complex expressions like `LOWER(column) = value`
- May include false positives for function names before operators
- Works well for common patterns: `WHERE age > 30`, `WHERE status = 'active'`

## Output Example

For a query like `SELECT * FROM users WHERE age > 30`:

```
warnings = [
    "Sequential Scan detected on table 'users'",
    "Missing index likely — filter applied during sequential scan"
]
suggestions = [
    "Avoid SELECT * — specify only the columns you need to reduce I/O",
    "Create index on filtered column: age"
]
```
