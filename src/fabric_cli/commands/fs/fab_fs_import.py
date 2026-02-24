# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import importlib
from argparse import Namespace

import_item = importlib.import_module("fabric_cli.commands.fs.import.fab_fs_import_item")
from fabric_cli.core.hiearchy.fab_hiearchy import FabricElement, Item
from fabric_cli.utils import fab_util as utils


def exec_command(args: Namespace, context: FabricElement) -> None:
    args.input = utils.process_nargs(args.input)

    if isinstance(context, Item):
        import_item.import_single_item(context, args)
