# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Copy between local file system and Fabric items.

This module bridges the `cp` command with the existing import/export logic,
enabling POSIX-style `cp <local_path> <fabric_path>` and
`cp <fabric_path> <local_path>` workflows.
"""

import os
import shutil
from argparse import Namespace

from fabric_cli.core import fab_constant
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.hiearchy.fab_folder import Folder
from fabric_cli.core.hiearchy.fab_hiearchy import Item, LocalPath, Workspace
from fabric_cli.utils import fab_ui


def copy_local_to_item(
    from_context: LocalPath, to_context: Item, args: Namespace
) -> None:
    """Copy (import) a local directory into a Fabric item."""
    from fabric_cli.commands.fs.impor import fab_fs_import_item as import_item

    local_path = from_context.path

    # Validate local path exists
    if not os.path.exists(local_path):
        raise FabricCLIError(
            f"Local path '{local_path}' does not exist",
            fab_constant.ERROR_INVALID_PATH,
        )

    # Build args compatible with import_single_item
    args.input = local_path

    if not hasattr(args, "format"):
        args.format = None

    import_item.import_single_item(to_context, args)


def _copy_local_to_container(
    from_context: LocalPath,
    to_context,
    args: Namespace,
) -> None:
    """Copy (import) a local item directory into a Fabric workspace or folder.

    The local path must be a directory whose name contains the item type
    in dot-suffix format (e.g., ``MyNotebook.Notebook``).
    """
    from fabric_cli.core import fab_handle_context as handle_context

    local_path = from_context.path

    # Validate local path exists
    if not os.path.exists(local_path):
        raise FabricCLIError(
            f"Local path '{local_path}' does not exist",
            fab_constant.ERROR_INVALID_PATH,
        )

    # Derive item name from the local directory/file name
    base_name = os.path.basename(local_path.rstrip(os.sep))

    # Build the target Fabric path: container_path/item_name
    target_item_path = f"{to_context.path}/{base_name}"

    # Resolve the target context (may or may not exist yet)
    args.path = [target_item_path]
    target_context = handle_context.get_command_context(
        args.path, raise_error=False
    )

    if isinstance(target_context, Item):
        copy_local_to_item(from_context, target_context, args)
    else:
        raise FabricCLIError(
            f"Cannot determine target item from '{base_name}'. "
            "Use the full item path with type suffix (e.g., MyNotebook.Notebook)",
            fab_constant.ERROR_INVALID_INPUT,
        )


def copy_local_to_workspace(
    from_context: LocalPath, to_context: Workspace, args: Namespace
) -> None:
    """Copy (import) a local item directory into a Fabric workspace."""
    _copy_local_to_container(from_context, to_context, args)


def copy_local_to_folder(
    from_context: LocalPath, to_context: Folder, args: Namespace
) -> None:
    """Copy (import) a local item directory into a Fabric folder."""
    _copy_local_to_container(from_context, to_context, args)


def copy_item_to_local(
    from_context: Item, to_context: LocalPath, args: Namespace
) -> None:
    """Copy (export) a Fabric item to a local directory.

    If the target local path does not exist but its parent directory does,
    and the target basename contains a dot-suffix (e.g., ``MyRenamed.Notebook``),
    the item is exported into the parent directory and then renamed to the
    requested name.  This enables
    ``cp ws.Workspace/MyNotebook.Notebook /local/MyRenamed.Notebook``.
    """
    from fabric_cli.commands.fs.export import fab_fs_export_item as export_item
    from fabric_cli.utils import fab_item_util

    local_path = to_context.path
    rename_to: str | None = None

    if os.path.exists(local_path):
        # Target exists and is a directory – export directly into it
        export_dir = local_path
    else:
        # Target does not exist – check if this is a rename request
        parent_dir = os.path.dirname(local_path)
        target_name = os.path.basename(local_path.rstrip(os.sep))

        if parent_dir and os.path.isdir(parent_dir) and "." in target_name:
            # Looks like a rename: parent exists, target has a type suffix
            export_dir = parent_dir
            rename_to = target_name
        else:
            raise FabricCLIError(
                f"Local path '{local_path}' does not exist",
                fab_constant.ERROR_INVALID_PATH,
            )

    fab_item_util.item_sensitivity_label_warnings(args, "exported")

    # Build args compatible with export_single_item
    args.output = export_dir

    if not hasattr(args, "format"):
        args.format = None

    export_item.export_single_item(from_context, args)

    # If a rename was requested, rename the exported folder
    if rename_to is not None:
        exported_path = os.path.join(export_dir, from_context.full_name)
        renamed_path = os.path.join(export_dir, rename_to)
        if os.path.exists(exported_path) and exported_path != renamed_path:
            if os.path.exists(renamed_path):
                if not getattr(args, "force", False):
                    raise FabricCLIError(
                        f"Target path '{renamed_path}' already exists. Use --force to overwrite.",
                        fab_constant.ERROR_INVALID_INPUT,
                    )
                shutil.rmtree(renamed_path)
            os.rename(exported_path, renamed_path)

    display_name = rename_to if rename_to else from_context.full_name
    fab_ui.print_output_format(args, message=f"'{display_name}' exported")


def copy_workspace_to_local(
    from_context: Workspace, to_context: LocalPath, args: Namespace
) -> None:
    """Copy (export) workspace items to a local directory."""
    from fabric_cli.commands.fs.export import fab_fs_export_item as export_item
    from fabric_cli.utils import fab_item_util

    local_path = to_context.path

    # Validate local directory exists
    if not os.path.exists(local_path):
        raise FabricCLIError(
            f"Local path '{local_path}' does not exist",
            fab_constant.ERROR_INVALID_PATH,
        )

    fab_item_util.item_sensitivity_label_warnings(args, "exported")

    # Build args compatible with export_bulk_items
    args.output = local_path

    # Map --recursive to args.all for export_bulk_items compatibility
    if not hasattr(args, "all"):
        args.all = getattr(args, "recursive", False)

    if not hasattr(args, "format"):
        args.format = None

    export_item.export_bulk_items(from_context, args)
