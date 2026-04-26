"""Tests for the zembra-cli command-line interface."""

import json
import sqlite3

from typer.testing import CliRunner

from zembra_cli import __version__, cli
from zembra_cli.cli import app
from zembra_cli.db import database_connection, initialize_database

runner = CliRunner()


def configure_cli_database(monkeypatch, database_path) -> None:
    """Point CLI commands at a test database path.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        database_path: Temporary database path used by the CLI.

    Returns:
        None.
    """
    monkeypatch.setattr(cli, "DEFAULT_DATABASE_PATH", database_path)


def initialize_cli_database(database_path) -> None:
    """Create the shared Zembra schema for CLI tests.

    Args:
        database_path: Temporary database path to initialize.

    Returns:
        None.
    """
    with database_connection(database_path) as connection:
        initialize_database(connection)


def test_version_flag_prints_package_version() -> None:
    """Verify the CLI exposes the installed package version.

    Args:
        None.

    Returns:
        None.
    """
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"zembra-cli {__version__}" in result.stdout


def test_hello_command_prints_greeting() -> None:
    """Verify the placeholder command can be invoked through Typer.

    Args:
        None.

    Returns:
        None.
    """
    result = runner.invoke(app, ["hello", "Ada"])

    assert result.exit_code == 0
    assert "Hello, Ada. Zembra is ready." in result.stdout


def test_add_command_creates_note_with_repeated_tags(tmp_path, monkeypatch) -> None:
    """Verify add creates a note with field and repeated tag options.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, database_path)

    result = runner.invoke(
        app,
        ["add", "hello world", "--field", "work", "--tags", "python", "--tags", "cli"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == {"note", "metadata"}
    assert payload["note"]["content"] == "hello world"
    assert payload["note"]["field_id"] is not None
    assert payload["metadata"] == {"field": "work", "tags": ["python", "cli"]}


def test_add_command_parses_comma_and_mixed_tags(tmp_path, monkeypatch) -> None:
    """Verify add supports comma-separated and mixed tag option values.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, database_path)

    result = runner.invoke(
        app,
        ["add", "tag parsing", "--field", "work", "--tags", "python, cli", "--tags", "cli,idea"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["metadata"]["tags"] == ["python", "cli", "idea"]


def test_add_command_preserves_shell_received_content(tmp_path, monkeypatch) -> None:
    """Verify add stores content without extra escape-sequence decoding.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, database_path)
    content = r"literal\ntext"

    result = runner.invoke(app, ["add", content, "--field", "work"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["note"]["content"] == content
    assert payload["metadata"]["tags"] == []


def test_add_command_reports_missing_database(tmp_path, monkeypatch) -> None:
    """Verify add fails clearly when the default database file is absent.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "missing.sqlite3"
    configure_cli_database(monkeypatch, database_path)

    result = runner.invoke(app, ["add", "hello", "--field", "work"])

    assert result.exit_code == 1
    assert f"Database is not initialized at {database_path}" in result.stderr


def test_add_command_reports_uninitialized_database(tmp_path, monkeypatch) -> None:
    """Verify add fails clearly when the database has no Zembra schema.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "empty.sqlite3"
    sqlite3.connect(database_path).close()
    configure_cli_database(monkeypatch, database_path)

    result = runner.invoke(app, ["add", "hello", "--field", "work"])

    assert result.exit_code == 1
    assert f"Database is not initialized at {database_path}" in result.stderr
