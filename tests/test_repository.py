"""Tests for repository-level CRUD operations."""

import sqlite3
from collections.abc import Iterator

import pytest

from zembra_cli.db import database_connection, initialize_database
from zembra_cli.repository import (
    AmbiguousNoteReferenceError,
    InvalidNoteReferenceError,
    NoteReferenceTooShortError,
    RecordNotFoundError,
    ZembraRepository,
)


class SequenceFactory:
    """Generate deterministic values for repository tests.

    Attributes:
        prefix: Text prefix included in generated values.
        next_value: Next numeric suffix to emit.
    """

    def __init__(self, prefix: str, start: int = 1) -> None:
        """Initialize the deterministic factory.

        Args:
            prefix: Text prefix included in generated values.
            start: First numeric suffix to emit.

        Returns:
            None.
        """
        self.prefix = prefix
        self.next_value = start

    def __call__(self) -> str:
        """Generate the next deterministic value.

        Args:
            None.

        Returns:
            A unique string for the current test.
        """
        value = f"{self.prefix}_{self.next_value}"
        self.next_value += 1
        return value


class IntegerSequenceFactory:
    """Generate deterministic integer timestamps for repository tests.

    Attributes:
        next_value: Next integer timestamp to emit.
    """

    def __init__(self, start: int = 1) -> None:
        """Initialize the timestamp factory.

        Args:
            start: First integer timestamp to emit.

        Returns:
            None.
        """
        self.next_value = start

    def __call__(self) -> int:
        """Generate the next deterministic timestamp.

        Args:
            None.

        Returns:
            Integer timestamp for the current test.
        """
        value = self.next_value
        self.next_value += 1
        return value


class ListFactory:
    """Return deterministic values from a supplied list.

    Attributes:
        values: Ordered values emitted by the factory.
        index: Next value index to emit.
    """

    def __init__(self, values: list[str]) -> None:
        """Initialize the list-backed factory.

        Args:
            values: Ordered values emitted by the factory.

        Returns:
            None.
        """
        self.values = values
        self.index = 0

    def __call__(self) -> str:
        """Return the next configured value.

        Args:
            None.

        Returns:
            Next configured value.
        """
        value = self.values[self.index]
        self.index += 1
        return value


@pytest.fixture
def connection(tmp_path) -> Iterator[sqlite3.Connection]:
    """Create an initialized temporary SQLite connection.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Iterator yielding an initialized SQLite connection.
    """
    database_path = tmp_path / "zembra.sqlite3"
    with database_connection(database_path) as sqlite_connection:
        initialize_database(sqlite_connection)
        yield sqlite_connection


@pytest.fixture
def repository(connection: sqlite3.Connection) -> ZembraRepository:
    """Create a repository with deterministic IDs and timestamps.

    Args:
        connection: Initialized SQLite connection fixture.

    Returns:
        Repository instance configured for repeatable tests.
    """
    return ZembraRepository(
        connection,
        id_factory=SequenceFactory("id"),
        clock=IntegerSequenceFactory(start=100),
    )


def prefix_repository(connection: sqlite3.Connection, ids: list[str]) -> ZembraRepository:
    """Create a repository that emits deterministic note and revision ids.

    Args:
        connection: Initialized SQLite connection fixture.
        ids: Ordered ids emitted for note and revision creation.

    Returns:
        Repository instance configured with deterministic ids.
    """
    return ZembraRepository(
        connection,
        id_factory=ListFactory(ids),
        clock=IntegerSequenceFactory(start=200),
    )


def test_get_or_create_field_is_idempotent(repository: ZembraRepository) -> None:
    """Verify repeated field creation by name returns one record.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    first = repository.get_or_create_field("work")
    second = repository.get_or_create_field("work")

    assert first.id == second.id
    assert [field.name for field in repository.list_fields()] == ["work"]


def test_get_or_create_tag_is_idempotent(repository: ZembraRepository) -> None:
    """Verify repeated tag creation by name returns one record.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    first = repository.get_or_create_tag("python")
    second = repository.get_or_create_tag("python")

    assert first.id == second.id
    assert [tag.name for tag in repository.list_tags()] == ["python"]


def test_create_note_writes_field_tags_and_initial_revision(
    repository: ZembraRepository,
) -> None:
    """Verify note creation creates related field, tags, and revision.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    note = repository.create_note("hello", field_name="work", tag_names=["python", "cli"])

    assert note.content == "hello"
    assert note.field_id is not None
    assert note.current_revision_id is not None
    assert [tag.name for tag in repository.list_note_tags(note.id)] == ["cli", "python"]

    revisions = repository.list_note_revisions(note.id)
    assert len(revisions) == 1
    assert revisions[0].id == note.current_revision_id
    assert revisions[0].content == "hello"


def test_update_note_content_writes_revision(repository: ZembraRepository) -> None:
    """Verify note content updates create a new full snapshot revision.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    note = repository.create_note("first")
    updated = repository.update_note_content(note.id, "second")

    assert updated.content == "second"
    assert updated.updated_at > note.updated_at
    assert updated.current_revision_id != note.current_revision_id

    revisions = repository.list_note_revisions(note.id)
    assert [revision.content for revision in revisions] == ["first", "second"]
    assert revisions[-1].id == updated.current_revision_id


def test_update_missing_note_raises(repository: ZembraRepository) -> None:
    """Verify updating an unknown note raises a repository error.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    with pytest.raises(RecordNotFoundError, match="notes"):
        repository.update_note_content("missing", "content")


def test_archive_note_keeps_note_visible(repository: ZembraRepository) -> None:
    """Verify archived notes remain visible in default note queries.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    note = repository.create_note("archive me")
    archived = repository.archive_note(note.id)

    assert archived.archived_at is not None
    assert repository.get_note(note.id) is not None


def test_delete_note_soft_deletes_and_default_queries_filter_it(
    repository: ZembraRepository,
) -> None:
    """Verify soft-deleted notes are hidden unless explicitly requested.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    note = repository.create_note("delete me")
    deleted = repository.delete_note(note.id)

    assert deleted.deleted_at is not None
    assert repository.get_note(note.id) is None
    assert repository.list_notes() == []
    assert repository.get_note(note.id, include_deleted=True) is not None
    assert repository.list_notes(include_deleted=True)[0].id == note.id


def test_add_tag_to_note_is_idempotent(repository: ZembraRepository) -> None:
    """Verify adding the same tag twice creates one association.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    note = repository.create_note("tag me")

    first = repository.add_tag_to_note(note.id, "python")
    second = repository.add_tag_to_note(note.id, "python")

    assert first.note_id == second.note_id
    assert first.tag_id == second.tag_id
    assert [tag.name for tag in repository.list_note_tags(note.id)] == ["python"]


def test_remove_tag_from_note_keeps_tag_record(repository: ZembraRepository) -> None:
    """Verify removing a note tag only deletes the association.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    note = repository.create_note("tag me", tag_names=["python"])

    repository.remove_tag_from_note(note.id, "python")

    assert repository.list_note_tags(note.id) == []
    assert repository.get_tag_by_name("python") is not None


def test_resolve_note_id_accepts_full_id(connection: sqlite3.Connection) -> None:
    """Verify complete note ids resolve through the exact lookup path.

    Args:
        connection: Initialized SQLite connection fixture.

    Returns:
        None.
    """
    note_id = "abcdef0123456789abcdef0123456789"
    repository = prefix_repository(connection, [note_id, "10000000000000000000000000000000"])
    note = repository.create_note("full id")

    assert repository.resolve_note_id(note.id) == note.id
    assert repository.get_note_by_ref(note.id).id == note.id


def test_resolve_note_id_accepts_unique_prefix(connection: sqlite3.Connection) -> None:
    """Verify a unique four-character prefix resolves to the complete note id.

    Args:
        connection: Initialized SQLite connection fixture.

    Returns:
        None.
    """
    note_id = "abcd0000000000000000000000000000"
    repository = prefix_repository(connection, [note_id, "10000000000000000000000000000000"])
    repository.create_note("unique prefix")

    assert repository.resolve_note_id("abcd") == note_id


def test_resolve_note_id_normalizes_uppercase_prefix(connection: sqlite3.Connection) -> None:
    """Verify uppercase hexadecimal prefixes match lowercase note ids.

    Args:
        connection: Initialized SQLite connection fixture.

    Returns:
        None.
    """
    note_id = "cafe0000000000000000000000000000"
    repository = prefix_repository(connection, [note_id, "10000000000000000000000000000000"])
    repository.create_note("uppercase prefix")

    assert repository.resolve_note_id("CAFE") == note_id


def test_resolve_note_id_rejects_short_prefix(repository: ZembraRepository) -> None:
    """Verify note id prefixes must be at least four characters.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    with pytest.raises(NoteReferenceTooShortError) as error:
        repository.resolve_note_id("abc")

    assert error.value.note_ref == "abc"
    assert error.value.minimum_length == 4


def test_resolve_note_id_rejects_non_hex_reference(repository: ZembraRepository) -> None:
    """Verify note references only accept hexadecimal characters.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    with pytest.raises(InvalidNoteReferenceError) as error:
        repository.resolve_note_id("note-123")

    assert error.value.note_ref == "note-123"


def test_resolve_note_id_reports_missing_prefix(repository: ZembraRepository) -> None:
    """Verify unknown prefixes raise the standard not-found error.

    Args:
        repository: Repository fixture.

    Returns:
        None.
    """
    with pytest.raises(RecordNotFoundError) as error:
        repository.resolve_note_id("abcd")

    assert error.value.table == "notes"
    assert error.value.record_id == "abcd"


def test_resolve_note_id_reports_ambiguous_prefix(connection: sqlite3.Connection) -> None:
    """Verify shared prefixes raise an ambiguity error with candidates.

    Args:
        connection: Initialized SQLite connection fixture.

    Returns:
        None.
    """
    first_id = "abcd0000000000000000000000000000"
    second_id = "abcd1111111111111111111111111111"
    repository = prefix_repository(
        connection,
        [
            first_id,
            "10000000000000000000000000000000",
            second_id,
            "20000000000000000000000000000000",
        ],
    )
    repository.create_note("first")
    repository.create_note("second")

    with pytest.raises(AmbiguousNoteReferenceError) as error:
        repository.resolve_note_id("abcd")

    assert error.value.note_ref == "abcd"
    assert [candidate.id for candidate in error.value.candidates] == [second_id, first_id]


def test_resolve_note_id_ignores_deleted_notes_by_default(
    connection: sqlite3.Connection,
) -> None:
    """Verify soft-deleted notes are excluded from default prefix resolution.

    Args:
        connection: Initialized SQLite connection fixture.

    Returns:
        None.
    """
    note_id = "dead0000000000000000000000000000"
    repository = prefix_repository(connection, [note_id, "10000000000000000000000000000000"])
    note = repository.create_note("deleted")
    repository.delete_note(note.id)

    with pytest.raises(RecordNotFoundError):
        repository.resolve_note_id("dead")

    assert repository.resolve_note_id("dead", include_deleted=True) == note_id


def test_resolve_note_id_keeps_full_id_exact_when_prefix_collides(
    connection: sqlite3.Connection,
) -> None:
    """Verify complete ids are not treated as ambiguous prefix references.

    Args:
        connection: Initialized SQLite connection fixture.

    Returns:
        None.
    """
    full_id = "face0000000000000000000000000000"
    shared_prefix_id = "face1111111111111111111111111111"
    repository = prefix_repository(
        connection,
        [
            full_id,
            "10000000000000000000000000000000",
            shared_prefix_id,
            "20000000000000000000000000000000",
        ],
    )
    repository.create_note("exact")
    repository.create_note("same prefix")

    assert repository.resolve_note_id(full_id) == full_id
