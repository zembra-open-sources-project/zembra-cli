"""Repository operations for fields, tags, and note tag associations."""

from zembra_cli.models import FieldRecord, NoteTagRecord, TagRecord
from zembra_cli.repository.base import BaseRepository
from zembra_cli.repository.exceptions import RecordNotFoundError


class FieldTagRepository(BaseRepository):
    """Provide field, tag, and note-tag association operations."""

    def get_field(self, field_id: str) -> FieldRecord | None:
        """Fetch a field by identifier.

        Args:
            field_id: Field identifier to look up.

        Returns:
            Matching field record, or None when no field exists.
        """
        row = self.connection.execute("SELECT * FROM fields WHERE id = ?", (field_id,)).fetchone()
        return self._row_to_model(row, FieldRecord) if row is not None else None

    def get_field_by_name(self, name: str) -> FieldRecord | None:
        """Fetch a field by name.

        Args:
            name: Field name to look up.

        Returns:
            Matching field record, or None when no field exists.
        """
        row = self.connection.execute("SELECT * FROM fields WHERE name = ?", (name,)).fetchone()
        return self._row_to_model(row, FieldRecord) if row is not None else None

    def list_fields(self) -> list[FieldRecord]:
        """List fields ordered by name.

        Args:
            None.

        Returns:
            Field records sorted by name.
        """
        rows = self.connection.execute("SELECT * FROM fields ORDER BY name ASC").fetchall()
        return [self._row_to_model(row, FieldRecord) for row in rows]

    def get_or_create_field(self, name: str) -> FieldRecord:
        """Fetch a field by name or create it when missing.

        Args:
            name: Field name to fetch or insert.

        Returns:
            Existing or newly-created field record.
        """
        existing = self.get_field_by_name(name)
        if existing is not None:
            return existing

        field_id = self._new_id()
        created_at = self._now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO fields (id, name, created_at) VALUES (?, ?, ?)",
                (field_id, name, created_at),
            )
        field = self.get_field_by_name(name)
        if field is None:
            raise RecordNotFoundError("fields", field_id)
        return field

    def get_tag_by_name(self, name: str) -> TagRecord | None:
        """Fetch a tag by name.

        Args:
            name: Tag name to look up.

        Returns:
            Matching tag record, or None when no tag exists.
        """
        row = self.connection.execute("SELECT * FROM tags WHERE name = ?", (name,)).fetchone()
        return self._row_to_model(row, TagRecord) if row is not None else None

    def list_tags(self) -> list[TagRecord]:
        """List tags ordered by name.

        Args:
            None.

        Returns:
            Tag records sorted by name.
        """
        rows = self.connection.execute("SELECT * FROM tags ORDER BY name ASC").fetchall()
        return [self._row_to_model(row, TagRecord) for row in rows]

    def get_or_create_tag(self, name: str) -> TagRecord:
        """Fetch a tag by name or create it when missing.

        Args:
            name: Tag name to fetch or insert.

        Returns:
            Existing or newly-created tag record.
        """
        existing = self.get_tag_by_name(name)
        if existing is not None:
            return existing

        tag_id = self._new_id()
        created_at = self._now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO tags (id, name, created_at) VALUES (?, ?, ?)",
                (tag_id, name, created_at),
            )
        tag = self.get_tag_by_name(name)
        if tag is None:
            raise RecordNotFoundError("tags", tag_id)
        return tag

    def add_tag_to_note(self, note_id: str, tag_name: str) -> NoteTagRecord:
        """Associate a tag with a note, creating the tag when needed.

        Args:
            note_id: Identifier of the note to tag.
            tag_name: Tag name to associate.

        Returns:
            The note-tag association record.
        """
        tag = self.get_or_create_tag(tag_name)
        created_at = self._now()
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO note_tags (note_id, tag_id, created_at)
                VALUES (?, ?, ?)
                """,
                (note_id, tag.id, created_at),
            )
        row = self.connection.execute(
            "SELECT * FROM note_tags WHERE note_id = ? AND tag_id = ?",
            (note_id, tag.id),
        ).fetchone()
        if row is None:
            raise RecordNotFoundError("note_tags", f"{note_id}:{tag.id}")
        return self._row_to_model(row, NoteTagRecord)

    def remove_tag_from_note(self, note_id: str, tag_name: str) -> None:
        """Remove a tag association from a note while keeping the tag.

        Args:
            note_id: Identifier of the note to update.
            tag_name: Tag name to remove from the note.

        Returns:
            None.
        """
        tag = self.get_tag_by_name(tag_name)
        if tag is None:
            return
        with self.connection:
            self.connection.execute(
                "DELETE FROM note_tags WHERE note_id = ? AND tag_id = ?",
                (note_id, tag.id),
            )

    def list_note_tags(self, note_id: str) -> list[TagRecord]:
        """List tags associated with a note.

        Args:
            note_id: Identifier of the note whose tags should be listed.

        Returns:
            Tag records associated with the note, sorted by name.
        """
        rows = self.connection.execute(
            """
            SELECT tags.*
            FROM tags
            JOIN note_tags ON note_tags.tag_id = tags.id
            WHERE note_tags.note_id = ?
            ORDER BY tags.name ASC
            """,
            (note_id,),
        ).fetchall()
        return [self._row_to_model(row, TagRecord) for row in rows]
