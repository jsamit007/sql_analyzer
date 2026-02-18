# Database Connector

**Module:** `sql_analyzer/db_connector.py`

Provides a unified interface for connecting to PostgreSQL, SQL Server, and SQLite. Manages connection lifecycle, transactions, and cursor creation.

## Class: `DatabaseConnector`

### Constructor

```python
DatabaseConnector(config: DatabaseConfig)
```

Stores the config and initializes `_connection = None`. Does **not** connect immediately — you must call `.connect()`.

### Connection Methods

#### `connect()`

Dispatches to the appropriate backend based on `config.db_type`:

| db_type | Method | Driver | Import |
|---------|--------|--------|--------|
| `postgres` | `_connect_postgres()` | psycopg2 | `import psycopg2` |
| `sqlserver` | `_connect_sqlserver()` | pyodbc | `import pyodbc` |
| `sqlite` | `_connect_sqlite()` | sqlite3 | `import sqlite3` (stdlib) |

**Lazy imports:** Each `_connect_*` method imports its driver inside the function body. This means you only need the driver for the backend you're using.

**Raises:**
- `ImportError` — if the required driver package is not installed
- `ConnectionError` — if the connection attempt fails

#### `_connect_postgres()`

```python
psycopg2.connect(host=, port=, dbname=, user=, password=)
connection.autocommit = False  # Manual transaction control
```

#### `_connect_sqlserver()`

Builds a connection string and uses `pyodbc.connect()`:

```
DRIVER={ODBC Driver 18 for SQL Server};
SERVER=...;DATABASE=...;
UID=...;PWD=...;TrustServerCertificate=yes;
```

If `mssql_trusted_connection` is `True`, uses `Trusted_Connection=yes` instead of UID/PWD.

#### `_connect_sqlite()`

```python
sqlite3.connect(sqlite_path)
connection.execute("PRAGMA foreign_keys = ON")
connection.isolation_level = "DEFERRED"
```

Foreign keys are enabled explicitly (off by default in SQLite). Isolation level is set to `DEFERRED` for proper transaction support.

### Properties

| Property | Returns | Raises |
|----------|---------|--------|
| `connection` | Active connection object | `RuntimeError` if not connected |
| `db_type` | `str` — the database type from config | — |

### Transaction Methods

| Method | Behavior |
|--------|----------|
| `commit()` | Calls `connection.commit()` |
| `rollback()` | Calls `connection.rollback()`, catches and logs errors |
| `close()` | Closes connection and sets `_connection = None` |

### Context Managers

#### `cursor()`

```python
with connector.cursor() as cur:
    cur.execute("SELECT 1")
    rows = cur.fetchall()
# Cursor is automatically closed after the block
```

Creates a cursor, yields it, and closes it in a `finally` block. Does **not** commit or rollback — that's the caller's responsibility.

#### `transaction()`

```python
with connector.transaction():
    # Queries here...
# Auto-commits on success, auto-rolls back on exception
```

#### Context Manager Protocol

```python
with DatabaseConnector(config) as connector:
    # connect() is called on __enter__
    ...
# close() is called on __exit__
```

## Error Handling Pattern

The executor uses this pattern consistently:

```python
try:
    with connector.cursor() as cur:
        cur.execute(query)
    connector.commit()
except Exception:
    connector.rollback()
    raise
```

## Thread Safety

The connector is **not** thread-safe. It manages a single connection object. For concurrent usage, create separate `DatabaseConnector` instances.
