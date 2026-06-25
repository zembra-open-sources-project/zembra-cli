"""Tests for SQLite database initialization."""

import sqlite3

import pytest

from zembra_cli.database import (
    CORE_TABLES,
    DatabaseSchemaIncompleteError,
    database_connection,
    initialize_database,
    initialize_database_file,
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


def test_initialize_database_creates_workspace_scoped_note_columns(tmp_path) -> None:
    """Verify latest notes schema includes workspace and sync state columns.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"

    with database_connection(database_path) as connection:
        initialize_database(connection)
        columns = connection.execute("PRAGMA table_info(notes)").fetchall()

    column_names = {column["name"] for column in columns}
    assert {"workspace_id", "last_change_id", "conflict_status"} <= column_names
    conflict_column = next(column for column in columns if column["name"] == "conflict_status")
    assert conflict_column["notnull"] == 1
    assert conflict_column["dflt_value"] == "'none'"


def test_initialize_database_creates_hierarchical_tag_columns(tmp_path) -> None:
    """Verify latest tags schema includes hierarchy fields.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"

    with database_connection(database_path) as connection:
        initialize_database(connection)
        columns = connection.execute("PRAGMA table_info(tags)").fetchall()

    column_names = {column["name"] for column in columns}
    assert {"workspace_id", "parent_tag_id", "path", "depth"} <= column_names
    depth_column = next(column for column in columns if column["name"] == "depth")
    assert depth_column["notnull"] == 1
    assert depth_column["dflt_value"] == "0"


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
        connection.execute(
            """
            INSERT INTO workspaces (id, workspace_name, created_at, updated_at)
            VALUES ('workspace_1', NULL, 1, 1)
            """
        )

        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            connection.execute(
                """
                INSERT INTO notes (id, workspace_id, content, role, created_at, updated_at)
                VALUES ('note_1', 'workspace_1', 'hello', 'System', 1, 1)
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


def test_initialize_database_file_creates_database_and_parent_directory(tmp_path) -> None:
    """Verify file initialization creates parent directories and core tables.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "nested" / "zembra.sqlite3"

    result = initialize_database_file(database_path)

    assert result.database_path == database_path
    assert result.status == "created"
    with database_connection(database_path) as connection:
        assert missing_core_tables(connection) == set()


def test_initialize_database_file_skips_complete_database(tmp_path) -> None:
    """Verify an existing complete database is treated as initialized.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_database_file(database_path)

    result = initialize_database_file(database_path)

    assert result.database_path == database_path
    assert result.status == "skipped"


def test_initialize_database_file_rejects_incomplete_database(tmp_path) -> None:
    """Verify an existing incomplete database is not overwritten.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    with database_connection(database_path) as connection:
        connection.execute("CREATE TABLE notes (id TEXT PRIMARY KEY)")

    with pytest.raises(DatabaseSchemaIncompleteError) as error:
        initialize_database_file(database_path)

    assert error.value.database_path == database_path
    assert "fields" in error.value.missing_tables
    with database_connection(database_path) as connection:
        assert "notes" in list_user_tables(connection)
        assert missing_core_tables(connection)
