"""Tests for zembra-cli interactive note capture."""

from datetime import datetime
from pathlib import Path

from rich.console import Console

from zembra_cli.interactive import (
    DEFAULT_INTERACTIVE_FIELD,
    InteractiveNoteInput,
    parse_interactive_note_input,
    render_help,
    render_intro,
    run_interactive_session,
)


class FakeInteractiveRepository:
    """Capture interactive note creation calls for tests.

    Attributes:
        created_notes: Note creation arguments received during the test.
        note_id: Stable note identifier returned from create calls.
    """

    def __init__(self, note_id: str = "abcdef0123456789") -> None:
        """Initialize the fake repository.

        Args:
            note_id: Stable note identifier returned from create calls.

        Returns:
            None.
        """
        self.created_notes: list[tuple[str, str | None, list[str] | None]] = []
        self.note_id = note_id

    def create_note(
        self,
        content: str,
        field_name: str | None = None,
        tag_names: list[str] | None = None,
    ):
        """Record note creation arguments and return a note-shaped object.

        Args:
            content: Note body text.
            field_name: Field name attached to the note.
            tag_names: Tag names attached to the note.

        Returns:
            A minimal object exposing an id attribute.
        """
        self.created_notes.append((content, field_name, tag_names))
        return type("FakeNote", (), {"id": self.note_id})()


def record_console() -> Console:
    """Create a Rich console that records output for assertions.

    Args:
        None.

    Returns:
        A recording Rich console.
    """
    return Console(record=True, force_terminal=False, width=120)


def test_parse_interactive_note_input_uses_default_field() -> None:
    """Verify plain note input falls back to the inbox field.

    Args:
        None.

    Returns:
        None.
    """
    parsed_input = parse_interactive_note_input("quick note")

    assert parsed_input == InteractiveNoteInput(
        content="quick note",
        field=DEFAULT_INTERACTIVE_FIELD,
        tags=[],
    )


def test_parse_interactive_note_input_extracts_field_and_tag() -> None:
    """Verify field and tag markers are removed from saved content.

    Args:
        None.

    Returns:
        None.
    """
    parsed_input = parse_interactive_note_input("I learn how to use codex today @dev #gpt")

    assert parsed_input == InteractiveNoteInput(
        content="I learn how to use codex today",
        field="dev",
        tags=["gpt"],
    )


def test_parse_interactive_note_input_deduplicates_tags() -> None:
    """Verify repeated tag markers preserve first-seen order.

    Args:
        None.

    Returns:
        None.
    """
    parsed_input = parse_interactive_note_input("ship parser #cli #gpt #cli #notes")

    assert parsed_input.tags == ["cli", "gpt", "notes"]


def test_parse_interactive_note_input_uses_last_field() -> None:
    """Verify multiple field markers resolve to the last field.

    Args:
        None.

    Returns:
        None.
    """
    parsed_input = parse_interactive_note_input("move this @inbox @dev")

    assert parsed_input.content == "move this"
    assert parsed_input.field == "dev"


def test_parse_interactive_note_input_ignores_embedded_markers() -> None:
    """Verify marker parsing only applies to standalone tokens.

    Args:
        None.

    Returns:
        None.
    """
    parsed_input = parse_interactive_note_input("email dev@example.com and keep hello#tag")

    assert parsed_input.content == "email dev@example.com and keep hello#tag"
    assert parsed_input.field == DEFAULT_INTERACTIVE_FIELD
    assert parsed_input.tags == []


def test_parse_interactive_note_input_strips_marker_punctuation() -> None:
    """Verify trailing punctuation is not included in parsed marker values.

    Args:
        None.

    Returns:
        None.
    """
    parsed_input = parse_interactive_note_input("learn codex @dev, #gpt.")

    assert parsed_input.content == "learn codex"
    assert parsed_input.field == "dev"
    assert parsed_input.tags == ["gpt"]


def test_render_intro_includes_database_path_and_stats() -> None:
    """Verify intro output contains startup context.

    Args:
        None.

    Returns:
        None.
    """
    console = record_console()

    render_intro(console, Path("/tmp/zembra.sqlite3"), note_count=12)

    output = console.export_text()
    assert "Zembra" in output
    assert "/tmp/zembra.sqlite3" in output
    assert "12" in output
    assert DEFAULT_INTERACTIVE_FIELD in output


def test_render_help_includes_commands() -> None:
    """Verify help output describes interactive commands.

    Args:
        None.

    Returns:
        None.
    """
    console = record_console()

    render_help(console)

    output = console.export_text()
    assert "/help" in output
    assert "/exit" in output
    assert "@dev" in output
    assert "#gpt" in output


def test_run_interactive_session_saves_note_and_exits() -> None:
    """Verify a normal input is saved and /exit ends the loop.

    Args:
        None.

    Returns:
        None.
    """
    repository = FakeInteractiveRepository()
    console = record_console()
    inputs = iter(["hello world @dev #gpt", "/exit"])

    run_interactive_session(
        repository,
        console,
        input_func=lambda _prompt: next(inputs),
        now_func=lambda: datetime(2026, 4, 27, 9, 30),
    )

    assert repository.created_notes == [("hello world", "dev", ["gpt"])]
    output = console.export_text()
    assert "Saved note abcdef01 · 09:30" in output
    assert "Goodbye." in output


def test_run_interactive_session_handles_help_empty_and_unknown_commands() -> None:
    """Verify non-save inputs keep the interactive loop alive.

    Args:
        None.

    Returns:
        None.
    """
    repository = FakeInteractiveRepository()
    console = record_console()
    inputs = iter(["", "/help", "/missing", "/exit"])

    run_interactive_session(repository, console, input_func=lambda _prompt: next(inputs))

    assert repository.created_notes == []
    output = console.export_text()
    assert "Write a note" in output
    assert "Commands" in output
    assert "Unknown command" in output
