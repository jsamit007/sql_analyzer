# CLI & Entry Point

**Module:** `sql_analyzer.py`

The main entry point that wires together all modules. Handles argument parsing, configuration building, and orchestrates the analysis pipeline.

## Functions

### `build_arg_parser() → ArgumentParser`

Builds the `argparse` argument parser with all CLI flags. Arguments are grouped by category:

| Group | Flags |
|-------|-------|
| **Required** | `--file` / `-f` |
| **Database** | `--db`, `--sqlite-path`, `--pg-*`, `--mssql-*`, `--reset-password` |
| **Analysis** | `--explain-analyze`, `--slow-threshold`, `--stop-on-error` |
| **Output** | `--json`, `--json-path`, `--csv`, `--csv-path`, `--no-color` |
| **AI (OpenAI)** | `--ai`, `--openai-key`, `--openai-model` |
| **AI (Ollama)** | `--ollama`, `--ollama-model`, `--ollama-host` |
| **AI (Groq)** | `--groq`, `--groq-key`, `--groq-model` |
| **Logging** | `--log-level`, `--log-file` |

### `build_configs(args) → (DatabaseConfig, AnalyzerConfig)`

Merges configuration from three sources in priority order:

1. **CLI arguments** (highest priority)
2. **Environment variables** (via `from_env()`)
3. **Encrypted credentials** (via `credential_manager`)
4. **Defaults** (dataclass field defaults)

Logic:
```
1. Call DatabaseConfig.from_env() and AnalyzerConfig.from_env()
2. If --reset-password: delete .credentials file
3. Override each field with CLI arg if the arg was provided
4. If db is postgres and no password: call prompt_and_save_password("pg")
5. If db is sqlserver and no password and not trusted: call prompt_and_save_password("mssql")
6. If --ollama is set: set ai_backend = "ollama"
7. If --groq is set: set ai_backend = "groq"
8. If AI is enabled but no key → call _prompt_for_api_key()
```

### `_prompt_for_api_key(provider, url, env_var) → str`

Interactive API key prompt used when `--ai` or `--groq` is specified without a key. Shared by both OpenAI and Groq.

**Behavior:**
1. Prints provider name and URL to get a key
2. Uses `getpass.getpass()` for hidden input (key is not echoed)
3. Asks if user wants to save to `.env` file
4. If saving: appends or replaces the key in `.env`
5. Returns the key (or empty string if skipped)

### `run_analysis(db_config, analyzer_config, sql_file) → List[QueryResult]`

The main pipeline. Executes in this order:

```
1. load_sql_file()          → raw SQL content
2. split_queries()          → List[(query, line_number)]
3. DatabaseConnector.connect()
4. execute_all_queries()    → List[QueryResult]
5. For each result:
   a. analyze_query_plan()  → PlanMetrics
   b. generate_suggestions() → (warnings, suggestions)
   c. get_*_suggestions()   → AI advice (optional)
   d. print_query_result()  → console output
6. print_summary()          → summary table
7. connector.close()
```

### `main()`

CLI entry point:
```python
parser = build_arg_parser()
args = parser.parse_args()
db_config, analyzer_config = build_configs(args)
setup_logging(analyzer_config)
results = run_analysis(db_config, analyzer_config, args.file)
# Save JSON/CSV if requested
```

## AI Backend Selection

The `run_analysis` function checks AI backends in this priority order:

```
1. Groq       (if analyzer_config.groq_enabled)
2. Ollama     (if analyzer_config.ollama_enabled)
3. OpenAI     (if analyzer_config.openai_enabled and key exists)
```

Only one backend runs per execution. AI is only invoked for `SELECT` queries.

## Error Handling

- **Connection failure** → prints error and calls `sys.exit(1)`
- **Query failure** → captured in `QueryResult.error_message`, execution continues (unless `--stop-on-error`)
- **EXPLAIN failure** → logged as warning, analysis continues without plan data
- **AI failure** → returns `None`, suggestion list is not modified
