# SQL Parser

**Module:** `sql_analyzer/sql_parser.py`

Handles loading `.sql` files, splitting them into individual statements, tracking source line numbers, and classifying query types.

## Dependencies

- `sqlparse` — used for robust SQL splitting and comment stripping
- `pathlib.Path` — file I/O
- `re` — regex for fallback query classification

## Functions

### `load_sql_file(file_path) → str`

Loads a `.sql` file and returns raw content.

**Validations:**
- File must exist → raises `FileNotFoundError`
- File should have `.sql` extension → logs a warning if not
- File must not be empty → raises `ValueError`
- Encoding: UTF-8

### `strip_comments(sql) → str`

Removes all SQL comments (single-line `--` and multi-line `/* */`) using `sqlparse.format(sql, strip_comments=True)`.

### `split_queries(sql_content) → List[Tuple[str, int]]`

The most complex function in this module. Splits a SQL script into individual executable statements while tracking the original line number of each.

**Algorithm:**

```
1. Save original file lines for line-number lookup
2. Strip comments using sqlparse
3. Split into statements using sqlparse.split()
4. Remove trailing semicolons
5. Filter out empty statements
6. For each statement, find its starting line number in the original file
```

**Line number tracking:**

The challenge is that `sqlparse` strips comments and normalizes whitespace, making direct character-offset mapping unreliable. Instead, a search-based approach is used:

```python
def _find_line_number_unique(stmt_text):
    # Get first non-empty line of the statement
    # Search for it in original file lines
    # Track which lines have been matched (for duplicate handling)
    # Return 1-based line number
```

This handles:
- Comments before/between statements
- Blank lines
- Duplicate statement text (matched sequentially using a `matched_lines` set)

**Return value:** Each tuple is `(sql_statement, line_number)` where `line_number` is 1-based.

### `get_query_type(query) → str`

Determines the SQL statement type. Uses two strategies:

1. **Primary:** `sqlparse.parse(query)[0].get_type()` — reliable for most standard SQL
2. **Fallback:** Checks the first word of the query against a keyword map

**Return values:** `"SELECT"`, `"INSERT"`, `"UPDATE"`, `"DELETE"`, `"DDL"`, `"TRANSACTION"`, `"SET"`, `"EXPLAIN"`, `"OTHER"`

### `truncate_query_text(query, max_length=200) → str`

Truncates long query text for display. Normalizes internal whitespace to single spaces, then adds `...` if the result exceeds `max_length`.

## Usage in Pipeline

```python
sql_content = load_sql_file("queries.sql")
queries = split_queries(sql_content)
# queries = [("SELECT * FROM users", 5), ("INSERT INTO ...", 12), ...]

for query_text, line_num in queries:
    query_type = get_query_type(query_text)  # "SELECT"
```

## Edge Cases

- **Empty file** → `ValueError` raised by `load_sql_file()`
- **File with only comments** → `split_queries()` returns empty list
- **Statements without semicolons** → `sqlparse.split()` handles this
- **Duplicate queries** → `_find_line_number_unique()` uses a set to avoid returning the same line twice
