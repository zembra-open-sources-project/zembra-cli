"""Tests for the zembra-cli command-line interface."""

from typer.testing import CliRunner

from zembra_cli import __version__
from zembra_cli.cli import app

runner = CliRunner()


def test_version_flag_prints_package_version() -> None:
    """Verify the CLI exposes the installed package version.

    Args:
        None.

    Returns:
        None.
    """
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"zembra-cli {__version__}" in result.stdout


def test_hello_command_prints_greeting() -> None:
    """Verify the placeholder command can be invoked through Typer.

    Args:
        None.

    Returns:
        None.
    """
    result = runner.invoke(app, ["hello", "Ada"])

    assert result.exit_code == 0
    assert "Hello, Ada. Zembra is ready." in result.stdout
