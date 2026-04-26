"""Shared repository utilities for SQLite-backed data access."""

import sqlite3
import time
import uuid
from collections.abc import Callable
from typing import TypeVar

from zembra_cli.models import SchemaModel

ModelT = TypeVar("ModelT", bound=SchemaModel)


class BaseRepository:
    """Provide shared database, ID, clock, and row mapping helpers.

    Attributes:
        connection: SQLite connection used by repository methods.
        id_factory: Callable used to generate stable record identifiers.
        clock: Callable returning the current Unix timestamp.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], int] | None = None,
    ) -> None:
        """Initialize the repository base.

        Args:
            connection: Open SQLite connection configured by the caller.
            id_factory: Optional ID generator for deterministic tests.
            clock: Optional Unix timestamp provider for deterministic tests.

        Returns:
            None.
        """
        self.connection = connection
        self.id_factory = id_factory or self._default_id_factory
        self.clock = clock or self._default_clock

    def _new_id(self) -> str:
        """Generate a new stable identifier.

        Args:
            None.

        Returns:
            A non-empty string identifier.
        """
        return self.id_factory()

    def _now(self) -> int:
        """Return the current Unix timestamp.

        Args:
            None.

        Returns:
            Current Unix timestamp as an integer.
        """
        return self.clock()

    def _row_to_model(self, row: sqlite3.Row, model_type: type[ModelT]) -> ModelT:
        """Convert a SQLite row into a Pydantic schema model.

        Args:
            row: SQLite row with named columns.
            model_type: Pydantic model class to instantiate.

        Returns:
            The validated Pydantic model instance.
        """
        return model_type.model_validate(dict(row))

    @staticmethod
    def _default_id_factory() -> str:
        """Generate a UUID-based identifier.

        Args:
            None.

        Returns:
            A lowercase hexadecimal UUID string.
        """
        return uuid.uuid4().hex

    @staticmethod
    def _default_clock() -> int:
        """Return the current Unix timestamp.

        Args:
            None.

        Returns:
            Current Unix timestamp as an integer.
        """
        return int(time.time())
