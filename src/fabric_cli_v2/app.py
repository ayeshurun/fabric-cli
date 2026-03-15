# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Fabric CLI v2 — Typer application definition.

This is the main entry point.  All command groups are registered here
using lazy imports so that startup stays fast (< 100 ms target).

Entry point (from pyproject.toml):  ``fab2 = "fabric_cli_v2.app:main"``
"""

from __future__ import annotations

from typing import Optional

import typer
from typing import Annotated

# ---------------------------------------------------------------------------
# App definition
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="fab",
    help="Fabric CLI — a fast, file-system-inspired CLI for Microsoft Fabric.",
    no_args_is_help=False,  # we launch REPL when no args
    add_completion=True,
    rich_markup_mode="markdown",
    pretty_exceptions_enable=False,
)


# ---------------------------------------------------------------------------
# Callback: handle global flags and REPL launch
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def _root_callback(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", "-v", help="Show version and exit.")
    ] = False,
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format: text | json."),
    ] = None,
) -> None:
    """Root callback — enters REPL when invoked without a sub-command."""
    if version:
        from fabric_cli_v2 import __version__

        typer.echo(f"fab {__version__}")
        raise typer.Exit()

    # Stash output format in typer context for sub-commands
    ctx.ensure_object(dict)
    if output_format:
        ctx.obj["output_format"] = output_format

    if ctx.invoked_subcommand is None:
        # No sub-command → interactive REPL
        from fabric_cli_v2.repl import start_repl

        start_repl()


# ---------------------------------------------------------------------------
# Register command groups (lazy imports for speed)
# ---------------------------------------------------------------------------

def _register_commands() -> None:
    """Import and register all command modules."""
    from fabric_cli_v2.commands.fs import fs_app
    from fabric_cli_v2.commands.auth_cmds import auth_app
    from fabric_cli_v2.commands.config_cmds import config_app

    # fs commands are top-level (ls, cd, mkdir, rm, …)
    # Register each fs sub-command directly on the root app
    for cmd_info in fs_app.registered_commands:
        app.command(cmd_info.name)(cmd_info.callback)

    app.add_typer(auth_app)
    app.add_typer(config_app)


# Deferred registration via a simple flag
_commands_registered = False


def _ensure_commands() -> None:
    global _commands_registered
    if not _commands_registered:
        _register_commands()
        _commands_registered = True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point invoked by ``fab2`` console script."""
    _ensure_commands()
    try:
        app()
    except KeyboardInterrupt:
        from fabric_cli_v2 import output
        output.print_warning("Interrupted")
        raise typer.Exit(code=2)
    except RuntimeError as exc:
        from fabric_cli_v2 import output
        output.print_error(str(exc))
        raise typer.Exit(code=1)
