"""Configuration management for SQL Analyzer."""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

    db_type: str = "postgres"  # "postgres", "sqlserver", or "sqlite"

    # SQLite settings
    sqlite_path: str = "database.db"

    # PostgreSQL settings
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "postgres"
    pg_user: str = "postgres"
    pg_password: str = ""

    # SQL Server settings
    mssql_driver: str = "{ODBC Driver 18 for SQL Server}"
    mssql_server: str = "localhost"
    mssql_database: str = "master"
    mssql_user: str = "sa"
    mssql_password: str = ""
    mssql_trusted_connection: bool = False

    @classmethod
    def from_env(cls, db_type: str = "postgres") -> "DatabaseConfig":
        """Create config from environment variables."""
        return cls(
            db_type=db_type,
            # SQLite
            sqlite_path=os.getenv("SQLITE_PATH", "database.db"),
            # PostgreSQL
            pg_host=os.getenv("PG_HOST", "localhost"),
            pg_port=int(os.getenv("PG_PORT", "5432")),
            pg_database=os.getenv("PG_DATABASE", "postgres"),
            pg_user=os.getenv("PG_USER", "postgres"),
            pg_password=os.getenv("PG_PASSWORD", ""),
            # SQL Server
            mssql_driver=os.getenv("MSSQL_DRIVER", "{ODBC Driver 18 for SQL Server}"),
            mssql_server=os.getenv("MSSQL_SERVER", "localhost"),
            mssql_database=os.getenv("MSSQL_DATABASE", "master"),
            mssql_user=os.getenv("MSSQL_USER", "sa"),
            mssql_password=os.getenv("MSSQL_PASSWORD", ""),
            mssql_trusted_connection=os.getenv("MSSQL_TRUSTED", "false").lower()
            == "true",
        )


@dataclass
class AnalyzerConfig:
    """Configuration for the SQL analyzer."""

    # Execution settings
    explain_analyze: bool = False  # Use EXPLAIN ANALYZE (actually runs query)
    slow_query_threshold_ms: float = 500.0  # Threshold to mark as SLOW QUERY
    interest_threshold_ms: float = 300.0  # Only consider queries above this for detail/AI
    continue_on_error: bool = True  # Continue executing after a query fails

    # Output settings
    save_json: bool = False
    save_csv: bool = False
    json_output_path: str = "performance_report.json"
    csv_output_path: str = "performance_report.csv"
    colored_output: bool = True
    batch_mode: bool = False  # Print full results without interactive prompt

    # AI backend: "openai", "ollama", or "groq"
    ai_backend: str = "openai"

    # OpenAI settings
    openai_enabled: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Ollama settings (local LLM — no API key needed)
    ollama_enabled: bool = False
    ollama_model: str = "llama3"
    ollama_host: str = "http://localhost:11434"

    # Groq settings (fast cloud inference — free tier available)
    groq_enabled: bool = False
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AnalyzerConfig":
        """Create config from environment variables."""
        return cls(
            explain_analyze=os.getenv("EXPLAIN_ANALYZE", "false").lower() == "true",
            slow_query_threshold_ms=float(
                os.getenv("SLOW_QUERY_THRESHOLD_MS", "500")
            ),
            interest_threshold_ms=float(
                os.getenv("INTEREST_THRESHOLD_MS", "300")
            ),
            ai_backend=os.getenv("AI_BACKEND", "openai"),
            openai_enabled=os.getenv("OPENAI_ENABLED", "false").lower() == "true",
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            ollama_enabled=os.getenv("OLLAMA_ENABLED", "false").lower() == "true",
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            groq_enabled=os.getenv("GROQ_ENABLED", "false").lower() == "true",
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            colored_output=os.getenv("COLORED_OUTPUT", "true").lower() == "true",
        )


def setup_logging(config: AnalyzerConfig) -> None:
    """Configure logging based on analyzer config."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if config.log_file:
        handlers.append(logging.FileHandler(config.log_file))

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format=log_format,
        handlers=handlers,
    )
