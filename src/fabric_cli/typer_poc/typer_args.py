# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Compatibility layer for migrating from argparse to Typer.

During the migration, existing command implementations expect an
argparse.Namespace-like object (accessed as `args.key`, `args.value`, etc.).
TyperArgs provides this interface so that Typer commands can call existing
exec_command(args) functions without modification.
"""

from argparse import Namespace
from typing import Optional


class TyperArgs(Namespace):
    """Compatibility layer: converts Typer parameters into an argparse.Namespace.

    This class bridges Typer commands with existing exec_command(args) functions.
    It sets the required attributes (command, subcommand, output_format, command_path,
    fab_mode) alongside any command-specific parameters.

    Usage in a Typer command:
        args = TyperArgs(
            command="config",
            subcommand="set",
            key="mode",
            value="command_line",
        )
        config_set.exec_command(args)
    """

    def __init__(
        self,
        command: str = "",
        subcommand: str = "",
        output_format: Optional[str] = None,
        **kwargs,
    ):
        super().__init__()
        self.command = command
        # Set the <command>_subcommand attribute used by print_output_format
        setattr(self, f"{command}_subcommand", subcommand)
        self.output_format = output_format
        self.command_path = f"{command} {subcommand}".strip()
        self.fab_mode = "command_line"

        # Set all additional command-specific parameters
        for key, value in kwargs.items():
            setattr(self, key, value)
