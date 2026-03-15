# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""File-system commands: ls, cd, mkdir, rm, pwd.

Registered as top-level commands on the main ``app`` for UX consistency
(``fab ls`` instead of ``fab fs ls``).
"""

from __future__ import annotations

from typing import Optional

import typer
from typing import Annotated

# ---------------------------------------------------------------------------
# Command group (used internally for registration)
# ---------------------------------------------------------------------------

fs_app = typer.Typer(name="fs", hidden=True)


# ---------------------------------------------------------------------------
# ls
# ---------------------------------------------------------------------------


@fs_app.command("ls")
def ls_command(
    path: Annotated[
        Optional[str], typer.Argument(help="Path to list (default: current context).")
    ] = None,
    long: Annotated[
        bool, typer.Option("--long", "-l", help="Detailed output.")
    ] = False,
    all_items: Annotated[
        bool, typer.Option("--all", "-a", help="Include hidden collections.")
    ] = False,
    query: Annotated[
        Optional[str],
        typer.Option("--query", "-q", help="JMESPath filter."),
    ] = None,
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format: text | json."),
    ] = None,
) -> None:
    """List workspaces, items, or OneLake contents."""
    from fabric_cli_v2 import client, output
    from fabric_cli_v2.context import Context

    fmt = output_format or "text"
    ctx = Context.get()

    # Determine what to list based on path / current context
    if path is None and ctx.current is None:
        # Root → list workspaces
        data = client.request("GET", "workspaces", paginate=True)
        items = data.get("value", [])
        if query:
            items = _jmespath_filter(items, query)
        output.print_items(items, long=long, output_format=fmt,
                           columns=["displayName", "id", "type"] if long else None)
        return

    # TODO: resolve path relative to context, list items/folders/onelake
    output.print_info(f"ls {path or ctx.path} — path resolution not yet implemented")


# ---------------------------------------------------------------------------
# cd
# ---------------------------------------------------------------------------


@fs_app.command("cd")
def cd_command(
    path: Annotated[
        Optional[str], typer.Argument(help="Target path (absolute or relative).")
    ] = None,
) -> None:
    """Change the current context (working directory)."""
    from fabric_cli_v2.context import Context
    from fabric_cli_v2 import output

    ctx = Context.get()
    if path is None or path in ("/", "~"):
        ctx.reset()
        ctx.save()
        output.print_info(f"Context: /")
        return

    # TODO: full path resolution
    output.print_info(f"cd {path} — path resolution not yet implemented")


# ---------------------------------------------------------------------------
# mkdir
# ---------------------------------------------------------------------------


@fs_app.command("mkdir")
def mkdir_command(
    path: Annotated[str, typer.Argument(help="Path of the resource to create.")],
    params: Annotated[
        Optional[list[str]],
        typer.Option("--params", "-P", help="Key=value parameters."),
    ] = None,
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format."),
    ] = None,
) -> None:
    """Create a workspace, item, or OneLake directory."""
    from fabric_cli_v2 import output as out

    # TODO: implement creation logic
    out.print_info(f"mkdir {path} — not yet implemented")


# ---------------------------------------------------------------------------
# rm
# ---------------------------------------------------------------------------


@fs_app.command("rm")
def rm_command(
    path: Annotated[str, typer.Argument(help="Path of the resource to delete.")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation.")
    ] = False,
) -> None:
    """Remove a workspace, item, or OneLake resource."""
    from fabric_cli_v2 import output as out

    # TODO: implement deletion logic
    out.print_info(f"rm {path} — not yet implemented")


# ---------------------------------------------------------------------------
# pwd
# ---------------------------------------------------------------------------


@fs_app.command("pwd")
def pwd_command() -> None:
    """Print the current context path."""
    from fabric_cli_v2.context import Context

    print(Context.get().path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jmespath_filter(items: list, expression: str) -> list:
    """Apply a JMESPath expression to a list of items."""
    try:
        import jmespath

        return jmespath.search(expression, items) or []
    except Exception:
        return items
