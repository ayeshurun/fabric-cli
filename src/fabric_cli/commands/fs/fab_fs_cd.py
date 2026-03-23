# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from argparse import Namespace

from fabric_cli.core.fab_context import Context
from fabric_cli.core.hiearchy.fab_hiearchy import FabricElement, Tenant
from fabric_cli.utils import fab_output_manager as output_manager


def exec_command(args: Namespace, context: FabricElement) -> None:
    _change_context(context, args)

def _change_context(context: FabricElement, args: Namespace) -> None:
    Context().context = context
    text_message = "Switched to root" if isinstance(context, Tenant) else f"Switched to '{context.name}'"
    output_manager.print_output_format(args, message=text_message)
