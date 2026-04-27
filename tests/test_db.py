"""Tests for SQLite database initialization."""

import sqlite3

import pytest

from zembra_cli.db import (
    CORE_TABLES,
    database_connection,
    initialize_database,
    list_user_tables,
    missing_core_tables,
)


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


def test_initialize_database_creates_note_role_column(tmp_path) -> None:
    """Verify the v0.2.0 schema creates the immutable note role column.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"

    with database_connection(database_path) as connection:
        initialize_database(connection)
        columns = connection.execute("PRAGMA table_info(notes)").fetchall()

    role_column = next(column for column in columns if column["name"] == "role")
    assert role_column["notnull"] == 1
    assert role_column["dflt_value"] == "'Human'"


def test_note_role_constraint_rejects_unknown_role(tmp_path) -> None:
    """Verify SQLite rejects note roles outside the shared schema enum.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"

    with database_connection(database_path) as connection:
        initialize_database(connection)

        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            connection.execute(
                """
                INSERT INTO notes (id, content, role, created_at, updated_at)
                VALUES ('note_1', 'hello', 'System', 1, 1)
                """
            )


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


def test_missing_core_tables_reports_absent_schema(tmp_path) -> None:
    """Verify uninitialized databases report every missing core table.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"

    with database_connection(database_path) as connection:
        assert missing_core_tables(connection) == set(CORE_TABLES)
