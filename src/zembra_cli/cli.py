"""Command-line entry points for zembra-cli."""

import json
import sqlite3
from typing import Annotated

import typer
from rich.console import Console

from zembra_cli import __version__
from zembra_cli.config import ConfigError, default_config_path, load_config, write_database_path
from zembra_cli.db import database_connection, missing_core_tables
from zembra_cli.repository import ZembraRepository

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


def fail_command(message: str) -> None:
    """Print a command failure reason and exit with a non-zero status.

    Args:
        message: Natural-language explanation for the command failure.

    Returns:
        None. The process exits after printing the message.
    """
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


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
) -> None:
    """Create a note with one field and zero or more tags.

    Args:
        note_string_content: Note body received from the shell.
        field: Field name to associate with the note.
        tags: Raw tag option values, supporting repeats and comma-separated values.

    Returns:
        None. The command prints JSON on success or exits on failure.
    """
    parsed_tags = parse_tag_values(tags)
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
        },
    }
    typer.echo(json.dumps(payload, ensure_ascii=False))
