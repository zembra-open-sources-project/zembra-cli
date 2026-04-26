"""Tests for zembra configuration file handling."""

from pathlib import Path

import pytest

from zembra_cli.config import (
    ConfigDatabasePathMissingError,
    ConfigFileMissingError,
    ConfigParentMissingError,
    ConfigParseError,
    ZembraConfig,
    default_config_path,
    load_config,
    write_database_path,
)


def test_default_config_path_uses_zembra_env(monkeypatch, tmp_path) -> None:
    """Verify the default config path uses the zembra system file name.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert default_config_path() == tmp_path / ".zembra.env"


def test_load_config_reads_database_path(tmp_path) -> None:
    """Verify a valid TOML config loads the database path.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    database_path = tmp_path / "zembra.sqlite3"
    config_path.write_text(f'[database]\npath = "{database_path}"\n', encoding="utf-8")

    config = load_config(config_path)

    assert config == ZembraConfig(database_path=database_path)


def test_load_config_reports_missing_file(tmp_path) -> None:
    """Verify missing config files raise a specific error.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"

    with pytest.raises(ConfigFileMissingError, match="Config file is missing"):
        load_config(config_path)


def test_load_config_reports_invalid_toml(tmp_path) -> None:
    """Verify invalid TOML raises a parse error.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text("[database\n", encoding="utf-8")

    with pytest.raises(ConfigParseError, match="not valid TOML"):
        load_config(config_path)


def test_load_config_reports_missing_database_path(tmp_path) -> None:
    """Verify configs without database.path are rejected.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    config_path = tmp_path / ".zembra.env"
    config_path.write_text("[database]\n", encoding="utf-8")

    with pytest.raises(ConfigDatabasePathMissingError, match="Database path is missing"):
        load_config(config_path)


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
    assert load_config(config_path).database_path == database_path
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
