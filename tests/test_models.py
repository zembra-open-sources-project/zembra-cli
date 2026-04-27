"""Tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError

from zembra_cli.models import FieldRecord, NoteLinkRecord, NoteRecord


def test_note_record_accepts_valid_minimal_note() -> None:
    """Verify a minimal note matching the shared schema can be created.

    Args:
        None.

    Returns:
        None.
    """
    note = NoteRecord(id="note_1", content="hello", created_at=1, updated_at=1)

    assert note.id == "note_1"
    assert note.role == "Human"
    assert note.field_id is None


def test_note_record_accepts_agent_role() -> None:
    """Verify note records accept the shared Agent creation role.

    Args:
        None.

    Returns:
        None.
    """
    note = NoteRecord(id="note_1", content="hello", role="Agent", created_at=1, updated_at=1)

    assert note.role == "Agent"


def test_note_record_rejects_unknown_role() -> None:
    """Verify note records reject roles outside the shared schema enum.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValidationError, match="role"):
        NoteRecord(id="note_1", content="hello", role="System", created_at=1, updated_at=1)


def test_note_record_rejects_updated_at_before_created_at() -> None:
    """Verify note timestamp ordering follows the SQLite schema.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValidationError, match="updated_at"):
        NoteRecord(id="note_1", content="hello", created_at=2, updated_at=1)


def test_field_record_rejects_empty_id() -> None:
    """Verify non-empty identifiers are enforced by Pydantic models.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValidationError):
        FieldRecord(id="", name="work", created_at=1)


def test_note_link_record_rejects_self_link() -> None:
    """Verify note links cannot point a note at itself.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValidationError, match="must differ"):
        NoteLinkRecord(
            id="link_1",
            source_note_id="note_1",
            target_note_id="note_1",
            created_at=1,
        )
