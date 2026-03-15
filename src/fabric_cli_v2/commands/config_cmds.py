# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Configuration commands: get, set, ls, clear-cache."""

from __future__ import annotations

from typing import Optional

import typer
from typing import Annotated

config_app = typer.Typer(
    name="config",
    help="View and manage Fabric CLI settings.",
    no_args_is_help=True,
)


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Configuration key.")],
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format."),
    ] = None,
) -> None:
    """Get a configuration value."""
    from fabric_cli_v2 import config, output

    value = config.get(key)
    if value is None:
        output.print_warning(f"Key '{key}' is not set")
    elif (output_format or "text") == "json":
        output.print_json({key: value})
    else:
        print(f"{key} = {value}")


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key.")],
    value: Annotated[str, typer.Argument(help="Value to assign.")],
) -> None:
    """Set a configuration value."""
    from fabric_cli_v2 import config, output

    # Validate
    valid = config.VALID_VALUES.get(key)
    if valid and value not in valid:
        output.print_error(f"Invalid value '{value}' for '{key}'. Valid: {', '.join(valid)}")
        raise typer.Exit(code=1)

    config.set_value(key, value)
    output.print_success(f"{key} = {value}")


@config_app.command("ls")
def config_ls(
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format."),
    ] = None,
) -> None:
    """List all configuration settings."""
    from fabric_cli_v2 import config, output

    data = config.read_all()
    if (output_format or "text") == "json":
        output.print_json(data)
    else:
        for k, v in sorted(data.items()):
            print(f"  {k} = {v}")


@config_app.command("clear-cache")
def config_clear_cache() -> None:
    """Clear the local cache."""
    from fabric_cli_v2 import config, output

    config.invalidate_cache()
    output.print_success("Cache cleared")
