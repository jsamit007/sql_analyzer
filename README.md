# SQL Analyzer

A production-ready SQL performance analyzer that parses `.sql` files, executes queries, measures timing, runs EXPLAIN plans, and provides actionable optimization suggestions.

## Features

- **Multi-database support** — PostgreSQL, SQL Server, SQLite
- **Precise timing** — `time.perf_counter()` for each query
- **EXPLAIN plan parsing** — detects sequential scans, missing indexes, costly sorts, nested loops
- **Smart suggestions** — index recommendations, query rewrites, WHERE clause analysis
- **AI-powered advice** — optional integration with OpenAI, Groq (free tier), or Ollama (local, no auth)
- **Interactive detail view** — after the summary, choose which query's execution plan & AI recommendation to inspect
- **Interest threshold filtering** — only queries exceeding a configurable time threshold (default: 300ms) are offered for detail inspection and AI analysis
- **JOIN decomposition** — when a multi-JOIN SELECT returns 0 rows, automatically diagnoses which table is empty or which join condition eliminates all matches
- **Rich console output** — colored panels, tables, and performance scores via Rich library
- **Secure password management** — database passwords prompted interactively (hidden input), encrypted with Fernet (AES), and saved locally
- **Export** — JSON and CSV report generation
- **Line tracking** — shows source file line numbers for each query

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd sql-parser
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt

# Build the sample SQLite database
python db/build_db.py

# Run analysis
python sql_analyzer.py --file sample.sql --db sqlite --sqlite-path db/database.db
```

## Usage

```bash
# Basic analysis (SQLite)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db

# PostgreSQL (password will be prompted securely on first run)
python sql_analyzer.py --file queries.sql --db postgres --pg-host localhost --pg-database mydb

# SQL Server (password prompted, or use trusted connection)
python sql_analyzer.py --file queries.sql --db sqlserver --mssql-server localhost --mssql-database mydb

# Reset saved passwords and prompt again
python sql_analyzer.py --file queries.sql --db postgres --pg-host localhost --pg-database mydb --reset-password

# With AI suggestions (Groq — free tier)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --groq

# With AI suggestions (Ollama — local, no API key)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ollama

# With AI suggestions (OpenAI)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ai

# Only inspect queries slower than 500ms (default: 300ms)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ollama --interest-threshold 500

# Inspect all queries regardless of speed
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ollama --interest-threshold 0

# Export reports
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --json --csv

# Plain text output (no colors)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --no-color
```

## CLI Options

| Flag | Description |
|------|-------------|
| `--file`, `-f` | Path to the `.sql` file to analyze (required) |
| `--db` | Database type: `postgres`, `sqlserver`, `sqlite` (default: postgres) |
| `--sqlite-path` | Path to SQLite database file |
| `--pg-host/port/database/user/password` | PostgreSQL connection settings |
| `--mssql-server/database/user/password` | SQL Server connection settings |
| `--mssql-trusted` | Use Windows trusted connection for SQL Server |
| `--reset-password` | Delete saved encrypted passwords and prompt again |
| `--explain-analyze` | Use EXPLAIN ANALYZE (actually runs query in EXPLAIN) |
| `--slow-threshold` | Slow query threshold in ms (default: 500) |
| `--interest-threshold` | Only show detail/AI for queries slower than this (ms, default: 300) |
| `--stop-on-error` | Stop on first query error |
| `--json` | Save report to JSON |
| `--csv` | Save report to CSV |
| `--no-color` | Disable colored output |
| `--ai` | Enable OpenAI suggestions |
| `--openai-key` | OpenAI API key |
| `--openai-model` | OpenAI model (default: gpt-4o) |
| `--groq` | Enable Groq suggestions (free tier available) |
| `--groq-key` | Groq API key |
| `--groq-model` | Groq model (default: llama-3.3-70b-versatile) |
| `--ollama` | Enable local Ollama suggestions (no API key needed) |
| `--ollama-model` | Ollama model (default: llama3) |
| `--ollama-host` | Ollama server URL (default: http://localhost:11434) |
| `--log-level` | Logging verbosity: DEBUG, INFO, WARNING, ERROR |
| `--log-file` | Path to log file |

## Interactive Detail View

After all queries are executed, the tool prints a compact summary for each query (timing, score, warnings, suggestions). Execution plans and AI recommendations are **not** shown automatically — instead, you get an interactive prompt that only lists queries **above the interest threshold** (default: 300ms):

```
Queries above 300 ms threshold — enter a number to view execution plan & AI recommendation.
Available: 1, 3, 5, 7  (type 'all' for all, or 'q' to skip)

Query #> 3
```

- Enter a single number (e.g. `3`) to view that query's details
- Enter comma-separated numbers (e.g. `1,3,5`) to view multiple
- Enter `all` to view every available query above the threshold
- Enter `q`, `exit`, or press Enter to skip

AI suggestions (Ollama/Groq/OpenAI) are also only generated for queries that exceed this threshold, saving time and API costs.

Adjust the threshold with `--interest-threshold`:

```bash
# Only care about queries slower than 500ms
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ollama --interest-threshold 500

# See details for all queries
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ollama --interest-threshold 0
```

This keeps the initial output clean and lets you drill into the queries you care about.

## AI Backends

| Backend | Flag | Auth Required | Cost |
|---------|------|---------------|------|
| **Ollama** | `--ollama` | None (runs locally) | Free |
| **Groq** | `--groq` | API key ([console.groq.com/keys](https://console.groq.com/keys)) | Free tier |
| **OpenAI** | `--ai` | API key ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)) | Paid |

When using `--ai` or `--groq` without providing a key, the tool will prompt interactively and offer to save it to `.env`.

### Setting Up Ollama (Local AI — Recommended)

Ollama runs entirely on your machine with no API key or account needed.

1. **Install Ollama** from [ollama.com](https://ollama.com)
2. **Pull a model:**
   ```bash
   ollama pull llama3
   ```
3. **Install the Python client** (included in `requirements.txt`):
   ```bash
   pip install ollama
   ```
4. **Run the analyzer with `--ollama`:**
   ```bash
   python sql_analyzer.py --file sample.sql --db sqlite --sqlite-path db/database.db --ollama
   ```

Use a different model with `--ollama-model`:
```bash
python sql_analyzer.py --file sample.sql --db sqlite --sqlite-path db/database.db --ollama --ollama-model codellama
```

Check available models: `ollama list`

## Password Management

Database passwords are handled securely:

1. **Interactive prompt** — if no password is provided via `--pg-password` / `--mssql-password` or the `PG_PASSWORD` / `MSSQL_PASSWORD` env vars, you’ll be prompted (input is hidden).
2. **Encrypted storage** — after entering a password, you can save it encrypted to a `.credentials` file using Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
3. **Auto-load** — on subsequent runs, the saved password is decrypted automatically — no prompt needed.
4. **Reset** — use `--reset-password` to delete saved credentials and re-prompt.
5. **Machine-bound** — the encryption key is derived from your machine’s identity, so `.credentials` files won’t work on other machines.

> The `.credentials` file is gitignored by default. Never commit it to version control.

## Environment Variables

Create a `.env` file in the project root (auto-loaded):

```env
# Database
SQLITE_PATH=db/database.db
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=mydb
PG_USER=postgres
PG_PASSWORD=secret          # Optional — prefer interactive prompt + encryption

# AI
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
OLLAMA_MODEL=llama3
OLLAMA_HOST=http://localhost:11434
INTEREST_THRESHOLD_MS=300
```

## Project Structure

```
sql-parser/
├── sql_analyzer.py            # CLI entry point
├── sql_analyzer/
│   ├── __init__.py            # Package init
│   ├── config.py              # Configuration management
│   ├── credential_manager.py  # Password encryption & secure storage
│   ├── sql_parser.py          # SQL file loading and query splitting
│   ├── db_connector.py        # Database connection (PostgreSQL, SQL Server, SQLite)
│   ├── executor.py            # Query execution with timing and EXPLAIN
│   ├── plan_analyzer.py       # EXPLAIN plan parsing and scoring
│   ├── suggestions.py         # Performance suggestion engine
│   ├── ai_advisor.py          # AI integrations (OpenAI, Groq, Ollama)
│   └── report.py              # Console output, JSON/CSV export
├── db/
│   ├── schema.sql             # Sample database schema (7 tables)
│   ├── seed.sql               # Sample seed data
│   ├── build_db.py            # Script to rebuild SQLite database
│   └── database.db            # Pre-built SQLite database
├── sample.sql                 # 12 sample queries for testing
├── requirements.txt           # Python dependencies
└── .gitignore
```

## Build Standalone Executable

```bash
pip install pyinstaller
python -m PyInstaller --onefile --name sql_analyzer --console sql_analyzer.py
# Output: dist/sql_analyzer.exe
```

## Requirements

- Python 3.10+
- Dependencies: `pip install -r requirements.txt`
- **Password encryption** uses the `cryptography` package (auto-installed via requirements)
- **For Ollama AI:** [Ollama](https://ollama.com) installed with at least one model pulled

## License

MIT
