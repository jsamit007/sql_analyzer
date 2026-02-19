# Configuration

**Module:** `sql_analyzer/config.py`

Manages all settings via Python dataclasses with environment variable loading through `python-dotenv`.

## Initialization

At module load time:
```python
from dotenv import load_dotenv
load_dotenv()  # Reads .env file into os.environ
```

This runs once when the module is first imported, making all `.env` values available to `os.getenv()`.

## `DatabaseConfig`

Holds connection parameters for all three database backends.

### Fields

| Field | Type | Default | Env Var |
|-------|------|---------|---------|
| `db_type` | `str` | `"postgres"` | — (set via CLI `--db`) |
| `sqlite_path` | `str` | `"database.db"` | `SQLITE_PATH` |
| `pg_host` | `str` | `"localhost"` | `PG_HOST` |
| `pg_port` | `int` | `5432` | `PG_PORT` |
| `pg_database` | `str` | `"postgres"` | `PG_DATABASE` |
| `pg_user` | `str` | `"postgres"` | `PG_USER` |
| `pg_password` | `str` | `""` | `PG_PASSWORD` |

> **Note:** Database passwords are preferably prompted interactively and stored encrypted. See [Credential Manager](credential-manager.md) for details. The `PG_PASSWORD` / `MSSQL_PASSWORD` env vars and `--pg-password` / `--mssql-password` CLI args still work but expose passwords in plain text.

| `mssql_driver` | `str` | `"{ODBC Driver 18 for SQL Server}"` | `MSSQL_DRIVER` |
| `mssql_server` | `str` | `"localhost"` | `MSSQL_SERVER` |
| `mssql_database` | `str` | `"master"` | `MSSQL_DATABASE` |
| `mssql_user` | `str` | `"sa"` | `MSSQL_USER` |
| `mssql_password` | `str` | `""` | `MSSQL_PASSWORD` |
| `mssql_trusted_connection` | `bool` | `False` | `MSSQL_TRUSTED` |

### `from_env(db_type) → DatabaseConfig`

Class method that reads all fields from environment variables, using the defaults shown above as fallbacks. The `db_type` parameter is passed explicitly (not from env).

## `AnalyzerConfig`

Controls execution behavior, output, and AI settings.

### Fields

| Field | Type | Default | Env Var |
|-------|------|---------|---------|
| `explain_analyze` | `bool` | `False` | `EXPLAIN_ANALYZE` |
| `slow_query_threshold_ms` | `float` | `500.0` | `SLOW_QUERY_THRESHOLD_MS` |
| `continue_on_error` | `bool` | `True` | — (inverted from CLI `--stop-on-error`) |
| `save_json` | `bool` | `False` | — |
| `save_csv` | `bool` | `False` | — |
| `json_output_path` | `str` | `"performance_report.json"` | — |
| `csv_output_path` | `str` | `"performance_report.csv"` | — |
| `colored_output` | `bool` | `True` | `COLORED_OUTPUT` |
| `ai_backend` | `str` | `"openai"` | `AI_BACKEND` |
| `openai_enabled` | `bool` | `False` | `OPENAI_ENABLED` |
| `openai_api_key` | `str` | `""` | `OPENAI_API_KEY` |
| `openai_model` | `str` | `"gpt-4o"` | `OPENAI_MODEL` |
| `ollama_enabled` | `bool` | `False` | `OLLAMA_ENABLED` |
| `ollama_model` | `str` | `"llama3"` | `OLLAMA_MODEL` |
| `ollama_host` | `str` | `"http://localhost:11434"` | `OLLAMA_HOST` |
| `groq_enabled` | `bool` | `False` | `GROQ_ENABLED` |
| `groq_api_key` | `str` | `""` | `GROQ_API_KEY` |
| `groq_model` | `str` | `"llama-3.3-70b-versatile"` | `GROQ_MODEL` |
| `log_level` | `str` | `"INFO"` | — |
| `log_file` | `Optional[str]` | `None` | — |

### `from_env() → AnalyzerConfig`

Reads boolean env vars by comparing `.lower()` to `"true"`. Numeric values are cast with `float()` / `int()`.

## `setup_logging(config)`

Configures Python's `logging` module:

- Sets the root log level from `config.log_level`
- Always adds a `StreamHandler` (stderr)
- Optionally adds a `FileHandler` if `config.log_file` is set
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

## Configuration Precedence

```
CLI args  >  Environment variables (.env)  >  Encrypted .credentials  >  Dataclass defaults
```

For passwords specifically:
```
--pg-password CLI arg  >  PG_PASSWORD env var / .env  >  .credentials (encrypted)  >  interactive prompt
```

The merging happens in `build_configs()` in `sql_analyzer.py`, not inside the config module itself. The config module only handles env → defaults.
