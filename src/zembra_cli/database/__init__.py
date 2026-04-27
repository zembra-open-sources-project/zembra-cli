"""Database infrastructure public API for zembra-cli."""

from zembra_cli.database.core import (
    CORE_TABLES,
    DEFAULT_DATABASE_PATH,
    SCHEMA_SQL_PATH,
    DatabaseInitializationError,
    DatabaseInitResult,
    DatabaseSchemaIncompleteError,
    connect_database,
    database_connection,
    initialize_database,
    initialize_database_file,
    list_user_tables,
    missing_core_tables,
    read_initial_schema,
)

__all__ = [
    "CORE_TABLES",
    "DEFAULT_DATABASE_PATH",
    "SCHEMA_SQL_PATH",
    "DatabaseInitializationError",
    "DatabaseInitResult",
    "DatabaseSchemaIncompleteError",
    "connect_database",
    "database_connection",
    "initialize_database",
    "initialize_database_file",
    "list_user_tables",
    "missing_core_tables",
    "read_initial_schema",
]
