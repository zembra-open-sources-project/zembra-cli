"""Tests for the zembra-cli command-line interface."""

import json
import sqlite3
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from zembra_cli import __version__, cli
from zembra_cli.cli import app
from zembra_cli.config import load_config
from zembra_cli.db import database_connection, initialize_database
from zembra_cli.models import NoteRecord
from zembra_cli.repository import (
    AmbiguousNoteReferenceError,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
)

runner = CliRunner()


def configure_cli_database(monkeypatch, tmp_path, database_path) -> Path:
    """Point CLI commands at a test config and database path.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Pytest temporary directory fixture.
        database_path: Temporary database path used by the CLI.

    Returns:
        The temporary config path.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(f'[database]\npath = "{database_path}"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)
    return config_path


def initialize_cli_database(database_path) -> None:
    """Create the shared Zembra schema for CLI tests.

    Args:
        database_path: Temporary database path to initialize.

    Returns:
        None.
    """
    with database_connection(database_path) as connection:
        initialize_database(connection)


class FakeNoteReferenceRepository:
    """Resolve note references with a configured result or error.

    Attributes:
        result: Complete note id returned by successful resolution.
        error: Optional exception raised during resolution.
    """

    def __init__(self, result: str = "abcd0000", error: Exception | None = None) -> None:
        """Initialize the fake repository.

        Args:
            result: Complete note id returned by successful resolution.
            error: Optional exception raised during resolution.

        Returns:
            None.
        """
        self.result = result
        self.error = error

    def resolve_note_id(self, note_ref: str) -> str:
        """Resolve a note reference or raise the configured error.

        Args:
            note_ref: User-provided note reference.

        Returns:
            Complete note id.
        """
        if self.error is not None:
            raise self.error
        return self.result


def make_note(note_id: str, content: str) -> NoteRecord:
    """Create a note record for CLI formatting tests.

    Args:
        note_id: Stable note identifier.
        content: Note body text.

    Returns:
        Note record with minimal valid timestamps.
    """
    return NoteRecord(
        id=note_id,
        content=content,
        created_at=1,
        updated_at=1,
    )


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
    configure_cli_database(monkeypatch, tmp_path, database_path)

    result = runner.invoke(
        app,
        ["add", "hello world", "--field", "work", "--tags", "python", "--tags", "cli"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == {"note", "metadata"}
    assert payload["note"]["content"] == "hello world"
    assert payload["note"]["role"] == "Human"
    assert payload["note"]["field_id"] is not None
    assert payload["metadata"] == {"field": "work", "tags": ["python", "cli"], "role": "Human"}


@pytest.mark.parametrize(
    ("role_value", "expected_role"),
    [
        ("Agent", "Agent"),
        ("agent", "Agent"),
        ("a", "Agent"),
        ("Human", "Human"),
        ("human", "Human"),
        ("h", "Human"),
    ],
)
def test_add_command_accepts_role_variants(
    tmp_path,
    monkeypatch,
    role_value: str,
    expected_role: str,
) -> None:
    """Verify add normalizes supported role option variants.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.
        role_value: Raw role option supplied to the CLI.
        expected_role: Shared schema role expected in command output.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)

    result = runner.invoke(app, ["add", "role note", "--field", "work", "--role", role_value])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["note"]["role"] == expected_role
    assert payload["metadata"]["role"] == expected_role


def test_add_command_rejects_unknown_role(tmp_path, monkeypatch) -> None:
    """Verify add reports an invalid role before creating a note.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)

    result = runner.invoke(app, ["add", "role note", "--field", "work", "--role", "system"])

    assert result.exit_code == 1
    assert "Role must be one of" in result.stderr


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
    configure_cli_database(monkeypatch, tmp_path, database_path)

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
    configure_cli_database(monkeypatch, tmp_path, database_path)
    content = r"literal\ntext"

    result = runner.invoke(app, ["add", content, "--field", "work"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["note"]["content"] == content
    assert payload["metadata"]["tags"] == []
    assert payload["metadata"]["role"] == "Human"


def test_add_command_reports_missing_database(tmp_path, monkeypatch) -> None:
    """Verify add fails clearly when the default database file is absent.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "missing.sqlite3"
    configure_cli_database(monkeypatch, tmp_path, database_path)

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
    configure_cli_database(monkeypatch, tmp_path, database_path)

    result = runner.invoke(app, ["add", "hello", "--field", "work"])

    assert result.exit_code == 1
    assert f"Database is not initialized at {database_path}" in result.stderr


def test_config_database_command_writes_config(tmp_path, monkeypatch) -> None:
    """Verify config database writes the shared zembra config.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    result = runner.invoke(app, ["config", "database", str(database_path)])

    assert result.exit_code == 0
    assert f"Configured zembra database path: {database_path}" in result.stdout
    assert load_config(config_path).database_path == database_path


def test_config_database_command_preserves_existing_fields(tmp_path, monkeypatch) -> None:
    """Verify config database updates only the database path.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    config_path.write_text(
        'theme = "light"\n\n[database]\npath = "old.sqlite3"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    result = runner.invoke(app, ["config", "database", str(database_path)])

    assert result.exit_code == 0
    config_text = config_path.read_text(encoding="utf-8")
    assert 'theme = "light"' in config_text
    assert f'path = "{database_path}"' in config_text


def test_add_command_reports_missing_config(tmp_path, monkeypatch) -> None:
    """Verify add prompts users to create the zembra config when missing.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    result = runner.invoke(app, ["add", "hello", "--field", "work"])

    assert result.exit_code == 1
    assert (
        f"Config file is missing at {config_path}. "
        "Create it with: zembra-cli config database <file-path>"
    ) in result.stderr


def test_hello_command_does_not_require_config(tmp_path, monkeypatch) -> None:
    """Verify non-database commands do not load the zembra config.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    monkeypatch.setattr(cli, "default_config_path", lambda: tmp_path / ".zembra.env")

    result = runner.invoke(app, ["hello", "Ada"])

    assert result.exit_code == 0
    assert "Hello, Ada. Zembra is ready." in result.stdout


def test_summarize_note_content_flattens_and_truncates_text() -> None:
    """Verify note summaries are stable single-line snippets.

    Args:
        None.

    Returns:
        None.
    """
    summary = cli.summarize_note_content("first line\nsecond\tline with extra text", max_length=18)

    assert summary == "first line seco..."


def test_resolve_note_reference_returns_complete_id() -> None:
    """Verify CLI note reference helper returns repository results.

    Args:
        None.

    Returns:
        None.
    """
    repository = FakeNoteReferenceRepository(result="abcd0000000000000000000000000000")

    assert cli.resolve_note_reference(repository, "abcd") == "abcd0000000000000000000000000000"


def test_resolve_note_reference_reports_invalid_input(capsys) -> None:
    """Verify invalid note references become readable CLI failures.

    Args:
        capsys: Pytest output capture fixture.

    Returns:
        None.
    """
    repository = FakeNoteReferenceRepository(
        error=InvalidNoteReferenceError("note-123", "only hexadecimal characters are supported")
    )

    with pytest.raises(typer.Exit) as error:
        cli.resolve_note_reference(repository, "note-123")

    assert error.value.exit_code == 1
    assert (
        'Note reference "note-123" is invalid: only hexadecimal characters are supported.'
        in capsys.readouterr().err
    )


def test_resolve_note_reference_reports_short_prefix(capsys) -> None:
    """Verify short note references become readable CLI failures.

    Args:
        capsys: Pytest output capture fixture.

    Returns:
        None.
    """
    repository = FakeNoteReferenceRepository(error=NoteReferenceTooShortError("abc", 4))

    with pytest.raises(typer.Exit) as error:
        cli.resolve_note_reference(repository, "abc")

    assert error.value.exit_code == 1
    assert (
        'Note reference "abc" is too short. Use at least 4 characters.'
        in capsys.readouterr().err
    )


def test_resolve_note_reference_reports_missing_note(capsys) -> None:
    """Verify missing note references become readable CLI failures.

    Args:
        capsys: Pytest output capture fixture.

    Returns:
        None.
    """
    repository = FakeNoteReferenceRepository(error=RecordNotFoundError("notes", "abcd"))

    with pytest.raises(typer.Exit) as error:
        cli.resolve_note_reference(repository, "abcd")

    assert error.value.exit_code == 1
    assert 'Note reference "abcd" did not match any note.' in capsys.readouterr().err


def test_resolve_note_reference_reports_ambiguous_candidates(capsys) -> None:
    """Verify ambiguous note references include candidate hints.

    Args:
        capsys: Pytest output capture fixture.

    Returns:
        None.
    """
    candidates = [
        make_note("abcd0000000000000000000000000000", "first\nnote"),
        make_note("abcd1111111111111111111111111111", "second note with a longer body"),
    ]
    repository = FakeNoteReferenceRepository(
        error=AmbiguousNoteReferenceError("abcd", candidates)
    )

    with pytest.raises(typer.Exit) as error:
        cli.resolve_note_reference(repository, "abcd")

    stderr = capsys.readouterr().err
    assert error.value.exit_code == 1
    assert 'Note reference "abcd" is ambiguous. Use more characters.' in stderr
    assert "- abcd0000  first note" in stderr
    assert "- abcd1111  second note with a longer body" in stderr
