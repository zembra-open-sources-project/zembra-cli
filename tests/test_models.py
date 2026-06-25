"""Tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError

from zembra_cli.models import (
    FieldRecord,
    NoteLinkRecord,
    NoteRecord,
    NoteWithMetadata,
    TagRecord,
    WorkspaceRecord,
)


def test_note_record_accepts_valid_minimal_note() -> None:
    """Verify a minimal note matching the shared schema can be created.

    Args:
        None.

    Returns:
        None.
    """
    note = NoteRecord(
        id="note_1",
        workspace_id="workspace_1",
        content="hello",
        created_at=1,
        updated_at=1,
        conflict_status="none",
    )

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
    note = NoteRecord(
        id="note_1",
        workspace_id="workspace_1",
        content="hello",
        role="Agent",
        created_at=1,
        updated_at=1,
        conflict_status="none",
    )

    assert note.role == "Agent"


def test_note_record_rejects_unknown_role() -> None:
    """Verify note records reject roles outside the shared schema enum.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValidationError, match="role"):
        NoteRecord(
            id="note_1",
            workspace_id="workspace_1",
            content="hello",
            role="System",
            created_at=1,
            updated_at=1,
            conflict_status="none",
        )


def test_note_record_rejects_updated_at_before_created_at() -> None:
    """Verify note timestamp ordering follows the SQLite schema.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValidationError, match="updated_at"):
        NoteRecord(
            id="note_1",
            workspace_id="workspace_1",
            content="hello",
            created_at=2,
            updated_at=1,
            conflict_status="none",
        )


def test_field_record_rejects_empty_id() -> None:
    """Verify non-empty identifiers are enforced by Pydantic models.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValidationError):
        FieldRecord(id="", workspace_id="workspace_1", name="work", created_at=1)


def test_workspace_record_accepts_null_name() -> None:
    """Verify workspace display name can be absent.

    Args:
        None.

    Returns:
        None.
    """
    workspace = WorkspaceRecord(
        id="workspace_1",
        workspace_name=None,
        created_at=1,
        updated_at=1,
    )

    assert workspace.workspace_name is None


def test_tag_record_accepts_root_tag_fields() -> None:
    """Verify root tags match latest hierarchical tag schema.

    Args:
        None.

    Returns:
        None.
    """
    tag = TagRecord(
        id="tag_1",
        workspace_id="workspace_1",
        name="cli",
        parent_tag_id=None,
        path="cli",
        depth=0,
        created_at=1,
    )

    assert tag.path == "cli"
    assert tag.depth == 0


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
            workspace_id="workspace_1",
            source_note_id="note_1",
            target_note_id="note_1",
            created_at=1,
        )


def test_note_with_metadata_dumps_complete_note_field_and_tags() -> None:
    """Verify random note DTO preserves full note metadata.

    Args:
        None.

    Returns:
        None.
    """
    note = NoteRecord(
        id="note_1",
        workspace_id="workspace_1",
        content="full\ncontent",
        created_at=1,
        updated_at=2,
        conflict_status="none",
    )
    field = FieldRecord(id="field_1", workspace_id="workspace_1", name="work", created_at=1)
    tag = TagRecord(
        id="tag_1",
        workspace_id="workspace_1",
        name="cli",
        parent_tag_id=None,
        path="cli",
        depth=0,
        created_at=1,
    )

    payload = NoteWithMetadata(note=note, field=field, tags=[tag]).model_dump()

    assert payload["note"]["content"] == "full\ncontent"
    assert payload["field"]["name"] == "work"
    assert payload["tags"][0]["name"] == "cli"
