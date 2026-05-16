"""Repository protocols shared by CLI entry points."""

from collections.abc import Sequence
from typing import Literal, Protocol

from zembra_cli.models import FieldNotesGroup, FieldRecord, NoteRecord, NoteWithMetadata, TagRecord
from zembra_cli.models import TaggedNotesGroup


class CliRepository(Protocol):
    """Describe repository behavior required by CLI commands.

    Args:
        None.

    Returns:
        A structural protocol implemented by local and HTTP repositories.
    """

    def create_note(
        self,
        content: str,
        role: Literal["Human", "Agent"] = "Human",
        field_name: str | None = None,
        tag_names: Sequence[str] | None = None,
        device_id: str | None = None,
    ) -> NoteRecord:
        """Create a note with optional metadata.

        Args:
            content: Note body text.
            role: Immutable note creation role.
            field_name: Optional field name to attach to the note.
            tag_names: Optional tag names to attach to the note.
            device_id: Optional device identifier recorded on the revision.

        Returns:
            The created note record.
        """

    def list_tags(self) -> list[TagRecord]:
        """List tags ordered by name.

        Args:
            None.

        Returns:
            Ordered tag records.
        """

    def list_fields(self) -> list[FieldRecord]:
        """List fields ordered by name.

        Args:
            None.

        Returns:
            Ordered field records.
        """

    def list_notes(self, include_deleted: bool = False) -> list[NoteRecord]:
        """List notes ordered by recent activity.

        Args:
            include_deleted: Whether soft-deleted notes are included.

        Returns:
            Ordered note records.
        """

    def random_notes(self, number: int) -> list[NoteWithMetadata]:
        """List random visible notes with metadata.

        Args:
            number: Maximum number of notes to return.

        Returns:
            Random visible note records with field and tag metadata.
        """

    def random_tagged_notes(self, number: int, count: int) -> list[TaggedNotesGroup]:
        """List visible notes grouped by randomly selected tags.

        Args:
            number: Maximum number of tag groups to return.
            count: Maximum cumulative number of notes to return.

        Returns:
            Random tag groups containing visible note records.
        """

    def random_field_notes(self, number: int, count: int) -> list[FieldNotesGroup]:
        """List visible notes grouped by randomly selected fields.

        Args:
            number: Maximum number of field groups to return.
            count: Maximum cumulative number of notes to return.

        Returns:
            Random field groups containing visible note records.
        """
