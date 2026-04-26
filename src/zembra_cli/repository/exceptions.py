"""Repository exceptions."""

from zembra_cli.models import NoteRecord


class RecordNotFoundError(LookupError):
    """Signal that a requested database record does not exist.

    Attributes:
        table: Database table where the lookup was attempted.
        record_id: Identifier used for the failed lookup.
    """

    def __init__(self, table: str, record_id: str) -> None:
        """Initialize the not-found error.

        Args:
            table: Database table where the lookup was attempted.
            record_id: Identifier used for the failed lookup.

        Returns:
            None.
        """
        self.table = table
        self.record_id = record_id
        super().__init__(f"{table} record not found: {record_id}")


class InvalidNoteReferenceError(ValueError):
    """Signal that a note reference cannot be parsed as a hexadecimal id prefix.

    Attributes:
        note_ref: User-provided note reference.
        reason: Short explanation of the validation failure.
    """

    def __init__(self, note_ref: str, reason: str) -> None:
        """Initialize the invalid note reference error.

        Args:
            note_ref: User-provided note reference.
            reason: Short explanation of the validation failure.

        Returns:
            None.
        """
        self.note_ref = note_ref
        self.reason = reason
        super().__init__(f"invalid note reference {note_ref!r}: {reason}")


class NoteReferenceTooShortError(ValueError):
    """Signal that a note id prefix is shorter than the supported minimum.

    Attributes:
        note_ref: User-provided note reference.
        minimum_length: Minimum supported prefix length.
    """

    def __init__(self, note_ref: str, minimum_length: int) -> None:
        """Initialize the short note reference error.

        Args:
            note_ref: User-provided note reference.
            minimum_length: Minimum supported prefix length.

        Returns:
            None.
        """
        self.note_ref = note_ref
        self.minimum_length = minimum_length
        super().__init__(
            f"note reference {note_ref!r} must be at least {minimum_length} characters"
        )


class AmbiguousNoteReferenceError(LookupError):
    """Signal that a note id prefix matches multiple notes.

    Attributes:
        note_ref: User-provided note reference.
        candidates: Matching note records eligible for the operation.
    """

    def __init__(self, note_ref: str, candidates: list[NoteRecord]) -> None:
        """Initialize the ambiguous note reference error.

        Args:
            note_ref: User-provided note reference.
            candidates: Matching note records eligible for the operation.

        Returns:
            None.
        """
        self.note_ref = note_ref
        self.candidates = candidates
        super().__init__(f"note reference {note_ref!r} matches {len(candidates)} notes")
