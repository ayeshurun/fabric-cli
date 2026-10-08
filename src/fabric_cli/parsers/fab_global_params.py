# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import argparse


class _OutputFormatAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        namespace.output_format = "json" if option_string == "--json" else values
        namespace.compact_json = option_string == "--json"


def add_global_flags(parser) -> None:
    """
    Add global flags that apply to all commands.

    Args:
        parser: The argparse parser to add flags to.
    """
    # Add help flag
    parser.add_argument("-help", action="help")

    # Add format flag to override output format
    parser.add_argument(
        "--output_format",
        required=False,
        action=_OutputFormatAction,
        default=argparse.SUPPRESS,
        choices=["json", "text"],
        help="Override output format type. Optional",
    )
    parser.add_argument(
        "--json",
        action=_OutputFormatAction,
        nargs=0,
        dest="output_format",
        default=argparse.SUPPRESS,
        help="Print compact JSON, preserving status and diagnostics. Optional",
    )

    parser.add_argument(
        "--skill",
        required=False,
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )


def add_output_queries(parser: argparse.ArgumentParser) -> None:
    """Add result queries to leaf commands without command-specific queries."""
    subparsers = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    if subparsers:
        for action in subparsers:
            for child in set(action.choices.values()):
                add_output_queries(child)
    elif "-q" not in parser._option_string_actions:
        parser.add_argument(
            "-q",
            "--query",
            dest="output_query",
            metavar="EXPRESSION",
            help="Apply JMESPath to result data, not status or diagnostics. Optional",
        )
