"""SQLite database infrastructure for zembra-cli."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_SQL_PATH = (
    Path(__file__).resolve().parents[2]
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
