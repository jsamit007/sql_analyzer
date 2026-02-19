"""Query execution engine with precise timing and error handling.

Executes SQL statements sequentially, measures execution time using
time.perf_counter(), and captures rows affected.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .db_connector import DatabaseConnector
from .sql_parser import get_query_type

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a single query execution."""

    query_number: int
    query_text: str
    query_type: str
    line_number: int = 0
    execution_time_ms: float = 0.0
    rows_affected: int = 0
    success: bool = True
    error_message: Optional[str] = None
    explain_output: Optional[str] = None
    explain_data: Optional[List[Dict[str, Any]]] = None
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    performance_score: Optional[int] = None
    is_slow: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a dictionary for serialization."""
        return {
            "query_number": self.query_number,
            "line_number": self.line_number,
            "query_text": self.query_text,
            "query_type": self.query_type,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "rows_affected": self.rows_affected,
            "success": self.success,
            "error_message": self.error_message,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "performance_score": self.performance_score,
            "is_slow": self.is_slow,
        }


def execute_query(
    connector: DatabaseConnector,
    query: str,
    query_number: int,
    explain_analyze: bool = False,
    line_number: int = 0,
) -> QueryResult:
    """Execute a single SQL query and measure its performance.

    Args:
        connector: Active database connector.
        query: SQL statement to execute.
        query_number: Sequential number of this query.
        explain_analyze: Whether to run EXPLAIN ANALYZE for SELECT queries.
        line_number: 1-based line number of the query in the original SQL file.

    Returns:
        QueryResult with timing, row count, and status.
    """
    query_type = get_query_type(query)
    result = QueryResult(
        query_number=query_number,
        query_text=query,
        query_type=query_type,
        line_number=line_number,
    )

    # Execute the main query
    try:
        with connector.cursor() as cur:
            # Measure execution time with high precision
            start_time = time.perf_counter()
            cur.execute(query)
            end_time = time.perf_counter()

            result.execution_time_ms = (end_time - start_time) * 1000.0

            # Get rows affected
            if query_type == "SELECT":
                rows = cur.fetchall()
                result.rows_affected = len(rows)
            elif cur.rowcount >= 0:
                result.rows_affected = cur.rowcount

            # Commit successful query
            connector.commit()

            logger.info(
                "Query #%d executed in %.2f ms (%d rows)",
                query_number,
                result.execution_time_ms,
                result.rows_affected,
            )

    except Exception as e:
        result.success = False
        result.error_message = str(e)
        connector.rollback()
        logger.error("Query #%d failed: %s", query_number, e)

    # Run EXPLAIN for SELECT queries (separate execution)
    if result.success and query_type == "SELECT":
        try:
            explain_output = _run_explain(connector, query, explain_analyze)
            result.explain_output = explain_output
        except Exception as e:
            logger.warning("EXPLAIN failed for query #%d: %s", query_number, e)

    return result


def _run_explain(
    connector: DatabaseConnector,
    query: str,
    analyze: bool = False,
) -> Optional[str]:
    """Run EXPLAIN on a query and return the plan output.

    Args:
        connector: Active database connector.
        query: The SELECT query to explain.
        analyze: If True, use EXPLAIN ANALYZE (actually executes the query).

    Returns:
        The EXPLAIN output as a string, or None on failure.
    """
    if connector.db_type == "postgres":
        return _run_explain_postgres(connector, query, analyze)
    elif connector.db_type == "sqlserver":
        return _run_explain_sqlserver(connector, query)
    elif connector.db_type == "sqlite":
        return _run_explain_sqlite(connector, query)
    return None


def _run_explain_postgres(
    connector: DatabaseConnector,
    query: str,
    analyze: bool = False,
) -> Optional[str]:
    """Run EXPLAIN on PostgreSQL.

    Uses JSON format for structured output parsing.
    """
    explain_prefix = "EXPLAIN (FORMAT JSON, BUFFERS ON"
    if analyze:
        explain_prefix += ", ANALYZE ON"
    explain_prefix += ")"

    explain_query = f"{explain_prefix} {query}"

    try:
        with connector.cursor() as cur:
            cur.execute(explain_query)
            rows = cur.fetchall()
            connector.commit()

            if rows:
                # PostgreSQL returns JSON plan in first column of first row
                import json

                plan_data = rows[0][0]
                if isinstance(plan_data, list):
                    return json.dumps(plan_data, indent=2)
                return str(plan_data)
    except Exception as e:
        connector.rollback()
        logger.warning("PostgreSQL EXPLAIN failed: %s", e)

    return None


def _run_explain_sqlserver(
    connector: DatabaseConnector,
    query: str,
) -> Optional[str]:
    """Run estimated execution plan on SQL Server.

    Uses SET SHOWPLAN_TEXT for text-based plan output.
    """
    try:
        with connector.cursor() as cur:
            # Enable showplan
            cur.execute("SET SHOWPLAN_TEXT ON")
            cur.execute(query)

            plans = []
            while True:
                rows = cur.fetchall()
                if rows:
                    for row in rows:
                        plans.append(str(row[0]))
                if not cur.nextset():
                    break

            # Disable showplan
            cur.execute("SET SHOWPLAN_TEXT OFF")
            connector.commit()

            return "\n".join(plans) if plans else None
    except Exception as e:
        connector.rollback()
        logger.warning("SQL Server EXPLAIN failed: %s", e)

    return None


def _run_explain_sqlite(
    connector: DatabaseConnector,
    query: str,
) -> Optional[str]:
    """Run EXPLAIN QUERY PLAN on SQLite.

    Returns structured text plan output with tree indentation.
    """
    explain_query = f"EXPLAIN QUERY PLAN {query}"

    try:
        with connector.cursor() as cur:
            cur.execute(explain_query)
            rows = cur.fetchall()
            connector.commit()

            if rows:
                # SQLite returns (id, parent, notused, detail)
                # Build indented tree from parent relationships
                nodes = []
                for row in rows:
                    node_id = row[0] if len(row) > 0 else 0
                    parent_id = row[1] if len(row) > 1 else 0
                    detail = row[3] if len(row) > 3 else str(row)
                    nodes.append((node_id, parent_id, str(detail)))

                # Calculate indent level from parent chain
                def _get_depth(nid, node_map, depth=0):
                    if nid not in node_map:
                        return depth
                    pid = node_map[nid]
                    if pid == 0 or pid == nid:
                        return depth
                    return _get_depth(pid, node_map, depth + 1)

                node_map = {n[0]: n[1] for n in nodes}
                lines = []
                for node_id, parent_id, detail in nodes:
                    depth = _get_depth(node_id, node_map)
                    indent = "  " * depth
                    lines.append(f"{indent}|--{detail}")

                return "\n".join(lines)
    except Exception as e:
        connector.rollback()
        logger.warning("SQLite EXPLAIN failed: %s", e)

    return None


def execute_all_queries(
    connector: DatabaseConnector,
    queries: List[tuple],
    explain_analyze: bool = False,
    continue_on_error: bool = True,
) -> List[QueryResult]:
    """Execute all queries sequentially and collect results.

    Args:
        connector: Active database connector.
        queries: List of (sql_statement, line_number) tuples.
        explain_analyze: Whether to run EXPLAIN ANALYZE for SELECT queries.
        continue_on_error: If True, continue executing after a query fails.

    Returns:
        List of QueryResult objects.
    """
    results: List[QueryResult] = []

    for idx, (query, line_num) in enumerate(queries, start=1):
        logger.info("Executing query #%d (line %d)...", idx, line_num)
        result = execute_query(connector, query, idx, explain_analyze, line_number=line_num)
        results.append(result)

        if not result.success and not continue_on_error:
            logger.error(
                "Stopping execution at query #%d due to error (continue_on_error=False).",
                idx,
            )
            break

    return results


@dataclass
class BatchResult:
    """Result of executing an entire SQL file as a single script."""

    script_text: str
    total_statements: int = 0
    execution_time_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    rows_affected: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a dictionary for serialization."""
        return {
            "total_statements": self.total_statements,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "success": self.success,
            "error_message": self.error_message,
            "rows_affected": self.rows_affected,
        }


def execute_as_script(
    connector: DatabaseConnector,
    sql_content: str,
    total_statements: int = 0,
) -> BatchResult:
    """Execute the entire SQL content as a single script.

    Sends the full SQL text to the database in one call via
    ``cursor.executescript()`` (SQLite) or ``cursor.execute()``
    (PostgreSQL / SQL Server), measuring total wall-clock time.

    Args:
        connector: Active database connector.
        sql_content: Full SQL file content.
        total_statements: Number of statements (for display only).

    Returns:
        BatchResult with overall timing and status.
    """
    result = BatchResult(
        script_text=sql_content,
        total_statements=total_statements,
    )

    try:
        with connector.cursor() as cur:
            start_time = time.perf_counter()

            if connector.db_type == "sqlite":
                # SQLite supports executescript for multi-statement scripts
                cur.executescript(sql_content)
            else:
                # PostgreSQL and SQL Server can handle multi-statement strings
                cur.execute(sql_content)

            end_time = time.perf_counter()
            result.execution_time_ms = (end_time - start_time) * 1000.0

            if cur.rowcount >= 0:
                result.rows_affected = cur.rowcount

            connector.commit()

        logger.info(
            "Batch script executed in %.2f ms (%d statements)",
            result.execution_time_ms,
            total_statements,
        )

    except Exception as e:
        result.success = False
        result.error_message = str(e)
        connector.rollback()
        logger.error("Batch script failed: %s", e)

    return result
