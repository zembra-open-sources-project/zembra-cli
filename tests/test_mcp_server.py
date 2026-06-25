"""Tests for the local Zembra MCP server."""

import sqlite3

import pytest

from zembra_cli.database import database_connection, initialize_database
from zembra_cli.mcp_server import (
    ZembraMcpError,
    create_note_tool,
    list_fields_tool,
    list_notes_tool,
    list_tags_tool,
    random_notes_tool,
)

TEST_WORKSPACE_ID = "550e8400-e29b-41d4-a716-446655440000"


def write_direct_config(tmp_path, database_path) -> object:
    """Write a direct-mode config for MCP tests.

    Args:
        tmp_path: Pytest temporary directory fixture.
        database_path: Temporary SQLite database path.

    Returns:
        The temporary config path.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(
        f'[cli]\nmode = "direct"\n\n[database]\npath = "{database_path}"\n\n'
        f'[workspace]\nid = "{TEST_WORKSPACE_ID}"\n',
        encoding="utf-8",
    )
    return config_path


def initialize_test_database(database_path) -> None:
    """Initialize a temporary Zembra database.

    Args:
        database_path: Temporary SQLite database path.

    Returns:
        None.
    """
    with database_connection(database_path) as connection:
        initialize_database(connection)
        connection.execute(
            """
            INSERT INTO workspaces (id, workspace_name, created_at, updated_at)
            VALUES (?, NULL, 1, 1)
            """,
            (TEST_WORKSPACE_ID,),
        )


def test_create_note_tool_defaults_to_agent_role(tmp_path) -> None:
    """Verify MCP-created notes are marked as Agent by default.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_test_database(database_path)
    config_path = write_direct_config(tmp_path, database_path)

    note = create_note_tool(
        "agent note",
        field_name="work",
        tag_names=["mcp", "agent"],
        config_path=config_path,
    )

    assert note["content"] == "agent note"
    assert note["role"] == "Agent"
    assert list_notes_tool(config_path=config_path)[0]["id"] == note["id"]


def test_create_note_tool_accepts_explicit_human_role(tmp_path) -> None:
    """Verify MCP create_note can explicitly write a Human note.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_test_database(database_path)
    config_path = write_direct_config(tmp_path, database_path)

    note = create_note_tool("human note", role="Human", config_path=config_path)

    assert note["role"] == "Human"


def test_list_taxonomy_tools_return_local_database_records(tmp_path) -> None:
    """Verify MCP taxonomy tools read direct SQLite records.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_test_database(database_path)
    config_path = write_direct_config(tmp_path, database_path)
    create_note_tool("tagged note", field_name="work", tag_names=["mcp"], config_path=config_path)

    fields = list_fields_tool(config_path=config_path)
    tags = list_tags_tool(config_path=config_path)

    assert [field["name"] for field in fields] == ["work"]
    assert [tag["name"] for tag in tags] == ["mcp"]


def test_random_notes_tool_returns_metadata(tmp_path) -> None:
    """Verify random_notes returns visible notes with field and tag metadata.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_test_database(database_path)
    config_path = write_direct_config(tmp_path, database_path)
    create_note_tool("random note", field_name="work", tag_names=["mcp"], config_path=config_path)

    notes = random_notes_tool(1, config_path=config_path)

    assert len(notes) == 1
    assert notes[0]["note"]["content"] == "random note"
    assert notes[0]["field"]["name"] == "work"
    assert [tag["name"] for tag in notes[0]["tags"]] == ["mcp"]


def test_random_notes_tool_rejects_invalid_number(tmp_path) -> None:
    """Verify random_notes rejects non-positive counts.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "zembra.sqlite3"
    initialize_test_database(database_path)
    config_path = write_direct_config(tmp_path, database_path)

    with pytest.raises(ZembraMcpError, match="Number must be greater than or equal to 1"):
        random_notes_tool(0, config_path=config_path)


def test_mcp_tools_reject_http_mode_config(tmp_path) -> None:
    """Verify the MCP server never uses HTTP backend mode.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(
        '[cli]\nmode = "http"\nhttp_base_url = "http://127.0.0.1:3000"\n\n'
        '[workspace]\nid = "550e8400-e29b-41d4-a716-446655440000"\n',
        encoding="utf-8",
    )

    with pytest.raises(ZembraMcpError, match="requires direct database mode"):
        list_notes_tool(config_path=config_path)


def test_mcp_tools_report_missing_database(tmp_path) -> None:
    """Verify missing direct databases return a clear MCP error.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "missing.sqlite3"
    config_path = write_direct_config(tmp_path, database_path)

    with pytest.raises(ZembraMcpError, match="Database is not initialized"):
        list_notes_tool(config_path=config_path)


def test_mcp_tools_report_incomplete_database(tmp_path) -> None:
    """Verify incomplete SQLite schemas return a clear MCP error.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    database_path = tmp_path / "empty.sqlite3"
    sqlite3.connect(database_path).close()
    config_path = write_direct_config(tmp_path, database_path)

    with pytest.raises(ZembraMcpError, match="Database is not initialized"):
        list_notes_tool(config_path=config_path)
