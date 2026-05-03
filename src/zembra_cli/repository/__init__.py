"""Repository facade for Zembra database operations."""

from zembra_cli.repository.exceptions import (
    AmbiguousNoteReferenceError,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
)
from zembra_cli.repository.notes import ZembraRepository
from zembra_cli.repository.protocol import CliRepository

__all__ = [
    "AmbiguousNoteReferenceError",
    "InvalidNoteReferenceError",
    "NoteReferenceTooShortError",
    "CliRepository",
    "RecordNotFoundError",
    "ZembraRepository",
]
