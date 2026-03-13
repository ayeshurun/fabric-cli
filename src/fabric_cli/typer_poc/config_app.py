# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Typer PoC — Config command group.

Demonstrates how `config get`, `config set`, and `config ls` commands
look when implemented with typer instead of argparse.
"""

from __future__ import annotations

from typing import Optional

try:
    import typer
    from typing import Annotated
except ImportError:
    typer = None  # type: ignore[assignment]

if typer is not None:
    config_app = typer.Typer(
        name="config",
        help="View and manage Fabric CLI settings.",
        no_args_is_help=True,
    )

    @config_app.command("get")
    def config_get(
        key: Annotated[
            str,
            typer.Argument(help="Configuration key to retrieve"),
        ],
    ) -> None:
        """Get the value of a configuration setting."""
        from fabric_cli.typer_poc.typer_args import TyperArgs

        args = TyperArgs(command="config", config_command="get", key=key)
        # Delegate to existing handler:
        # from fabric_cli.commands.config.fab_config_commands import config_get_command
        # config_get_command(args)
        typer.echo(f"[PoC] config get {args.key}")

    @config_app.command("set")
    def config_set(
        key: Annotated[
            str,
            typer.Argument(help="Configuration key to set"),
        ],
        value: Annotated[
            str,
            typer.Argument(help="Value to assign"),
        ],
    ) -> None:
        """Set a configuration value."""
        from fabric_cli.typer_poc.typer_args import TyperArgs

        args = TyperArgs(command="config", config_command="set", key=key, value=value)
        typer.echo(f"[PoC] config set {args.key}={args.value}")

    @config_app.command("ls")
    def config_ls() -> None:
        """List all configuration settings."""
        from fabric_cli.typer_poc.typer_args import TyperArgs

        args = TyperArgs(command="config", config_command="ls")
        typer.echo(f"[PoC] config ls (command={args.command})")

    @config_app.command("clear-cache")
    def config_clear_cache() -> None:
        """Clear the local cache."""
        from fabric_cli.typer_poc.typer_args import TyperArgs

        args = TyperArgs(command="config", config_command="clear-cache")
        typer.echo(f"[PoC] config clear-cache (command={args.command})")
else:
    config_app = None  # type: ignore[assignment]
