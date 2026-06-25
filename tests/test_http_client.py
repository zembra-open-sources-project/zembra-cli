"""Tests for the zembra HTTP repository."""

import json

import httpx
import pytest

from zembra_cli.http_client import HttpZembraRepository, ZembraHttpClientError

TEST_WORKSPACE_ID = "550e8400-e29b-41d4-a716-446655440000"


def make_client(handler) -> httpx.Client:
    """Create an httpx client backed by a mock transport.

    Args:
        handler: Callable that maps requests to responses.

    Returns:
        Configured httpx client.
    """
    return httpx.Client(
        base_url="http://backend.test",
        transport=httpx.MockTransport(handler),
    )


def make_repository(handler) -> HttpZembraRepository:
    """Create a workspace-scoped HTTP repository backed by a mock transport.

    Args:
        handler: Callable that maps requests to responses.

    Returns:
        Configured HTTP repository.
    """
    return HttpZembraRepository(
        "http://backend.test",
        workspace_id=TEST_WORKSPACE_ID,
        client=make_client(handler),
    )


def note_payload(content: str = "hello", note_id: str = "abcd0000000000000000000000000000") -> dict:
    """Create a valid note response object.

    Args:
        content: Note content to include.
        note_id: Note identifier to include.

    Returns:
        JSON-serializable note response.
    """
    return {
        "id": note_id,
        "workspace_id": TEST_WORKSPACE_ID,
        "content": content,
        "role": "Human",
        "field_id": "field-1",
        "created_at": 1,
        "updated_at": 1,
        "archived_at": None,
        "deleted_at": None,
        "current_revision_id": None,
        "last_change_id": None,
        "conflict_status": "none",
    }


def field_payload(name: str = "work", field_id: str = "field-1") -> dict:
    """Create a valid field response object.

    Args:
        name: Field name to include.
        field_id: Field identifier to include.

    Returns:
        JSON-serializable field response.
    """
    return {"id": field_id, "workspace_id": TEST_WORKSPACE_ID, "name": name, "created_at": 1}


def tag_payload(name: str = "cli", tag_id: str = "tag-1") -> dict:
    """Create a valid root tag response object.

    Args:
        name: Tag name to include.
        tag_id: Tag identifier to include.

    Returns:
        JSON-serializable tag response.
    """
    return {
        "id": tag_id,
        "workspace_id": TEST_WORKSPACE_ID,
        "name": name,
        "parent_tag_id": None,
        "path": name,
        "depth": 0,
        "created_at": 1,
    }


def test_http_repository_create_note_sends_payload_and_parses_note() -> None:
    """Verify create_note posts JSON and returns a note model.

    Args:
        None.

    Returns:
        None.
    """
    captured_payload: dict | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        """Return a created note response for POST /notes.

        Args:
            request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        nonlocal captured_payload
        assert request.url.params["workspace_id"] == TEST_WORKSPACE_ID
        captured_payload = json.loads(request.content)
        return httpx.Response(201, json={"note": note_payload("hello"), "metadata": {}})

    repository = make_repository(handler)

    note = repository.create_note(
        "hello",
        role="Human",
        field_name="work",
        tag_names=["cli"],
        device_id="device-1",
    )

    assert note.content == "hello"
    assert captured_payload == {
        "content": "hello",
        "role": "Human",
        "field": "work",
        "tags": ["cli"],
        "device_id": "device-1",
    }


def test_http_repository_lists_tags_and_fields() -> None:
    """Verify list endpoints parse tag and field records.

    Args:
        None.

    Returns:
        None.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """Return taxonomy responses based on the request path.

        Args:
            request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        if request.url.path == "/tags":
            assert request.url.params["all"] == "true"
            return httpx.Response(
                200,
                json={
                    "tags": [tag_payload()],
                    "names": ["cli"],
                },
            )
        assert request.url.params["all"] == "true"
        return httpx.Response(
            200,
            json={
                "fields": [field_payload()],
                "names": ["work"],
            },
        )

    repository = make_repository(handler)

    assert [tag.name for tag in repository.list_tags()] == ["cli"]
    assert [field.name for field in repository.list_fields()] == ["work"]


def test_http_repository_lists_notes() -> None:
    """Verify list_notes parses note records.

    Args:
        None.

    Returns:
        None.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """Return a notes response.

        Args:
            request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        assert request.url.params["workspace_id"] == TEST_WORKSPACE_ID
        return httpx.Response(200, json={"notes": [note_payload("saved")]})

    repository = make_repository(handler)

    assert [note.content for note in repository.list_notes()] == ["saved"]


def test_http_repository_adds_workspace_id_to_backend_records() -> None:
    """Verify backend records inherit the configured workspace when omitted.

    Args:
        None.

    Returns:
        None.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """Return current backend-shaped records without workspace_id.

        Args:
            request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        note = note_payload("saved")
        note.pop("workspace_id")
        assert request.url.params["workspace_id"] == TEST_WORKSPACE_ID
        return httpx.Response(200, json={"notes": [note]})

    repository = make_repository(handler)

    notes = repository.list_notes()

    assert notes[0].workspace_id == TEST_WORKSPACE_ID


def test_http_repository_random_notes_enriches_metadata() -> None:
    """Verify random_notes calls the backend and adds field and tags.

    Args:
        None.

    Returns:
        None.
    """
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Return random notes and metadata responses.

        Args:
            request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        paths.append(str(request.url))
        if request.url.path == "/random/notes":
            return httpx.Response(200, json={"notes": [note_payload("full content")]})
        if request.url.path == "/fields":
            return httpx.Response(
                200,
                json={
                    "fields": [field_payload()],
                    "names": ["work"],
                },
            )
        if request.url.path == "/notes/abcd0000000000000000000000000000/tags":
            return httpx.Response(
                200,
                json={"tags": [tag_payload()]},
            )
        return httpx.Response(404, json={"error": {"message": "missing", "code": "missing"}})

    repository = make_repository(handler)

    notes = repository.random_notes(3)

    assert paths[0] == f"http://backend.test/random/notes?workspace_id={TEST_WORKSPACE_ID}&n=3"
    assert notes[0].note.content == "full content"
    assert notes[0].field is not None
    assert notes[0].field.name == "work"
    assert [tag.name for tag in notes[0].tags] == ["cli"]


def test_http_repository_random_tagged_notes_parses_groups() -> None:
    """Verify random_tagged_notes parses groups and enriches notes.

    Args:
        None.

    Returns:
        None.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """Return random tag group and metadata responses.

        Args:
            request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        if request.url.path == "/random/tags":
            assert request.url.params["workspace_id"] == TEST_WORKSPACE_ID
            assert request.url.params["n"] == "2"
            assert request.url.params["count"] == "5"
            return httpx.Response(
                200,
                json={
                    "tagged_notes": [
                        {
                            "tag": tag_payload(),
                            "notes": [note_payload("tagged")],
                        }
                    ]
                },
            )
        if request.url.path == "/fields":
            return httpx.Response(
                200,
                json={
                    "fields": [field_payload()],
                    "names": ["work"],
                },
            )
        if request.url.path == "/notes/abcd0000000000000000000000000000/tags":
            assert request.url.params["workspace_id"] == TEST_WORKSPACE_ID
            return httpx.Response(
                200,
                json={"tags": [tag_payload()]},
            )
        return httpx.Response(404, json={"error": {"message": "missing", "code": "missing"}})

    repository = make_repository(handler)

    groups = repository.random_tagged_notes(2, 5)

    assert groups[0].tag.name == "cli"
    assert groups[0].notes[0].note.content == "tagged"
    assert groups[0].notes[0].field is not None
    assert groups[0].notes[0].field.name == "work"
    assert [tag.name for tag in groups[0].notes[0].tags] == ["cli"]


def test_http_repository_random_field_notes_parses_groups() -> None:
    """Verify random_field_notes parses groups and enriches notes.

    Args:
        None.

    Returns:
        None.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """Return random field group and metadata responses.

        Args:
            request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        if request.url.path == "/random/fields":
            assert request.url.params["workspace_id"] == TEST_WORKSPACE_ID
            assert request.url.params["n"] == "2"
            assert request.url.params["count"] == "5"
            return httpx.Response(
                200,
                json={
                    "field_notes": [
                        {
                            "field": field_payload(),
                            "notes": [note_payload("field note")],
                        }
                    ]
                },
            )
        if request.url.path == "/fields":
            return httpx.Response(200, json={"fields": [], "names": []})
        if request.url.path == "/notes/abcd0000000000000000000000000000/tags":
            return httpx.Response(200, json={"tags": []})
        return httpx.Response(404, json={"error": {"message": "missing", "code": "missing"}})

    repository = make_repository(handler)

    groups = repository.random_field_notes(2, 5)

    assert groups[0].field.name == "work"
    assert groups[0].notes[0].field is not None
    assert groups[0].notes[0].field.name == "work"
    assert groups[0].notes[0].note.content == "field note"


def test_http_repository_raises_structured_error_message() -> None:
    """Verify backend error bodies become client errors.

    Args:
        None.

    Returns:
        None.
    """

    def handler(_request: httpx.Request) -> httpx.Response:
        """Return a structured validation error.

        Args:
            _request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        return httpx.Response(
            422,
            json={"error": {"code": "validation_error", "message": "Request validation failed."}},
        )

    repository = make_repository(handler)

    with pytest.raises(ZembraHttpClientError, match="Request validation failed"):
        repository.create_note("")


def test_http_repository_rejects_invalid_response_shape() -> None:
    """Verify missing response fields are reported clearly.

    Args:
        None.

    Returns:
        None.
    """

    def handler(_request: httpx.Request) -> httpx.Response:
        """Return a response missing the expected tags field.

        Args:
            _request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        return httpx.Response(200, json={"names": []})

    repository = make_repository(handler)

    with pytest.raises(ZembraHttpClientError, match='missing "tags"'):
        repository.list_tags()
