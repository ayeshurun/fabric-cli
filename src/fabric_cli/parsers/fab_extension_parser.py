# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from argparse import Namespace, _SubParsersAction

from fabric_cli.core import fab_constant
from fabric_cli.utils import fab_output_manager as output_manager


def register_parser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "extension", help=fab_constant.COMMAND_EXTENSIONS_DESCRIPTION
    )
    parser.set_defaults(func=show_help)


def show_help(args: Namespace) -> None:
    output_manager.log_warning(fab_constant.INFO_FEATURE_NOT_SUPPORTED, args.command_path)
