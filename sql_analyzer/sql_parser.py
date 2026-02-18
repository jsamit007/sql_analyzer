"""SQL file loading and query splitting.

Handles multiline queries, semicolon splitting, and comment stripping.
Uses sqlparse for robust SQL parsing.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

import sqlparse

logger = logging.getLogger(__name__)


def load_sql_file(file_path: str) -> str:
    """Load a SQL file and return its contents as a string.

    Args:
        file_path: Path to the .sql file.

    Returns:
        The raw SQL content.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty or not a .sql file.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")

    if path.suffix.lower() != ".sql":
        logger.warning("File '%s' does not have a .sql extension.", file_path)

    content = path.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(f"SQL file is empty: {file_path}")

    logger.info("Loaded SQL file: %s (%d bytes)", file_path, len(content))
    return content


def strip_comments(sql: str) -> str:
    """Remove SQL comments (single-line and multi-line) from SQL text.

    Args:
        sql: Raw SQL string.

    Returns:
        SQL string with comments removed.
    """
    # Use sqlparse to format and strip comments
    return sqlparse.format(sql, strip_comments=True)


def split_queries(sql_content: str) -> List[Tuple[str, int]]:
    """Split a SQL script into individual executable statements with line numbers.

    Handles:
    - Multiline queries
    - Semicolon splitting
    - Comment stripping
    - Empty statement filtering

    Args:
        sql_content: Raw SQL content from the file.

    Returns:
        List of (sql_statement, line_number) tuples.
        line_number is the 1-based line in the original file where the statement starts.
    """
    # Build a map from cleaned-statement text to original line number.
    # We strip comments but need to remember where each statement began
    # in the *original* file.
    original_lines = sql_content.splitlines()

    # Strip comments for parsing
    clean_sql = strip_comments(sql_content)

    # Parse and split using sqlparse
    statements = sqlparse.split(clean_sql)

    # For each cleaned statement, find its starting line in the original file.
    # We walk through the original content character-by-character to correlate.
    clean_lines = clean_sql.splitlines()

    # Build a mapping: for each line in clean_sql, what is the corresponding
    # original line number?  After comment stripping, blank lines may shift.
    # Strategy: search for each statement's first meaningful tokens in the
    # original content to find the real line number.
    def _find_line_number(stmt_text: str) -> int:
        """Find the 1-based line number of stmt_text in the original file."""
        # Get the first non-whitespace line of the statement
        first_line = ""
        for line in stmt_text.splitlines():
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break

        if not first_line:
            return 1

        # Search for this line in the original file content
        for idx, orig_line in enumerate(original_lines):
            if first_line in orig_line:
                return idx + 1  # 1-based

        return 1  # fallback

    # Track which original lines have already been matched (for duplicate statements)
    matched_lines: set = set()

    def _find_line_number_unique(stmt_text: str) -> int:
        """Find line number, skipping already-matched lines for duplicates."""
        first_line = ""
        for line in stmt_text.splitlines():
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break

        if not first_line:
            return 1

        for idx, orig_line in enumerate(original_lines):
            if first_line in orig_line and idx not in matched_lines:
                matched_lines.add(idx)
                return idx + 1

        return _find_line_number(stmt_text)

    # Filter out empty statements, find line numbers
    queries: List[Tuple[str, int]] = []
    for stmt in statements:
        trimmed = stmt.strip()
        # Remove trailing semicolons for cleaner execution
        if trimmed.endswith(";"):
            trimmed = trimmed[:-1].strip()
        if trimmed:
            line_num = _find_line_number_unique(trimmed)
            queries.append((trimmed, line_num))

    logger.info("Split SQL into %d executable statements.", len(queries))
    return queries


def get_query_type(query: str) -> str:
    """Determine the type of SQL statement.

    Args:
        query: A single SQL statement.

    Returns:
        Query type string (e.g., 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DDL', 'OTHER').
    """
    parsed = sqlparse.parse(query)
    if not parsed:
        return "OTHER"

    stmt = parsed[0]
    stmt_type = stmt.get_type()

    if stmt_type:
        return stmt_type.upper()

    # Fallback: check first keyword
    first_token = query.strip().split()[0].upper() if query.strip() else ""
    type_map = {
        "SELECT": "SELECT",
        "INSERT": "INSERT",
        "UPDATE": "UPDATE",
        "DELETE": "DELETE",
        "CREATE": "DDL",
        "ALTER": "DDL",
        "DROP": "DDL",
        "TRUNCATE": "DDL",
        "BEGIN": "TRANSACTION",
        "COMMIT": "TRANSACTION",
        "ROLLBACK": "TRANSACTION",
        "SET": "SET",
        "EXPLAIN": "EXPLAIN",
    }

    return type_map.get(first_token, "OTHER")


def truncate_query_text(query: str, max_length: int = 200) -> str:
    """Truncate query text for display purposes.

    Args:
        query: Full SQL query text.
        max_length: Maximum character length for display.

    Returns:
        Truncated query text with ellipsis if needed.
    """
    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", query).strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length] + "..."
