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
from zembra_cli.database import database_connection, initialize_database, missing_core_tables
from zembra_cli.models import FieldRecord, NoteRecord, TagRecord
from zembra_cli.repository import (
    AmbiguousNoteReferenceError,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
    ZembraRepository,
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
    config_path.write_text(
        f'[cli]\nmode = "direct"\n\n[database]\npath = "{database_path}"\n',
        encoding="utf-8",
    )
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


def seed_cli_list_items(database_path, fields: list[str], tags: list[str]) -> None:
    """Create fields and tags for list command tests.

    Args:
        database_path: Temporary database path used by the CLI.
        fields: Field names to create.
        tags: Tag names to create.

    Returns:
        None.
    """
    with database_connection(database_path) as connection:
        repository = ZembraRepository(connection)
        for field in fields:
            repository.get_or_create_field(field)
        for tag in tags:
            repository.get_or_create_tag(tag)


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


class FakeHttpRepository:
    """Fake HTTP repository used by CLI mode-switching tests.

    Attributes:
        base_url: Backend URL passed by the CLI.
        created_payloads: Captured create_note calls.
    """

    instances: list["FakeHttpRepository"] = []

    def __init__(self, base_url: str) -> None:
        """Initialize the fake repository.

        Args:
            base_url: Backend URL passed by the CLI.

        Returns:
            None.
        """
        self.base_url = base_url
        self.created_payloads: list[dict] = []
        FakeHttpRepository.instances.append(self)

    def close(self) -> None:
        """Close the fake repository.

        Args:
            None.

        Returns:
            None.
        """

    def create_note(
        self,
        content: str,
        role: str = "Human",
        field_name: str | None = None,
        tag_names: list[str] | None = None,
        device_id: str | None = None,
    ) -> NoteRecord:
        """Capture note creation and return a valid note.

        Args:
            content: Note body text.
            role: Note creation role.
            field_name: Optional field name.
            tag_names: Optional tag names.
            device_id: Optional device identifier.

        Returns:
            Created note record.
        """
        self.created_payloads.append(
            {
                "content": content,
                "role": role,
                "field_name": field_name,
                "tag_names": list(tag_names or []),
                "device_id": device_id,
            }
        )
        return make_note("abcd0000000000000000000000000000", content)

    def list_tags(self) -> list[TagRecord]:
        """Return fake tag records.

        Args:
            None.

        Returns:
            Fake tag records.
        """
        return [
            TagRecord(id="tag-1", name="alpha", created_at=1),
            TagRecord(id="tag-2", name="beta", created_at=1),
        ]

    def list_fields(self) -> list[FieldRecord]:
        """Return fake field records.

        Args:
            None.

        Returns:
            Fake field records.
        """
        return [FieldRecord(id="field-1", name="work", created_at=1)]

    def list_notes(self, include_deleted: bool = False) -> list[NoteRecord]:
        """Return fake notes.

        Args:
            include_deleted: Whether deleted notes are requested.

        Returns:
            Fake note records.
        """
        return [make_note("abcd0000000000000000000000000000", "saved")]


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


def test_list_tags_defaults_to_first_five_names(tmp_path, monkeypatch) -> None:
    """Verify list tags prints the first five names in compact form.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)
    seed_cli_list_items(
        database_path,
        fields=[],
        tags=["gamma", "alpha", "zeta", "beta", "epsilon", "delta"],
    )

    result = runner.invoke(app, ["list", "tags"])

    assert result.exit_code == 0
    assert result.stdout == "alpha  beta  delta  epsilon  gamma\n"


def test_list_fields_accepts_number_limit(tmp_path, monkeypatch) -> None:
    """Verify list fields applies the explicit number limit.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)
    seed_cli_list_items(
        database_path,
        fields=["research", "admin", "writing", "coding"],
        tags=[],
    )

    result = runner.invoke(app, ["list", "fields", "-n", "3"])

    assert result.exit_code == 0
    assert result.stdout == "admin  coding  research\n"


def test_list_tags_all_overrides_number_limit(tmp_path, monkeypatch) -> None:
    """Verify list tags -a prints every tag even when -n is supplied.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)
    seed_cli_list_items(
        database_path,
        fields=[],
        tags=["gamma", "alpha", "zeta", "beta", "epsilon", "delta"],
    )

    result = runner.invoke(app, ["list", "tags", "-n", "2", "-a"])

    assert result.exit_code == 0
    assert result.stdout == "alpha  beta  delta  epsilon  gamma  zeta\n"


def test_list_fields_empty_database_outputs_empty_content(tmp_path, monkeypatch) -> None:
    """Verify list fields succeeds with empty output when no fields exist.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)

    result = runner.invoke(app, ["list", "fields"])

    assert result.exit_code == 0
    assert result.stdout == "\n"


def test_list_tags_rejects_invalid_number(tmp_path, monkeypatch) -> None:
    """Verify list tags rejects non-positive number limits.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)

    result = runner.invoke(app, ["list", "tags", "-n", "0"])

    assert result.exit_code == 1
    assert "Number must be greater than or equal to 1." in result.stderr


def test_add_command_uses_http_mode_from_cli_config(tmp_path, monkeypatch) -> None:
    """Verify add uses HTTP mode when configured in the cli section.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    FakeHttpRepository.instances = []
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(
        '[cli]\nmode = "http"\nhttp_base_url = "http://backend.test"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)
    monkeypatch.setattr(cli, "HttpZembraRepository", FakeHttpRepository)

    result = runner.invoke(
        app,
        ["add", "hello http", "--field", "work", "--tags", "alpha,beta", "--role", "Agent"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["note"]["content"] == "hello http"
    assert payload["metadata"] == {"field": "work", "tags": ["alpha", "beta"], "role": "Agent"}
    assert FakeHttpRepository.instances[0].base_url == "http://backend.test"
    assert FakeHttpRepository.instances[0].created_payloads == [
        {
            "content": "hello http",
            "role": "Agent",
            "field_name": "work",
            "tag_names": ["alpha", "beta"],
            "device_id": None,
        }
    ]


def test_list_tags_uses_http_mode_from_cli_config(tmp_path, monkeypatch) -> None:
    """Verify list tags uses HTTP mode when configured in the cli section.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    FakeHttpRepository.instances = []
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(
        '[cli]\nmode = "http"\nhttp_base_url = "http://backend.test"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)
    monkeypatch.setattr(cli, "HttpZembraRepository", FakeHttpRepository)

    result = runner.invoke(app, ["list", "tags"])

    assert result.exit_code == 0
    assert result.stdout == "alpha  beta\n"
    assert FakeHttpRepository.instances[0].base_url == "http://backend.test"


def test_add_command_rejects_config_without_cli_mode(tmp_path, monkeypatch) -> None:
    """Verify database.path alone does not imply direct mode.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    config_path.write_text(f'[database]\npath = "{database_path}"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    result = runner.invoke(app, ["add", "hello", "--field", "work"])

    assert result.exit_code == 1
    assert "CLI mode is missing" in result.stderr


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
    config_text = config_path.read_text(encoding="utf-8")
    assert f'path = "{database_path}"' in config_text
    assert "[cli]" not in config_text


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
        'theme = "light"\n\n[cli]\nmode = "direct"\n\n[database]\npath = "old.sqlite3"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    result = runner.invoke(app, ["config", "database", str(database_path)])

    assert result.exit_code == 0
    config_text = config_path.read_text(encoding="utf-8")
    assert 'theme = "light"' in config_text
    assert 'mode = "direct"' in config_text
    assert f'path = "{database_path}"' in config_text


def test_init_command_creates_default_database_and_config(tmp_path, monkeypatch) -> None:
    """Verify init creates the default database and config paths.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / ".zembra" / "zembra.sqlite3"
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)
    monkeypatch.setattr(cli, "DEFAULT_DATABASE_PATH", database_path)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert "Initialized zembra." in result.stdout
    assert f"Database: {database_path} (created)" in result.stdout
    assert f"Config: {config_path} (created)" in result.stdout
    config = load_config(config_path)
    assert config.cli_mode == "direct"
    assert config.database_path == database_path
    with database_connection(database_path) as connection:
        assert missing_core_tables(connection) == set()


def test_init_command_updates_config_and_skips_complete_database(tmp_path, monkeypatch) -> None:
    """Verify init is safe to rerun against a complete database.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    config_path.write_text('theme = "light"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    first_result = runner.invoke(app, ["init", "--database", str(database_path)])
    second_result = runner.invoke(app, ["init", "--database", str(database_path)])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert f"Database: {database_path} (already initialized)" in second_result.stdout
    assert f"Config: {config_path} (updated)" in second_result.stdout
    config_text = config_path.read_text(encoding="utf-8")
    assert 'theme = "light"' in config_text
    assert 'mode = "direct"' in config_text
    assert f'path = "{database_path}"' in config_text


def test_init_command_rejects_incomplete_database(tmp_path, monkeypatch) -> None:
    """Verify init does not overwrite an existing incomplete database.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)
    with database_connection(database_path) as connection:
        connection.execute("CREATE TABLE notes (id TEXT PRIMARY KEY)")

    result = runner.invoke(app, ["init", "--database", str(database_path)])

    assert result.exit_code == 1
    assert f"Database already exists at {database_path}" in result.stderr
    assert not config_path.exists()


def test_init_command_reports_invalid_existing_config(tmp_path, monkeypatch) -> None:
    """Verify init reports invalid TOML config without hiding the parse error.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    config_path.write_text("[database\n", encoding="utf-8")
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    result = runner.invoke(app, ["init", "--database", str(database_path)])

    assert result.exit_code == 1
    assert "Config file is not valid TOML" in result.stderr


def test_init_command_allows_add_to_use_initialized_database(tmp_path, monkeypatch) -> None:
    """Verify add can use the config and database created by init.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    init_result = runner.invoke(app, ["init", "--database", str(database_path)])
    add_result = runner.invoke(app, ["add", "hello from init", "--field", "work"])

    assert init_result.exit_code == 0
    assert add_result.exit_code == 0
    payload = json.loads(add_result.stdout)
    assert payload["note"]["content"] == "hello from init"
    assert payload["metadata"]["field"] == "work"


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


def test_run_command_reports_missing_config(tmp_path, monkeypatch) -> None:
    """Verify run prompts users to create the zembra config when missing.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    monkeypatch.setattr(cli, "default_config_path", lambda: config_path)

    result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert (
        f"Config file is missing at {config_path}. "
        "Create it with: zembra-cli config database <file-path>"
    ) in result.stderr


def test_run_command_reports_missing_database(tmp_path, monkeypatch) -> None:
    """Verify run fails clearly when the configured database file is absent.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "missing.sqlite3"
    configure_cli_database(monkeypatch, tmp_path, database_path)

    result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert f"Database is not initialized at {database_path}" in result.stderr


def test_run_command_starts_intro_and_interactive_session(tmp_path, monkeypatch) -> None:
    """Verify run loads a configured database and starts the interactive loop.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_cli_database(database_path)
    configure_cli_database(monkeypatch, tmp_path, database_path)
    calls: list[str] = []

    def fake_render_intro(repository, output_console, rendered_database_path) -> None:
        """Record intro rendering without printing the full Rich panel.

        Args:
            repository: Repository created by the run command.
            output_console: Console supplied by the CLI.
            rendered_database_path: Database path passed to the intro renderer.

        Returns:
            None.
        """
        calls.append(f"intro:{rendered_database_path}:{len(repository.list_notes())}")

    def fake_run_interactive_session(repository, output_console) -> None:
        """Record interactive session startup without blocking for input.

        Args:
            repository: Repository created by the run command.
            output_console: Console supplied by the CLI.

        Returns:
            None.
        """
        calls.append(f"session:{len(repository.list_notes())}")

    monkeypatch.setattr(cli, "render_intro_for_repository", fake_render_intro)
    monkeypatch.setattr(cli, "run_interactive_session", fake_run_interactive_session)

    result = runner.invoke(app, ["run"])

    assert result.exit_code == 0
    assert calls == [f"intro:{database_path}:0", "session:0"]


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
