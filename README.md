# SQL Analyzer

A production-ready SQL performance analyzer that parses `.sql` files, executes queries, measures timing, runs EXPLAIN plans, and provides actionable optimization suggestions.

## Features

- **Multi-database support** — PostgreSQL, SQL Server, SQLite
- **Precise timing** — `time.perf_counter()` for each query
- **EXPLAIN plan parsing** — detects sequential scans, missing indexes, costly sorts, nested loops
- **Smart suggestions** — index recommendations, query rewrites, WHERE clause analysis
- **AI-powered advice** — optional integration with OpenAI, Groq (free tier), or Ollama (local, no auth)
- **Rich console output** — colored panels, tables, and performance scores via Rich library
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

# PostgreSQL
python sql_analyzer.py --file queries.sql --db postgres --pg-host localhost --pg-database mydb

# SQL Server
python sql_analyzer.py --file queries.sql --db sqlserver --mssql-server localhost --mssql-database mydb

# With AI suggestions (Groq — free tier)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --groq

# With AI suggestions (Ollama — local, no API key)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ollama

# With AI suggestions (OpenAI)
python sql_analyzer.py --file queries.sql --db sqlite --sqlite-path mydb.db --ai

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
| `--explain-analyze` | Use EXPLAIN ANALYZE (actually runs query in EXPLAIN) |
| `--slow-threshold` | Slow query threshold in ms (default: 500) |
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

## AI Backends

| Backend | Flag | Auth Required | Cost |
|---------|------|---------------|------|
| **Ollama** | `--ollama` | None (runs locally) | Free |
| **Groq** | `--groq` | API key ([console.groq.com/keys](https://console.groq.com/keys)) | Free tier |
| **OpenAI** | `--ai` | API key ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)) | Paid |

When using `--ai` or `--groq` without providing a key, the tool will prompt interactively and offer to save it to `.env`.

## Environment Variables

Create a `.env` file in the project root (auto-loaded):

```env
# Database
SQLITE_PATH=db/database.db
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=mydb
PG_USER=postgres
PG_PASSWORD=secret

# AI
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
OLLAMA_MODEL=llama3
OLLAMA_HOST=http://localhost:11434
```

## Project Structure

```
sql-parser/
├── sql_analyzer.py            # CLI entry point
├── sql_analyzer/
│   ├── __init__.py            # Package init
│   ├── config.py              # Configuration management
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

## License

MIT
