"""JOIN decomposition analyzer — diagnoses empty results from multi-JOIN queries.

When a SELECT with JOINs returns 0 rows, this module breaks the query
apart to identify *which* table is empty or which JOIN condition
eliminates all rows.

Strategy
--------
1. Parse the query to extract the FROM table and all JOINed tables
   along with their ON conditions and aliases.
2. Run ``SELECT COUNT(*)`` on each individual table (applying any
   per-table WHERE filters when possible).
3. Incrementally reconstruct the JOIN chain, checking the row count
   after each additional JOIN.  The first JOIN that drops the count
   to zero is the culprit.
4. Return a structured ``JoinDiagnostic`` with per-table and
   per-step row counts so the report layer can display them.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Where
from sqlparse.tokens import Keyword, DML

from .db_connector import DatabaseConnector

logger = logging.getLogger(__name__)


# ── Data Structures ────────────────────────────────────────────────


@dataclass
class TableInfo:
    """A table reference extracted from a JOIN query."""

    table_name: str
    alias: str  # Equals table_name when no alias is given
    join_type: str  # "FROM", "JOIN", "LEFT JOIN", etc.
    on_condition: str = ""  # Raw ON clause text


@dataclass
class TableCount:
    """Row count result for a single table."""

    table_name: str
    alias: str
    row_count: int = 0
    error: Optional[str] = None


@dataclass
class JoinStepResult:
    """Row count after incrementally adding one more JOIN."""

    step: int  # 1-based step number
    tables_joined: List[str]  # Table names included so far
    join_sql: str  # The SQL fragment used
    row_count: int = 0
    error: Optional[str] = None


@dataclass
class JoinDiagnostic:
    """Full diagnostic result for a multi-JOIN query that returned 0 rows."""

    original_query: str
    tables: List[TableInfo] = field(default_factory=list)
    table_counts: List[TableCount] = field(default_factory=list)
    join_steps: List[JoinStepResult] = field(default_factory=list)
    culprit_table: Optional[str] = None  # Table whose JOIN drops count to 0
    culprit_reason: str = ""  # Human-readable explanation


# ── Query Parsing ──────────────────────────────────────────────────


def _extract_tables_from_query(query: str) -> List[TableInfo]:
    """Parse a SELECT query and extract all table references with JOIN info.

    Handles patterns like:
        FROM orders o
        JOIN users u ON u.id = o.user_id
        LEFT JOIN products p ON p.id = oi.product_id

    Args:
        query: A SELECT SQL statement.

    Returns:
        Ordered list of TableInfo objects.
    """
    tables: List[TableInfo] = []

    # Normalise whitespace for regex matching
    normalised = " ".join(query.split())

    # Pattern: captures FROM / JOIN variants, table name, optional alias, optional ON
    # We process FROM first, then all JOINs

    # Extract FROM table
    from_match = re.search(
        r"\bFROM\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?",
        normalised,
        re.IGNORECASE,
    )
    if from_match:
        tbl = from_match.group(1)
        alias = from_match.group(2) or tbl
        # Skip subqueries (they start with '(' before the table name)
        # Check if it's a real table name (alphanumeric, no parens before)
        pos = from_match.start(1)
        if pos > 0 and normalised[pos - 1] == "(":
            pass  # subquery — skip
        else:
            tables.append(TableInfo(
                table_name=tbl,
                alias=alias,
                join_type="FROM",
            ))

    # Extract JOINed tables
    join_pattern = re.compile(
        r"((?:LEFT|RIGHT|FULL|CROSS|INNER|OUTER)?\s*JOIN)\s+"
        r"(\w+)(?:\s+(?:AS\s+)?(\w+))?"
        r"(?:\s+ON\s+(.*?))?(?=\s+(?:LEFT|RIGHT|FULL|CROSS|INNER|OUTER)?\s*JOIN\b|\s+WHERE\b|\s+GROUP\b|\s+ORDER\b|\s+LIMIT\b|\s+HAVING\b|\s+UNION\b|;|\s*$)",
        re.IGNORECASE,
    )

    for m in join_pattern.finditer(normalised):
        join_type = m.group(1).strip().upper()
        tbl = m.group(2)
        alias = m.group(3) or tbl
        on_cond = (m.group(4) or "").strip()

        # Skip if table looks like a subquery alias
        if tbl.upper() in ("SELECT", "ON", "WHERE", "SET"):
            continue

        tables.append(TableInfo(
            table_name=tbl,
            alias=alias,
            join_type=join_type,
            on_condition=on_cond,
        ))

    return tables


# ── Diagnostic Execution ───────────────────────────────────────────


def _count_table(connector: DatabaseConnector, table_name: str) -> Tuple[int, Optional[str]]:
    """Run SELECT COUNT(*) on a single table.

    Returns:
        Tuple of (row_count, error_message_or_None).
    """
    sql = f"SELECT COUNT(*) FROM {table_name}"
    try:
        with connector.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            connector.commit()
            return (row[0] if row else 0, None)
    except Exception as e:
        connector.rollback()
        return (0, str(e))


def _count_join_step(
    connector: DatabaseConnector,
    tables: List[TableInfo],
    up_to_index: int,
    where_clause: str = "",
) -> Tuple[int, str, Optional[str]]:
    """Build a SELECT COUNT(*) with JOINs up to the given step index.

    Args:
        connector: Active database connection.
        tables: Full list of tables from the query.
        up_to_index: Include tables[0..up_to_index] in the JOIN chain.
        where_clause: Optional WHERE clause to append.

    Returns:
        Tuple of (row_count, sql_used, error_or_None).
    """
    base = tables[0]
    sql = f"SELECT COUNT(*) FROM {base.table_name} {base.alias}"

    for i in range(1, up_to_index + 1):
        t = tables[i]
        on_part = f" ON {t.on_condition}" if t.on_condition else ""
        sql += f" {t.join_type} {t.table_name} {t.alias}{on_part}"

    if where_clause:
        sql += f" WHERE {where_clause}"

    try:
        with connector.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            connector.commit()
            return (row[0] if row else 0, sql, None)
    except Exception as e:
        connector.rollback()
        return (0, sql, str(e))


def _extract_where_clause(query: str) -> str:
    """Extract the WHERE clause from a query (without the WHERE keyword).

    Returns empty string if no WHERE clause is present.
    """
    normalised = " ".join(query.split())
    match = re.search(
        r"\bWHERE\s+(.*?)(?:\s+GROUP\b|\s+ORDER\b|\s+LIMIT\b|\s+HAVING\b|\s+UNION\b|;|\s*$)",
        normalised,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


# ── Public API ─────────────────────────────────────────────────────


def has_joins(query: str) -> bool:
    """Check whether a query contains JOIN clauses.

    Args:
        query: SQL statement.

    Returns:
        True if the query contains at least one JOIN keyword.
    """
    return bool(re.search(r"\bJOIN\b", query, re.IGNORECASE))


def diagnose_empty_join(
    connector: DatabaseConnector,
    query: str,
) -> Optional[JoinDiagnostic]:
    """Diagnose why a multi-JOIN SELECT returned 0 rows.

    Breaks the query into individual table counts and incremental
    JOIN steps to pinpoint the table or condition that eliminates
    all rows.

    Args:
        connector: Active database connection.
        query: The original SELECT query that returned 0 rows.

    Returns:
        JoinDiagnostic with full breakdown, or None if the query
        has fewer than 2 tables.
    """
    tables = _extract_tables_from_query(query)

    if len(tables) < 2:
        return None

    diagnostic = JoinDiagnostic(
        original_query=query,
        tables=tables,
    )

    # Step 1: Count rows in each individual table
    for t in tables:
        count, err = _count_table(connector, t.table_name)
        diagnostic.table_counts.append(TableCount(
            table_name=t.table_name,
            alias=t.alias,
            row_count=count,
            error=err,
        ))

    # Check if any table is empty — that's the simplest explanation
    empty_tables = [tc for tc in diagnostic.table_counts if tc.row_count == 0 and not tc.error]
    if empty_tables:
        names = ", ".join(t.table_name for t in empty_tables)
        diagnostic.culprit_table = empty_tables[0].table_name
        diagnostic.culprit_reason = (
            f"Table(s) {names} contain 0 rows — "
            f"any JOIN involving an empty table will always produce 0 results."
        )
        return diagnostic

    # Step 2: Incrementally add JOINs and check where the count drops to 0
    where_clause = _extract_where_clause(query)

    prev_count = -1
    for step_idx in range(1, len(tables)):
        count, sql, err = _count_join_step(
            connector, tables, step_idx, where_clause=""
        )
        step = JoinStepResult(
            step=step_idx,
            tables_joined=[t.table_name for t in tables[: step_idx + 1]],
            join_sql=sql,
            row_count=count,
            error=err,
        )
        diagnostic.join_steps.append(step)

        if count == 0 and prev_count != 0:
            # This JOIN caused the drop to 0
            culprit = tables[step_idx]
            diagnostic.culprit_table = culprit.table_name
            diagnostic.culprit_reason = (
                f"JOIN with {culprit.table_name} ({culprit.join_type} ON "
                f"{culprit.on_condition}) reduces the result to 0 rows. "
                f"Check that matching records exist in '{culprit.table_name}' "
                f"for the join condition."
            )
        prev_count = count

    # Step 3: If still not found, it may be the WHERE clause
    if not diagnostic.culprit_table and where_clause:
        # Re-run the last step WITH the WHERE clause
        last_count_no_where = diagnostic.join_steps[-1].row_count if diagnostic.join_steps else 0
        count_with_where, sql, err = _count_join_step(
            connector, tables, len(tables) - 1, where_clause=where_clause
        )

        if last_count_no_where > 0 and count_with_where == 0:
            diagnostic.culprit_table = "WHERE clause"
            diagnostic.culprit_reason = (
                f"The full JOIN produces {last_count_no_where} rows, but the "
                f"WHERE clause ({where_clause}) filters all of them out."
            )

    # Fallback reason
    if not diagnostic.culprit_table:
        if diagnostic.join_steps and diagnostic.join_steps[-1].row_count == 0:
            diagnostic.culprit_reason = (
                "The combination of all JOINs produces 0 rows. "
                "Check that join conditions have matching data across tables."
            )

    return diagnostic
