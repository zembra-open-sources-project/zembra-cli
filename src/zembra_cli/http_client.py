"""HTTP repository implementation for zembra backend connections."""

from collections.abc import Sequence
from typing import Any, Literal

import httpx
from pydantic import ValidationError

from zembra_cli.models import FieldRecord, NoteRecord, TagRecord

DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0


class ZembraHttpClientError(RuntimeError):
    """Signal that an HTTP repository operation failed.

    Attributes:
        message: Natural-language description suitable for CLI output.
    """

    def __init__(self, message: str) -> None:
        """Initialize the HTTP client error.

        Args:
            message: Natural-language description suitable for CLI output.

        Returns:
            None.
        """
        self.message = message
        super().__init__(message)


class HttpZembraRepository:
    """Provide repository operations through the zembra HTTP backend."""

    def __init__(
        self,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the HTTP repository.

        Args:
            base_url: Backend base URL such as ``http://127.0.0.1:3000``.
            client: Optional preconfigured httpx client for tests.
            timeout: Request timeout in seconds when creating the default client.

        Returns:
            None.
        """
        normalized_base_url = base_url.rstrip("/")
        parsed_base_url = httpx.URL(normalized_base_url)
        if not normalized_base_url or parsed_base_url.scheme not in {"http", "https"}:
            raise ZembraHttpClientError("Zembra backend URL must start with http:// or https://.")

        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=normalized_base_url,
            timeout=timeout,
        )

    def close(self) -> None:
        """Close the underlying HTTP client when owned by this repository.

        Args:
            None.

        Returns:
            None.
        """
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "HttpZembraRepository":
        """Enter a context manager for the HTTP repository.

        Args:
            None.

        Returns:
            This repository instance.
        """
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Exit a context manager and close owned resources.

        Args:
            *_exc_info: Exception details supplied by the context manager protocol.

        Returns:
            None.
        """
        self.close()

    def create_note(
        self,
        content: str,
        role: Literal["Human", "Agent"] = "Human",
        field_name: str | None = None,
        tag_names: Sequence[str] | None = None,
        device_id: str | None = None,
    ) -> NoteRecord:
        """Create a note through ``POST /notes``.

        Args:
            content: Note body text.
            role: Immutable note creation role.
            field_name: Optional field name to attach to the note.
            tag_names: Optional tag names to attach to the note.
            device_id: Optional device identifier recorded on the revision.

        Returns:
            The created note record.
        """
        payload = {
            "content": content,
            "role": role,
            "field": field_name,
            "tags": list(tag_names or ()),
            "device_id": device_id,
        }
        data = self._request_json("POST", "/notes", json=payload)
        note_data = self._require_key(data, "note")
        return self._parse_model(note_data, NoteRecord, "note")

    def list_tags(self) -> list[TagRecord]:
        """List tags through ``GET /tags``.

        Args:
            None.

        Returns:
            Ordered tag records.
        """
        data = self._request_json("GET", "/tags")
        tags_data = self._require_key(data, "tags")
        return self._parse_model_list(tags_data, TagRecord, "tags")

    def list_fields(self) -> list[FieldRecord]:
        """List fields through ``GET /fields``.

        Args:
            None.

        Returns:
            Ordered field records.
        """
        data = self._request_json("GET", "/fields")
        fields_data = self._require_key(data, "fields")
        return self._parse_model_list(fields_data, FieldRecord, "fields")

    def list_notes(self, include_deleted: bool = False) -> list[NoteRecord]:
        """List notes through ``GET /notes``.

        Args:
            include_deleted: Whether soft-deleted notes are included. The current backend endpoint
                lists active notes only, so this flag is accepted for protocol compatibility.

        Returns:
            Ordered note records.
        """
        data = self._request_json("GET", "/notes")
        notes_data = self._require_key(data, "notes")
        return self._parse_model_list(notes_data, NoteRecord, "notes")

    def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Send a request and decode a JSON object response.

        Args:
            method: HTTP method.
            path: Backend request path.
            **kwargs: Additional httpx request arguments.

        Returns:
            Decoded JSON object.
        """
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.RequestError as error:
            raise ZembraHttpClientError(
                f"Could not connect to Zembra backend: {error}"
            ) from error

        if response.is_error:
            raise ZembraHttpClientError(self._format_error_response(response))

        try:
            data = response.json()
        except ValueError as error:
            raise ZembraHttpClientError("Zembra backend returned invalid JSON.") from error

        if not isinstance(data, dict):
            raise ZembraHttpClientError("Zembra backend returned an invalid response shape.")
        return data

    def _format_error_response(self, response: httpx.Response) -> str:
        """Format an error response for CLI output.

        Args:
            response: HTTP error response.

        Returns:
            Natural-language error message.
        """
        try:
            data = response.json()
        except ValueError:
            return f"Zembra backend returned HTTP {response.status_code}."

        if isinstance(data, dict):
            error_body = data.get("error")
            if isinstance(error_body, dict):
                message = error_body.get("message")
                code = error_body.get("code")
                if isinstance(message, str) and message.strip():
                    return message
                if isinstance(code, str) and code.strip():
                    return code
        return f"Zembra backend returned HTTP {response.status_code}."

    def _require_key(self, data: dict[str, Any], key: str) -> Any:
        """Read a required key from a response object.

        Args:
            data: Decoded response object.
            key: Required response key.

        Returns:
            The value stored under ``key``.
        """
        if key not in data:
            raise ZembraHttpClientError(f'Zembra backend response is missing "{key}".')
        return data[key]

    def _parse_model(
        self,
        data: Any,
        model_type: type[FieldRecord | NoteRecord | TagRecord],
        name: str,
    ):
        """Parse one Pydantic model from response data.

        Args:
            data: Decoded response data.
            model_type: Pydantic model class.
            name: Response field name used in error messages.

        Returns:
            Parsed model instance.
        """
        try:
            return model_type.model_validate(data)
        except ValidationError as error:
            raise ZembraHttpClientError(
                f'Zembra backend returned invalid "{name}" data.'
            ) from error

    def _parse_model_list(
        self,
        data: Any,
        model_type: type[FieldRecord | NoteRecord | TagRecord],
        name: str,
    ):
        """Parse a list of Pydantic models from response data.

        Args:
            data: Decoded response data.
            model_type: Pydantic model class.
            name: Response field name used in error messages.

        Returns:
            Parsed model instances.
        """
        if not isinstance(data, list):
            raise ZembraHttpClientError(f'Zembra backend returned invalid "{name}" data.')
        return [self._parse_model(item, model_type, name) for item in data]
