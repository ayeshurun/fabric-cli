# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from argparse import Namespace
from typing import Any, Union

from fabric_cli.core.hiearchy.fab_folder import Folder
from fabric_cli.core.hiearchy.fab_hiearchy import Item
from fabric_cli.utils import fab_cmd_fs_utils as utils_fs
from fabric_cli.utils import fab_jmespath as utils_jmespath
from fabric_cli.utils import fab_ui as utils_ui
from fabric_cli.utils import fab_util as utils


def exec(folder: Folder, args: Namespace) -> None:
    """List folder contents with optional result projection."""
    show_details = bool(args.long)
    query = getattr(args, "query", None)

    ws_elements: list[Union[Item, Folder]] = utils_fs.get_ws_elements(folder)
    sort_elements: Any = utils_fs.sort_ws_elements(
        ws_elements, show_details or bool(query)
    )
    if query:
        sort_elements = utils_jmespath.search(sort_elements, utils.process_nargs(query))

    utils_ui.print_output_format(args, data=sort_elements, show_headers=show_details)
