"""Shared zembra system configuration helpers."""

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


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


class CascadingConfigMissingError(ConfigFileMissingError):
    """Signal that no config file exists in the cascading config chain."""

    def __init__(self, cli_config_path: Path, global_config_path: Path) -> None:
        """Initialize the cascading missing-file error.

        Args:
            cli_config_path: Expected CLI-specific configuration path.
            global_config_path: Expected global fallback configuration path.

        Returns:
            None.
        """
        self.cli_config_path = cli_config_path
        self.global_config_path = global_config_path
        ConfigError.__init__(
            self,
            f"Config file is missing. Checked {cli_config_path} and {global_config_path}. "
            "Create it with: zembra-cli config database <file-path>",
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


class ConfigCliModeMissingError(ConfigError):
    """Signal that the zembra configuration does not define cli.mode."""

    def __init__(self) -> None:
        """Initialize the missing CLI mode error.

        Args:
            None.

        Returns:
            None.
        """
        super().__init__(
            'CLI mode is missing in the zembra config. Set [cli].mode to "direct" or "http".'
        )


class ConfigCliModeInvalidError(ConfigError):
    """Signal that cli.mode is not a supported value.

    Attributes:
        mode: Unsupported mode value decoded from config.
    """

    def __init__(self, mode: object) -> None:
        """Initialize the invalid CLI mode error.

        Args:
            mode: Unsupported mode value decoded from config.

        Returns:
            None.
        """
        self.mode = mode
        super().__init__('CLI mode must be "direct" or "http".')


class ConfigHttpBaseUrlMissingError(ConfigError):
    """Signal that HTTP mode does not define cli.http_base_url."""

    def __init__(self) -> None:
        """Initialize the missing HTTP base URL error.

        Args:
            None.

        Returns:
            None.
        """
        super().__init__(
            "HTTP backend URL is missing in the zembra config. "
            'Set [cli].http_base_url when [cli].mode is "http".'
        )


class ConfigWorkspaceIdMissingError(ConfigError):
    """Signal that direct mode does not define workspace.id in CLI config."""

    def __init__(self) -> None:
        """Initialize the missing workspace ID error.

        Args:
            None.

        Returns:
            None.
        """
        super().__init__(
            "Workspace ID is missing in the zembra CLI config. Run: zembra-cli init"
        )


class ConfigParentMissingError(ConfigError):
    """Signal that the configuration file parent directory is absent."""


@dataclass(frozen=True)
class ZembraConfig:
    """Represent loaded zembra system configuration.

    Attributes:
        cli_mode: CLI connection mode.
        database_path: SQLite database path configured for direct mode.
        http_base_url: Backend base URL configured for HTTP mode.
        workspace_id: CLI workspace identifier.
        workspace_name: Optional CLI direct-mode workspace display name.
    """

    cli_mode: Literal["direct", "http"]
    database_path: Path | None = None
    http_base_url: str | None = None
    workspace_id: str | None = None
    workspace_name: str | None = None


def default_cli_config_path() -> Path:
    """Return the default zembra-cli configuration path.

    Args:
        None.

    Returns:
        The default CLI-specific configuration path under the user's home directory.
    """
    return Path.home() / ".zembra" / "config.cli.toml"


def default_global_config_path() -> Path:
    """Return the default global zembra fallback configuration path.

    Args:
        None.

    Returns:
        The global configuration path under the current user's home directory.
    """
    return Path.home() / ".zembra.env"


def load_cascading_config(
    cli_config_path: str | Path | None = None,
    global_config_path: str | Path | None = None,
) -> ZembraConfig:
    """Load zembra config from CLI and global files with field-level fallback.

    Args:
        cli_config_path: Optional CLI-specific TOML configuration path.
        global_config_path: Optional global fallback TOML configuration path.

    Returns:
        The validated zembra configuration built from merged fields.
    """
    cli_path = (
        Path(cli_config_path).expanduser()
        if cli_config_path is not None
        else default_cli_config_path()
    )
    global_path = (
        Path(global_config_path).expanduser()
        if global_config_path is not None
        else default_global_config_path()
    )

    cli_data = _read_optional_config_data(cli_path)
    global_data = _read_optional_config_data(global_path)
    if cli_data is None and global_data is None:
        raise CascadingConfigMissingError(cli_path, global_path)

    merged_data = _merge_config_data(global_data or {}, cli_data or {})
    if isinstance(cli_data, dict):
        workspace_section = cli_data.get("workspace")
        if isinstance(workspace_section, dict):
            merged_data["workspace"] = dict(workspace_section)
    return _config_from_data(merged_data)


def write_database_path(
    database_path: str | Path,
    config_path: str | Path | None = None,
    set_direct_mode: bool = False,
    workspace_id: str | None = None,
    workspace_name: str | None = None,
) -> ZembraConfig:
    """Write the configured zembra database path to a TOML file.

    Args:
        database_path: SQLite database path to store.
        config_path: Optional TOML configuration path.
        set_direct_mode: Whether to explicitly set ``[cli].mode`` to ``direct``.
        workspace_id: Optional workspace ID to write into CLI config.
        workspace_name: Optional workspace display name to write into CLI config.

    Returns:
        A direct-mode config object containing the written database path.
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

    resolved_database_path = Path(database_path).expanduser()
    database_section["path"] = str(resolved_database_path)
    if set_direct_mode:
        cli_section = data.get("cli")
        if not isinstance(cli_section, dict):
            cli_section = {}
            data["cli"] = cli_section
        cli_section["mode"] = "direct"

    if workspace_id is not None:
        workspace_section = data.get("workspace")
        if not isinstance(workspace_section, dict):
            workspace_section = {}
            data["workspace"] = workspace_section
        workspace_section["id"] = workspace_id
        if workspace_name is not None:
            workspace_section["name"] = workspace_name
        else:
            workspace_section.pop("name", None)

    path.write_text(_dump_toml(data), encoding="utf-8")
    return ZembraConfig(
        cli_mode="direct",
        database_path=resolved_database_path,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
    )


def _resolve_config_path(config_path: str | Path | None) -> Path:
    """Resolve an optional configuration path.

    Args:
        config_path: Optional path supplied by tests or callers.

    Returns:
        An expanded filesystem path.
    """
    return Path(config_path).expanduser() if config_path is not None else default_cli_config_path()


def _read_optional_config_data(path: Path) -> dict[str, Any] | None:
    """Read TOML config data when the path exists.

    Args:
        path: Configuration path to read.

    Returns:
        Parsed TOML data, or None when the file does not exist.
    """
    if not path.exists():
        return None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigParseError(f"Config file is not valid TOML at {path}: {error}") from error


def _merge_config_data(global_data: dict[str, Any], cli_data: dict[str, Any]) -> dict[str, Any]:
    """Merge CLI config over global config at supported field granularity.

    Args:
        global_data: Parsed global fallback config.
        cli_data: Parsed CLI-specific config.

    Returns:
        A minimal config dictionary containing merged supported fields.
    """
    merged: dict[str, Any] = {}
    cli_section = _merged_section(global_data, cli_data, "cli", ("mode", "http_base_url"))
    if cli_section:
        merged["cli"] = cli_section
    database_section = _merged_section(global_data, cli_data, "database", ("path",))
    if database_section:
        merged["database"] = database_section
    return merged


def _merged_section(
    global_data: dict[str, Any],
    cli_data: dict[str, Any],
    section_name: str,
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    """Merge selected fields for a single TOML section.

    Args:
        global_data: Parsed global fallback config.
        cli_data: Parsed CLI-specific config.
        section_name: TOML section name to merge.
        field_names: Supported field names within the section.

    Returns:
        A dictionary containing merged section fields.
    """
    merged: dict[str, Any] = {}
    global_section = global_data.get(section_name)
    cli_section = cli_data.get(section_name)
    if not isinstance(global_section, dict):
        global_section = {}
    if not isinstance(cli_section, dict):
        cli_section = {}
    for field_name in field_names:
        if field_name in cli_section:
            merged[field_name] = cli_section[field_name]
        elif field_name in global_section:
            merged[field_name] = global_section[field_name]
    return merged


def _config_from_data(data: dict[str, Any]) -> ZembraConfig:
    """Build a configuration model from decoded TOML data.

    Args:
        data: Decoded TOML object.

    Returns:
        The validated zembra configuration.
    """
    cli_section = data.get("cli")
    if not isinstance(cli_section, dict):
        raise ConfigCliModeMissingError()

    raw_cli_mode = cli_section.get("mode")
    if raw_cli_mode is None:
        raise ConfigCliModeMissingError()
    if raw_cli_mode not in {"direct", "http"}:
        raise ConfigCliModeInvalidError(raw_cli_mode)

    if raw_cli_mode == "http":
        raw_http_base_url = cli_section.get("http_base_url")
        if not isinstance(raw_http_base_url, str) or not raw_http_base_url.strip():
            raise ConfigHttpBaseUrlMissingError()
        workspace_id, workspace_name = _workspace_config_from_data(data)
        return ZembraConfig(
            cli_mode="http",
            http_base_url=raw_http_base_url.strip(),
            workspace_id=workspace_id,
            workspace_name=workspace_name,
        )

    database_section = data.get("database")
    if not isinstance(database_section, dict):
        raise ConfigDatabasePathMissingError()

    raw_database_path = database_section.get("path")
    if not isinstance(raw_database_path, str) or not raw_database_path.strip():
        raise ConfigDatabasePathMissingError()

    workspace_id, workspace_name = _workspace_config_from_data(data)

    return ZembraConfig(
        cli_mode="direct",
        database_path=Path(raw_database_path).expanduser(),
        workspace_id=workspace_id,
        workspace_name=workspace_name,
    )


def _workspace_config_from_data(data: dict[str, Any]) -> tuple[str, str | None]:
    """Read workspace configuration from decoded TOML data.

    Args:
        data: Decoded TOML object.

    Returns:
        Workspace identifier and optional display name.
    """
    workspace_section = data.get("workspace")
    if not isinstance(workspace_section, dict):
        raise ConfigWorkspaceIdMissingError()

    raw_workspace_id = workspace_section.get("id")
    if not isinstance(raw_workspace_id, str) or not raw_workspace_id.strip():
        raise ConfigWorkspaceIdMissingError()

    raw_workspace_name = workspace_section.get("name")
    workspace_name = raw_workspace_name.strip() if isinstance(raw_workspace_name, str) else None

    return raw_workspace_id.strip(), workspace_name


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
