# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Public output helpers for the Fabric CLI.

Every function in this module delegates to
:class:`~fabric_cli.utils.fab_output_manager.OutputManager`.  The
module-level API is preserved so that the 300+ existing call sites
(``fab_ui.print_warning(…)``, ``utils_ui.print_output_format(…)``, etc.)
continue to work without any changes.
"""

from argparse import Namespace
from typing import Any, Optional, Sequence

from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.utils.fab_output_manager import (
    OutputManager,
    _format_key_to_title_case,
    _check_special_cases,
    get_visual_length,
    output_manager,
)


# ------------------------------------------------------------------
# Prompt helpers
# ------------------------------------------------------------------

def get_common_style():
    from fabric_cli.utils.fab_output_manager import _questionary_style

    return _questionary_style()


def prompt_ask(text: str = "Question") -> Any:
    return output_manager().prompt_ask(text)


def prompt_password(text: str = "password") -> Any:
    return output_manager().prompt_password(text)


def prompt_confirm(text: str = "Are you sure?") -> Any:
    return output_manager().prompt_confirm(text)


def prompt_select_items(question: str, choices: Sequence) -> Any:
    return output_manager().prompt_select_items(question, choices)


def prompt_select_item(question: str, choices: Sequence) -> Any:
    return output_manager().prompt_select_item(question, choices)


# ------------------------------------------------------------------
# Plain text output  (stdout)
# ------------------------------------------------------------------

def print(text: str) -> None:
    output_manager().plain(text)


def print_fabric(text: str) -> None:
    output_manager().fabric(text)


def print_grey(text: str, to_stderr: bool = True) -> None:
    output_manager().muted(text, to_stderr=to_stderr)


# ------------------------------------------------------------------
# Progress / version
# ------------------------------------------------------------------

def print_progress(text, progress: Optional[str] = None) -> None:
    output_manager().progress(text, progress)


def print_version(args=None):
    output_manager().print_version(args)


# ------------------------------------------------------------------
# Structured output
# ------------------------------------------------------------------

def print_output_format(
    args: Namespace,
    message: Optional[str] = None,
    data: Optional[Any] = None,
    hidden_data: Optional[Any] = None,
    show_headers: bool = False,
    show_key_value_list: bool = False,
) -> None:
    output_manager().print_output_format(
        args,
        message=message,
        data=data,
        hidden_data=hidden_data,
        show_headers=show_headers,
        show_key_value_list=show_key_value_list,
    )


# ------------------------------------------------------------------
# Status / diagnostics  (stderr)
# ------------------------------------------------------------------

def print_done(text: str, to_stderr: bool = False) -> None:
    output_manager().status(text, to_stderr=to_stderr)


def print_warning(text: str, command: Optional[str] = None) -> None:
    output_manager().warning(text, command)


def print_output_error(
    error: FabricCLIError,
    command: Optional[str] = None,
    output_format_type: Optional[str] = None,
) -> None:
    output_manager().print_output_error(error, command, output_format_type)


def print_info(text, command: Optional[str] = None) -> None:
    output_manager().info(text, command)


# ------------------------------------------------------------------
# Display helpers
# ------------------------------------------------------------------

def display_help(
    commands: dict[str, dict[str, str]], custom_header: Optional[str] = None
) -> None:
    output_manager().display_help(commands, custom_header)


def print_entries_unix_style(
    entries: Any, fields: Any, header: Optional[bool] = False
) -> None:
    output_manager().print_entries_unix_style(entries, fields, header)


# ------------------------------------------------------------------
# Re-exports for backward compatibility
# ------------------------------------------------------------------

_format_key_to_convert_to_title_case = _format_key_to_title_case


def _print_entries_key_value_list_style(entries: Any) -> None:
    """Backward-compatible wrapper for key-value list printing."""
    output_manager().print_key_value_list(entries)


def _print_error_format_text(message: str, command: Optional[str] = None) -> None:
    """Backward-compatible wrapper for text error formatting."""
    output_manager()._print_error_text(message, command)