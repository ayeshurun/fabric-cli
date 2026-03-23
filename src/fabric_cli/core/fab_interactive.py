# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import html
import shlex

from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from fabric_cli.core import fab_constant
from fabric_cli.utils import fab_output_manager as output_manager
from fabric_cli.core.fab_commands import Command
from fabric_cli.core.fab_context import Context
from fabric_cli.core.fab_decorators import singleton
from fabric_cli.utils import fab_commands
from fabric_cli.core.fab_parser_setup import get_global_parser_and_subparsers

@singleton
class InteractiveCLI:
    def __init__(self, parser=None, subparsers=None):
        """Initialize the interactive CLI."""
        if parser is None or subparsers is None:
            parser, subparsers = get_global_parser_and_subparsers()

        self.parser = parser
        self.parser.set_mode(fab_constant.FAB_MODE_INTERACTIVE)
        output_manager.set_mode(fab_constant.FAB_MODE_INTERACTIVE)
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

    def handle_command(self, command):
        """Process the user command."""
        output_manager.print_log_file_path()

        command_parts = shlex.split(command.strip())

        if command in fab_constant.INTERACTIVE_QUIT_COMMANDS:
            output_manager.print(fab_constant.INTERACTIVE_EXIT_MESSAGE)
            return True
        elif command in fab_constant.INTERACTIVE_HELP_COMMANDS:
            output_manager.display_help(
                fab_commands.COMMANDS, "Usage: <command> <subcommand> [flags]"
            )
            return False
        elif command in fab_constant.INTERACTIVE_VERSION_COMMANDS:
            output_manager.print_version()
            return False
        elif command.strip() == "fab":
            output_manager.print(
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
                        output_manager.print(
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
            output_manager.print("Interactive mode is already running.")
            return

        self._is_running = True

        try:
            output_manager.print("\nWelcome to the Fabric CLI ⚡")
            output_manager.print("Type 'help' for help. \n")

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
                    output_manager.print("\nUse 'quit' or 'exit' to leave interactive mode.")
                    continue
                except Exception as e:
                    # Handle unexpected errors during prompt processing
                    output_manager.print(f"Error in interactive session: {str(e)}")
                    break

        except (EOFError, KeyboardInterrupt):
            output_manager.print(f"\n{fab_constant.INTERACTIVE_EXIT_MESSAGE}")
        except Exception as e:
            # Handle critical errors that would terminate the session
            output_manager.print(f"\nCritical error in interactive mode: {str(e)}")
            output_manager.print(fab_constant.INTERACTIVE_EXIT_MESSAGE)
        finally:
            self._is_running = False


def start_interactive_mode():
    """Launch interactive mode using singleton pattern"""
    interactive_cli = InteractiveCLI()
    interactive_cli.start_interactive()
