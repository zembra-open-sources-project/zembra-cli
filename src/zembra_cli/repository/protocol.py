"""Repository protocols shared by CLI entry points."""

from collections.abc import Sequence
from typing import Literal, Protocol

from zembra_cli.models import FieldRecord, NoteRecord, TagRecord


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
