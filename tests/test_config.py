"""Tests for zembra configuration file handling."""

from pathlib import Path

import pytest

from zembra_cli.config import (
    ConfigCliModeInvalidError,
    ConfigDatabasePathMissingError,
    ConfigFileMissingError,
    ConfigHttpBaseUrlMissingError,
    ConfigParentMissingError,
    ConfigParseError,
    ConfigWorkspaceIdMissingError,
    ZembraConfig,
    default_cli_config_path,
    default_global_config_path,
    load_cascading_config,
    load_workspace_command_config,
    write_database_path,
    write_default_workspace,
)


def test_default_cli_config_path_uses_zembra_directory(monkeypatch, tmp_path) -> None:
    """Verify the default CLI config path lives under the zembra directory.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert default_cli_config_path() == tmp_path / ".zembra" / "config.cli.toml"
    assert default_global_config_path() == tmp_path / ".zembra.env"


def test_load_cascading_config_reads_database_path(tmp_path) -> None:
    """Verify a valid TOML config loads the database path.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    config_path.write_text(
        f'[database]\npath = "{database_path}"\n\n'
        '[workspace]\nid = "550e8400-e29b-41d4-a716-446655440000"\n',
        encoding="utf-8",
    )

    config = load_cascading_config(config_path, tmp_path / "missing.env")

    assert config == ZembraConfig(
        database_path=database_path,
        workspace_id="550e8400-e29b-41d4-a716-446655440000",
    )


def test_load_cascading_config_reads_http_mode(tmp_path) -> None:
    """Verify HTTP mode loads the configured backend URL.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(
        '[cli]\nhttp_base_url = "http://127.0.0.1:3000"\n\n'
        '[workspace]\nid = "550e8400-e29b-41d4-a716-446655440000"\n',
        encoding="utf-8",
    )

    config = load_cascading_config(config_path, tmp_path / "missing.env")

    assert config == ZembraConfig(
        http_base_url="http://127.0.0.1:3000",
        workspace_id="550e8400-e29b-41d4-a716-446655440000",
    )


def test_load_cascading_config_reads_cli_config_first(tmp_path) -> None:
    """Verify CLI config values override global config values.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    cli_database_path = tmp_path / "cli.sqlite3"
    global_database_path = tmp_path / "global.sqlite3"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        f'[cli]\nmode = "direct"\n\n[database]\npath = "{cli_database_path}"\n\n'
        '[workspace]\nid = "550e8400-e29b-41d4-a716-446655440000"\nname = "Work"\n',
        encoding="utf-8",
    )
    global_config_path.write_text(
        f'[cli]\nmode = "http"\nhttp_base_url = "http://global.test"\n\n'
        f'[database]\npath = "{global_database_path}"\n',
        encoding="utf-8",
    )

    config = load_cascading_config(cli_config_path, global_config_path)

    assert config == ZembraConfig(
        cli_mode="direct",
        database_path=cli_database_path,
        workspace_id="550e8400-e29b-41d4-a716-446655440000",
        workspace_name="Work",
    )


def test_load_cascading_config_falls_back_to_global_config(tmp_path) -> None:
    """Verify the global config is used when CLI config is absent.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "global.sqlite3"
    global_config_path.write_text(
        f'[cli]\nmode = "direct"\n\n[database]\npath = "{database_path}"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigWorkspaceIdMissingError, match="Workspace ID is missing"):
        load_cascading_config(cli_config_path, global_config_path)


def test_load_cascading_config_merges_missing_database_path_from_global(tmp_path) -> None:
    """Verify direct mode can read database.path from global config.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "global.sqlite3"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        '[cli]\nmode = "direct"\n\n[workspace]\nid = "workspace-1"\n',
        encoding="utf-8",
    )
    global_config_path.write_text(
        f'[database]\npath = "{database_path}"\n',
        encoding="utf-8",
    )

    config = load_cascading_config(cli_config_path, global_config_path)

    assert config == ZembraConfig(
        cli_mode="direct",
        database_path=database_path,
        workspace_id="workspace-1",
    )


def test_load_cascading_config_does_not_merge_workspace_from_global(tmp_path) -> None:
    """Verify workspace config is read only from the CLI config file.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "global.sqlite3"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text('[cli]\nmode = "direct"\n', encoding="utf-8")
    global_config_path.write_text(
        f'[database]\npath = "{database_path}"\n\n[workspace]\nid = "global-workspace"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigWorkspaceIdMissingError, match="Workspace ID is missing"):
        load_cascading_config(cli_config_path, global_config_path)


def test_load_cascading_config_merges_missing_http_base_url_from_global(tmp_path) -> None:
    """Verify HTTP mode can read cli.http_base_url from global config.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        '[cli]\nmode = "http"\n\n[workspace]\nid = "550e8400-e29b-41d4-a716-446655440000"\n',
        encoding="utf-8",
    )
    global_config_path.write_text(
        '[cli]\nhttp_base_url = "http://global.test"\n',
        encoding="utf-8",
    )

    config = load_cascading_config(cli_config_path, global_config_path)

    assert config == ZembraConfig(
        cli_mode="http",
        http_base_url="http://global.test",
        workspace_id="550e8400-e29b-41d4-a716-446655440000",
    )


def test_load_cascading_config_derives_http_base_url_from_server(tmp_path) -> None:
    """Verify runtime config derives HTTP URL from configured backend server.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        f'[database]\npath = "{database_path}"\n\n'
        '[workspace]\nid = "550e8400-e29b-41d4-a716-446655440000"\n',
        encoding="utf-8",
    )
    global_config_path.write_text(
        '[server]\nhost = "127.0.0.1"\nport = 3000\n',
        encoding="utf-8",
    )

    config = load_cascading_config(cli_config_path, global_config_path)

    assert config == ZembraConfig(
        database_path=database_path,
        http_base_url="http://127.0.0.1:3000",
        workspace_id="550e8400-e29b-41d4-a716-446655440000",
    )


def test_load_cascading_config_reports_checked_paths(tmp_path) -> None:
    """Verify missing cascaded config reports both checked paths.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"

    with pytest.raises(ConfigFileMissingError) as error:
        load_cascading_config(cli_config_path, global_config_path)

    assert str(cli_config_path) in error.value.message
    assert str(global_config_path) in error.value.message


def test_load_cascading_config_reports_missing_file(tmp_path) -> None:
    """Verify missing config files raise a specific error.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"

    with pytest.raises(ConfigFileMissingError, match="Config file is missing"):
        load_cascading_config(config_path, tmp_path / "missing.env")


def test_load_cascading_config_reports_invalid_toml(tmp_path) -> None:
    """Verify invalid TOML raises a parse error.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text("[database\n", encoding="utf-8")

    with pytest.raises(ConfigParseError, match="not valid TOML"):
        load_cascading_config(config_path, tmp_path / "missing.env")


def test_load_cascading_config_accepts_missing_cli_mode(tmp_path) -> None:
    """Verify configs without cli.mode are accepted.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(
        '[database]\npath = "zembra.sqlite3"\n\n[workspace]\nid = "workspace-1"\n',
        encoding="utf-8",
    )

    config = load_cascading_config(config_path, tmp_path / "missing.env")

    assert config.cli_mode is None
    assert config.database_path == Path("zembra.sqlite3")
    assert config.workspace_id == "workspace-1"


def test_load_cascading_config_reports_invalid_cli_mode(tmp_path) -> None:
    """Verify unsupported cli.mode values are rejected.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text('[cli]\nmode = "sqlite"\n', encoding="utf-8")

    with pytest.raises(ConfigCliModeInvalidError, match="direct"):
        load_cascading_config(config_path, tmp_path / "missing.env")


def test_load_cascading_config_reports_missing_http_base_url(tmp_path) -> None:
    """Verify HTTP mode requires cli.http_base_url.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text('[cli]\nmode = "http"\n', encoding="utf-8")

    with pytest.raises(ConfigHttpBaseUrlMissingError, match="HTTP backend URL is missing"):
        load_cascading_config(config_path, tmp_path / "missing.env")


def test_load_cascading_config_reports_missing_http_workspace_id(tmp_path) -> None:
    """Verify HTTP mode requires workspace.id.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text(
        '[cli]\nmode = "http"\nhttp_base_url = "http://127.0.0.1:3000"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigWorkspaceIdMissingError, match="Workspace ID is missing"):
        load_cascading_config(config_path, tmp_path / "missing.env")


def test_load_cascading_config_reports_missing_direct_database_path(tmp_path) -> None:
    """Verify direct mode requires database.path.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text('[cli]\nmode = "direct"\n', encoding="utf-8")

    with pytest.raises(ConfigDatabasePathMissingError, match="Database path is missing"):
        load_cascading_config(config_path, tmp_path / "missing.env")


def test_write_database_path_creates_config(tmp_path) -> None:
    """Verify database path writing creates a readable config file.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"

    config = write_database_path(database_path, config_path)

    assert config.database_path == database_path
    assert config_path.read_text(encoding="utf-8") == (
        "[database]\n"
        f'path = "{database_path}"\n'
    )


def test_write_database_path_updates_config_and_preserves_fields(tmp_path) -> None:
    """Verify database path writing preserves existing future config fields.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    old_database_path = tmp_path / "old.sqlite3"
    new_database_path = tmp_path / "new.sqlite3"
    config_path.write_text(
        "\n".join(
            [
                'theme = "light"',
                "",
                "[database]",
                f'path = "{old_database_path}"',
                'mode = "local"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = write_database_path(new_database_path, config_path)

    assert config.database_path == new_database_path
    config_text = config_path.read_text(encoding="utf-8")
    assert 'theme = "light"' in config_text
    assert 'mode = "local"' in config_text
    assert f'path = "{new_database_path}"' in config_text


def test_write_database_path_can_set_direct_mode(tmp_path) -> None:
    """Verify callers can explicitly write CLI direct mode.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"

    write_database_path(database_path, config_path, set_direct_mode=True)

    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + '\n[workspace]\nid = "550e8400-e29b-41d4-a716-446655440000"\n',
        encoding="utf-8",
    )

    config = load_cascading_config(config_path, tmp_path / "missing.env")
    assert config == ZembraConfig(
        cli_mode="direct",
        database_path=database_path,
        workspace_id="550e8400-e29b-41d4-a716-446655440000",
    )


def test_write_database_path_reports_missing_parent(tmp_path) -> None:
    """Verify config writing does not create absent parent directories.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / "missing" / ".zembra.env"

    with pytest.raises(ConfigParentMissingError, match="does not exist"):
        write_database_path(tmp_path / "zembra.sqlite3", config_path)


def test_load_workspace_command_config_allows_missing_workspace_id(tmp_path) -> None:
    """Verify workspace commands can load the backend URL before a default workspace exists.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        '[cli]\nhttp_base_url = "http://backend.test"\n',
        encoding="utf-8",
    )

    config = load_workspace_command_config(cli_config_path, global_config_path)

    assert config.http_base_url == "http://backend.test"
    assert config.workspace_id is None
    assert config.workspace_name is None


def test_load_workspace_command_config_requires_http_base_url(tmp_path) -> None:
    """Verify workspace commands do not assume a default backend URL.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        f'[database]\npath = "{tmp_path / "zembra.sqlite3"}"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigHttpBaseUrlMissingError, match="HTTP backend URL is missing"):
        load_workspace_command_config(cli_config_path, global_config_path)


def test_load_workspace_command_config_reads_global_server_url(tmp_path) -> None:
    """Verify workspace commands can derive the backend URL from global server config.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        '[workspace]\nid = "workspace-1"\n',
        encoding="utf-8",
    )
    global_config_path.write_text(
        '[server]\nhost = "127.0.0.1"\nport = 3000\n',
        encoding="utf-8",
    )

    config = load_workspace_command_config(cli_config_path, global_config_path)

    assert config.http_base_url == "http://127.0.0.1:3000"
    assert config.workspace_id == "workspace-1"


def test_load_workspace_command_config_prefers_cli_http_base_url_over_server(
    tmp_path,
) -> None:
    """Verify explicit CLI backend URLs override server host and port config.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    cli_config_path = tmp_path / ".zembra" / "config.cli.toml"
    global_config_path = tmp_path / ".zembra.env"
    cli_config_path.parent.mkdir()
    cli_config_path.write_text(
        '[cli]\nhttp_base_url = "http://cli.test"\n',
        encoding="utf-8",
    )
    global_config_path.write_text(
        '[server]\nhost = "127.0.0.1"\nport = 3000\n',
        encoding="utf-8",
    )

    config = load_workspace_command_config(cli_config_path, global_config_path)

    assert config.http_base_url == "http://cli.test"


def test_write_default_workspace_updates_workspace_and_preserves_config(tmp_path) -> None:
    """Verify default workspace writing preserves unrelated config fields.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra" / "config.cli.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        '[cli]\nhttp_base_url = "http://backend.test"\n\n'
        '[database]\npath = "zembra.sqlite3"\n\n'
        '[workspace]\nid = "old-workspace"\nname = "Old"\n',
        encoding="utf-8",
    )

    config = write_default_workspace("new-workspace", "New", config_path)

    assert config.workspace_id == "new-workspace"
    assert config.workspace_name == "New"
    config_text = config_path.read_text(encoding="utf-8")
    assert 'http_base_url = "http://backend.test"' in config_text
    assert 'path = "zembra.sqlite3"' in config_text
    assert 'id = "new-workspace"' in config_text
    assert 'name = "New"' in config_text


def test_write_default_workspace_removes_name_when_backend_name_is_null(tmp_path) -> None:
    """Verify null backend workspace names remove stale CLI display names.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra" / "config.cli.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        '[workspace]\nid = "old-workspace"\nname = "Old"\n',
        encoding="utf-8",
    )

    config = write_default_workspace("new-workspace", None, config_path)

    assert config.workspace_id == "new-workspace"
    assert config.workspace_name is None
    config_text = config_path.read_text(encoding="utf-8")
    assert 'id = "new-workspace"' in config_text
    assert "name =" not in config_text
