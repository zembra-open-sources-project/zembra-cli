"""Tests for SQLite database initialization."""

from zembra_cli.db import CORE_TABLES, database_connection, initialize_database, list_user_tables


def test_initialize_database_creates_core_tables(tmp_path) -> None:
    """Verify the shared SQLite schema creates every core table.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"

    with database_connection(database_path) as connection:
        initialize_database(connection)

        assert set(CORE_TABLES) <= list_user_tables(connection)


def test_database_connection_enables_foreign_keys(tmp_path) -> None:
    """Verify every managed SQLite connection enables foreign key checks.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"

    with database_connection(database_path) as connection:
        foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert foreign_keys_enabled == 1
