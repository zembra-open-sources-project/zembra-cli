"""Interactive Rich-powered note capture for zembra-cli."""

import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
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
class SlashCommandHelp:
    """Represent one interactive slash command help entry.

    Attributes:
        command: Slash command text entered by the user.
        description: Short description shown in the candidate table.
    """

    command: str
    description: str


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


SLASH_COMMANDS = (
    SlashCommandHelp(HELP_COMMAND, "Show this help"),
    SlashCommandHelp(EXIT_COMMAND, "Exit the interactive session"),
)


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


def match_slash_commands(input_text: str) -> list[SlashCommandHelp]:
    """Match slash command help entries by the current input prefix.

    Args:
        input_text: Current editable input text from the interactive prompt.

    Returns:
        Slash command entries matching the input prefix, or an empty list when
        the input does not start with a slash.
    """
    if not input_text.startswith("/"):
        return []

    return [
        command_help
        for command_help in SLASH_COMMANDS
        if command_help.command.startswith(input_text)
    ]


class SlashCommandCompleter(Completer):
    """Provide transient prompt_toolkit completions for slash commands.

    Attributes:
        None.
    """

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ):
        """Yield slash command completions for the current prompt document.

        Args:
            document: prompt_toolkit document containing the editable input.
            complete_event: Completion event metadata supplied by prompt_toolkit.

        Yields:
            Completion entries for slash commands matching the current prefix.
        """
        input_text = document.text_before_cursor
        if document.cursor_position != len(document.text) or not input_text.startswith("/"):
            return

        for match in match_slash_commands(input_text):
            yield Completion(
                match.command,
                start_position=-len(input_text),
                display=match.command,
                display_meta=match.description,
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
    for command_help in SLASH_COMMANDS:
        help_table.add_row(command_help.command, command_help.description)
    help_table.add_row("note @dev #gpt", "Save a note in field dev with tag gpt")
    help_table.add_row("note without field", "Save a note in the default inbox field")
    console.print(help_table)


def read_interactive_line(prompt_text: str) -> str:
    """Read one interactive command line with Unicode-aware editing.

    Args:
        prompt_text: Prompt text displayed before the editable input line.

    Returns:
        User-entered text after the user submits the line.
    """
    session = PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
    )
    return session.prompt(prompt_text)


def run_interactive_session(
    repository: ZembraRepository,
    console: Console,
    input_func: Callable[[str], str] = read_interactive_line,
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
