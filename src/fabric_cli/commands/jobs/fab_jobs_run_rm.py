# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from argparse import Namespace

from fabric_cli.client import fab_api_jobs as jobs_api
from fabric_cli.core import fab_constant
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.hiearchy.fab_hiearchy import Item
from fabric_cli.utils import fab_output_manager as output_manager


def exec_command(args: Namespace, context: Item) -> None:
    if not args.force:
        output_manager.print_warning(f"You are about to delete schedule '{args.schedule_id}' from '{context.full_name}'. This action cannot be undone.")

    if args.force or output_manager.prompt_confirm():
        output_manager.print_grey(f"Removing job schedule '{args.schedule_id}'... from '{context.full_name}'")

        response = jobs_api.remove_item_schedule(args)

        if response.status_code == 200:
            output_manager.print_output_format(
                args,
                message=f"Job schedule '{args.schedule_id}' removed",
            )