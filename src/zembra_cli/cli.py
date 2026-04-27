"""Command-line entry points for zembra-cli."""

import json
import sqlite3
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console

from zembra_cli import __version__
from zembra_cli.config import ConfigError, default_config_path, load_config, write_database_path
from zembra_cli.database import (
    DEFAULT_DATABASE_PATH,
    DatabaseInitializationError,
    database_connection,
    initialize_database_file,
    missing_core_tables,
)
from zembra_cli.interactive import render_intro_for_repository, run_interactive_session
from zembra_cli.repository import (
    AmbiguousNoteReferenceError,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
    ZembraRepository,
)

app = typer.Typer(
    name="zembra-cli",
    help="A calm command-line workspace for notes.",
    no_args_is_help=True,
)
console = Console()
config_app = typer.Typer(help="Manage zembra system configuration.")
app.add_typer(config_app, name="config")


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
) -> None:
    """Initialize the local zembra database and shared config.

    Args:
        database_path: SQLite database path to initialize.

    Returns:
        None. The command prints initialization status or exits on failure.
    """
    resolved_database_path = database_path if database_path is not None else DEFAULT_DATABASE_PATH
    config_path = default_config_path()
    config_status = "updated" if config_path.exists() else "created"

    try:
        database_result = initialize_database_file(resolved_database_path)
        config = write_database_path(database_result.database_path, config_path)
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
        config = write_database_path(file_path, default_config_path())
    except ConfigError as error:
        fail_command(error.message)

    typer.echo(f"Configured zembra database path: {config.database_path}")


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
        config = load_config(default_config_path())
    except ConfigError as error:
        fail_command(error.message)

    database_path = config.database_path.expanduser()
    require_initialized_database(database_path)

    try:
        with database_connection(database_path) as connection:
            repository = ZembraRepository(connection)
            note = repository.create_note(
                note_string_content,
                role=parsed_role,
                field_name=field,
                tag_names=parsed_tags,
            )
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
        config = load_config(default_config_path())
    except ConfigError as error:
        fail_command(error.message)

    database_path = config.database_path.expanduser()
    require_initialized_database(database_path)

    try:
        with database_connection(database_path) as connection:
            repository = ZembraRepository(connection)
            render_intro_for_repository(repository, console, database_path)
            run_interactive_session(repository, console)
    except sqlite3.Error as error:
        fail_command(f"Could not open the Zembra database: {error}")
