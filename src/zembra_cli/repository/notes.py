"""Repository operations for notes and note revisions."""

from collections.abc import Sequence

from zembra_cli.models import NoteRecord, NoteRevisionRecord
from zembra_cli.repository.exceptions import RecordNotFoundError
from zembra_cli.repository.field_tag import FieldTagRepository


class ZembraRepository(FieldTagRepository):
    """Provide high-level CRUD operations for the Zembra note database."""

    def create_note(
        self,
        content: str,
        field_name: str | None = None,
        tag_names: Sequence[str] | None = None,
        device_id: str | None = None,
    ) -> NoteRecord:
        """Create a note with optional field, tags, and initial revision.

        Args:
            content: Note body text.
            field_name: Optional field name to attach to the note.
            tag_names: Optional tag names to attach to the note.
            device_id: Optional device identifier recorded on the revision.

        Returns:
            The created note record with current revision populated.
        """
        now = self._now()
        note_id = self._new_id()
        revision_id = self._new_id()
        field_id = self.get_or_create_field(field_name).id if field_name is not None else None

        with self.connection:
            self.connection.execute(
                """
                INSERT INTO notes (
                    id, content, field_id, created_at, updated_at, current_revision_id
                )
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (note_id, content, field_id, now, now),
            )
            self.connection.execute(
                """
                INSERT INTO note_revisions (id, note_id, content, title, device_id, created_at)
                VALUES (?, ?, ?, NULL, ?, ?)
                """,
                (revision_id, note_id, content, device_id, now),
            )
            self.connection.execute(
                "UPDATE notes SET current_revision_id = ? WHERE id = ?",
                (revision_id, note_id),
            )

        for tag_name in tag_names or ():
            self.add_tag_to_note(note_id, tag_name)

        note = self.get_note(note_id)
        if note is None:
            raise RecordNotFoundError("notes", note_id)
        return note

    def get_note(self, note_id: str, include_deleted: bool = False) -> NoteRecord | None:
        """Fetch a note by identifier.

        Args:
            note_id: Identifier of the note to fetch.
            include_deleted: Whether soft-deleted notes are eligible.

        Returns:
            Matching note record, or None when absent or filtered.
        """
        if include_deleted:
            row = self.connection.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        else:
            row = self.connection.execute(
                "SELECT * FROM notes WHERE id = ? AND deleted_at IS NULL",
                (note_id,),
            ).fetchone()
        return self._row_to_model(row, NoteRecord) if row is not None else None

    def list_notes(self, include_deleted: bool = False) -> list[NoteRecord]:
        """List notes ordered by recent activity.

        Args:
            include_deleted: Whether soft-deleted notes are included.

        Returns:
            Note records ordered by updated_at and created_at descending.
        """
        if include_deleted:
            rows = self.connection.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC, created_at DESC"
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT * FROM notes
                WHERE deleted_at IS NULL
                ORDER BY updated_at DESC, created_at DESC
                """
            ).fetchall()
        return [self._row_to_model(row, NoteRecord) for row in rows]

    def update_note_content(
        self,
        note_id: str,
        content: str,
        device_id: str | None = None,
    ) -> NoteRecord:
        """Update a note body and write a full revision snapshot.

        Args:
            note_id: Identifier of the note to update.
            content: Replacement note body.
            device_id: Optional device identifier recorded on the revision.

        Returns:
            Updated note record.
        """
        self._require_note(note_id)
        now = self._now()
        revision_id = self._new_id()

        with self.connection:
            self.connection.execute(
                """
                INSERT INTO note_revisions (id, note_id, content, title, device_id, created_at)
                VALUES (?, ?, ?, NULL, ?, ?)
                """,
                (revision_id, note_id, content, device_id, now),
            )
            self.connection.execute(
                """
                UPDATE notes
                SET content = ?, updated_at = ?, current_revision_id = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (content, now, revision_id, note_id),
            )

        return self._require_note(note_id)

    def archive_note(self, note_id: str) -> NoteRecord:
        """Archive a note without deleting it.

        Args:
            note_id: Identifier of the note to archive.

        Returns:
            Updated note record with archived_at populated.
        """
        self._require_note(note_id)
        archived_at = self._now()
        with self.connection:
            self.connection.execute(
                "UPDATE notes SET archived_at = ? WHERE id = ? AND deleted_at IS NULL",
                (archived_at, note_id),
            )
        return self._require_note(note_id)

    def delete_note(self, note_id: str) -> NoteRecord:
        """Soft-delete a note by setting deleted_at.

        Args:
            note_id: Identifier of the note to soft-delete.

        Returns:
            Updated note record including the soft-delete timestamp.
        """
        self._require_note(note_id)
        deleted_at = self._now()
        with self.connection:
            self.connection.execute(
                "UPDATE notes SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                (deleted_at, note_id),
            )
        return self._require_note(note_id, include_deleted=True)

    def list_note_revisions(self, note_id: str) -> list[NoteRevisionRecord]:
        """List revisions for a note by creation time.

        Args:
            note_id: Identifier of the note whose revisions should be listed.

        Returns:
            Revision records ordered by creation time.
        """
        rows = self.connection.execute(
            """
            SELECT * FROM note_revisions
            WHERE note_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (note_id,),
        ).fetchall()
        return [self._row_to_model(row, NoteRevisionRecord) for row in rows]

    def _require_note(self, note_id: str, include_deleted: bool = False) -> NoteRecord:
        """Fetch a note or raise a not-found error.

        Args:
            note_id: Identifier of the note to fetch.
            include_deleted: Whether soft-deleted notes are eligible.

        Returns:
            Matching note record.
        """
        note = self.get_note(note_id, include_deleted=include_deleted)
        if note is None:
            raise RecordNotFoundError("notes", note_id)
        return note
