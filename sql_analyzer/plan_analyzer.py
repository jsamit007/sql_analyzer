"""Query plan analyzer for EXPLAIN output parsing.

Parses EXPLAIN (JSON) output from PostgreSQL, text-based plans from
SQL Server, and EXPLAIN QUERY PLAN output from SQLite.
Extracts cost, timing, rows, buffers, and detects performance anti-patterns.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlanMetrics:
    """Extracted metrics from a query execution plan."""

    # Cost estimates
    startup_cost: float = 0.0
    total_cost: float = 0.0

    # Actual timing (only from EXPLAIN ANALYZE)
    actual_time_ms: float = 0.0

    # Row estimates
    estimated_rows: int = 0
    actual_rows: int = 0

    # Buffer statistics
    shared_hit_blocks: int = 0
    shared_read_blocks: int = 0
    temp_read_blocks: int = 0
    temp_written_blocks: int = 0

    # Planning and execution time
    planning_time_ms: float = 0.0
    execution_time_ms: float = 0.0

    # Detected patterns
    node_types: List[str] = field(default_factory=list)
    scan_types: List[str] = field(default_factory=list)
    join_types: List[str] = field(default_factory=list)
    tables_scanned: List[str] = field(default_factory=list)

    # Issues detected
    has_sequential_scan: bool = False
    has_full_table_scan: bool = False
    has_nested_loop: bool = False
    has_hash_join: bool = False
    has_large_sort: bool = False
    has_bitmap_heap_scan: bool = False
    has_temp_disk_usage: bool = False
    missing_index_likely: bool = False

    # Performance score (1-10, 10 = best)
    performance_score: int = 10


def analyze_query_plan(
    explain_output: Optional[str],
    execution_time_ms: float = 0.0,
    slow_threshold_ms: float = 500.0,
    db_type: str = "postgres",
) -> PlanMetrics:
    """Analyze an EXPLAIN output and extract metrics.

    Args:
        explain_output: Raw EXPLAIN output (JSON or text).
        execution_time_ms: Measured execution time in milliseconds.
        slow_threshold_ms: Threshold for marking as slow.
        db_type: Database type ('postgres', 'sqlserver', 'sqlite').

    Returns:
        PlanMetrics with extracted data and detected issues.
    """
    metrics = PlanMetrics()
    metrics.execution_time_ms = execution_time_ms

    if not explain_output:
        return metrics

    if db_type == "sqlite":
        _parse_sqlite_plan(explain_output, metrics)
    else:
        # Try parsing as JSON first (PostgreSQL JSON format)
        try:
            plan_data = json.loads(explain_output)
            if isinstance(plan_data, list) and len(plan_data) > 0:
                _parse_postgres_json_plan(plan_data[0], metrics)
        except (json.JSONDecodeError, TypeError):
            # Fall back to text-based parsing
            _parse_text_plan(explain_output, metrics)

    # Calculate performance score
    metrics.performance_score = _calculate_score(metrics, slow_threshold_ms)

    return metrics


def _parse_postgres_json_plan(plan_data: Dict[str, Any], metrics: PlanMetrics) -> None:
    """Parse PostgreSQL JSON EXPLAIN output recursively.

    Args:
        plan_data: Parsed JSON plan dictionary.
        metrics: PlanMetrics to populate.
    """
    # Extract top-level timing info
    if "Planning Time" in plan_data:
        metrics.planning_time_ms = plan_data["Planning Time"]
    if "Execution Time" in plan_data:
        metrics.actual_time_ms = plan_data["Execution Time"]

    # Parse the plan tree
    if "Plan" in plan_data:
        _walk_plan_node(plan_data["Plan"], metrics)


def _walk_plan_node(node: Dict[str, Any], metrics: PlanMetrics) -> None:
    """Recursively walk a plan node tree and extract metrics.

    Args:
        node: A plan node dictionary.
        metrics: PlanMetrics to populate.
    """
    node_type = node.get("Node Type", "")
    metrics.node_types.append(node_type)

    # Extract cost
    startup_cost = node.get("Startup Cost", 0.0)
    total_cost = node.get("Total Cost", 0.0)
    if total_cost > metrics.total_cost:
        metrics.total_cost = total_cost
        metrics.startup_cost = startup_cost

    # Extract row estimates
    metrics.estimated_rows += node.get("Plan Rows", 0)
    metrics.actual_rows += node.get("Actual Rows", 0)

    # Extract buffer info
    if "Shared Hit Blocks" in node:
        metrics.shared_hit_blocks += node["Shared Hit Blocks"]
    if "Shared Read Blocks" in node:
        metrics.shared_read_blocks += node["Shared Read Blocks"]
    if "Temp Read Blocks" in node:
        metrics.temp_read_blocks += node["Temp Read Blocks"]
        if node["Temp Read Blocks"] > 0:
            metrics.has_temp_disk_usage = True
    if "Temp Written Blocks" in node:
        metrics.temp_written_blocks += node["Temp Written Blocks"]
        if node["Temp Written Blocks"] > 0:
            metrics.has_temp_disk_usage = True

    # Detect scan types
    scan_types = {"Seq Scan", "Index Scan", "Index Only Scan", "Bitmap Index Scan",
                  "Bitmap Heap Scan", "Tid Scan"}
    if node_type in scan_types:
        metrics.scan_types.append(node_type)
        table = node.get("Relation Name", "unknown")
        if table not in metrics.tables_scanned:
            metrics.tables_scanned.append(table)

    # Detect sequential scan
    if node_type == "Seq Scan":
        metrics.has_sequential_scan = True
        metrics.has_full_table_scan = True
        # If there's a filter on Seq Scan, likely missing index
        if node.get("Filter"):
            metrics.missing_index_likely = True

    # Detect bitmap heap scan
    if node_type == "Bitmap Heap Scan":
        metrics.has_bitmap_heap_scan = True

    # Detect join types
    join_types = {"Nested Loop", "Hash Join", "Merge Join"}
    if node_type in join_types:
        metrics.join_types.append(node_type)

    if node_type == "Nested Loop":
        metrics.has_nested_loop = True
    if node_type == "Hash Join":
        metrics.has_hash_join = True

    # Detect large sort
    if node_type == "Sort":
        sort_method = node.get("Sort Method", "")
        if "disk" in sort_method.lower() or "external" in sort_method.lower():
            metrics.has_large_sort = True
        # Large sort by row count
        plan_rows = node.get("Plan Rows", 0)
        if plan_rows > 10000:
            metrics.has_large_sort = True

    # Recurse into child plans
    for child in node.get("Plans", []):
        _walk_plan_node(child, metrics)


def _parse_text_plan(explain_text: str, metrics: PlanMetrics) -> None:
    """Parse text-based EXPLAIN output (SQL Server or PostgreSQL text format).

    Args:
        explain_text: Text EXPLAIN output.
        metrics: PlanMetrics to populate.
    """
    lines = explain_text.lower()

    # Detect scan types
    if "seq scan" in lines or "table scan" in lines or "clustered index scan" in lines:
        metrics.has_sequential_scan = True
        metrics.has_full_table_scan = True

    if "nested loop" in lines or "nested loops" in lines:
        metrics.has_nested_loop = True
        metrics.join_types.append("Nested Loop")

    if "hash join" in lines or "hash match" in lines:
        metrics.has_hash_join = True
        metrics.join_types.append("Hash Join")

    if "bitmap heap scan" in lines:
        metrics.has_bitmap_heap_scan = True

    if "sort" in lines:
        if "disk" in lines or "external" in lines:
            metrics.has_large_sort = True

    # Extract cost from text format (cost=X..Y)
    cost_match = re.search(r"cost=(\d+\.?\d*)\.\.([\d.]+)", explain_text)
    if cost_match:
        metrics.startup_cost = float(cost_match.group(1))
        metrics.total_cost = float(cost_match.group(2))

    # Extract rows from text format
    rows_match = re.search(r"rows=(\d+)", explain_text)
    if rows_match:
        metrics.estimated_rows = int(rows_match.group(1))

    # Check for missing index hints
    if "filter:" in lines and "seq scan" in lines:
        metrics.missing_index_likely = True


def _parse_sqlite_plan(explain_text: str, metrics: PlanMetrics) -> None:
    """Parse SQLite EXPLAIN QUERY PLAN output.

    SQLite plan keywords:
    - SCAN <table>              — full table scan (no index)
    - SEARCH <table> USING INDEX — indexed lookup
    - SEARCH <table> USING COVERING INDEX — index-only scan
    - SEARCH <table> USING INTEGER PRIMARY KEY — rowid lookup
    - USING TEMPORARY B-TREE    — temp sort / GROUP BY / DISTINCT
    - COMPOUND SUBQUERIES       — UNION operations
    - CO-ROUTINE / SUBQUERY     — subquery execution
    - USE TEMP B-TREE FOR ORDER BY — sort spill

    Args:
        explain_text: SQLite EXPLAIN QUERY PLAN text output.
        metrics: PlanMetrics to populate.
    """
    for raw_line in explain_text.splitlines():
        line = raw_line.strip().lstrip("|- ")
        line_lower = line.lower()

        # --- SCAN (full table scan, no index) ---
        scan_match = re.match(r"SCAN\s+(\w+)", line, re.IGNORECASE)
        if scan_match:
            table = scan_match.group(1)
            metrics.node_types.append("SCAN")
            metrics.scan_types.append("Full Table Scan")
            if table not in metrics.tables_scanned:
                metrics.tables_scanned.append(table)
            metrics.has_sequential_scan = True
            metrics.has_full_table_scan = True
            # If there's a filter (WHERE) on a SCAN, index is likely missing
            metrics.missing_index_likely = True
            continue

        # --- SEARCH with index ---
        search_match = re.match(
            r"SEARCH\s+(\w+)\s+USING\s+(.+)", line, re.IGNORECASE
        )
        if search_match:
            table = search_match.group(1)
            using_detail = search_match.group(2).strip()
            metrics.node_types.append("SEARCH")
            if table not in metrics.tables_scanned:
                metrics.tables_scanned.append(table)

            if "covering index" in using_detail.lower():
                metrics.scan_types.append("Covering Index Scan")
            elif "integer primary key" in using_detail.lower():
                metrics.scan_types.append("Primary Key Lookup")
            elif "automatic" in using_detail.lower():
                # Auto-index created by SQLite — not ideal
                metrics.scan_types.append("Automatic Index")
                metrics.missing_index_likely = True
            else:
                metrics.scan_types.append("Index Scan")
            continue

        # --- USING TEMPORARY B-TREE (sort / group / distinct) ---
        if "temporary b-tree" in line_lower or "temp b-tree" in line_lower:
            metrics.node_types.append("Temporary B-Tree")
            metrics.has_large_sort = True
            if "order by" in line_lower:
                metrics.scan_types.append("Temp Sort (ORDER BY)")
            elif "group by" in line_lower:
                metrics.scan_types.append("Temp Sort (GROUP BY)")
            elif "distinct" in line_lower:
                metrics.scan_types.append("Temp Sort (DISTINCT)")
            else:
                metrics.scan_types.append("Temp Sort")
            continue

        # --- Compound subqueries (UNION etc.) ---
        if "compound subqueries" in line_lower:
            metrics.node_types.append("Compound Subqueries")
            continue

        # --- Co-routine / Subquery ---
        if "co-routine" in line_lower or "coroutine" in line_lower:
            metrics.node_types.append("Co-Routine")
            continue
        if line_lower.startswith("subquery"):
            metrics.node_types.append("Subquery")
            continue

        # --- Catch-all: record any remaining node text ---
        if line:
            metrics.node_types.append(line)


def _calculate_score(metrics: PlanMetrics, slow_threshold_ms: float) -> int:
    """Calculate a performance score from 1-10.

    Args:
        metrics: Extracted plan metrics.
        slow_threshold_ms: Threshold for slow query (ms).

    Returns:
        Score from 1 (worst) to 10 (best).
    """
    score = 10

    # Deduct for slow execution
    if metrics.execution_time_ms > slow_threshold_ms:
        score -= 3
    elif metrics.execution_time_ms > slow_threshold_ms / 2:
        score -= 1

    # Deduct for sequential / full table scan
    if metrics.has_sequential_scan:
        score -= 2

    # Deduct for missing index
    if metrics.missing_index_likely:
        score -= 1

    # Deduct for nested loops (can be expensive)
    if metrics.has_nested_loop:
        score -= 1

    # Deduct for large sort operations
    if metrics.has_large_sort:
        score -= 1

    # Deduct for temporary disk usage
    if metrics.has_temp_disk_usage:
        score -= 1

    # Deduct for high cost
    if metrics.total_cost > 10000:
        score -= 1
    elif metrics.total_cost > 1000:
        score -= 0  # mild warning only

    # Clamp to 1-10
    return max(1, min(10, score))


def get_plan_summary(metrics: PlanMetrics) -> Dict[str, Any]:
    """Get a summary dictionary of the plan analysis.

    Args:
        metrics: Analyzed plan metrics.

    Returns:
        Dictionary with key plan metrics for reporting.
    """
    return {
        "total_cost": metrics.total_cost,
        "estimated_rows": metrics.estimated_rows,
        "actual_rows": metrics.actual_rows,
        "planning_time_ms": round(metrics.planning_time_ms, 2),
        "execution_time_ms": round(metrics.execution_time_ms, 2),
        "shared_hit_blocks": metrics.shared_hit_blocks,
        "shared_read_blocks": metrics.shared_read_blocks,
        "temp_disk_usage": metrics.has_temp_disk_usage,
        "node_types": metrics.node_types,
        "join_types": metrics.join_types,
        "tables_scanned": metrics.tables_scanned,
        "performance_score": metrics.performance_score,
        "issues": {
            "sequential_scan": metrics.has_sequential_scan,
            "full_table_scan": metrics.has_full_table_scan,
            "missing_index": metrics.missing_index_likely,
            "nested_loop": metrics.has_nested_loop,
            "hash_join": metrics.has_hash_join,
            "large_sort": metrics.has_large_sort,
            "bitmap_heap_scan": metrics.has_bitmap_heap_scan,
            "temp_disk_usage": metrics.has_temp_disk_usage,
        },
    }
