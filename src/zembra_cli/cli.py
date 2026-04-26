"""Command-line entry points for zembra-cli."""

from typing import Annotated

import typer
from rich.console import Console

from zembra_cli import __version__

app = typer.Typer(
    name="zembra-cli",
    help="A calm command-line workspace for notes.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print the application version and exit when requested.

    Args:
        value: Whether the version flag was provided.

    Returns:
        None. The process exits after printing the version.
    """
    if value:
        console.print(f"zembra-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            help="Show the installed zembra-cli version.",
        ),
    ] = None,
) -> None:
    """Configure global CLI options.

    Args:
        version: Optional flag that prints the package version.

    Returns:
        None.
    """


@app.command()
def hello(
    name: Annotated[
        str,
        typer.Argument(help="Name to greet while the note commands are being built."),
    ] = "there",
) -> None:
    """Print a friendly smoke-test message.

    Args:
        name: Name included in the greeting.

    Returns:
        None.
    """
    console.print(f"Hello, {name}. Zembra is ready.")
