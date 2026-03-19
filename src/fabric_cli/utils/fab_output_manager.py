# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Central output facade for the Fabric CLI.

OutputManager is the single gateway that controls how the CLI writes to
stdout, stderr, and the debug log file.  It is **mode-aware**
(command-line vs interactive REPL) and **format-aware** (text vs JSON)
so every output helper automatically routes content to the correct
stream with the correct formatting.

Design principles (matching existing behaviour):
  * **stdout**  – machine-readable data / results only (safe for piping)
  * **stderr**  – human-facing diagnostics (progress, warnings, errors,
                  info, debug messages)
  * **file log** – debug HTTP traces, always active regardless of
                   output format

Usage
-----
The singleton is accessed via ``OutputManager.instance()`` (or the
module-level ``output_manager()`` shortcut).  At startup ``main.py``
calls ``set_mode()`` / ``set_output_format()`` once; every subsequent
call inherits those settings automatically.

Backward compatibility
----------------------
``fab_ui.py`` public functions are kept as thin wrappers that delegate
to this manager, so the 300+ existing call sites remain unchanged.
"""

from __future__ import annotations

import builtins
import sys
import unicodedata
from argparse import Namespace
from typing import Any, Optional, Sequence

from rich import box as rich_box
from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from fabric_cli.core import fab_constant, fab_state_config
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.fab_output import FabricCLIOutput, OutputStatus
from fabric_cli.errors import ErrorMessages

# ---------------------------------------------------------------------------
# Theme & shared console instances
# ---------------------------------------------------------------------------

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

console = Console(theme=FAB_THEME, highlight=False)
console_err = Console(theme=FAB_THEME, stderr=True, highlight=False)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[OutputManager] = None


def output_manager() -> OutputManager:
    """Return the global OutputManager singleton (created on first call)."""
    global _instance
    if _instance is None:
        _instance = OutputManager()
    return _instance


def reset_instance() -> None:
    """Reset the singleton – intended **only** for tests."""
    global _instance
    _instance = None


class OutputManager:
    """Central facade for all CLI output."""

    # Convenience class-level accessor
    instance = staticmethod(lambda: output_manager())

    def __init__(self) -> None:
        self._mode: str = fab_constant.FAB_MODE_COMMANDLINE
        # resolved lazily from config
        self._output_format: Optional[str] = None
        self.console = console
        self.console_err = console_err

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def get_mode(self) -> str:
        return self._mode

    @property
    def is_interactive(self) -> bool:
        return self._mode == fab_constant.FAB_MODE_INTERACTIVE

    def set_output_format(self, fmt: Optional[str]) -> None:
        self._output_format = fmt

    def get_output_format(self) -> str:
        """Resolve output format: explicit override → config → 'text'."""
        return (
            self._output_format
            or fab_state_config.get_config(fab_constant.FAB_OUTPUT_FORMAT)
            or "text"
        )

    @property
    def is_json_mode(self) -> bool:
        return self.get_output_format() == "json"

    # ------------------------------------------------------------------
    # Data output  (stdout — safe for piping)
    # ------------------------------------------------------------------

    def print_output_format(
        self,
        args: Namespace,
        message: Optional[str] = None,
        data: Optional[Any] = None,
        hidden_data: Optional[Any] = None,
        show_headers: bool = False,
        show_key_value_list: bool = False,
    ) -> None:
        """Primary data printer — dispatches to JSON or text rendering."""
        command = getattr(args, "command", None)
        subcommand = getattr(args, f"{command}_subcommand", None)

        output = FabricCLIOutput(
            command=command,
            subcommand=subcommand,
            output_format_type=getattr(args, "output_format", None),
            message=message,
            data=data,
            hidden_data=hidden_data,
            show_headers=show_headers,
            show_key_value_list=show_key_value_list,
        )

        format_type = output.output_format_type or fab_state_config.get_config(
            fab_constant.FAB_OUTPUT_FORMAT
        )
        match format_type:
            case "json":
                self._print_json(output.to_json())
            case "text":
                self._print_text_result(output)
            case _:
                raise FabricCLIError(
                    ErrorMessages.Common.output_format_not_supported(
                        str(format_type)),
                    fab_constant.ERROR_NOT_SUPPORTED,
                )

    def print_output_error(
        self,
        error: FabricCLIError,
        command: Optional[str] = None,
        output_format_type: Optional[str] = None,
    ) -> None:
        """Print an error in the active output format."""
        format_type = output_format_type or fab_state_config.get_config(
            fab_constant.FAB_OUTPUT_FORMAT
        )
        match format_type:
            case "json":
                self._print_error_json(
                    FabricCLIOutput(
                        status=OutputStatus.Failure,
                        error_code=error.status_code,
                        command=command,
                        message=error.message,
                    ).to_json()
                )
            case "text":
                self._print_error_text(error.formatted_message(), command)
            case _:
                raise FabricCLIError(
                    ErrorMessages.Common.output_format_not_supported(
                        str(format_type)),
                    fab_constant.ERROR_NOT_SUPPORTED,
                )

    # ------------------------------------------------------------------
    # Diagnostic output  (stderr — never captured when piping stdout)
    # ------------------------------------------------------------------

    def status(self, text: str, to_stderr: bool = False) -> None:
        """Print a success/done message with green checkmark."""
        target = self.console_err if to_stderr else self.console
        try:
            target.print(f"\n[success]✔[/success] {text}")
        except Exception as e:
            self._fallback(text, e, to_stderr=to_stderr)

    def warning(self, text: str, command: Optional[str] = None) -> None:
        """Print a warning (always stderr)."""
        text = text.rstrip(".")
        command_text = f"{command}: " if command else ""
        try:
            self.console_err.print(
                f"[warning]![/warning] {command_text}{text}")
        except Exception as e:
            self._fallback(text, e, to_stderr=True)

    def error(self, text: str) -> None:
        """Print an error line (always stderr)."""
        try:
            self.console_err.print(f"[error]✘[/error] {text}")
        except Exception as e:
            self._fallback(text, e, to_stderr=True)

    def info(self, text: str, command: Optional[str] = None) -> None:
        """Print an info message (always stderr)."""
        text = str(text).rstrip(".")
        command_text = f"{command}: " if command else ""
        try:
            self.console_err.print(f"[info]ℹ[/info] {command_text}{text}")
        except Exception as e:
            self._fallback(text, e, to_stderr=True)

    def progress(self, text: str, progress: Optional[str] = None) -> None:
        """Print a progress indicator (stderr)."""
        progress_text = f": {progress}%" if progress else ""
        self.muted(f"∟ {text}{progress_text}", to_stderr=True)

    def debug(self, message: str) -> None:
        """Print a debug message to stderr (when debug enabled) AND to log file."""
        if fab_state_config.get_config(fab_constant.FAB_DEBUG_ENABLED) == "true":
            self.muted(f"[debug] {message}", to_stderr=True)

    # ------------------------------------------------------------------
    # Styled text helpers
    # ------------------------------------------------------------------

    def plain(self, text: str) -> None:
        """Print plain text to stdout."""
        self._safe_print(text)

    def fabric(self, text: str) -> None:
        """Print text in the Fabric brand colour (stdout)."""
        self._safe_print(text, style="fabric")

    def muted(self, text: str, to_stderr: bool = True) -> None:
        """Print grey/muted text. Default: stderr (diagnostic context)."""
        self._safe_print(text, style="muted", to_stderr=to_stderr)

    # ------------------------------------------------------------------
    # Display helpers  (stdout — structured data presentation)
    # ------------------------------------------------------------------

    def print_entries_unix_style(
        self,
        entries: Any,
        fields: Any,
        header: Optional[bool] = False,
        footer_items: Optional[list[str]] = None,
    ) -> None:
        """Print a list of entries in Unix-like column format (stdout)."""
        if isinstance(entries, dict):
            _entries = [entries]
        elif isinstance(entries, list):
            _entries = [{}] if len(entries) == 0 else entries
        else:
            raise FabricCLIError(
                ErrorMessages.Labels.invalid_entries_format(),
                fab_constant.ERROR_INVALID_ENTRIES_FORMAT,
            )

        table = Table(show_header=bool(header), box=None if bool(
            header) == False else rich_box.ROUNDED, padding=(0, 2), expand=True, highlight=True)
        for field in fields:
            table.add_column(field, style="muted")
        for entry in _entries:
            table.add_row(*(str(entry.get(field, "")) for field in fields))

        if footer_items:
            table.add_row()
            for item in footer_items:
                table.add_row(str(item), *[""] * (len(fields) - 1), style="dim italic")

        self.console.print(table)

    def display_help(
        self,
        commands: dict[str, dict[str, str]],
        custom_header: Optional[str] = None,
    ) -> None:
        """Display categorised command help."""
        if not commands or len(commands) == 0:
            self.plain("No commands available.")
            return
        if custom_header:
            self.plain(f"{custom_header} \n")
        else:
            self.plain("Work seamlessly with Fabric from the command line.\n")
            self.plain("Usage: fab <command> <subcommand> [flags]\n")

        for category, cmd_dict in commands.items():
            table = Table(
                title=category,
                show_header=False,
                title_style="bold",
                box=None,
                padding=(0, 2),
            )
            table.add_column("Command", style="fabric")
            table.add_column("Description")
            for cmd, description in cmd_dict.items():
                table.add_row(cmd, description)
            self.console.print(table)
            self.console.print()

        self.plain("Learn More:")
        self.plain(
            "  Use `fab <command> <subcommand> --help` for more information about a command."
        )
        self.plain(
            "  Use `fab config set mode interactive` to enable interactive mode.")
        self.plain("  Read the docs at https://aka.ms/fabric-cli.\n")

    def print_version(self, args: Any = None) -> None:
        """Print CLI version info."""
        from fabric_cli import __version__

        self.plain(f"fab version {__version__}")
        self.plain("https://aka.ms/fabric-cli/release-notes")

    def print_key_value_list(self, entries: Any) -> None:
        """Print entries in a key-value list format with formatted keys."""
        if isinstance(entries, dict):
            _entries = [entries]
        elif isinstance(entries, list):
            if not entries:
                return
            _entries = entries
        else:
            raise FabricCLIError(
                ErrorMessages.Common.invalid_entries_format(),
                fab_constant.ERROR_INVALID_ENTRIES_FORMAT,
            )

        for i, entry in enumerate(_entries):
            for key, value in entry.items():
                pretty_key = _format_key_to_title_case(key)
                self.console.print(f"[muted]{pretty_key}: {value}[/muted]")
            if i < len(_entries) - 1:
                self.console.print()

    # ------------------------------------------------------------------
    # Prompt helpers  (delegate to questionary — interactive only)
    # ------------------------------------------------------------------

    def prompt_ask(self, text: str = "Question") -> Any:
        from fabric_cli.utils import fab_lazy_load

        return fab_lazy_load.questionary().text(text, style=_questionary_style()).ask()

    def prompt_password(self, text: str = "password") -> Any:
        from fabric_cli.utils import fab_lazy_load

        return fab_lazy_load.questionary().password(text, style=_questionary_style()).ask()

    def prompt_confirm(self, text: str = "Are you sure?") -> Any:
        from fabric_cli.utils import fab_lazy_load

        return fab_lazy_load.questionary().confirm(text, style=_questionary_style()).ask()

    def prompt_select_items(self, question: str, choices: Sequence) -> Any:
        from fabric_cli.utils import fab_lazy_load

        return (
            fab_lazy_load.questionary()
            .checkbox(question, choices=choices, pointer=">", style=_questionary_style())
            .ask()
        )

    def prompt_select_item(self, question: str, choices: Sequence) -> Any:
        from fabric_cli.utils import fab_lazy_load

        return (
            fab_lazy_load.questionary()
            .select(question, choices=choices, pointer=">", style=_questionary_style())
            .ask()
        )

    # ------------------------------------------------------------------
    # Internal: text format rendering
    # ------------------------------------------------------------------

    def _print_text_result(self, output: FabricCLIOutput) -> None:
        output_result = output.result
        if all(
            v is None
            for v in [output_result.data, output_result.hidden_data, output_result.message]
        ):
            raise FabricCLIError(
                ErrorMessages.Common.invalid_result_format(),
                fab_constant.ERROR_INVALID_INPUT,
            )

        show_headers = output.show_headers
        hidden_items = output_result.hidden_data if output_result.hidden_data else None

        if output_result.data:
            entries_unix_style_command = ["ls", "dir"]
            if (
                output._command in entries_unix_style_command
                or output._subcommand in entries_unix_style_command
                or show_headers
            ):
                data_keys = output.result.get_data_keys() if output_result.data else []
                if len(data_keys) > 0:
                    self.print_entries_unix_style(
                        output_result.data,
                        data_keys,
                        header=(len(data_keys) > 1 or show_headers),
                        footer_items=hidden_items,
                    )
                else:
                    self._print_raw_data(output_result.data)
                    if hidden_items:
                        self._print_raw_data(hidden_items)
            elif output.show_key_value_list:
                self.print_key_value_list(output_result.data)
            else:
                self._print_raw_data(output_result.data)
        elif hidden_items:
            self._print_raw_data(hidden_items)

        if output_result.message:
            self.status(f"{output_result.message}\n")

    def _print_raw_data(self, data: list[Any], to_stderr: bool = False) -> None:
        if not data:
            return
        if isinstance(data[0], dict):
            self._print_dict(data, to_stderr)
        else:
            self._print_simple_items(data, to_stderr)

    def _print_dict(self, data: list[Any], to_stderr: bool) -> None:
        try:
            from fabric_cli.utils.fab_util import dumps

            json_output = dumps(data[0] if len(data) == 1 else data, indent=2)
            self.muted(json_output, to_stderr)
        except (TypeError, ValueError):
            self._print_simple_items(data, to_stderr)

    def _print_simple_items(self, data: list[Any], to_stderr: bool) -> None:
        for item in data:
            self.muted(str(item), to_stderr)

    # ------------------------------------------------------------------
    # Internal: JSON / error format rendering
    # ------------------------------------------------------------------

    def _print_json(self, output_json: str) -> None:
        self._safe_print(output_json)

    def _print_error_json(self, output: str) -> None:
        self._safe_print(output, to_stderr=False)

    def _print_error_text(self, message: str, command: Optional[str] = None) -> None:
        command_text = f"{command}: " if command else ""
        try:
            self.console_err.print(f"[error]✘[/error] {command_text}{message}")
        except Exception as e:
            self._fallback(f"x {command_text}{message}", e, to_stderr=True)

    # ------------------------------------------------------------------
    # Internal: low-level print with fallback
    # ------------------------------------------------------------------

    def _safe_print(
        self,
        text: str,
        style: Optional[str] = None,
        to_stderr: bool = False,
    ) -> None:
        try:
            target = self.console_err if to_stderr else self.console
            target.print(text, style=style)
        except (RuntimeError, AttributeError, Exception) as e:
            self._fallback(text, e, to_stderr=to_stderr)

    @staticmethod
    def _fallback(text: str, e: Exception, to_stderr: bool = False) -> None:
        stream = sys.stderr if to_stderr else sys.stdout
        builtins.print(text, file=stream)
        if isinstance(e, AttributeError):
            raise


# ---------------------------------------------------------------------------
# Module-level utilities (shared / used by fab_ui wrappers)
# ---------------------------------------------------------------------------

def get_visual_length(entry: dict, field: Any) -> int:
    return _get_visual_length(str(entry.get(field, "")))


def _get_visual_length(string: str) -> int:
    length = 0
    for char in string:
        if unicodedata.east_asian_width(char) in ["F", "W"]:
            length += 2
        else:
            length += 1
    return length


def _format_key_to_title_case(key: str) -> str:
    """Convert a snake_case key to a Title Case name."""
    if not key.replace("_", "").replace(" ", "").isalnum():
        raise ValueError(
            f"Invalid key format: '{key}'. Only underscore-separated words are allowed."
        )
    if " " in key and "_" in key:
        raise ValueError(
            f"Invalid key format: '{key}'. Only underscore-separated words are allowed."
        )
    if any(char.isupper() for char in key[1:]) and "_" not in key:
        raise ValueError(
            f"Invalid key format: '{key}'. Only underscore-separated words are allowed."
        )
    pretty = key.replace("_", " ").title().strip()
    return _check_special_cases(pretty)


def _check_special_cases(pretty: str) -> str:
    special_cases = {
        "Id": "ID",
        "Powerbi": "PowerBI",
    }
    for case_key, case_value in special_cases.items():
        pretty = pretty.replace(case_key.title(), case_value)
    return pretty


def _questionary_style():
    """Return the shared questionary style (lazy-loaded)."""
    from fabric_cli.utils import fab_lazy_load

    return fab_lazy_load.questionary().Style(
        [
            ("qmark", "fg:#49C5B1"),
            ("question", ""),
            ("answer", "fg:#6c6c6c"),
            ("pointer", "fg:#49C5B1"),
            ("highlighted", "fg:#49C5B1"),
            ("selected", "fg:#49C5B1"),
            ("separator", "fg:#6c6c6c"),
            ("instruction", "fg:#49C5B1"),
            ("text", ""),
            ("disabled", "fg:#858585 italic"),
        ]
    )
