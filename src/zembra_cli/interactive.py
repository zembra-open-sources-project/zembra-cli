"""Interactive Rich-powered note capture for zembra-cli."""

import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from zembra_cli.repository import ZembraRepository

DEFAULT_INTERACTIVE_FIELD = "inbox"
EXIT_COMMAND = "/exit"
HELP_COMMAND = "/help"
MARKER_PATTERN = re.compile(r"^([@#])([A-Za-z0-9][A-Za-z0-9_-]*)([.,;:!?)]*)$")


@dataclass(frozen=True)
class InteractiveNoteInput:
    """Represent a parsed interactive note entry.

    Attributes:
        content: Note body after command markers are removed.
        field: Field name parsed from an ``@field`` marker or the default field.
        tags: Tag names parsed from ``#tag`` markers in input order.
    """

    content: str
    field: str
    tags: list[str]


def parse_interactive_note_input(raw_input: str) -> InteractiveNoteInput:
    """Parse interactive note text into content, field, and tags.

    Args:
        raw_input: User-provided note text from the interactive prompt.

    Returns:
        Parsed note input with default field and de-duplicated tags.
    """
    content_tokens: list[str] = []
    tags: list[str] = []
    seen_tags: set[str] = set()
    field = DEFAULT_INTERACTIVE_FIELD

    for token in raw_input.split():
        marker_match = MARKER_PATTERN.match(token)
        if marker_match is None:
            content_tokens.append(token)
            continue

        marker_type, marker_value, _trailing_punctuation = marker_match.groups()
        if marker_type == "@":
            field = marker_value
        else:
            if marker_value not in seen_tags:
                tags.append(marker_value)
                seen_tags.add(marker_value)

    return InteractiveNoteInput(
        content=" ".join(content_tokens).strip(),
        field=field,
        tags=tags,
    )


def render_intro(console: Console, database_path: Path, note_count: int) -> None:
    """Render the interactive startup screen.

    Args:
        console: Rich console used for terminal output.
        database_path: Configured SQLite database path.
        note_count: Number of active notes in the database.

    Returns:
        None.
    """
    logo = Text(
        "\n".join(
            [
                "███████╗███████╗███╗   ███╗██████╗ ██████╗  █████╗",
                "╚══███╔╝██╔════╝████╗ ████║██╔══██╗██╔══██╗██╔══██╗",
                "  ███╔╝ █████╗  ██╔████╔██║██████╔╝██████╔╝███████║",
                " ███╔╝  ██╔══╝  ██║╚██╔╝██║██╔══██╗██╔══██╗██╔══██║",
                "███████╗███████╗██║ ╚═╝ ██║██████╔╝██║  ██║██║  ██║",
                "╚══════╝╚══════╝╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝",
            ]
        ),
        style="bold cyan",
    )

    stats_table = Table.grid(padding=(0, 2))
    stats_table.add_column(style="bold white")
    stats_table.add_column(style="green")
    stats_table.add_row("Database", str(database_path.expanduser()))
    stats_table.add_row("Notes", str(note_count))
    stats_table.add_row("Default field", DEFAULT_INTERACTIVE_FIELD)

    body = Table.grid(padding=(1, 0))
    body.add_row(Align.center(logo))
    body.add_row(stats_table)
    body.add_row(Text("Use @field and #tag while writing. /help for commands.", style="dim"))

    console.print(
        Panel(
            body,
            title="[bold]Zembra[/bold]",
            subtitle="calm note capture",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def render_help(console: Console) -> None:
    """Render interactive command help.

    Args:
        console: Rich console used for terminal output.

    Returns:
        None.
    """
    help_table = Table(title="Commands", show_header=True, header_style="bold cyan")
    help_table.add_column("Input")
    help_table.add_column("Action")
    help_table.add_row("/help", "Show this help")
    help_table.add_row("/exit", "Exit the interactive session")
    help_table.add_row("note @dev #gpt", "Save a note in field dev with tag gpt")
    help_table.add_row("note without field", "Save a note in the default inbox field")
    console.print(help_table)


def run_interactive_session(
    repository: ZembraRepository,
    console: Console,
    input_func: Callable[[str], str] = input,
    now_func: Callable[[], datetime] = datetime.now,
) -> None:
    """Run the persistent interactive note capture loop.

    Args:
        repository: Repository used to create notes.
        console: Rich console used for terminal output.
        input_func: Callable used to read user input.
        now_func: Callable returning the timestamp shown in save feedback.

    Returns:
        None.
    """
    while True:
        try:
            raw_input = input_func("zembra> ")
        except EOFError:
            console.print("Goodbye.")
            return

        stripped_input = raw_input.strip()
        if not stripped_input:
            console.print("[dim]Write a note, or use /help.[/dim]")
            continue

        if stripped_input == EXIT_COMMAND:
            console.print("Goodbye.")
            return

        if stripped_input == HELP_COMMAND:
            render_help(console)
            continue

        if stripped_input.startswith("/"):
            console.print("[yellow]Unknown command. Use /help.[/yellow]")
            continue

        parsed_input = parse_interactive_note_input(stripped_input)
        if not parsed_input.content:
            console.print("[yellow]Write note content before saving.[/yellow]")
            continue

        try:
            note = repository.create_note(
                parsed_input.content,
                field_name=parsed_input.field,
                tag_names=parsed_input.tags,
            )
        except sqlite3.Error as error:
            console.print(f"[red]Could not create the note: {error}[/red]")
            continue

        saved_at = now_func().strftime("%H:%M")
        console.print(f"[green]Saved note {note.id[:8]} · {saved_at}[/green]")


def render_intro_for_repository(
    repository: ZembraRepository,
    console: Console,
    database_path: Path,
) -> None:
    """Render startup intro using repository-backed statistics.

    Args:
        repository: Repository used to read note statistics.
        console: Rich console used for terminal output.
        database_path: Configured SQLite database path.

    Returns:
        None.
    """
    render_intro(console, database_path, len(repository.list_notes()))
