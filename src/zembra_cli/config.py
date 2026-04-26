"""Shared zembra system configuration helpers."""

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(RuntimeError):
    """Base error for zembra configuration failures.

    Attributes:
        message: Natural-language description suitable for CLI output.
    """

    def __init__(self, message: str) -> None:
        """Initialize the configuration error.

        Args:
            message: Natural-language description suitable for CLI output.

        Returns:
            None.
        """
        self.message = message
        super().__init__(message)


class ConfigFileMissingError(ConfigError):
    """Signal that the zembra configuration file does not exist.

    Attributes:
        config_path: Expected configuration file path.
    """

    def __init__(self, config_path: Path) -> None:
        """Initialize the missing-file error.

        Args:
            config_path: Expected configuration file path.

        Returns:
            None.
        """
        self.config_path = config_path
        super().__init__(
            f"Config file is missing at {config_path}. "
            "Create it with: zembra-cli config database <file-path>"
        )


class ConfigParseError(ConfigError):
    """Signal that the zembra configuration file is not valid TOML."""


class ConfigDatabasePathMissingError(ConfigError):
    """Signal that the zembra configuration does not define database.path."""

    def __init__(self) -> None:
        """Initialize the missing database path error.

        Args:
            None.

        Returns:
            None.
        """
        super().__init__(
            "Database path is missing in the zembra config. "
            "Set it with: zembra-cli config database <file-path>"
        )


class ConfigParentMissingError(ConfigError):
    """Signal that the configuration file parent directory is absent."""


@dataclass(frozen=True)
class ZembraConfig:
    """Represent loaded zembra system configuration.

    Attributes:
        database_path: SQLite database path configured for zembra.
    """

    database_path: Path


def default_config_path() -> Path:
    """Return the default zembra system configuration path.

    Args:
        None.

    Returns:
        The default configuration path under the current user's home directory.
    """
    return Path.home() / ".zembra.env"


def load_config(config_path: str | Path | None = None) -> ZembraConfig:
    """Load zembra configuration from a TOML file.

    Args:
        config_path: Optional TOML configuration path.

    Returns:
        The validated zembra configuration.
    """
    path = _resolve_config_path(config_path)
    if not path.exists():
        raise ConfigFileMissingError(path)

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigParseError(f"Config file is not valid TOML: {error}") from error

    return _config_from_data(data)


def write_database_path(
    database_path: str | Path,
    config_path: str | Path | None = None,
) -> ZembraConfig:
    """Write the configured zembra database path to a TOML file.

    Args:
        database_path: SQLite database path to store.
        config_path: Optional TOML configuration path.

    Returns:
        The validated zembra configuration after writing.
    """
    path = _resolve_config_path(config_path)
    if not path.parent.exists():
        raise ConfigParentMissingError(f"Config directory does not exist: {path.parent}")

    data: dict[str, Any]
    if path.exists():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise ConfigParseError(f"Config file is not valid TOML: {error}") from error
    else:
        data = {}

    database_section = data.get("database")
    if not isinstance(database_section, dict):
        database_section = {}
        data["database"] = database_section
    database_section["path"] = str(Path(database_path).expanduser())

    path.write_text(_dump_toml(data), encoding="utf-8")
    return _config_from_data(data)


def _resolve_config_path(config_path: str | Path | None) -> Path:
    """Resolve an optional configuration path.

    Args:
        config_path: Optional path supplied by tests or callers.

    Returns:
        An expanded filesystem path.
    """
    return Path(config_path).expanduser() if config_path is not None else default_config_path()


def _config_from_data(data: dict[str, Any]) -> ZembraConfig:
    """Build a configuration model from decoded TOML data.

    Args:
        data: Decoded TOML object.

    Returns:
        The validated zembra configuration.
    """
    database_section = data.get("database")
    if not isinstance(database_section, dict):
        raise ConfigDatabasePathMissingError()

    raw_database_path = database_section.get("path")
    if not isinstance(raw_database_path, str) or not raw_database_path.strip():
        raise ConfigDatabasePathMissingError()

    return ZembraConfig(database_path=Path(raw_database_path).expanduser())


def _dump_toml(data: dict[str, Any]) -> str:
    """Serialize a simple TOML dictionary.

    Args:
        data: TOML-compatible values decoded from the existing config.

    Returns:
        A TOML document string.
    """
    lines: list[str] = []
    scalar_items = [(key, value) for key, value in data.items() if not isinstance(value, dict)]
    table_items = [(key, value) for key, value in data.items() if isinstance(value, dict)]

    for key, value in scalar_items:
        lines.append(f"{key} = {_dump_toml_value(value)}")

    for table_index, (table_name, table_values) in enumerate(table_items):
        if lines or table_index:
            lines.append("")
        lines.append(f"[{table_name}]")
        for key, value in table_values.items():
            lines.append(f"{key} = {_dump_toml_value(value)}")

    return "\n".join(lines) + "\n"


def _dump_toml_value(value: Any) -> str:
    """Serialize a scalar TOML value.

    Args:
        value: Scalar value to serialize.

    Returns:
        TOML representation for the scalar value.
    """
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    raise ConfigError(f"Unsupported config value: {value!r}")
