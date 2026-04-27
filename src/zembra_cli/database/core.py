"""SQLite database infrastructure for zembra-cli."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SCHEMA_SQL_PATH = (
    Path(__file__).resolve().parents[3]
    / "vendor"
    / "zembra-schema"
    / "sqlite"
    / "001_initial_schema.sql"
)

CORE_TABLES = (
    "fields",
    "tags",
    "devices",
    "notes",
    "note_tags",
    "note_links",
    "attachments",
    "note_revisions",
)

DEFAULT_DATABASE_PATH = Path.home() / ".zembra" / "zembra.sqlite3"


class DatabaseInitializationError(RuntimeError):
    """Base error for database initialization failures.

    Attributes:
        message: Natural-language description suitable for CLI output.
    """

    def __init__(self, message: str) -> None:
        """Initialize the database initialization error.

        Args:
            message: Natural-language description suitable for CLI output.

        Returns:
            None.
        """
        self.message = message
        super().__init__(message)


class DatabaseSchemaIncompleteError(DatabaseInitializationError):
    """Signal that an existing database is missing required core tables.

    Attributes:
        database_path: Existing SQLite database path.
        missing_tables: Required core tables absent from the database.
    """

    def __init__(self, database_path: Path, missing_tables: set[str]) -> None:
        """Initialize the incomplete schema error.

        Args:
            database_path: Existing SQLite database path.
            missing_tables: Required core tables absent from the database.

        Returns:
            None.
        """
        self.database_path = database_path
        self.missing_tables = missing_tables
        missing_table_list = ", ".join(sorted(missing_tables))
        super().__init__(
            f"Database already exists at {database_path}, but its schema is incomplete. "
            f"Missing tables: {missing_table_list}"
        )


@dataclass(frozen=True)
class DatabaseInitResult:
    """Represent the result of initializing a SQLite database file.

    Attributes:
        database_path: Expanded SQLite database path.
        status: Whether the database was created or already initialized.
    """

    database_path: Path
    status: Literal["created", "skipped"]


def connect_database(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign key enforcement enabled.

    Args:
        database_path: Filesystem path or SQLite URI accepted by sqlite3.

    Returns:
        A SQLite connection configured with row access by column name.
    """
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Provide a managed SQLite connection that commits on success.

    Args:
        database_path: Filesystem path or SQLite URI accepted by sqlite3.

    Returns:
        An iterator yielding the managed SQLite connection.
    """
    connection = connect_database(database_path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def read_initial_schema(schema_path: Path = SCHEMA_SQL_PATH) -> str:
    """Read the shared SQLite initialization script.

    Args:
        schema_path: Path to the SQLite schema script from zembra-schema.

    Returns:
        The SQL script text.
    """
    return schema_path.read_text(encoding="utf-8")


def initialize_database(
    connection: sqlite3.Connection,
    schema_path: Path = SCHEMA_SQL_PATH,
) -> None:
    """Create the database schema from the shared SQLite contract.

    Args:
        connection: Open SQLite connection to initialize.
        schema_path: Path to the SQLite schema script from zembra-schema.

    Returns:
        None.
    """
    connection.executescript(read_initial_schema(schema_path))
    connection.commit()


def initialize_database_file(database_path: str | Path) -> DatabaseInitResult:
    """Safely create or reuse a fully initialized SQLite database file.

    Args:
        database_path: SQLite database path to initialize.

    Returns:
        Initialization result describing the database path and status.
    """
    path = Path(database_path).expanduser()
    existed_before = path.exists()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with database_connection(path) as connection:
            if existed_before:
                missing_tables = missing_core_tables(connection)
                if missing_tables:
                    raise DatabaseSchemaIncompleteError(path, missing_tables)
                return DatabaseInitResult(database_path=path, status="skipped")

            initialize_database(connection)
            return DatabaseInitResult(database_path=path, status="created")
    except DatabaseInitializationError:
        raise
    except OSError as error:
        raise DatabaseInitializationError(
            f"Could not create database directory for {path}: {error}"
        ) from error
    except sqlite3.Error as error:
        raise DatabaseInitializationError(
            f"Could not initialize database at {path}: {error}"
        ) from error


def list_user_tables(connection: sqlite3.Connection) -> set[str]:
    """List user-defined SQLite tables in the current database.

    Args:
        connection: Open SQLite connection to inspect.

    Returns:
        A set containing user-defined table names.
    """
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row["name"] for row in rows}


def missing_core_tables(connection: sqlite3.Connection) -> set[str]:
    """List required Zembra tables that are absent from the current database.

    Args:
        connection: Open SQLite connection to inspect.

    Returns:
        A set containing required table names that are missing.
    """
    return set(CORE_TABLES) - list_user_tables(connection)
