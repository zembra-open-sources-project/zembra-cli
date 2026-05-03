"""Tests for the zembra HTTP repository."""

import json

import httpx
import pytest

from zembra_cli.http_client import HttpZembraRepository, ZembraHttpClientError


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


def note_payload(content: str = "hello") -> dict:
    """Create a valid note response object.

    Args:
        content: Note content to include.

    Returns:
        JSON-serializable note response.
    """
    return {
        "id": "abcd0000000000000000000000000000",
        "content": content,
        "role": "Human",
        "field_id": None,
        "created_at": 1,
        "updated_at": 1,
        "archived_at": None,
        "deleted_at": None,
        "current_revision_id": None,
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
        captured_payload = json.loads(request.content)
        return httpx.Response(201, json={"note": note_payload("hello"), "metadata": {}})

    repository = HttpZembraRepository("http://backend.test", client=make_client(handler))

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
            return httpx.Response(
                200,
                json={
                    "tags": [{"id": "tag-1", "name": "cli", "created_at": 1}],
                    "names": ["cli"],
                },
            )
        return httpx.Response(
            200,
            json={
                "fields": [{"id": "field-1", "name": "work", "created_at": 1}],
                "names": ["work"],
            },
        )

    repository = HttpZembraRepository("http://backend.test", client=make_client(handler))

    assert [tag.name for tag in repository.list_tags()] == ["cli"]
    assert [field.name for field in repository.list_fields()] == ["work"]


def test_http_repository_lists_notes() -> None:
    """Verify list_notes parses note records.

    Args:
        None.

    Returns:
        None.
    """

    def handler(_request: httpx.Request) -> httpx.Response:
        """Return a notes response.

        Args:
            _request: Captured HTTP request.

        Returns:
            Mock HTTP response.
        """
        return httpx.Response(200, json={"notes": [note_payload("saved")]})

    repository = HttpZembraRepository("http://backend.test", client=make_client(handler))

    assert [note.content for note in repository.list_notes()] == ["saved"]


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

    repository = HttpZembraRepository("http://backend.test", client=make_client(handler))

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

    repository = HttpZembraRepository("http://backend.test", client=make_client(handler))

    with pytest.raises(ZembraHttpClientError, match='missing "tags"'):
        repository.list_tags()
