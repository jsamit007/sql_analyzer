"""Database connection management for PostgreSQL, SQL Server, and SQLite.

Provides a unified interface for connecting to different database backends
with proper transaction handling and connection lifecycle management.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseConnector:
    """Manages database connections with support for PostgreSQL, SQL Server, and SQLite."""

    def __init__(self, config: DatabaseConfig):
        """Initialize the database connector.

        Args:
            config: Database configuration instance.
        """
        self.config = config
        self._connection = None

    def connect(self) -> None:
        """Establish a database connection based on the configured database type.

        Raises:
            ImportError: If the required database driver is not installed.
            ConnectionError: If the connection fails.
        """
        if self.config.db_type == "postgres":
            self._connect_postgres()
        elif self.config.db_type == "sqlserver":
            self._connect_sqlserver()
        elif self.config.db_type == "sqlite":
            self._connect_sqlite()
        else:
            raise ValueError(f"Unsupported database type: {self.config.db_type}")

    def _connect_postgres(self) -> None:
        """Connect to PostgreSQL using psycopg2."""
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "psycopg2 is not installed. Install it with: pip install psycopg2-binary"
            )

        try:
            self._connection = psycopg2.connect(
                host=self.config.pg_host,
                port=self.config.pg_port,
                dbname=self.config.pg_database,
                user=self.config.pg_user,
                password=self.config.pg_password,
            )
            # Set autocommit to False for transaction management
            self._connection.autocommit = False
            logger.info(
                "Connected to PostgreSQL: %s:%s/%s",
                self.config.pg_host,
                self.config.pg_port,
                self.config.pg_database,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e

    def _connect_sqlserver(self) -> None:
        """Connect to SQL Server using pyodbc."""
        try:
            import pyodbc
        except ImportError:
            raise ImportError(
                "pyodbc is not installed. Install it with: pip install pyodbc"
            )

        try:
            if self.config.mssql_trusted_connection:
                conn_str = (
                    f"DRIVER={self.config.mssql_driver};"
                    f"SERVER={self.config.mssql_server};"
                    f"DATABASE={self.config.mssql_database};"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate=yes;"
                )
            else:
                conn_str = (
                    f"DRIVER={self.config.mssql_driver};"
                    f"SERVER={self.config.mssql_server};"
                    f"DATABASE={self.config.mssql_database};"
                    f"UID={self.config.mssql_user};"
                    f"PWD={self.config.mssql_password};"
                    f"TrustServerCertificate=yes;"
                )

            self._connection = pyodbc.connect(conn_str, autocommit=False)
            logger.info(
                "Connected to SQL Server: %s/%s",
                self.config.mssql_server,
                self.config.mssql_database,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQL Server: {e}") from e

    def _connect_sqlite(self) -> None:
        """Connect to SQLite database."""
        import sqlite3

        try:
            self._connection = sqlite3.connect(self.config.sqlite_path)
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Use Row factory for dict-like access
            self._connection.isolation_level = "DEFERRED"
            logger.info("Connected to SQLite: %s", self.config.sqlite_path)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQLite: {e}") from e

    @property
    def connection(self):
        """Get the active database connection.

        Raises:
            RuntimeError: If not connected.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to database. Call connect() first.")
        return self._connection

    @property
    def db_type(self) -> str:
        """Get the database type."""
        return self.config.db_type

    def commit(self) -> None:
        """Commit the current transaction."""
        self.connection.commit()
        logger.debug("Transaction committed.")

    def rollback(self) -> None:
        """Rollback the current transaction."""
        try:
            self.connection.rollback()
            logger.debug("Transaction rolled back.")
        except Exception as e:
            logger.error("Rollback failed: %s", e)

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            try:
                self._connection.close()
                logger.info("Database connection closed.")
            except Exception as e:
                logger.error("Error closing connection: %s", e)
            finally:
                self._connection = None

    @contextmanager
    def cursor(self) -> Generator:
        """Context manager for creating and managing a database cursor.

        Yields:
            A database cursor.
        """
        cur = self.connection.cursor()
        try:
            yield cur
        finally:
            cur.close()

    @contextmanager
    def transaction(self) -> Generator:
        """Context manager for transaction handling.

        Automatically commits on success, rolls back on failure.

        Yields:
            The database connection.
        """
        try:
            yield self.connection
            self.commit()
        except Exception:
            self.rollback()
            raise

    def __enter__(self):
        """Enter context manager."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and close connection."""
        self.close()
        return False
