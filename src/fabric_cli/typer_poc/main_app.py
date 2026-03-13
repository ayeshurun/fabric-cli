# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Typer PoC — Main CLI application.

Demonstrates how the top-level ``fab`` CLI and its command groups would
look when built with typer instead of argparse.  This is a *proof of
concept* — it does not replace the production argparse-based CLI.

Run the PoC (requires ``typer`` installed):

    python -m fabric_cli.typer_poc.main_app --help
    python -m fabric_cli.typer_poc.main_app ls --help
    python -m fabric_cli.typer_poc.main_app config get output_format
"""

from __future__ import annotations

from typing import Optional

try:
    import typer
    from typing import Annotated
except ImportError:
    raise SystemExit(
        "typer is not installed.  Install it with:  pip install typer\n"
        "This PoC is for evaluation only and is not required for production use."
    )

from fabric_cli.typer_poc.config_app import config_app
from fabric_cli.typer_poc.typer_args import TyperArgs

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
main_app = typer.Typer(
    name="fab",
    help="Fabric CLI — a file-system-inspired CLI for Microsoft Fabric.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="markdown",
)

# Register command groups
if config_app is not None:
    main_app.add_typer(config_app)


# ---------------------------------------------------------------------------
# fs commands — shown as top-level verbs (same UX as current CLI)
# ---------------------------------------------------------------------------


@main_app.command("ls", help="List items in the current context or at a given path.")
def ls_command(
    path: Annotated[
        Optional[str], typer.Argument(help="Directory path")
    ] = None,
    long: Annotated[
        bool, typer.Option("--long", "-l", help="Show detailed output")
    ] = False,
    all_items: Annotated[
        bool, typer.Option("--all", "-a", help="Show all items including hidden")
    ] = False,
    query: Annotated[
        Optional[str],
        typer.Option("--query", "-q", help="JMESPath query to filter output"),
    ] = None,
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format: text, json"),
    ] = None,
) -> None:
    """List items — delegates to existing ``fs.ls_command`` via TyperArgs bridge.

    Note: The original argparse ``ls`` command uses ``nargs="*"`` for path,
    producing a list.  The TyperArgs bridge preserves this as a list.
    """
    args = TyperArgs(
        command="ls",
        path=[path] if path else None,
        long=long,
        all=all_items,
        query=query,
        output_format=output_format,
    )
    # In production this would call:
    #   from fabric_cli.commands.fs import fab_fs as fs
    #   fs.ls_command(args)
    typer.echo(f"[PoC] ls path={args.path} long={args.long} all={args.all}")


@main_app.command("mkdir", help="Create a workspace, item, or directory.")
def mkdir_command(
    path: Annotated[str, typer.Argument(help="Path of the resource to create")],
    params: Annotated[
        Optional[list[str]],
        typer.Option(
            "--params",
            "-P",
            help="Custom parameters as key=value pairs",
        ),
    ] = None,
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format: text, json"),
    ] = None,
) -> None:
    """Create — delegates to existing ``fs.mkdir_command`` via TyperArgs bridge.

    Note: The original argparse ``mkdir`` command uses ``nargs="+"`` for path,
    producing a list.  The TyperArgs bridge preserves this as a list.
    """
    args = TyperArgs(
        command="mkdir",
        path=[path],
        params=params or [],
        output_format=output_format,
    )
    typer.echo(f"[PoC] mkdir path={args.path} params={args.params}")


@main_app.command("cd", help="Change the current context to a different path.")
def cd_command(
    path: Annotated[
        Optional[str], typer.Argument(help="Target path")
    ] = None,
) -> None:
    """Change directory — delegates to existing handler."""
    args = TyperArgs(command="cd", path=path)
    typer.echo(f"[PoC] cd path={args.path}")


@main_app.command("version", help="Show Fabric CLI version.")
def version_command() -> None:
    """Print the version and exit."""
    from fabric_cli import __version__

    typer.echo(f"fab version {__version__}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _main() -> None:
    main_app()


if __name__ == "__main__":
    _main()
