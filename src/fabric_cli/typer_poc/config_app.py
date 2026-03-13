# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Typer-based config command group — Proof of Concept.

This module demonstrates how the existing argparse-based `config` command group
can be rewritten using Typer. It preserves full compatibility with the existing
exec_command(args) implementations through the TyperArgs compatibility layer.

Comparison with current implementation (fab_config_parser.py):
  - argparse version: ~100 lines of parser registration code
  - Typer version: ~70 lines with richer help output

Usage (standalone PoC):
    python -m fabric_cli.typer_poc.config_app set mode command_line
    python -m fabric_cli.typer_poc.config_app get mode
    python -m fabric_cli.typer_poc.config_app ls
    python -m fabric_cli.typer_poc.config_app clear-cache
"""

from typing import Callable, Optional

import typer

from fabric_cli.typer_poc.typer_args import TyperArgs

# --- Typer App Definition ---

config_app = typer.Typer(
    name="config",
    help="Manage Fabric CLI configuration settings.",
    no_args_is_help=True,
)


# --- Helper ---


def _run_command(exec_fn: Callable, args: TyperArgs) -> None:
    """Run an exec_command function with standard decorators applied.

    Wraps the given function with handle_exceptions and set_command_context
    decorators, then invokes it with the provided TyperArgs.
    """
    from fabric_cli.core.fab_decorators import handle_exceptions, set_command_context

    @handle_exceptions()
    @set_command_context()
    def _run(a):
        exec_fn(a)

    _run(args)


# --- Commands ---


@config_app.command(
    epilog=(
        "Examples:\n"
        "  # switch to command line mode\n"
        "  $ config set mode command_line\n\n"
        "  # set default capacity\n"
        "  $ config set default_capacity Trial-0000\n\n"
        "Learn more:\n"
        "  For more usage examples, see https://aka.ms/fabric-cli"
    ),
)
def set(
    key: str = typer.Argument(help="Configuration key to set."),
    value: str = typer.Argument(help="Value to assign to the configuration key."),
    output_format: Optional[str] = typer.Option(
        None,
        "--output_format",
        help="Override output format type.",
        show_default=False,
    ),
) -> None:
    """Set a configuration key to a specified value."""
    from fabric_cli.commands.config import fab_config_set as config_set

    args = TyperArgs(
        command="config", subcommand="set", output_format=output_format,
        key=key, value=value,
    )
    _run_command(config_set.exec_command, args)


@config_app.command(
    epilog=(
        "Examples:\n"
        "  # get current CLI mode\n"
        "  $ config get mode\n\n"
        "  # get default capacity\n"
        "  $ config get default_capacity\n\n"
        "Learn more:\n"
        "  For more usage examples, see https://aka.ms/fabric-cli"
    ),
)
def get(
    key: str = typer.Argument(help="Configuration key to retrieve."),
    output_format: Optional[str] = typer.Option(
        None,
        "--output_format",
        help="Override output format type.",
        show_default=False,
    ),
) -> None:
    """Get the value of a configuration key."""
    from fabric_cli.commands.config import fab_config_get as config_get

    args = TyperArgs(
        command="config", subcommand="get", output_format=output_format, key=key,
    )
    _run_command(config_get.exec_command, args)


@config_app.command(
    name="ls",
    epilog=(
        "Examples:\n"
        "  # print configuration values\n"
        "  $ config ls\n\n"
        "Learn more:\n"
        "  For more usage examples, see https://aka.ms/fabric-cli"
    ),
)
def list_configs(
    output_format: Optional[str] = typer.Option(
        None,
        "--output_format",
        help="Override output format type.",
        show_default=False,
    ),
) -> None:
    """List all configuration keys and their values."""
    from fabric_cli.commands.config import fab_config_ls as config_ls

    args = TyperArgs(
        command="config", subcommand="ls", output_format=output_format,
    )
    _run_command(config_ls.exec_command, args)


@config_app.command(
    name="clear-cache",
    epilog=(
        "Examples:\n"
        "  # clear CLI cache\n"
        "  $ config clear-cache\n\n"
        "Learn more:\n"
        "  For more usage examples, see https://aka.ms/fabric-cli"
    ),
)
def clear_cache(
    output_format: Optional[str] = typer.Option(
        None,
        "--output_format",
        help="Override output format type.",
        show_default=False,
    ),
) -> None:
    """Clear the CLI cache."""
    from fabric_cli.commands.config import fab_config_clear_cache as config_clear_cache

    args = TyperArgs(
        command="config", subcommand="clear-cache", output_format=output_format,
    )
    _run_command(config_clear_cache.exec_command, args)


# --- Main App (for standalone PoC execution) ---

# This demonstrates how config_app would be added to the main Fabric CLI app:
#   main_app = typer.Typer()
#   main_app.add_typer(config_app, name="config")

if __name__ == "__main__":
    config_app()
