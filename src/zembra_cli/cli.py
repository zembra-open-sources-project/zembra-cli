"""Command-line entry points for zembra-cli."""

import json
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.markdown import Markdown

from zembra_cli import __version__
from zembra_cli.config import (
    ConfigError,
    default_cli_config_path,
    default_global_config_path,
    load_cascading_config,
    write_database_path,
)
from zembra_cli.database import (
    DEFAULT_DATABASE_PATH,
    DatabaseInitializationError,
    database_connection,
    initialize_database_file,
    missing_core_tables,
)
from zembra_cli.http_client import HttpZembraRepository, ZembraHttpClientError
from zembra_cli.interactive import render_intro_for_repository, run_interactive_session
from zembra_cli.mcp_server import run_mcp_server
from zembra_cli.models import FieldNotesGroup, NoteWithMetadata, TaggedNotesGroup
from zembra_cli.repository import (
    AmbiguousNoteReferenceError,
    CliRepository,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
    ZembraRepository,
)

DEFAULT_RANDOM_NOTES_TEXT_COUNT = 3
DEFAULT_RANDOM_NOTES_JSON_COUNT = 20
DEFAULT_RANDOM_GROUP_COUNT = 2
DEFAULT_RANDOM_GROUP_NOTE_COUNT = 5

app = typer.Typer(
    name="zembra-cli",
    help="A calm command-line workspace for notes.",
    no_args_is_help=True,
)
console = Console()
config_app = typer.Typer(help="Manage zembra system configuration.")
list_app = typer.Typer(help="List zembra fields and tags.")
random_app = typer.Typer(help="Show random zembra notes.")
app.add_typer(config_app, name="config")
app.add_typer(list_app, name="list")
app.add_typer(random_app, name="random")


def parse_tag_values(tag_values: list[str] | None) -> list[str]:
    """Parse repeated and comma-separated tag option values.

    Args:
        tag_values: Raw values received from repeated ``--tags`` options.

    Returns:
        A stable, de-duplicated list of non-empty tag names.
    """
    parsed_tags: list[str] = []
    seen_tags: set[str] = set()
    for tag_value in tag_values or []:
        for raw_tag in tag_value.split(","):
            tag = raw_tag.strip()
            if tag and tag not in seen_tags:
                parsed_tags.append(tag)
                seen_tags.add(tag)
    return parsed_tags


def parse_role_value(role_value: str) -> Literal["Human", "Agent"]:
    """Normalize CLI role aliases to shared schema role values.

    Args:
        role_value: User-provided role option value.

    Returns:
        Shared schema role value accepted by the database.
    """
    normalized_role = role_value.strip().lower()
    role_aliases: dict[str, Literal["Human", "Agent"]] = {
        "human": "Human",
        "h": "Human",
        "agent": "Agent",
        "a": "Agent",
    }
    try:
        return role_aliases[normalized_role]
    except KeyError:
        fail_command('Role must be one of: Human, Agent, human, agent, h, a.')


def fail_command(message: str) -> None:
    """Print a command failure reason and exit with a non-zero status.

    Args:
        message: Natural-language explanation for the command failure.

    Returns:
        None. The process exits after printing the message.
    """
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


def summarize_note_content(content: str, max_length: int = 48) -> str:
    """Create a single-line note summary for command-line error messages.

    Args:
        content: Note body text.
        max_length: Maximum summary length including any ellipsis.

    Returns:
        Single-line note summary.
    """
    summary = " ".join(content.split())
    if len(summary) <= max_length:
        return summary
    if max_length <= 3:
        return "." * max_length
    return f"{summary[: max_length - 3]}..."


def format_ambiguous_note_reference(error: AmbiguousNoteReferenceError) -> str:
    """Format an ambiguous note reference error for CLI output.

    Args:
        error: Repository ambiguity error containing matching note candidates.

    Returns:
        Multi-line error message with candidate note hints.
    """
    lines = [
        f'Note reference "{error.note_ref}" is ambiguous. Use more characters.',
        "Matches:",
    ]
    for candidate in error.candidates:
        lines.append(f"- {candidate.id[:8]}  {summarize_note_content(candidate.content)}")
    return "\n".join(lines)


def format_compact_names(names: list[str]) -> str:
    """Format names as compact CLI output.

    Args:
        names: Ordered names to render.

    Returns:
        A single-line string joined by two spaces.
    """
    return "  ".join(names)


def select_list_names(names: list[str], number: int, list_all: bool) -> list[str]:
    """Apply list command limit options to ordered names.

    Args:
        names: Ordered names from the repository.
        number: Maximum number of names to return when list_all is false.
        list_all: Whether all names should be returned.

    Returns:
        Names selected for output.
    """
    if number < 1:
        fail_command("Number must be greater than or equal to 1.")
    if list_all:
        return names
    return names[:number]


def require_positive_number(value: int, name: str) -> None:
    """Validate a positive integer CLI option.

    Args:
        value: User-provided integer option.
        name: Human-readable option name used in the error message.

    Returns:
        None. The command exits when validation fails.
    """
    if value < 1:
        fail_command(f"{name} must be greater than or equal to 1.")


def resolve_random_number(number: int | None, json_output: bool) -> int:
    """Resolve random notes count from explicit input and output mode.

    Args:
        number: Optional user-provided random notes count.
        json_output: Whether JSON output is requested.

    Returns:
        Explicit count, or the mode-specific default.
    """
    if number is not None:
        return number
    if json_output:
        return DEFAULT_RANDOM_NOTES_JSON_COUNT
    return DEFAULT_RANDOM_NOTES_TEXT_COUNT


def note_with_metadata_to_dict(item: NoteWithMetadata) -> dict:
    """Convert a note with metadata to a JSON-compatible dictionary.

    Args:
        item: Note and metadata object returned by a repository.

    Returns:
        JSON-compatible dictionary preserving complete note, field, and tags.
    """
    return item.model_dump()


def tagged_notes_group_to_dict(group: TaggedNotesGroup) -> dict:
    """Convert a tagged notes group to a JSON-compatible dictionary.

    Args:
        group: Tagged notes group returned by a repository.

    Returns:
        JSON-compatible dictionary preserving the group tag and notes.
    """
    return group.model_dump()


def field_notes_group_to_dict(group: FieldNotesGroup) -> dict:
    """Convert a field notes group to a JSON-compatible dictionary.

    Args:
        group: Field notes group returned by a repository.

    Returns:
        JSON-compatible dictionary preserving the group field and notes.
    """
    return group.model_dump()


def format_note_metadata(item: NoteWithMetadata) -> str:
    """Format a note with metadata as human-readable text.

    Args:
        item: Note and metadata object returned by a repository.

    Returns:
        Multi-line metadata text for terminal display.
    """
    field_name = item.field.name if item.field is not None else "null"
    tag_names = ", ".join(tag.name for tag in item.tags) if item.tags else "[]"
    return "\n".join(
        [
            f"{item.note.id}  {item.note.role}",
            f"Field: {field_name}",
            f"Tags: {tag_names}",
            f"Created: {item.note.created_at}",
            f"Updated: {item.note.updated_at}",
        ]
    )


def print_random_notes(notes: list[NoteWithMetadata]) -> None:
    """Print random notes as human-readable Rich output.

    Args:
        notes: Random note records with metadata.

    Returns:
        None.
    """
    for index, note in enumerate(notes):
        if index > 0:
            console.print()
        console.print(format_note_metadata(note))
        console.print("Content:")
        console.print(Markdown(note.note.content))


def print_random_tagged_notes(groups: list[TaggedNotesGroup]) -> None:
    """Print random tagged notes as human-readable Rich output.

    Args:
        groups: Random tag groups with note metadata.

    Returns:
        None.
    """
    for index, group in enumerate(groups):
        if index > 0:
            console.print()
        console.print(f"# tag: {group.tag.name}")
        console.print()
        print_random_notes(group.notes)


def print_random_field_notes(groups: list[FieldNotesGroup]) -> None:
    """Print random field notes as human-readable Rich output.

    Args:
        groups: Random field groups with note metadata.

    Returns:
        None.
    """
    for index, group in enumerate(groups):
        if index > 0:
            console.print()
        console.print(f"# field: {group.field.name}")
        console.print()
        print_random_notes(group.notes)


def resolve_note_reference(repository: ZembraRepository, note_ref: str) -> str:
    """Resolve a user-provided note reference or fail the CLI command.

    Args:
        repository: Repository used to resolve note identifiers.
        note_ref: User-provided full note id or note id prefix.

    Returns:
        Complete note id for a unique matching note.
    """
    try:
        return repository.resolve_note_id(note_ref)
    except InvalidNoteReferenceError as error:
        fail_command(f'Note reference "{error.note_ref}" is invalid: {error.reason}.')
    except NoteReferenceTooShortError as error:
        fail_command(
            f'Note reference "{error.note_ref}" is too short. '
            f"Use at least {error.minimum_length} characters."
        )
    except AmbiguousNoteReferenceError as error:
        fail_command(format_ambiguous_note_reference(error))
    except RecordNotFoundError as error:
        fail_command(f'Note reference "{error.record_id}" did not match any note.')


def require_initialized_database(database_path) -> None:
    """Validate that a configured local database exists and has core tables.

    Args:
        database_path: SQLite database path loaded from zembra config.

    Returns:
        None. The command exits when the database is unavailable.
    """
    database_path = database_path.expanduser()
    if not database_path.exists():
        fail_command(f"Database is not initialized at {database_path}")

    try:
        with database_connection(database_path) as connection:
            missing_tables = missing_core_tables(connection)
    except sqlite3.Error as error:
        fail_command(f"Could not open the Zembra database: {error}")

    if missing_tables:
        fail_command(f"Database is not initialized at {database_path}")


def ensure_workspace(database_path: Path, workspace_id: str, workspace_name: str | None) -> None:
    """Create the configured workspace record when it is missing.

    Args:
        database_path: Initialized SQLite database path.
        workspace_id: Workspace identifier to ensure.
        workspace_name: Optional workspace display name to store on creation.

    Returns:
        None.
    """
    now = int(time.time())
    try:
        with database_connection(database_path) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO workspaces (
                    id, workspace_name, created_at, updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (workspace_id, workspace_name, now, now),
            )
    except sqlite3.Error as error:
        fail_command(f"Could not initialize workspace {workspace_id}: {error}")


@contextmanager
def open_cli_repository() -> Iterator[tuple[CliRepository, str]]:
    """Open the repository configured for CLI database commands.

    Args:
        None.

    Returns:
        A context manager yielding the repository and a human-readable location.
    """
    try:
        config = load_cascading_config(default_cli_config_path(), default_global_config_path())
    except ConfigError as error:
        fail_command(error.message)

    if config.cli_mode == "http":
        if config.http_base_url is None:
            fail_command("HTTP backend URL is missing in the zembra config.")
        repository = HttpZembraRepository(config.http_base_url)
        try:
            yield repository, config.http_base_url
        finally:
            repository.close()
        return

    if config.database_path is None:
        fail_command("Database path is missing in the zembra config.")
    if config.workspace_id is None:
        fail_command("Workspace ID is missing in the zembra CLI config. Run: zembra-cli init")
    database_path = config.database_path.expanduser()
    require_initialized_database(database_path)

    try:
        with database_connection(database_path) as connection:
            yield ZembraRepository(connection, workspace_id=config.workspace_id), str(database_path)
    except sqlite3.Error as error:
        fail_command(f"Could not open the Zembra database: {error}")


def version_callback(value: bool) -> None:
    """Print the application version and exit when requested.

    Args:
        value: Whether the version flag was provided.

    Returns:
        None. The process exits after printing the version.
    """
    if value:
        console.print(f"zembra-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            help="Show the installed zembra-cli version.",
        ),
    ] = None,
) -> None:
    """Configure global CLI options.

    Args:
        version: Optional flag that prints the package version.

    Returns:
        None.
    """


@app.command("mcp")
def mcp() -> None:
    """Run the local Zembra MCP server over stdio.

    Args:
        None.

    Returns:
        None.
    """
    run_mcp_server()


@app.command()
def hello(
    name: Annotated[
        str,
        typer.Argument(help="Name to greet while the note commands are being built."),
    ] = "there",
) -> None:
    """Print a friendly smoke-test message.

    Args:
        name: Name included in the greeting.

    Returns:
        None.
    """
    console.print(f"Hello, {name}. Zembra is ready.")


@app.command()
def init(
    database_path: Annotated[
        Path | None,
        typer.Option(
            "--database",
            help="SQLite database path to initialize and store in the zembra config.",
        ),
    ] = None,
    workspace_id: Annotated[
        str | None,
        typer.Option(
            "--workspace-id",
            help="Workspace UUID to store in the zembra CLI config.",
        ),
    ] = None,
    workspace_name: Annotated[
        str | None,
        typer.Option(
            "--workspace-name",
            help="Optional workspace display name to store on initialization.",
        ),
    ] = None,
) -> None:
    """Initialize the local zembra database and shared config.

    Args:
        database_path: SQLite database path to initialize.

    Returns:
        None. The command prints initialization status or exits on failure.
    """
    resolved_database_path = database_path if database_path is not None else DEFAULT_DATABASE_PATH
    config_path = default_cli_config_path()
    config_status = "updated" if config_path.exists() else "created"

    try:
        resolved_workspace_id = workspace_id or str(uuid.uuid4())
        database_result = initialize_database_file(resolved_database_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = write_database_path(
            database_result.database_path,
            config_path,
            set_direct_mode=True,
            workspace_id=resolved_workspace_id,
            workspace_name=workspace_name,
        )
        ensure_workspace(database_result.database_path, resolved_workspace_id, workspace_name)
    except DatabaseInitializationError as error:
        fail_command(error.message)
    except ConfigError as error:
        fail_command(error.message)

    database_status = (
        "already initialized" if database_result.status == "skipped" else database_result.status
    )
    typer.echo("Initialized zembra.")
    typer.echo(f"Database: {database_result.database_path} ({database_status})")
    typer.echo(f"Config: {config_path} ({config_status})")
    typer.echo(f"Configured database path: {config.database_path}")
    typer.echo(f"Workspace: {config.workspace_id}")


@config_app.command()
def database(
    file_path: Annotated[
        str,
        typer.Argument(help="SQLite database path to store in the zembra config."),
    ],
) -> None:
    """Write the zembra database path to the shared config file.

    Args:
        file_path: SQLite database path to store.

    Returns:
        None. The command prints a success message or exits on failure.
    """
    try:
        config_path = default_cli_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = write_database_path(file_path, config_path)
    except ConfigError as error:
        fail_command(error.message)

    typer.echo(f"Configured zembra database path: {config.database_path}")


@list_app.command("tags")
def list_tags(
    number: Annotated[
        int,
        typer.Option("-n", "--number", help="Maximum number of tags to list."),
    ] = 5,
    list_all: Annotated[
        bool,
        typer.Option("-a", "--all", help="List all tags and ignore --number."),
    ] = False,
) -> None:
    """List tag names in compact form.

    Args:
        number: Maximum number of tag names to print unless list_all is true.
        list_all: Whether to print every tag name.

    Returns:
        None. The command prints compact tag names or exits on failure.
    """
    try:
        with open_cli_repository() as (repository, _location):
            names = [tag.name for tag in repository.list_tags()]
    except ZembraHttpClientError as error:
        fail_command(error.message)
    except sqlite3.Error as error:
        fail_command(f"Could not list tags: {error}")

    selected_names = select_list_names(names, number, list_all)
    typer.echo(format_compact_names(selected_names))


@list_app.command("fields")
def list_fields(
    number: Annotated[
        int,
        typer.Option("-n", "--number", help="Maximum number of fields to list."),
    ] = 5,
    list_all: Annotated[
        bool,
        typer.Option("-a", "--all", help="List all fields and ignore --number."),
    ] = False,
) -> None:
    """List field names in compact form.

    Args:
        number: Maximum number of field names to print unless list_all is true.
        list_all: Whether to print every field name.

    Returns:
        None. The command prints compact field names or exits on failure.
    """
    try:
        with open_cli_repository() as (repository, _location):
            names = [field.name for field in repository.list_fields()]
    except ZembraHttpClientError as error:
        fail_command(error.message)
    except sqlite3.Error as error:
        fail_command(f"Could not list fields: {error}")

    selected_names = select_list_names(names, number, list_all)
    typer.echo(format_compact_names(selected_names))


@random_app.command("notes")
def random_notes(
    number: Annotated[
        int | None,
        typer.Option("-n", "--number", help="Number of random notes to return."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output random notes as JSON."),
    ] = False,
) -> None:
    """Show random visible notes.

    Args:
        number: Optional maximum number of random notes to print.
        json_output: Whether to print JSON instead of human-readable text.

    Returns:
        None. The command prints random notes or exits on failure.
    """
    resolved_number = resolve_random_number(number, json_output)
    require_positive_number(resolved_number, "Number")
    try:
        with open_cli_repository() as (repository, _location):
            notes = repository.random_notes(resolved_number)
    except ZembraHttpClientError as error:
        fail_command(error.message)
    except sqlite3.Error as error:
        fail_command(f"Could not list random notes: {error}")

    if json_output:
        payload = {"notes": [note_with_metadata_to_dict(note) for note in notes]}
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return
    print_random_notes(notes)


@random_app.command("tags")
def random_tags(
    number: Annotated[
        int,
        typer.Option("-n", "--number", help="Number of random tags to return."),
    ] = DEFAULT_RANDOM_GROUP_COUNT,
    count: Annotated[
        int,
        typer.Option("--count", help="Maximum cumulative number of notes to return."),
    ] = DEFAULT_RANDOM_GROUP_NOTE_COUNT,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output random tag groups as JSON."),
    ] = False,
) -> None:
    """Show visible notes grouped by random tags.

    Args:
        number: Maximum number of random tag groups to print.
        count: Maximum cumulative number of notes to print.
        json_output: Whether to print JSON instead of human-readable text.

    Returns:
        None. The command prints random tag groups or exits on failure.
    """
    require_positive_number(number, "Number")
    require_positive_number(count, "Count")
    try:
        with open_cli_repository() as (repository, _location):
            groups = repository.random_tagged_notes(number, count)
    except ZembraHttpClientError as error:
        fail_command(error.message)
    except sqlite3.Error as error:
        fail_command(f"Could not list random tag notes: {error}")

    if json_output:
        payload = {"tagged_notes": [tagged_notes_group_to_dict(group) for group in groups]}
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return
    print_random_tagged_notes(groups)


@random_app.command("fields")
def random_fields(
    number: Annotated[
        int,
        typer.Option("-n", "--number", help="Number of random fields to return."),
    ] = DEFAULT_RANDOM_GROUP_COUNT,
    count: Annotated[
        int,
        typer.Option("--count", help="Maximum cumulative number of notes to return."),
    ] = DEFAULT_RANDOM_GROUP_NOTE_COUNT,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output random field groups as JSON."),
    ] = False,
) -> None:
    """Show visible notes grouped by random fields.

    Args:
        number: Maximum number of random field groups to print.
        count: Maximum cumulative number of notes to print.
        json_output: Whether to print JSON instead of human-readable text.

    Returns:
        None. The command prints random field groups or exits on failure.
    """
    require_positive_number(number, "Number")
    require_positive_number(count, "Count")
    try:
        with open_cli_repository() as (repository, _location):
            groups = repository.random_field_notes(number, count)
    except ZembraHttpClientError as error:
        fail_command(error.message)
    except sqlite3.Error as error:
        fail_command(f"Could not list random field notes: {error}")

    if json_output:
        payload = {"field_notes": [field_notes_group_to_dict(group) for group in groups]}
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return
    print_random_field_notes(groups)


@app.command()
def add(
    note_string_content: Annotated[
        str,
        typer.Argument(help="Note content to save exactly as received from the shell."),
    ],
    field: Annotated[
        str,
        typer.Option("--field", help="Field name to associate with the note."),
    ],
    tags: Annotated[
        list[str] | None,
        typer.Option("--tags", help="Tag name or comma-separated tag names."),
    ] = None,
    role: Annotated[
        str,
        typer.Option("--role", help="Creation role: Human, Agent, h, or a."),
    ] = "Human",
) -> None:
    """Create a note with one field and zero or more tags.

    Args:
        note_string_content: Note body received from the shell.
        field: Field name to associate with the note.
        tags: Raw tag option values, supporting repeats and comma-separated values.
        role: Raw note creation role option value.

    Returns:
        None. The command prints JSON on success or exits on failure.
    """
    parsed_tags = parse_tag_values(tags)
    parsed_role = parse_role_value(role)
    try:
        with open_cli_repository() as (repository, _location):
            note = repository.create_note(
                note_string_content,
                role=parsed_role,
                field_name=field,
                tag_names=parsed_tags,
            )
    except ZembraHttpClientError as error:
        fail_command(error.message)
    except sqlite3.Error as error:
        fail_command(f"Could not create the note: {error}")

    payload = {
        "note": note.model_dump(),
        "metadata": {
            "field": field,
            "tags": parsed_tags,
            "role": parsed_role,
        },
    }
    typer.echo(json.dumps(payload, ensure_ascii=False))


@app.command()
def run() -> None:
    """Start the persistent interactive note capture session.

    Args:
        None.

    Returns:
        None. The command exits when the user enters /exit or sends EOF.
    """
    try:
        with open_cli_repository() as (repository, location):
            render_intro_for_repository(repository, console, location)
            run_interactive_session(repository, console)
    except ZembraHttpClientError as error:
        fail_command(error.message)
    except sqlite3.Error as error:
        fail_command(f"Could not open the Zembra database: {error}")
