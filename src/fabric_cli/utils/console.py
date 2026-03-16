# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Centralized rich console utilities for consistent CLI output.

This module provides a shared Console instance and helper functions
so the entire CLI uses consistent styling and formatting.
"""

import sys
from typing import Any, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Consistent color theme for the CLI
FAB_THEME = Theme(
    {
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "cyan",
        "fabric": "#49C5B1",
        "muted": "grey62",
        "header": "bold cyan",
    }
)

# Shared console instances — stdout and stderr
console = Console(theme=FAB_THEME, highlight=False)
console_err = Console(theme=FAB_THEME, stderr=True, highlight=False)


def print_success(message: str, *, to_stderr: bool = False) -> None:
    """Print a success message with a green checkmark."""
    target = console_err if to_stderr else console
    target.print(f"[success]✔[/success] {message}")


def print_error(message: str, *, to_stderr: bool = True) -> None:
    """Print an error message with a red cross."""
    target = console_err if to_stderr else console
    target.print(f"[error]✘[/error] {message}")


def print_warning(message: str, *, to_stderr: bool = True) -> None:
    """Print a warning message with a yellow exclamation mark."""
    target = console_err if to_stderr else console
    target.print(f"[warning]![/warning] {message}")


def print_info(message: str, *, to_stderr: bool = True) -> None:
    """Print an informational message with a cyan bullet."""
    target = console_err if to_stderr else console
    target.print(f"[info]ℹ[/info] {message}")


def print_muted(message: str, *, to_stderr: bool = False) -> None:
    """Print a muted/grey message."""
    target = console_err if to_stderr else console
    target.print(f"[muted]{message}[/muted]")


def print_fabric(message: str) -> None:
    """Print a message in the Fabric brand colour."""
    console.print(f"[fabric]{message}[/fabric]")


def print_plain(message: str, *, to_stderr: bool = False) -> None:
    """Print a plain message with no extra styling."""
    target = console_err if to_stderr else console
    target.print(message)


def print_error_panel(
    title: str,
    *,
    reason: Optional[str] = None,
    suggestion: Optional[str] = None,
    error_code: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """Print a rich Panel summarising an error."""
    parts: list[str] = []
    if reason:
        parts.append(f"[bold]Reason:[/bold]\n  {reason}")
    if suggestion:
        parts.append(f"[bold]Suggested action:[/bold]\n  {suggestion}")
    if error_code:
        parts.append(f"[muted]Error code:[/muted] {error_code}")
    if request_id:
        parts.append(f"[muted]Request ID:[/muted] {request_id}")

    body = "\n\n".join(parts) if parts else title
    console_err.print(
        Panel(body, title=f"[error]✘ {title}[/error]", border_style="red")
    )


def print_table(
    rows: Sequence[dict[str, Any]],
    columns: Optional[Sequence[str]] = None,
    *,
    title: Optional[str] = None,
    show_header: bool = True,
) -> None:
    """Print structured data as a rich Table."""
    if not rows:
        return
    if columns is None:
        columns = list(rows[0].keys()) if isinstance(rows[0], dict) else []
    table = Table(title=title, show_header=show_header, highlight=False)
    for col in columns:
        table.add_column(col)
    for row in rows:
        if isinstance(row, dict):
            table.add_row(*(str(row.get(c, "")) for c in columns))
        else:
            table.add_row(str(row))
    console.print(table)


def print_file_written(path: str, *, overwritten: bool = False) -> None:
    """Inform the user that a file was written successfully."""
    if overwritten:
        print_warning(f"File overwritten: {path}")
    print_success("File written")
    console.print()
    print_muted(f"  Path: {path}")
