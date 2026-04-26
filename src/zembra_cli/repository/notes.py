"""Repository operations for notes and note revisions."""

from collections.abc import Sequence

from zembra_cli.models import NoteRecord, NoteRevisionRecord
from zembra_cli.repository.exceptions import (
    AmbiguousNoteReferenceError,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
)
from zembra_cli.repository.field_tag import FieldTagRepository

MIN_NOTE_REFERENCE_LENGTH = 4
FULL_NOTE_ID_LENGTH = 32
NOTE_REFERENCE_CANDIDATE_LIMIT = 6


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

    def resolve_note_id(self, note_ref: str, include_deleted: bool = False) -> str:
        """Resolve a full note id or unique note id prefix to a complete note id.

        Args:
            note_ref: User-provided full note id or note id prefix.
            include_deleted: Whether soft-deleted notes are eligible.

        Returns:
            The complete note id matching the reference.
        """
        normalized_ref = self._normalize_note_ref(note_ref)
        if len(normalized_ref) < MIN_NOTE_REFERENCE_LENGTH:
            raise NoteReferenceTooShortError(normalized_ref, MIN_NOTE_REFERENCE_LENGTH)

        if len(normalized_ref) == FULL_NOTE_ID_LENGTH:
            note = self.get_note(normalized_ref, include_deleted=include_deleted)
            if note is None:
                raise RecordNotFoundError("notes", normalized_ref)
            return note.id

        candidates = self._find_notes_by_id_prefix(normalized_ref, include_deleted=include_deleted)
        if not candidates:
            raise RecordNotFoundError("notes", normalized_ref)
        if len(candidates) > 1:
            raise AmbiguousNoteReferenceError(normalized_ref, candidates)
        return candidates[0].id

    def get_note_by_ref(self, note_ref: str, include_deleted: bool = False) -> NoteRecord | None:
        """Fetch a note by full id or unique note id prefix.

        Args:
            note_ref: User-provided full note id or note id prefix.
            include_deleted: Whether soft-deleted notes are eligible.

        Returns:
            Matching note record, or None when no record exists for a complete id.
        """
        note_id = self.resolve_note_id(note_ref, include_deleted=include_deleted)
        return self.get_note(note_id, include_deleted=include_deleted)

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

    def _normalize_note_ref(self, note_ref: str) -> str:
        """Normalize and validate a user-provided note reference.

        Args:
            note_ref: User-provided full note id or note id prefix.

        Returns:
            Lowercase hexadecimal note reference without surrounding whitespace.
        """
        normalized_ref = note_ref.strip().lower()
        if not normalized_ref:
            raise InvalidNoteReferenceError(note_ref, "empty note reference")
        if not all(character in "0123456789abcdef" for character in normalized_ref):
            raise InvalidNoteReferenceError(note_ref, "only hexadecimal characters are supported")
        return normalized_ref

    def _find_notes_by_id_prefix(
        self,
        note_ref: str,
        include_deleted: bool = False,
    ) -> list[NoteRecord]:
        """Find notes whose identifiers start with the supplied prefix.

        Args:
            note_ref: Normalized hexadecimal note id prefix.
            include_deleted: Whether soft-deleted notes are eligible.

        Returns:
            Matching note records ordered for stable ambiguity messages.
        """
        if include_deleted:
            rows = self.connection.execute(
                """
                SELECT * FROM notes
                WHERE id LIKE ?
                ORDER BY updated_at DESC, created_at DESC, id ASC
                LIMIT ?
                """,
                (f"{note_ref}%", NOTE_REFERENCE_CANDIDATE_LIMIT),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT * FROM notes
                WHERE id LIKE ? AND deleted_at IS NULL
                ORDER BY updated_at DESC, created_at DESC, id ASC
                LIMIT ?
                """,
                (f"{note_ref}%", NOTE_REFERENCE_CANDIDATE_LIMIT),
            ).fetchall()
        return [self._row_to_model(row, NoteRecord) for row in rows]
