"""Local MCP server for direct Zembra database access."""

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from zembra_cli.config import ConfigError, default_config_path, load_config
from zembra_cli.database import database_connection, missing_core_tables
from zembra_cli.models import FieldRecord, NoteRecord, NoteWithMetadata, TagRecord
from zembra_cli.repository import ZembraRepository

MCP_SERVER_NAME = "zembra"


class ZembraMcpError(RuntimeError):
    """Signal an MCP server configuration or repository failure.

    Attributes:
        message: Natural-language description safe to return to MCP clients.
    """

    def __init__(self, message: str) -> None:
        """Initialize the MCP error.

        Args:
            message: Natural-language description safe to return to MCP clients.

        Returns:
            None.
        """
        self.message = message
        super().__init__(message)


def model_to_dict(model: NoteRecord | FieldRecord | TagRecord | NoteWithMetadata) -> dict:
    """Convert a Pydantic model to a JSON-compatible dictionary.

    Args:
        model: Zembra schema model returned by the repository.

    Returns:
        JSON-compatible model dictionary.
    """
    return model.model_dump(mode="json")


@contextmanager
def open_mcp_repository(config_path: str | Path | None = None) -> Iterator[ZembraRepository]:
    """Open a direct SQLite repository for one MCP tool call.

    Args:
        config_path: Optional configuration path used by tests or callers.

    Returns:
        An iterator yielding a direct SQLite repository.
    """
    try:
        config = load_config(config_path or default_config_path())
    except ConfigError as error:
        raise ZembraMcpError(error.message) from error

    if config.cli_mode != "direct":
        raise ZembraMcpError("MCP Server requires direct database mode.")
    if config.database_path is None:
        raise ZembraMcpError("Database path is missing in the zembra config.")

    database_path = config.database_path.expanduser()
    if not database_path.exists():
        raise ZembraMcpError(f"Database is not initialized at {database_path}")

    try:
        with database_connection(database_path) as connection:
            missing_tables = missing_core_tables(connection)
            if missing_tables:
                raise ZembraMcpError(f"Database is not initialized at {database_path}")
            yield ZembraRepository(connection)
    except sqlite3.Error as error:
        raise ZembraMcpError(f"Could not open the Zembra database: {error}") from error


def create_note_tool(
    content: str,
    field_name: str | None = None,
    tag_names: Sequence[str] | None = None,
    role: Literal["Human", "Agent"] = "Agent",
    config_path: str | Path | None = None,
) -> dict:
    """Create a note through the local MCP database chain.

    Args:
        content: Note body text.
        field_name: Optional field name to attach to the note.
        tag_names: Optional tag names to attach to the note.
        role: Immutable creation role, defaulting to Agent for MCP calls.
        config_path: Optional configuration path used by tests or callers.

    Returns:
        Created note record as a JSON-compatible dictionary.
    """
    with open_mcp_repository(config_path) as repository:
        note = repository.create_note(
            content=content,
            role=role,
            field_name=field_name,
            tag_names=tag_names,
        )
    return model_to_dict(note)


def list_notes_tool(
    include_deleted: bool = False,
    config_path: str | Path | None = None,
) -> list[dict]:
    """List notes through the local MCP database chain.

    Args:
        include_deleted: Whether soft-deleted notes are included.
        config_path: Optional configuration path used by tests or callers.

    Returns:
        Note records as JSON-compatible dictionaries.
    """
    with open_mcp_repository(config_path) as repository:
        notes = repository.list_notes(include_deleted=include_deleted)
    return [model_to_dict(note) for note in notes]


def list_tags_tool(config_path: str | Path | None = None) -> list[dict]:
    """List tags through the local MCP database chain.

    Args:
        config_path: Optional configuration path used by tests or callers.

    Returns:
        Tag records as JSON-compatible dictionaries.
    """
    with open_mcp_repository(config_path) as repository:
        tags = repository.list_tags()
    return [model_to_dict(tag) for tag in tags]


def list_fields_tool(config_path: str | Path | None = None) -> list[dict]:
    """List fields through the local MCP database chain.

    Args:
        config_path: Optional configuration path used by tests or callers.

    Returns:
        Field records as JSON-compatible dictionaries.
    """
    with open_mcp_repository(config_path) as repository:
        fields = repository.list_fields()
    return [model_to_dict(field) for field in fields]


def random_notes_tool(number: int, config_path: str | Path | None = None) -> list[dict]:
    """List random visible notes through the local MCP database chain.

    Args:
        number: Maximum number of random notes to return.
        config_path: Optional configuration path used by tests or callers.

    Returns:
        Random note records with metadata as JSON-compatible dictionaries.
    """
    if number < 1:
        raise ZembraMcpError("Number must be greater than or equal to 1.")

    with open_mcp_repository(config_path) as repository:
        notes = repository.random_notes(number)
    return [model_to_dict(note) for note in notes]


def create_mcp_server(config_path: str | Path | None = None) -> FastMCP:
    """Create the local Zembra MCP server and register tools.

    Args:
        config_path: Optional configuration path used by tests or callers.

    Returns:
        Configured FastMCP server.
    """
    server = FastMCP(MCP_SERVER_NAME)

    @server.tool()
    def create_note(
        content: str,
        field_name: str | None = None,
        tag_names: list[str] | None = None,
        role: Literal["Human", "Agent"] = "Agent",
    ) -> dict:
        """Create a local Zembra note."""
        return create_note_tool(content, field_name, tag_names, role, config_path)

    @server.tool()
    def list_notes(include_deleted: bool = False) -> list[dict]:
        """List local Zembra notes."""
        return list_notes_tool(include_deleted, config_path)

    @server.tool()
    def list_tags() -> list[dict]:
        """List local Zembra tags."""
        return list_tags_tool(config_path)

    @server.tool()
    def list_fields() -> list[dict]:
        """List local Zembra fields."""
        return list_fields_tool(config_path)

    @server.tool()
    def random_notes(number: int) -> list[dict]:
        """List random visible local Zembra notes."""
        return random_notes_tool(number, config_path)

    return server


def run_mcp_server(config_path: str | Path | None = None) -> None:
    """Run the local Zembra MCP server over stdio.

    Args:
        config_path: Optional configuration path used by tests or callers.

    Returns:
        None.
    """
    create_mcp_server(config_path).run(transport="stdio")
