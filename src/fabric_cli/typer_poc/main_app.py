# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Typer-based main app skeleton — Proof of Concept.

This module demonstrates how the main Fabric CLI entry point would look
after migration from argparse to Typer. It shows the composition pattern
where command groups (config, auth, etc.) are added as sub-apps.

This PoC only wires the config command group. The remaining groups
would be added in subsequent migration phases.

Usage (standalone PoC):
    python -m fabric_cli.typer_poc.main_app config set mode command_line
    python -m fabric_cli.typer_poc.main_app config get mode
    python -m fabric_cli.typer_poc.main_app --version
"""

from typing import Optional

import typer

from fabric_cli.typer_poc.config_app import config_app


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from fabric_cli.utils import fab_ui

        fab_ui.print_version()
        raise typer.Exit()


# --- Main App ---

app = typer.Typer(
    name="fab",
    help="Command-line tool for Microsoft Fabric.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
    epilog=(
        "Learn more:\n"
        "  For usage examples, see https://aka.ms/fabric-cli"
    ),
)

# --- Global Options ---
# These are handled via a callback on the main app


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Print CLI version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Command-line tool for Microsoft Fabric."""
    # If no subcommand is provided, enter interactive mode
    if ctx.invoked_subcommand is None:
        pass  # In production: start_interactive_mode()


# --- Register Command Groups ---
# Phase 0 (PoC): Only config is wired
app.add_typer(config_app, name="config")

# Phase 2 (future): Each group is added similarly:
# app.add_typer(auth_app, name="auth")
# app.add_typer(jobs_app, name="job")
# app.add_typer(acls_app, name="acl")
# app.add_typer(labels_app, name="label")
# app.add_typer(tables_app, name="table")

# Phase 2 (future): Top-level commands (ls, mkdir, etc.) are added directly:
# @app.command()
# def ls(path: Optional[str] = typer.Argument(None), ...):
#     ...


if __name__ == "__main__":
    app()
