# Report Output

**Module:** `sql_analyzer/report.py`

Handles all output: Rich colored console panels, plain text fallback, JSON export, and CSV export.

## Console Output

### `print_query_result(result, colored=True)`

Full query result — calls either `_print_query_result_rich()` or `_print_query_result_plain()`. Shows all details: timing, score, EXPLAIN plan, warnings, suggestions, and AI advice. Used in `--batch` mode.

### `print_query_result_compact(result, colored=True)`

Compact summary — shows timing, score, warnings, and suggestions, but **omits** the EXPLAIN plan and AI output. Appends an `[i]` note indicating details are available via the interactive prompt. Used in default interactive mode (`--time-queries` without `--batch`).

### `print_query_detail(result, colored=True)`

Displays only the EXPLAIN plan and AI suggestions for a single query. Called from the interactive detail prompt when the user selects a query number.

### `print_join_diagnostic(diagnostic, colored=True)`

Renders the JOIN decomposition analysis. Dispatches to `_print_join_diagnostic_rich()` or `_print_join_diagnostic_plain()`.

**Rich mode** shows:
- Panel titled "JOIN Diagnostic" with yellow border
- Table of individual table row counts (with ✓/✗ status)
- Table of incremental JOIN steps (with row counts and drop detection)
- Red-bordered panel with root cause explanation

**Plain mode** shows the same data with `=` separators and text indicators.

### `print_batch_result(batch_result, colored=True)`

Displays the result of `--batch` mode execution: success/failure, statement count, total time, rows affected. Used when the entire SQL file is run as a single script.

### `_print_query_result_rich(result)`

Renders each query result as a Rich `Panel` with dynamic border color:

| Condition | Border Color | Status Icon |
|-----------|-------------|-------------|
| Failed | `red` | `✗ FAILED` |
| Slow | `yellow` | `⚠ SLOW` |
| Score ≤ 4 | `yellow` | `⚠ NEEDS OPTIMIZATION` |
| OK | `green` | `✓ OK` |

**Panel contents:**

```
Query #N  (line M)  ✓ OK
<query text, truncated to 120 chars>

Execution Time: 0.78 ms        (cyan)
Rows Affected:  10              (cyan)
Query Type:     SELECT          (cyan)
Perf Score:     7/10            (green/yellow/red based on value)

Execution Plan:                 (white heading)
  |--SCAN users                 (dim)

Performance Warnings:           (yellow heading)
  • Sequential Scan detected    (yellow)

Suggestions:                    (cyan heading)
  → Avoid SELECT *              (bright_white)
  [AI] Index recommendations... (bright_green)
```

**Color scheme:**

| Element | Color |
|---------|-------|
| Query header | bold white |
| Line number | magenta |
| Metrics values | cyan |
| Score ≥ 8 | green |
| Score 5-7 | yellow |
| Score < 5 | red |
| EXPLAIN plan lines | dim |
| Warning heading | bold yellow |
| Warning items | yellow |
| Suggestion heading | bold cyan |
| Suggestion items | bright_white |
| AI suggestions | bright_green |

### `_print_query_result_plain(result)`

Plain text output for `--no-color` mode. Uses dashes for separators, simple formatting.

## Summary Output

### `print_summary(results, colored=True)`

Displays after all queries:

**Rich mode:**
1. Summary panel with total queries, successful, failed, slow count, total time
2. Top 3 Slowest Queries table (columns: #, Line, Time, Score, Query)
3. Optimization Summary — deduplicated suggestions across all queries (max 10)

**Plain mode:**
Same data with `=` separators and plain text formatting.

**Top 3 Slowest table columns:**

| Column | Style |
|--------|-------|
| `#` | bold |
| `Line` | magenta |
| `Time (ms)` | red |
| `Score` | yellow |
| `Query` | dim |

**Optimization Summary deduplication:**
```python
all_suggestions = []
for r in results:
    all_suggestions.extend(r.suggestions)
unique_suggestions = list(dict.fromkeys(all_suggestions))  # preserves order
```

## File Export

### `save_json_report(results, output_path)`

Generates a structured JSON file:

```json
{
  "summary": {
    "total_queries": 12,
    "successful": 12,
    "failed": 0,
    "slow_queries": 0,
    "total_execution_time_ms": 5.07,
    "top_3_slowest": [
      {
        "query_number": 10,
        "execution_time_ms": 1.11,
        "query_text": "INSERT INTO orders ..."
      }
    ]
  },
  "queries": [
    // QueryResult.to_dict() for each query
  ]
}
```

### `save_csv_report(results, output_path)`

Generates a CSV file with these columns:

| Column | Source |
|--------|--------|
| `query_number` | `result.query_number` |
| `line_number` | `result.line_number` |
| `query_type` | `result.query_type` |
| `execution_time_ms` | Rounded to 2 decimal places |
| `rows_affected` | `result.rows_affected` |
| `success` | `result.success` |
| `error_message` | Empty string if none |
| `performance_score` | Empty string if none |
| `is_slow` | `result.is_slow` |
| `warnings` | Joined with `"; "` |
| `suggestions` | Joined with `"; "` |
| `query_text` | Truncated to 200 chars |

Both export functions print a green confirmation message to the console after writing.
