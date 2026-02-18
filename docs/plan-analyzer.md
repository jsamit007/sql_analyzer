# Plan Analyzer

**Module:** `sql_analyzer/plan_analyzer.py`

Parses EXPLAIN output from all three database backends, extracts performance metrics, detects anti-patterns, and assigns a performance score (1-10).

## `PlanMetrics` Dataclass

Structured output from plan analysis.

### Cost & Timing Fields

| Field | Type | Description |
|-------|------|-------------|
| `startup_cost` | `float` | Cost before first row is returned |
| `total_cost` | `float` | Total estimated cost |
| `actual_time_ms` | `float` | Actual time from EXPLAIN ANALYZE |
| `planning_time_ms` | `float` | Query planning overhead |
| `execution_time_ms` | `float` | Measured execution time (passed in) |

### Row & Buffer Fields

| Field | Type | Description |
|-------|------|-------------|
| `estimated_rows` | `int` | Planner's row estimate |
| `actual_rows` | `int` | Actual rows (ANALYZE only) |
| `shared_hit_blocks` | `int` | Buffer cache hits |
| `shared_read_blocks` | `int` | Disk reads |
| `temp_read_blocks` | `int` | Temp file reads |
| `temp_written_blocks` | `int` | Temp file writes |

### Detection Lists

| Field | Type | Contains |
|-------|------|----------|
| `node_types` | `list[str]` | All plan node types encountered |
| `scan_types` | `list[str]` | Scan types: "Seq Scan", "Index Scan", "Full Table Scan", etc. |
| `join_types` | `list[str]` | Join types: "Nested Loop", "Hash Join", "Merge Join" |
| `tables_scanned` | `list[str]` | Table names referenced in the plan |

### Boolean Issue Flags

| Flag | Meaning |
|------|---------|
| `has_sequential_scan` | Full table scan detected |
| `has_full_table_scan` | Alias for sequential scan |
| `has_nested_loop` | Nested loop join present |
| `has_hash_join` | Hash join present |
| `has_large_sort` | Sort spilling to disk or large row count |
| `has_bitmap_heap_scan` | Partial index usage |
| `has_temp_disk_usage` | Temp blocks read/written > 0 |
| `missing_index_likely` | Filter on sequential scan = likely missing index |

## `analyze_query_plan(explain_output, execution_time_ms, slow_threshold_ms, db_type) → PlanMetrics`

Entry point. Dispatches to the correct parser based on `db_type`:

```
if db_type == "sqlite":
    _parse_sqlite_plan()
else:
    try JSON parse → _parse_postgres_json_plan()
    except → _parse_text_plan()
```

After parsing, calls `_calculate_score()` to set `performance_score`.

## PostgreSQL Parser

### `_parse_postgres_json_plan(plan_data, metrics)`

Handles PostgreSQL `EXPLAIN (FORMAT JSON)` output.

Top-level extraction:
- `Planning Time`, `Execution Time`

Then recursively walks the plan tree via `_walk_plan_node()`.

### `_walk_plan_node(node, metrics)`

Recursive function that processes each node in the PostgreSQL plan tree:

```
1. Extract Node Type (e.g., "Seq Scan", "Index Scan", "Hash Join")
2. Track max cost (Startup Cost, Total Cost)
3. Accumulate row estimates and buffer stats
4. Detect scan type → set has_sequential_scan, etc.
5. Check for Filter on Seq Scan → set missing_index_likely
6. Detect join type → set has_nested_loop/has_hash_join
7. Detect Sort with disk spill → set has_large_sort
8. Recurse into node["Plans"] children
```

**Key detection rules:**

| Node Type | Sets |
|-----------|------|
| `Seq Scan` | `has_sequential_scan`, `has_full_table_scan` |
| `Seq Scan` + `Filter` | `missing_index_likely` |
| `Bitmap Heap Scan` | `has_bitmap_heap_scan` |
| `Nested Loop` | `has_nested_loop` |
| `Hash Join` | `has_hash_join` |
| `Sort` + disk method | `has_large_sort` |
| `Sort` + rows > 10000 | `has_large_sort` |
| `Temp Read Blocks > 0` | `has_temp_disk_usage` |

## SQL Server Parser

### `_parse_text_plan(explain_text, metrics)`

Parses text-based SHOWPLAN output. Uses keyword searches on lowercased text:

| Keyword | Detection |
|---------|-----------|
| `seq scan`, `table scan`, `clustered index scan` | Sequential scan |
| `nested loop`, `nested loops` | Nested loop join |
| `hash join`, `hash match` | Hash join |
| `bitmap heap scan` | Bitmap heap scan |
| `sort` + `disk` / `external` | Large sort |
| `filter:` + `seq scan` | Missing index |

Also extracts `cost=X..Y` and `rows=N` via regex.

## SQLite Parser

### `_parse_sqlite_plan(explain_text, metrics)`

Parses SQLite `EXPLAIN QUERY PLAN` output line by line. Each line is stripped of `|--` prefixes before matching.

**Keyword mapping:**

| Pattern | Detection | Scan Type |
|---------|-----------|-----------|
| `SCAN <table>` | Full table scan, missing index | "Full Table Scan" |
| `SEARCH <table> USING COVERING INDEX` | Indexed | "Covering Index Scan" |
| `SEARCH <table> USING INTEGER PRIMARY KEY` | Indexed | "Primary Key Lookup" |
| `SEARCH <table> USING AUTOMATIC ...` | Auto-index | "Automatic Index" + missing index |
| `SEARCH <table> USING ...` (other) | Indexed | "Index Scan" |
| `TEMPORARY B-TREE` / `TEMP B-TREE` | Sort spill | "Temp Sort (ORDER BY/GROUP BY/DISTINCT)" |
| `COMPOUND SUBQUERIES` | — | — |
| `CO-ROUTINE` / `COROUTINE` | — | — |
| `SUBQUERY` | — | — |

## Performance Scoring

### `_calculate_score(metrics, slow_threshold_ms) → int`

Simple point-deduction system starting from 10:

| Condition | Deduction |
|-----------|-----------|
| `execution_time_ms > slow_threshold_ms` | -3 |
| `execution_time_ms > slow_threshold_ms / 2` | -1 |
| `has_sequential_scan` | -2 |
| `missing_index_likely` | -1 |
| `has_nested_loop` | -1 |
| `has_large_sort` | -1 |
| `has_temp_disk_usage` | -1 |
| `total_cost > 10000` | -1 |

Result is clamped to range `[1, 10]`.

## `get_plan_summary(metrics) → dict`

Returns a dictionary summary suitable for JSON reports, including all key metrics and a nested `issues` dictionary of boolean flags.
