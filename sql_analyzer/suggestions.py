"""Performance suggestion engine.

Generates actionable performance improvement suggestions based on
query type and EXPLAIN plan analysis results.
"""

import logging
import re
from typing import List

from .plan_analyzer import PlanMetrics
from .sql_parser import get_query_type

logger = logging.getLogger(__name__)


def generate_suggestions(
    query: str,
    metrics: PlanMetrics,
    slow_threshold_ms: float = 500.0,
) -> tuple[List[str], List[str]]:
    """Generate performance warnings and suggestions for a query.

    Args:
        query: The SQL query text.
        metrics: Plan analysis metrics.
        slow_threshold_ms: Threshold for slow query warning (ms).

    Returns:
        Tuple of (warnings, suggestions).
    """
    warnings: List[str] = []
    suggestions: List[str] = []

    query_type = get_query_type(query)

    # Check for slow query
    if metrics.execution_time_ms > slow_threshold_ms:
        warnings.append(
            f"SLOW QUERY: Execution time {metrics.execution_time_ms:.2f} ms "
            f"exceeds threshold of {slow_threshold_ms:.0f} ms"
        )

    # Query-type-specific analysis
    if query_type == "SELECT":
        _analyze_select(query, metrics, warnings, suggestions)
    elif query_type in ("INSERT", "UPDATE", "DELETE"):
        _analyze_dml(query, query_type, metrics, warnings, suggestions)

    # General suggestions based on plan metrics
    _analyze_plan_metrics(metrics, warnings, suggestions)

    return warnings, suggestions


def _analyze_select(
    query: str,
    metrics: PlanMetrics,
    warnings: List[str],
    suggestions: List[str],
) -> None:
    """Analyze SELECT query for performance issues.

    Args:
        query: SELECT query text.
        metrics: Plan metrics.
        warnings: List to append warnings to.
        suggestions: List to append suggestions to.
    """
    query_upper = query.strip().upper()

    # Detect SELECT *
    if re.search(r"SELECT\s+\*", query_upper):
        suggestions.append(
            "Avoid SELECT * — specify only the columns you need to reduce I/O"
        )

    # Check for missing WHERE clause
    if "WHERE" not in query_upper and "JOIN" not in query_upper:
        suggestions.append(
            "No WHERE clause detected — consider adding filters to limit results"
        )

    # Suggest LIMIT for potentially large result sets
    if "LIMIT" not in query_upper and "TOP" not in query_upper:
        if metrics.estimated_rows > 1000 or metrics.actual_rows > 1000:
            suggestions.append(
                "Large result set detected — consider using LIMIT to restrict rows"
            )

    # Sequential scan warnings
    if metrics.has_sequential_scan:
        for table in metrics.tables_scanned:
            warnings.append(f"Sequential Scan detected on table '{table}'")

        # Extract filter columns for index suggestion
        filter_cols = _extract_where_columns(query)
        for col in filter_cols:
            suggestions.append(
                f"Create index on filtered column: {col}"
            )

    # Missing index
    if metrics.missing_index_likely:
        warnings.append("Missing index likely — filter applied during sequential scan")

    # High cost warning
    if metrics.total_cost > 10000:
        warnings.append(f"High cost query: estimated cost = {metrics.total_cost:.1f}")


def _analyze_dml(
    query: str,
    query_type: str,
    metrics: PlanMetrics,
    warnings: List[str],
    suggestions: List[str],
) -> None:
    """Analyze INSERT/UPDATE/DELETE query for performance issues.

    Args:
        query: DML query text.
        query_type: 'INSERT', 'UPDATE', or 'DELETE'.
        metrics: Plan metrics.
        warnings: List to append warnings to.
        suggestions: List to append suggestions to.
    """
    query_upper = query.strip().upper()

    # Suggest batch operations for INSERT
    if query_type == "INSERT":
        suggestions.append(
            "Consider batch INSERT operations for better performance "
            "(e.g., multi-row VALUES or COPY)"
        )

    # Check UPDATE/DELETE without WHERE
    if query_type in ("UPDATE", "DELETE") and "WHERE" not in query_upper:
        warnings.append(
            f"{query_type} without WHERE clause — this affects ALL rows in the table"
        )

    # Indexing suggestion for WHERE columns in UPDATE/DELETE
    if query_type in ("UPDATE", "DELETE") and "WHERE" in query_upper:
        filter_cols = _extract_where_columns(query)
        for col in filter_cols:
            suggestions.append(
                f"Ensure index exists on WHERE column: {col}"
            )

    # Trigger warning
    suggestions.append(
        "Check for unnecessary triggers that may slow down DML operations"
    )

    # Foreign key constraint check
    suggestions.append(
        "Review foreign key constraints — cascading actions can impact performance"
    )


def _analyze_plan_metrics(
    metrics: PlanMetrics,
    warnings: List[str],
    suggestions: List[str],
) -> None:
    """Generate warnings and suggestions from plan-level metrics.

    Args:
        metrics: Plan analysis metrics.
        warnings: List to append warnings to.
        suggestions: List to append suggestions to.
    """
    # Nested loop warning
    if metrics.has_nested_loop:
        warnings.append("Nested Loop Join detected — may be slow on large datasets")
        suggestions.append(
            "Verify join conditions have proper indexes to avoid nested loop scans"
        )

    # Hash join note
    if metrics.has_hash_join:
        warnings.append(
            "Hash Join detected — acceptable for large joins but uses more memory"
        )

    # Large sort
    if metrics.has_large_sort:
        warnings.append("Large sort operation detected (possibly spilling to disk)")
        suggestions.append(
            "Add index on ORDER BY / GROUP BY columns to avoid in-memory sorting"
        )

    # Bitmap heap scan
    if metrics.has_bitmap_heap_scan:
        warnings.append("Bitmap Heap Scan detected — partial index usage")
        suggestions.append(
            "Consider a more selective index or adjust query filters"
        )

    # Temporary disk usage
    if metrics.has_temp_disk_usage:
        warnings.append("Temporary disk usage detected — work_mem may be too low")
        suggestions.append(
            "Increase work_mem setting or optimize query to reduce data volume"
        )


def _extract_where_columns(query: str) -> List[str]:
    """Extract column names referenced in WHERE clause.

    Simple heuristic extraction — not a full SQL parser.

    Args:
        query: SQL query text.

    Returns:
        List of column references found in WHERE conditions.
    """
    columns: List[str] = []

    # Find WHERE clause content
    where_match = re.search(
        r"\bWHERE\b\s+(.*?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|\bHAVING\b|$)",
        query,
        re.IGNORECASE | re.DOTALL,
    )
    if not where_match:
        return columns

    where_clause = where_match.group(1)

    # Extract column references from common patterns:
    # column = value, column > value, column IN (...), column LIKE ...
    col_patterns = re.findall(
        r"(\b[\w]+(?:\.[\w]+)?)\s*(?:=|!=|<>|>=|<=|>|<|\bIN\b|\bLIKE\b|\bBETWEEN\b|\bIS\b)",
        where_clause,
        re.IGNORECASE,
    )

    # Filter out SQL keywords and values
    sql_keywords = {
        "AND", "OR", "NOT", "NULL", "TRUE", "FALSE", "IN", "LIKE",
        "BETWEEN", "IS", "EXISTS", "ANY", "ALL", "SOME",
    }

    for col in col_patterns:
        if col.upper() not in sql_keywords:
            columns.append(col)

    return list(dict.fromkeys(columns))  # Deduplicate while preserving order
