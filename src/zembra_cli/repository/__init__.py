"""Repository facade for Zembra database operations."""

from zembra_cli.repository.exceptions import RecordNotFoundError
from zembra_cli.repository.notes import ZembraRepository

__all__ = ["RecordNotFoundError", "ZembraRepository"]
