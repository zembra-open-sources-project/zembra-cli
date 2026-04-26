"""Repository facade for Zembra database operations."""

from zembra_cli.repository.exceptions import (
    AmbiguousNoteReferenceError,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
)
from zembra_cli.repository.notes import ZembraRepository

__all__ = [
    "AmbiguousNoteReferenceError",
    "InvalidNoteReferenceError",
    "NoteReferenceTooShortError",
    "RecordNotFoundError",
    "ZembraRepository",
]
