# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Interactive REPL for Fabric CLI v2.

Provides a ``prompt_toolkit``-based interactive shell with:
 - Context-aware prompt (``fab:/workspace$``)
 - Command history (in-memory)
 - Graceful Ctrl+C / Ctrl+D handling
 - Delegates commands to the Typer app
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def start_repl() -> None:
    """Launch the interactive REPL loop."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML

    from fabric_cli_v2.context import Context
    from fabric_cli_v2 import output

    ctx = Context.get()
    ctx.load()  # restore persisted context

    session: PromptSession[str] = PromptSession()
    output.print_info(f"Fabric CLI v2 interactive mode. Type 'help' or 'exit'.")

    while True:
        try:
            path_display = ctx.path
            prompt_text = HTML(f"<b>fab</b>:<ansiblue>{path_display}</ansiblue>$ ")
            line = session.prompt(prompt_text).strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if not line:
            continue

        lower = line.lower()
        if lower in ("exit", "quit"):
            break
        if lower in ("help", "?"):
            _print_help()
            continue

        _run_command(line)


def _run_command(line: str) -> None:
    """Parse and execute a single command line in the REPL."""
    from fabric_cli_v2.app import app
    from fabric_cli_v2 import output

    try:
        args = shlex.split(line)
    except ValueError as exc:
        output.print_error(f"Invalid input: {exc}")
        return

    try:
        # Typer/Click apps can be invoked programmatically
        app(args, standalone_mode=False)
    except SystemExit:
        pass  # Typer raises SystemExit on --help, etc.
    except Exception as exc:
        output.print_error(str(exc))


def _print_help() -> None:
    """Minimal help for interactive mode."""
    from fabric_cli_v2 import output

    output.print_info(
        "Commands:  ls, cd, mkdir, rm, get, set, auth, config, version\n"
        "  Type '<command> --help' for details.\n"
        "  exit / quit — leave interactive mode"
    )
