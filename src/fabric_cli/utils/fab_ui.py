# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import builtins
import csv
import io
import sys
import unicodedata
from argparse import Namespace
from typing import Any, Optional, Sequence

import rich.box as box
from rich.console import Console as _RichConsole
from rich.table import Table
from rich.text import Text

from fabric_cli import __version__
from fabric_cli.core import fab_constant, fab_state_config
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.fab_output import FabricCLIOutput, OutputStatus
from fabric_cli.errors import ErrorMessages
from fabric_cli.utils import fab_lazy_load
from fabric_cli.utils.console import console, err_console


def get_common_style():
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


def prompt_ask(text: str = "Question") -> Any:
    return fab_lazy_load.questionary().text(text, style=get_common_style()).ask()


def prompt_password(text: str = "password") -> Any:
    return fab_lazy_load.questionary().password(text, style=get_common_style()).ask()


def prompt_confirm(text: str = "Are you sure?") -> Any:
    return fab_lazy_load.questionary().confirm(text, style=get_common_style()).ask()


def prompt_select_items(question: str, choices: Sequence) -> Any:
    selected_items = (
        fab_lazy_load.questionary()
        .checkbox(question, choices=choices, pointer=">", style=get_common_style())
        .ask()
    )

    return selected_items


def prompt_select_item(question: str, choices: Sequence) -> Any:
    # Prompt the user to select a single item from a list of choices
    selected_item = (
        fab_lazy_load.questionary()
        .select(question, choices=choices, pointer=">", style=get_common_style())
        .ask()
    )

    return selected_item


def print(text: str) -> None:
    _safe_print(text)


def print_fabric(text: str) -> None:
    _safe_print(text, style="#49C5B1")


def print_grey(text: str, to_stderr: bool = True) -> None:
    _safe_print(text, style="grey62", to_stderr=to_stderr)


def print_progress(text, progress: Optional[str] = None) -> None:
    progress_text = f": {progress}%" if progress else ""
    print_grey(f"∟ {text}{progress_text}")


def print_version(args=None):
    print(f"fab version {__version__}")
    print("https://aka.ms/fabric-cli/release-notes")


def print_output_format(
    args: Namespace,
    message: Optional[str] = None,
    data: Optional[Any] = None,
    hidden_data: Optional[Any] = None,
    show_headers: bool = False,
    show_key_value_list: bool = False,
) -> None:
    """Create a FabricCLIOutput instance and print it depends on the format.

    Args:
        args: The command arguments namespace containing command and output_format
        message: Success message to display
        data: Optional data to include in output
        hidden_data: Optional hidden data to include in output
        show_headers: Whether to show headers in the output (default: False)
        show_key_value_list: Whether to show output in key-value list format (default: False)

    Returns:
        FabricCLIOutput: Configured output instance ready for printing
    """

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

    # Get format from output or config
    format_type = output.output_format_type or fab_state_config.get_config(
        fab_constant.FAB_OUTPUT_FORMAT
    )
    match format_type:
        case "json":
            _print_output_format_json(output.to_json())
        case "text":
            _print_output_format_result_text(output)
        case "table":
            _print_output_format_table(output)
        case "yaml":
            _print_output_format_yaml(output)
        case "csv":
            _print_output_format_csv(output)
        case _:
            raise FabricCLIError(
                ErrorMessages.Common.output_format_not_supported(str(format_type)),
                fab_constant.ERROR_NOT_SUPPORTED,
            )


def print_done(text: str, to_stderr: bool = False) -> None:
    if text is None:
        raise AttributeError("Cannot print None value")
    t = Text()
    t.append("\n")
    t.append("*", style="green")
    t.append(f" {text}")
    _safe_print_rich_text(t, text, to_stderr)


def print_warning(text: str, command: Optional[str] = None) -> None:
    if text is None:
        raise AttributeError("Cannot print None value")
    text = text.rstrip(".")
    command_text = f"{command}: " if command else ""
    t = Text()
    t.append("!", style="yellow")
    t.append(f" {command_text}{text}")
    _safe_print_rich_text(t, text, to_stderr=True)


def print_output_error(
    error: FabricCLIError,
    command: Optional[str] = None,
    output_format_type: Optional[str] = None,
) -> None:
    """
    Prints an error message in the specified output format defined in config file.

    Args:
        error (FabricCLIError): The error to display.
        command (Optional[str], optional): The command associated with the error.
        output_format_type (Optional[str], optional): The output format to use.

    Raises:
        FabricCLIError: If the output format is not supported.
    """
    # Get format from output or config
    format_type = output_format_type or fab_state_config.get_config(
        fab_constant.FAB_OUTPUT_FORMAT
    )
    match format_type:
        case "json":
            _print_error_format_json(
                FabricCLIOutput(
                    status=OutputStatus.Failure,
                    error_code=error.status_code,
                    command=command,
                    message=error.message,
                ).to_json()
            )
            return
        case "text" | "table" | "csv":
            _print_error_format_text(error.formatted_message(), command)
            return
        case "yaml":
            _print_error_format_yaml(
                FabricCLIOutput(
                    status=OutputStatus.Failure,
                    error_code=error.status_code,
                    command=command,
                    message=error.message,
                )
            )
            return
        case _:
            raise FabricCLIError(
                ErrorMessages.Common.output_format_not_supported(str(format_type)),
                fab_constant.ERROR_NOT_SUPPORTED,
            )


def print_info(text, command: Optional[str] = None) -> None:
    if text is None:
        raise AttributeError("Cannot print None value")
    clean_text = text.rstrip(".")
    command_text = f"{command}: " if command else ""
    t = Text()
    t.append("*", style="blue")
    t.append(f" {command_text}{clean_text}")
    _safe_print_rich_text(t, clean_text, to_stderr=True)


# Display


# Display all available commands organized by category with descriptions
def display_help(
    commands: dict[str, dict[str, str]], custom_header: Optional[str] = None
) -> None:
    if not commands or len(commands) == 0:
        print("No commands available.")
        return
    if custom_header:
        print(f"{custom_header} \n")
    else:
        print("Work seamlessly with Fabric from the command line.\n")
        print("Usage: fab <command> <subcommand> [flags]\n")

    max_command_length = max(
        len(cmd) for cmd_dict in commands.values() for cmd in cmd_dict
    )

    for category, cmd_dict in commands.items():
        print(f"{category}:")
        for command, description in cmd_dict.items():
            padded_command = f"{command:<{max_command_length}}"
            print(f"  {padded_command}: {description}")
        print("")

    # Learn more
    print("Learn More:")
    print(
        "  Use `fab <command> <subcommand> --help` for more information about a command."
    )
    print("  Use `fab config set mode interactive` to enable interactive mode.")
    print("  Read the docs at https://aka.ms/fabric-cli.\n")


# ascii Display


def get_visual_length(entry: dict, field: Any) -> int:
    return _get_visual_length(str(entry.get(field, "")))


# Prints a list of entries in Unix-like format based on specified fields
def print_entries_unix_style(
    entries: Any, fields: Any, header: Optional[bool] = False
) -> None:
    if isinstance(entries, dict):
        _entries = [entries]
    elif isinstance(entries, list):
        if len(entries) == 0:
            # Putting an empty dictionary to avoid errors and print a blank line instead
            # This way in case of headers, the header will be printed
            _entries = [{}]
        else:
            _entries = entries
    else:
        raise FabricCLIError(
            ErrorMessages.Labels.invalid_entries_format(),
            fab_constant.ERROR_INVALID_ENTRIES_FORMAT,
        )

    table = Table(
        show_header=bool(header),
        box=box.SIMPLE_HEAD if header else None,
        show_edge=False,
        pad_edge=False,
        padding=(0, 2),
        style="grey62",
        header_style="grey62",
    )
    for field in fields:
        table.add_column(field, no_wrap=True, overflow="fold")

    for entry in _entries:
        row = [str(entry.get(field, "")) for field in fields]
        table.add_row(*row)

    # Render table to string and print via standard path so that
    # test mocks on _safe_print capture the rendered output.
    buf = io.StringIO()
    _RichConsole(file=buf, width=10000, force_terminal=False, highlight=False).print(table, end="")
    print_grey(buf.getvalue(), to_stderr=False)


# Others


# Utils


def _safe_print(
    text: str, style: Optional[str] = None, to_stderr: bool = False
) -> None:

    try:
        if text is None:
            raise AttributeError("Cannot print None value")
        target = err_console if to_stderr else console
        target.print(text, style=style, markup=False)

    except (RuntimeError, AttributeError, Exception) as e:
        _print_fallback(text, e, to_stderr=to_stderr)


def _safe_print_rich_text(
    rich_text: Any, fallback_text: str, to_stderr: bool = False
) -> None:
    """Print a Rich renderable with fallback to plain text."""
    try:
        if rich_text is None:
            raise AttributeError("Cannot print None value")
        target = err_console if to_stderr else console
        target.print(rich_text)
    except (RuntimeError, AttributeError, Exception) as e:
        _print_fallback(fallback_text, e, to_stderr)


def _print_output_format_result_text(output: FabricCLIOutput) -> None:
    # if there is no result to print it means something went wrong
    output_result = output.result
    if all(
        value is None
        for value in [
            output_result.data,
            output_result.hidden_data,
            output_result.message,
        ]
    ):
        raise FabricCLIError(
            ErrorMessages.Common.invalid_result_format(),
            fab_constant.ERROR_INVALID_INPUT,
        )

    show_headers = output.show_headers
    if output_result.data:
        # ls command and command pass show_headers = True (like job run-status) need special print handler
        entries_unix_style_command = ["ls", "dir"]
        if (
            output._command in entries_unix_style_command
            or output._subcommand in entries_unix_style_command
            or show_headers
        ):
            data_keys = output.result.get_data_keys() if output_result.data else []
            if len(data_keys) > 0:
                print_entries_unix_style(output_result.data, data_keys, header=(len(data_keys) > 1 or show_headers))
            else:
                _print_raw_data(output_result.data)
        elif output.show_key_value_list:
            _print_entries_key_value_list_style(output_result.data)
        else:
            _print_raw_data(output_result.data)

    if output_result.hidden_data:
        print_grey("------------------------------")
        _print_raw_data(output_result.hidden_data)

    if output_result.message:
        print_done(f"{output_result.message}\n")


def _print_output_format_table(output: FabricCLIOutput) -> None:
    """Print output as a Rich bordered table."""
    output_result = output.result
    if all(
        value is None
        for value in [
            output_result.data,
            output_result.hidden_data,
            output_result.message,
        ]
    ):
        raise FabricCLIError(
            ErrorMessages.Common.invalid_result_format(),
            fab_constant.ERROR_INVALID_INPUT,
        )

    if output_result.data:
        data_keys = output.result.get_data_keys() if output_result.data else []
        if len(data_keys) > 0:
            _print_rich_bordered_table(output_result.data, data_keys)
        else:
            _print_raw_data(output_result.data)

    if output_result.hidden_data:
        print_grey("------------------------------")
        _print_raw_data(output_result.hidden_data)

    if output_result.message:
        print_done(f"{output_result.message}\n")


def _print_rich_bordered_table(data: list[Any], keys: list[str]) -> None:
    """Render data as a Rich table with rounded borders."""
    table = Table(
        show_header=True,
        box=box.ROUNDED,
        header_style="bold cyan",
        padding=(0, 1),
    )
    for key in keys:
        table.add_column(_format_key_to_convert_to_title_case(key))

    for entry in data:
        row = [str(entry.get(key, "")) for key in keys]
        table.add_row(*row)

    console.print(table)


def _print_output_format_yaml(output: FabricCLIOutput) -> None:
    """Print output in YAML format."""
    import yaml

    output_dict = output._to_dict()
    yaml_output = yaml.dump(output_dict, default_flow_style=False, sort_keys=False)
    _safe_print(yaml_output.rstrip())


def _print_output_format_csv(output: FabricCLIOutput) -> None:
    """Print output data in CSV format."""
    output_result = output.result
    if all(
        value is None
        for value in [
            output_result.data,
            output_result.hidden_data,
            output_result.message,
        ]
    ):
        raise FabricCLIError(
            ErrorMessages.Common.invalid_result_format(),
            fab_constant.ERROR_INVALID_INPUT,
        )

    if output_result.data:
        data_keys = output.result.get_data_keys()
        if data_keys:
            string_io = io.StringIO()
            writer = csv.DictWriter(
                string_io, fieldnames=data_keys, extrasaction="ignore"
            )
            writer.writeheader()
            for row in output_result.data:
                writer.writerow({k: str(v) for k, v in row.items() if k in data_keys})
            _safe_print(string_io.getvalue().rstrip())
        else:
            for item in output_result.data:
                _safe_print(str(item))

    if output_result.message:
        print_done(f"{output_result.message}\n")


def _print_raw_data(data: list[Any], to_stderr: bool = False) -> None:
    """
    Print raw data without headers/formatting using appropriate display strategy.

    This function intelligently chooses the output format based on data structure:
    - Complex dictionaries (multiple keys or list values) -> JSON formatting
    - Simple dictionaries (single key-value pairs) -> Extract and display values only
    - Other data types -> Direct string conversion

    Args:
        data: List of data items to print
        to_stderr: Whether to output to stderr (True) or stdout (False)

    Returns:
        None
    """
    # Early exit for empty data
    if not data:
        return

    # Determine formatting strategy based on data structure
    if isinstance(data[0], dict):
        _print_dict(data, to_stderr)
    else:
        _print_simple_items(data, to_stderr)


def _print_dict(data: list[Any], to_stderr: bool) -> None:
    """
    Format and print data as pretty-printed JSON.

    Args:
        data: Data to format as JSON
        to_stderr: Output stream selection
    """
    try:
        from fabric_cli.utils.fab_util import dumps

        # In case of single item list print the item directly else print the list
        json_output = dumps(data[0] if len(data) == 1 else data, indent=2)
        print_grey(json_output, to_stderr)
    except (TypeError, ValueError):
        # Fallback to string representation if JSON serialization fails
        _print_simple_items(data, to_stderr)


def _print_simple_items(data: list[Any], to_stderr: bool) -> None:
    """
    Format non-dictionary data as simple string representations.
    Example command: get x.Lakehouse (without -q)
    Args:
        data: List of items to format as strings
        to_stderr: Output stream selection
    """
    for item in data:
        print_grey(str(item), to_stderr)


def _print_output_format_json(output_json: str) -> None:
    _safe_print(output_json)


def _print_error_format_json(output: str) -> None:
    _safe_print(output, to_stderr=False)


def _print_error_format_text(message: str, command: Optional[str] = None) -> None:
    command_text = f"{command}: " if command else ""
    t = Text()
    t.append("x", style="red")
    t.append(f" {command_text}{message}")
    _safe_print_rich_text(t, str(message))


def _print_error_format_yaml(output: FabricCLIOutput) -> None:
    """Print error in YAML format."""
    import yaml

    output_dict = output._to_dict()
    yaml_output = yaml.dump(output_dict, default_flow_style=False, sort_keys=False)
    _safe_print(yaml_output.rstrip())


def _print_fallback(text: str, e: Exception, to_stderr: bool = False) -> None:
    # Fallback print
    # https://github.com/prompt-toolkit/python-prompt-toolkit/issues/406
    output_stream = sys.stderr if to_stderr else sys.stdout
    builtins.print(text, file=output_stream)
    if isinstance(e, AttributeError):  # Only re-raise AttributeError (pytest)
        raise


def _get_visual_length(string: str) -> int:
    length = 0
    for char in string:
        # Check if the character is wide or normal
        if unicodedata.east_asian_width(char) in [
            "F",
            "W",
        ]:  # Fullwidth or Wide characters
            length += 2
        else:
            length += 1
    return length


def _print_entries_key_value_list_style(entries: Any) -> None:
    """Print entries in a key-value list format with formatted keys.

    Args:
        entries: Dictionary or list of dictionaries to print

    Example output:
        Logged In: true
        Account: johndoe@example.com
    """
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
            pretty_key = _format_key_to_convert_to_title_case(key)
            print_grey(f"{pretty_key}: {value}", to_stderr=False)
        if i < len(_entries) - 1:
            print_grey("", to_stderr=False)  # Empty line between entries


def _format_key_to_convert_to_title_case(key: str) -> str:
    """Convert a snake_case key to a Title Case name.

    Args:
        key: The key to format in snake_case format (e.g. 'user_id', 'account_name')

    Returns:
        str: Formatted to title case name (e.g. 'User ID', 'Account Name')

    Raises:
        ValueError: If the key is not in the expected underscore-separated format
    """
    # Allow letters, numbers, and underscores only
    if not key.replace('_', '').replace(' ', '').isalnum():
        raise ValueError(f"Invalid key format: '{key}'. Only underscore-separated words are allowed.")

    # Check for invalid patterns (camelCase, spaces mixed with underscores, etc.)
    if ' ' in key and '_' in key:
        raise ValueError(f"Invalid key format: '{key}'. Only underscore-separated words are allowed.")

    # Check for camelCase pattern (uppercase letters not at the start)
    if any(char.isupper() for char in key[1:]) and '_' not in key:
        raise ValueError(f"Invalid key format: '{key}'. Only underscore-separated words are allowed.")

    pretty = key.replace('_', ' ').title().strip()

    return _check_special_cases(pretty)


def _check_special_cases(pretty: str) -> str:
    """Check for special cases and replace them with the correct value."""
    # Here add special cases for specific keys that need to be formatted differently
    special_cases = {
        "Id": "ID",
        "Powerbi": "PowerBI",
    }

    for case_key, case_value in special_cases.items():
        pretty = pretty.replace(case_key.title(), case_value)

    return pretty
