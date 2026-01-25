# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import html
import io
import shlex
import subprocess
import sys

from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from fabric_cli.core import fab_constant, fab_logger
from fabric_cli.core.fab_commands import Command
from fabric_cli.core.fab_context import Context
from fabric_cli.core.fab_decorators import singleton
from fabric_cli.utils import fab_commands
from fabric_cli.utils import fab_ui as utils_ui


@singleton
class InteractiveCLI:
    def __init__(self, parser=None, subparsers=None):
        """Initialize the interactive CLI."""
        if parser is None or subparsers is None:
            from fabric_cli.core.fab_parser_setup import (
                get_global_parser_and_subparsers,
            )

            parser, subparsers = get_global_parser_and_subparsers()

        self.parser = parser
        self.parser.set_mode(fab_constant.FAB_MODE_INTERACTIVE)
        self.subparsers = subparsers
        self.history = InMemoryHistory()
        self.session = self.init_session(self.history)
        self.custom_style = Style(
            [
                ("prompt", "fg:#49C5B1"),  # Prompt color, original #49C5B1
                ("context", "fg:#017864"),  # Context color, original #017864
                ("detail", "fg:grey"),
                ("input", "fg:white"),  # Input color
            ]
        )
        self._is_running = False

    def init_session(self, session_history: InMemoryHistory) -> PromptSession:
        return PromptSession(history=session_history)

    def _has_pipe(self, command: str) -> bool:
        """Check if command contains a pipe operator outside of quoted strings."""
        in_single_quote = False
        in_double_quote = False
        i = 0
        while i < len(command):
            char = command[i]
            # Handle escape sequences
            if char == '\\' and i + 1 < len(command):
                i += 2
                continue
            # Track quote state
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == '|' and not in_single_quote and not in_double_quote:
                return True
            i += 1
        return False

    def _split_pipe(self, command: str) -> tuple[str, str]:
        """Split command at the first pipe operator outside of quoted strings.
        
        Returns a tuple of (cli_command, shell_command).
        """
        in_single_quote = False
        in_double_quote = False
        i = 0
        while i < len(command):
            char = command[i]
            # Handle escape sequences
            if char == '\\' and i + 1 < len(command):
                i += 2
                continue
            # Track quote state
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == '|' and not in_single_quote and not in_double_quote:
                return (command[:i].strip(), command[i + 1:].strip())
            i += 1
        return (command.strip(), "")

    def _execute_cli_command(self, command: str) -> str | None:
        """Execute a CLI command and capture its stdout output.
        
        Returns the captured stdout as a string, or None if the command is a special command.
        """
        command_parts = shlex.split(command.strip())

        if command in fab_constant.INTERACTIVE_QUIT_COMMANDS:
            return None
        elif command in fab_constant.INTERACTIVE_HELP_COMMANDS:
            return None
        elif command in fab_constant.INTERACTIVE_VERSION_COMMANDS:
            return None
        elif command.strip() == "fab":
            return None
        elif not command.strip():
            return None

        self.parser.set_mode(fab_constant.FAB_MODE_INTERACTIVE)

        # Now check for subcommands
        if command_parts:  # Only if there's something to process
            subcommand_name = command_parts[0]
            if subcommand_name in self.subparsers.choices:
                subparser = self.subparsers.choices[subcommand_name]

                try:
                    subparser_args = subparser.parse_args(command_parts[1:])
                    subparser_args.command = subcommand_name
                    subparser_args.fab_mode = fab_constant.FAB_MODE_INTERACTIVE
                    subparser_args.command_path = Command.get_command_path(
                        subparser_args
                    )

                    # Capture stdout
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    captured_stdout = io.StringIO()
                    captured_stderr = io.StringIO()
                    sys.stdout = captured_stdout
                    sys.stderr = captured_stderr

                    try:
                        if not command_parts[1:]:
                            subparser_args.func(subparser_args)
                        elif hasattr(subparser_args, "func"):
                            subparser_args.func(subparser_args)
                    finally:
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr

                    # Combine stdout and stderr (stderr typically contains the actual output)
                    return captured_stdout.getvalue() + captured_stderr.getvalue()

                except SystemExit:
                    # Catch SystemExit raised by ArgumentParser and prevent exiting
                    return ""
            else:
                self.parser.error(f"invalid choice: '{command.strip()}'. Type 'help' for available commands.")
                return ""

        return ""

    def _pipe_to_shell(self, input_data: str, shell_command: str) -> None:
        """Pipe input data through a shell command and print the result."""
        try:
            # Use shell=True to support full shell syntax (e.g., grep -i, head -n 10)
            result = subprocess.run(
                shell_command,
                shell=True,
                input=input_data,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                utils_ui.print(result.stdout.rstrip('\n'))
            if result.stderr:
                utils_ui.print_grey(result.stderr.rstrip('\n'))
        except Exception as e:
            utils_ui.print(f"Error running pipe command: {str(e)}")

    def handle_command(self, command):
        """Process the user command."""
        fab_logger.print_log_file_path()

        # Check for pipe in command
        if self._has_pipe(command):
            cli_cmd, shell_cmd = self._split_pipe(command)
            if cli_cmd and shell_cmd:
                output = self._execute_cli_command(cli_cmd)
                if output is not None:
                    self._pipe_to_shell(output, shell_cmd)
                    return False
                else:
                    # Special commands like quit, help, version with pipe - just run the special command
                    return self.handle_command(cli_cmd)

        command_parts = shlex.split(command.strip())

        if command in fab_constant.INTERACTIVE_QUIT_COMMANDS:
            utils_ui.print(fab_constant.INTERACTIVE_EXIT_MESSAGE)
            return True
        elif command in fab_constant.INTERACTIVE_HELP_COMMANDS:
            utils_ui.display_help(
                fab_commands.COMMANDS, "Usage: <command> <subcommand> [flags]"
            )
            return False
        elif command in fab_constant.INTERACTIVE_VERSION_COMMANDS:
            utils_ui.print_version()
            return False
        elif command.strip() == "fab":
            utils_ui.print(
                "In interactive mode, commands don't require the fab prefix. Use --help to view the list of supported commands."
            )
            return False
        elif not command.strip():
            return False

        self.parser.set_mode(fab_constant.FAB_MODE_INTERACTIVE)

        # Now check for subcommands
        if command_parts:  # Only if there's something to process
            subcommand_name = command_parts[0]
            if subcommand_name in self.subparsers.choices:
                subparser = self.subparsers.choices[subcommand_name]

                try:
                    subparser_args = subparser.parse_args(command_parts[1:])
                    subparser_args.command = subcommand_name
                    subparser_args.fab_mode = fab_constant.FAB_MODE_INTERACTIVE
                    subparser_args.command_path = Command.get_command_path(
                        subparser_args
                    )

                    if not command_parts[1:]:
                        subparser_args.func(subparser_args)
                    elif hasattr(subparser_args, "func"):
                        subparser_args.func(subparser_args)
                    else:
                        utils_ui.print(
                            f"No function associated with the command: {command.strip()}"
                        )
                except SystemExit:
                    # Catch SystemExit raised by ArgumentParser and prevent exiting
                    return
            else:
                self.parser.error(f"invalid choice: '{command.strip()}'. Type 'help' for available commands.")

        return False

    def start_interactive(self):
        """Start the interactive mode using prompt_toolkit for input."""
        if self._is_running:
            utils_ui.print("Interactive mode is already running.")
            return

        self._is_running = True

        try:
            utils_ui.print("\nWelcome to the Fabric CLI ⚡")
            utils_ui.print("Type 'help' for help. \n")

            while True:
                try:
                    context = Context().context
                    pwd_context = f"/{context.path.strip('/')}"

                    prompt_text = HTML(
                        f"<prompt>fab</prompt><detail>:</detail><context>{html.escape(pwd_context)}</context><detail>$</detail> "
                    )

                    user_input = self.session.prompt(
                        prompt_text,
                        style=self.custom_style,
                        cursor=CursorShape.BLINKING_BEAM,
                        enable_history_search=True,
                    )
                    should_exit = self.handle_command(user_input)
                    if should_exit:  # Check if the command was to exit
                        break

                except KeyboardInterrupt:
                    # Handle Ctrl+C gracefully during command input
                    utils_ui.print("\nUse 'quit' or 'exit' to leave interactive mode.")
                    continue
                except Exception as e:
                    # Handle unexpected errors during prompt processing
                    utils_ui.print(f"Error in interactive session: {str(e)}")
                    break

        except (EOFError, KeyboardInterrupt):
            utils_ui.print(f"\n{fab_constant.INTERACTIVE_EXIT_MESSAGE}")
        except Exception as e:
            # Handle critical errors that would terminate the session
            utils_ui.print(f"\nCritical error in interactive mode: {str(e)}")
            utils_ui.print(fab_constant.INTERACTIVE_EXIT_MESSAGE)
        finally:
            self._is_running = False


def start_interactive_mode():
    """Launch interactive mode using singleton pattern"""
    interactive_cli = InteractiveCLI()
    interactive_cli.start_interactive()
