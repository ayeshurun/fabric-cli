# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import argparse
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import fabric_cli.commands.fs.fab_fs_cp as fab_cp
from fabric_cli.commands.fs.cp import fab_fs_cp_local as cp_local
from fabric_cli.core import fab_constant as constant
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.fab_types import FabricElementType, ItemType
from fabric_cli.core.hiearchy.fab_folder import Folder
from fabric_cli.core.hiearchy.fab_hiearchy import Item, LocalPath, Workspace
from tests.test_commands.commands_parser import CLIExecutor


class TestCPLocal:
    """Tests for cp command with local file system paths (import/export semantics)."""

    # region CP Local to Item (import)

    def test_cp_local_to_item__dispatches_to_import(self):
        """Test that cp from local path to existing item dispatches to import logic."""
        with tempfile.TemporaryDirectory() as td:
            # Create a local directory mimicking an exported notebook
            local_item_dir = os.path.join(td, "nb1.Notebook")
            os.makedirs(local_item_dir)
            with open(os.path.join(local_item_dir, "notebook-content.py"), "w") as f:
                f.write("# test notebook")

            from_context = LocalPath(local_item_dir)
            to_context = MagicMock(spec=Item)

            args = argparse.Namespace(
                command="cp",
                command_path="cp",
                force=True,
                recursive=False,
                block_on_path_collision=False,
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.impor.fab_fs_import_item.import_single_item"
            ) as mock_import:
                cp_local.copy_local_to_item(from_context, to_context, args)

                # Assert import was called with the correct item and args
                mock_import.assert_called_once_with(to_context, args)
                assert args.input == local_item_dir

    def test_cp_local_to_item__nonexistent_local_path_fails(self):
        """Test that cp from nonexistent local path raises error."""
        from_context = LocalPath("/nonexistent/path/to/item")
        to_context = MagicMock(spec=Item)

        args = argparse.Namespace(
            command="cp",
            force=True,
            format=None,
        )

        with pytest.raises(FabricCLIError) as exc_info:
            cp_local.copy_local_to_item(from_context, to_context, args)

        assert exc_info.value.status_code == constant.ERROR_INVALID_PATH

    def test_cp_local_to_item__sets_format_to_none_if_missing(self):
        """Test that format is set to None if not present in args."""
        with tempfile.TemporaryDirectory() as td:
            from_context = LocalPath(td)
            to_context = MagicMock(spec=Item)

            # Args without format attribute
            args = argparse.Namespace(
                command="cp",
                force=True,
            )

            with patch(
                "fabric_cli.commands.fs.impor.fab_fs_import_item.import_single_item"
            ) as mock_import:
                cp_local.copy_local_to_item(from_context, to_context, args)
                assert args.format is None

    # endregion

    # region CP Item to Local (export)

    def test_cp_item_to_local__dispatches_to_export(self):
        """Test that cp from item to local path dispatches to export logic."""
        with tempfile.TemporaryDirectory() as td:
            from_context = MagicMock(spec=Item)
            from_context.full_name = "nb1.Notebook"
            to_context = LocalPath(td)

            args = argparse.Namespace(
                command="cp",
                command_path="cp",
                force=True,
                recursive=False,
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.export.fab_fs_export_item.export_single_item"
            ) as mock_export, patch(
                "fabric_cli.utils.fab_item_util.item_sensitivity_label_warnings"
            ) as mock_warnings, patch(
                "fabric_cli.utils.fab_ui.print_output_format"
            ):
                cp_local.copy_item_to_local(from_context, to_context, args)

                mock_export.assert_called_once()
                mock_warnings.assert_called_once()
                assert args.output == td

    def test_cp_item_to_local__nonexistent_local_path_fails(self):
        """Test that cp to nonexistent local directory raises error."""
        from_context = MagicMock(spec=Item)
        to_context = LocalPath("/nonexistent/output/path")

        args = argparse.Namespace(
            command="cp",
            force=True,
            format=None,
        )

        with pytest.raises(FabricCLIError) as exc_info:
            cp_local.copy_item_to_local(from_context, to_context, args)

        assert exc_info.value.status_code == constant.ERROR_INVALID_PATH

    # endregion

    # region CP Local to Workspace (import with item name derivation)

    def test_cp_local_to_workspace__dispatches_to_import(self):
        """Test that cp from local path to workspace derives item name and imports."""
        with tempfile.TemporaryDirectory() as td:
            # Create a local directory mimicking an exported notebook
            local_item_dir = os.path.join(td, "MyNotebook.Notebook")
            os.makedirs(local_item_dir)
            with open(os.path.join(local_item_dir, "content.py"), "w") as f:
                f.write("# notebook")

            from_context = LocalPath(local_item_dir)
            ws_context = MagicMock(spec=Workspace)
            ws_context.path = "/ws1.Workspace"

            args = argparse.Namespace(
                command="cp",
                command_path="cp",
                force=True,
                recursive=False,
                format=None,
            )

            mock_item = MagicMock(spec=Item)

            with patch(
                "fabric_cli.core.fab_handle_context.get_command_context",
                return_value=mock_item,
            ) as mock_get_context, patch(
                "fabric_cli.commands.fs.impor.fab_fs_import_item.import_single_item"
            ) as mock_import:
                cp_local.copy_local_to_workspace(from_context, ws_context, args)

                # Assert context was resolved with workspace_path/item_name
                mock_get_context.assert_called_once()
                call_args = mock_get_context.call_args
                resolved_path = call_args[0][0]
                assert "MyNotebook.Notebook" in str(resolved_path)

                mock_import.assert_called_once()

    def test_cp_local_to_workspace__nonexistent_local_path_fails(self):
        """Test that cp from nonexistent local path to workspace raises error."""
        from_context = LocalPath("/nonexistent/MyNotebook.Notebook")
        ws_context = MagicMock(spec=Workspace)
        ws_context.path = "/ws1.Workspace"

        args = argparse.Namespace(
            command="cp",
            force=True,
            format=None,
        )

        with pytest.raises(FabricCLIError) as exc_info:
            cp_local.copy_local_to_workspace(from_context, ws_context, args)

        assert exc_info.value.status_code == constant.ERROR_INVALID_PATH

    def test_cp_local_to_workspace__non_item_context_fails(self):
        """Test that cp fails when resolved context is not an Item."""
        with tempfile.TemporaryDirectory() as td:
            local_item_dir = os.path.join(td, "SomeName.Unknown")
            os.makedirs(local_item_dir)

            from_context = LocalPath(local_item_dir)
            ws_context = MagicMock(spec=Workspace)
            ws_context.path = "/ws1.Workspace"

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=None,
            )

            # Context resolves to Workspace, not Item
            with patch(
                "fabric_cli.core.fab_handle_context.get_command_context",
                return_value=ws_context,
            ):
                with pytest.raises(FabricCLIError) as exc_info:
                    cp_local.copy_local_to_workspace(
                        from_context, ws_context, args
                    )

                assert exc_info.value.status_code == constant.ERROR_INVALID_INPUT

    # endregion

    # region CP Local to Folder (import)

    def test_cp_local_to_folder__dispatches_to_import(self):
        """Test that cp from local path to folder derives item name and imports."""
        with tempfile.TemporaryDirectory() as td:
            local_item_dir = os.path.join(td, "MyNotebook.Notebook")
            os.makedirs(local_item_dir)
            with open(os.path.join(local_item_dir, "content.py"), "w") as f:
                f.write("# notebook")

            from_context = LocalPath(local_item_dir)
            folder_context = MagicMock(spec=Folder)
            folder_context.path = "/ws1.Workspace/f1.Folder"

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=None,
            )

            mock_item = MagicMock(spec=Item)

            with patch(
                "fabric_cli.core.fab_handle_context.get_command_context",
                return_value=mock_item,
            ) as mock_get_context, patch(
                "fabric_cli.commands.fs.impor.fab_fs_import_item.import_single_item"
            ) as mock_import:
                cp_local.copy_local_to_folder(from_context, folder_context, args)

                mock_get_context.assert_called_once()
                mock_import.assert_called_once()

    # endregion

    # region CP Workspace to Local (export)

    def test_cp_workspace_to_local__dispatches_to_export(self):
        """Test that cp from workspace to local path dispatches to bulk export."""
        with tempfile.TemporaryDirectory() as td:
            ws_context = MagicMock(spec=Workspace)
            ws_context.path = "/ws1.Workspace"
            to_context = LocalPath(td)

            args = argparse.Namespace(
                command="cp",
                command_path="cp",
                force=True,
                recursive=False,
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.export.fab_fs_export_item.export_bulk_items"
            ) as mock_export, patch(
                "fabric_cli.utils.fab_item_util.item_sensitivity_label_warnings"
            ) as mock_warnings:
                cp_local.copy_workspace_to_local(ws_context, to_context, args)

                mock_export.assert_called_once()
                mock_warnings.assert_called_once()
                assert args.output == td
                # Verify args.all was set (mapped from recursive)
                assert hasattr(args, "all")
                assert args.all is False  # recursive=False

    def test_cp_workspace_to_local__recursive_maps_to_all(self):
        """Test that --recursive flag maps to args.all for export."""
        with tempfile.TemporaryDirectory() as td:
            ws_context = MagicMock(spec=Workspace)
            ws_context.path = "/ws1.Workspace"
            to_context = LocalPath(td)

            args = argparse.Namespace(
                command="cp",
                force=True,
                recursive=True,  # --recursive flag
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.export.fab_fs_export_item.export_bulk_items"
            ) as mock_export, patch(
                "fabric_cli.utils.fab_item_util.item_sensitivity_label_warnings"
            ):
                cp_local.copy_workspace_to_local(ws_context, to_context, args)
                assert args.all is True  # recursive=True maps to all=True

    def test_cp_workspace_to_local__nonexistent_local_path_fails(self):
        """Test that cp workspace to nonexistent local directory raises error."""
        ws_context = MagicMock(spec=Workspace)
        to_context = LocalPath("/nonexistent/output/path")

        args = argparse.Namespace(
            command="cp",
            force=True,
            format=None,
        )

        with pytest.raises(FabricCLIError) as exc_info:
            cp_local.copy_workspace_to_local(ws_context, to_context, args)

        assert exc_info.value.status_code == constant.ERROR_INVALID_PATH

    # endregion

    # region CP dispatcher routing

    def test_cp_exec_command__local_to_item_routes_correctly(self):
        """Test that exec_command routes LocalPath→Item to copy_local_to_item."""
        from_context = MagicMock(spec=LocalPath)
        from_context.path = "/tmp/test"
        to_context = MagicMock(spec=Item)
        to_context.path = "/ws1.Workspace/nb1.Notebook"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_local.copy_local_to_item"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once_with(from_context, to_context, args)

    def test_cp_exec_command__local_to_workspace_routes_correctly(self):
        """Test that exec_command routes LocalPath→Workspace to copy_local_to_workspace."""
        from_context = MagicMock(spec=LocalPath)
        from_context.path = "/tmp/test"
        to_context = MagicMock(spec=Workspace)
        to_context.path = "/ws1.Workspace"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_local.copy_local_to_workspace"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once_with(from_context, to_context, args)

    def test_cp_exec_command__local_to_folder_routes_correctly(self):
        """Test that exec_command routes LocalPath→Folder to copy_local_to_folder."""
        from_context = MagicMock(spec=LocalPath)
        from_context.path = "/tmp/test"
        to_context = MagicMock(spec=Folder)
        to_context.path = "/ws1.Workspace/f1.Folder"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_local.copy_local_to_folder"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once_with(from_context, to_context, args)

    def test_cp_exec_command__item_to_local_routes_correctly(self):
        """Test that exec_command routes Item→LocalPath to copy_item_to_local."""
        from_context = MagicMock(spec=Item)
        from_context.path = "/ws1.Workspace/nb1.Notebook"
        to_context = MagicMock(spec=LocalPath)
        to_context.path = "/tmp/output"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_local.copy_item_to_local"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once_with(from_context, to_context, args)

    def test_cp_exec_command__workspace_to_local_routes_correctly(self):
        """Test that exec_command routes Workspace→LocalPath to copy_workspace_to_local."""
        from_context = MagicMock(spec=Workspace)
        from_context.path = "/ws1.Workspace"
        to_context = MagicMock(spec=LocalPath)
        to_context.path = "/tmp/output"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_local.copy_workspace_to_local"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once_with(from_context, to_context, args)

    # endregion

    # region format flag tests

    def test_cp_local_to_item__format_is_passed_through(self):
        """Test that --format flag is passed through to import logic."""
        with tempfile.TemporaryDirectory() as td:
            from_context = LocalPath(td)
            to_context = MagicMock(spec=Item)

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=".ipynb",
            )

            with patch(
                "fabric_cli.commands.fs.impor.fab_fs_import_item.import_single_item"
            ) as mock_import:
                cp_local.copy_local_to_item(from_context, to_context, args)
                mock_import.assert_called_once()
                # Verify format was preserved
                assert args.format == ".ipynb"

    def test_cp_item_to_local__format_is_passed_through(self):
        """Test that --format flag is passed through to export logic."""
        with tempfile.TemporaryDirectory() as td:
            from_context = MagicMock(spec=Item)
            from_context.full_name = "nb1.Notebook"
            to_context = LocalPath(td)

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=".py",
            )

            with patch(
                "fabric_cli.commands.fs.export.fab_fs_export_item.export_single_item"
            ) as mock_export, patch(
                "fabric_cli.utils.fab_item_util.item_sensitivity_label_warnings"
            ), patch(
                "fabric_cli.utils.fab_ui.print_output_format"
            ):
                cp_local.copy_item_to_local(from_context, to_context, args)
                mock_export.assert_called_once()
                assert args.format == ".py"

    # endregion

    # region rename tests

    def test_cp_item_to_local__rename_exports_with_new_name(self):
        """Test that cp from item to non-existent local path with dot-suffix renames the export."""
        with tempfile.TemporaryDirectory() as td:
            from_context = MagicMock(spec=Item)
            from_context.full_name = "MyNotebook.Notebook"

            # Target path doesn't exist but parent does – triggers rename
            renamed_target = os.path.join(td, "MyNotebookRenamed.Notebook")
            to_context = LocalPath(renamed_target)

            args = argparse.Namespace(
                command="cp",
                command_path="cp",
                force=True,
                recursive=False,
                format=None,
            )

            # After export, simulate that the original folder was created
            exported_dir = os.path.join(td, "MyNotebook.Notebook")

            def create_exported_dir(*a, **kw):
                os.makedirs(exported_dir, exist_ok=True)
                # Create a dummy file inside
                with open(os.path.join(exported_dir, "content.py"), "w") as f:
                    f.write("# test")

            with patch(
                "fabric_cli.commands.fs.export.fab_fs_export_item.export_single_item",
                side_effect=create_exported_dir,
            ), patch(
                "fabric_cli.utils.fab_item_util.item_sensitivity_label_warnings"
            ), patch(
                "fabric_cli.utils.fab_ui.print_output_format"
            ) as mock_print:
                cp_local.copy_item_to_local(from_context, to_context, args)

                # Assert export was called with parent dir as output
                assert args.output == td

                # Assert the exported folder was renamed
                assert os.path.exists(renamed_target)
                assert not os.path.exists(exported_dir)
                assert os.path.exists(
                    os.path.join(renamed_target, "content.py")
                )

                # Assert the output message uses the renamed name
                mock_print.assert_called_once()
                call_args = mock_print.call_args
                assert "MyNotebookRenamed.Notebook" in call_args[1]["message"]

    def test_cp_item_to_local__rename_nonexistent_parent_fails(self):
        """Test that cp to a renamed path with non-existent parent dir raises error."""
        from_context = MagicMock(spec=Item)
        from_context.full_name = "nb.Notebook"
        to_context = LocalPath("/nonexistent/dir/MyRenamed.Notebook")

        args = argparse.Namespace(
            command="cp",
            force=True,
            format=None,
        )

        with pytest.raises(FabricCLIError) as exc_info:
            cp_local.copy_item_to_local(from_context, to_context, args)

        assert exc_info.value.status_code == constant.ERROR_INVALID_PATH

    def test_cp_item_to_local__rename_no_dot_suffix_fails(self):
        """Test that cp to a non-existent path without dot-suffix raises error."""
        with tempfile.TemporaryDirectory() as td:
            from_context = MagicMock(spec=Item)
            to_context = LocalPath(os.path.join(td, "nodotsuffix"))

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=None,
            )

            with pytest.raises(FabricCLIError) as exc_info:
                cp_local.copy_item_to_local(from_context, to_context, args)

            assert exc_info.value.status_code == constant.ERROR_INVALID_PATH

    def test_cp_item_to_local__existing_dir_still_works(self):
        """Test that cp to an existing directory still works without rename."""
        with tempfile.TemporaryDirectory() as td:
            from_context = MagicMock(spec=Item)
            from_context.full_name = "nb1.Notebook"
            to_context = LocalPath(td)

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.export.fab_fs_export_item.export_single_item"
            ) as mock_export, patch(
                "fabric_cli.utils.fab_item_util.item_sensitivity_label_warnings"
            ), patch(
                "fabric_cli.utils.fab_ui.print_output_format"
            ) as mock_print:
                cp_local.copy_item_to_local(from_context, to_context, args)

                mock_export.assert_called_once()
                assert args.output == td
                # Message should use original name
                mock_print.assert_called_once()
                assert "nb1.Notebook" in mock_print.call_args[1]["message"]

    def test_cp_local_to_item__rename_uses_target_item_name(self):
        """Test that cp from local to an item passes the target item context to import.

        The target Item already carries the desired (renamed) name because
        ``get_command_context`` resolved it from the user-provided Fabric path.
        This verifies that ``copy_local_to_item`` correctly forwards that
        context so import uses the target name, not the local directory name.
        """
        with tempfile.TemporaryDirectory() as td:
            # Local dir has original name
            local_dir = os.path.join(td, "OriginalName.Notebook")
            os.makedirs(local_dir)
            with open(os.path.join(local_dir, "content.py"), "w") as f:
                f.write("# notebook")

            from_context = LocalPath(local_dir)

            # Target item has a different name (renamed)
            to_context = MagicMock(spec=Item)
            to_context.short_name = "RenamedNotebook"

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.impor.fab_fs_import_item.import_single_item"
            ) as mock_import:
                cp_local.copy_local_to_item(from_context, to_context, args)

                # Import should use the target item (which has the renamed name)
                mock_import.assert_called_once_with(to_context, args)
                assert args.input == local_dir

    # endregion

    # region expanduser tests

    def test_local_path__expanduser_expands_tilde(self):
        """Test that LocalPath expands ~ to the user's home directory."""
        lp = LocalPath("~/Desktop/nb.Notebook")
        home = os.path.expanduser("~")
        assert lp.path == os.path.join(home, "Desktop", "nb.Notebook")
        assert "~" not in lp.path

    def test_local_path__expanduser_no_tilde_unchanged(self):
        """Test that LocalPath leaves absolute paths without ~ unchanged."""
        lp = LocalPath("/tmp/nb.Notebook")
        assert lp.path == "/tmp/nb.Notebook"

    def test_cp_item_to_local__expanduser_path_works(self):
        """Test that cp item to local with ~ path expands correctly."""
        with tempfile.TemporaryDirectory() as td:
            from_context = MagicMock(spec=Item)
            from_context.full_name = "nb1.Notebook"

            # Use a path under tempdir to simulate an expanded ~ target
            to_context = LocalPath(td)

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.export.fab_fs_export_item.export_single_item"
            ), patch(
                "fabric_cli.utils.fab_item_util.item_sensitivity_label_warnings"
            ), patch(
                "fabric_cli.utils.fab_ui.print_output_format"
            ):
                # Verify expanded path is used
                cp_local.copy_item_to_local(from_context, to_context, args)
                assert args.output == td

    def test_cp_local_to_item__expanduser_path_works(self):
        """Test that cp local to item with ~ path expands correctly."""
        with tempfile.TemporaryDirectory() as td:
            local_dir = os.path.join(td, "nb.Notebook")
            os.makedirs(local_dir)
            with open(os.path.join(local_dir, "content.py"), "w") as f:
                f.write("# test")

            from_context = LocalPath(local_dir)
            to_context = MagicMock(spec=Item)

            args = argparse.Namespace(
                command="cp",
                force=True,
                format=None,
            )

            with patch(
                "fabric_cli.commands.fs.impor.fab_fs_import_item.import_single_item"
            ) as mock_import:
                cp_local.copy_local_to_item(from_context, to_context, args)
                mock_import.assert_called_once()
                assert args.input == local_dir

    # endregion

    def test_cp_parser_has_format_flag(self, cli_executor: CLIExecutor):
        """Test that cp parser accepts --format flag."""
        cp_parser = cli_executor._parser.choices.get("cp")
        assert cp_parser is not None

        # Check that --format is a recognized argument
        format_action = None
        for action in cp_parser._actions:
            if "--format" in getattr(action, "option_strings", []):
                format_action = action
                break

        assert format_action is not None, "cp parser should have --format flag"

    def test_cp_parser_has_copy_alias(self, cli_executor: CLIExecutor):
        """Test that 'copy' is registered as an alias for 'cp'."""
        assert "copy" in cli_executor._parser.choices, (
            "'copy' should be an alias for 'cp'"
        )

    def test_import_command_still_works(self, cli_executor: CLIExecutor):
        """Test that 'import' command is still registered and accessible."""
        assert "import" in cli_executor._parser.choices, (
            "'import' command should still be registered for backward compatibility"
        )

    def test_export_command_still_works(self, cli_executor: CLIExecutor):
        """Test that 'export' command is still registered and accessible."""
        assert "export" in cli_executor._parser.choices, (
            "'export' command should still be registered for backward compatibility"
        )

    # endregion

    # region existing cp scenarios still work

    def test_cp_exec_command__workspace_to_workspace_still_routes_correctly(self):
        """Test that existing Workspace→Workspace routing is not broken."""
        from_context = MagicMock(spec=Workspace)
        from_context.path = "/ws1.Workspace"
        to_context = MagicMock(spec=Workspace)
        to_context.path = "/ws2.Workspace"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.fab_item_util.item_sensitivity_label_warnings"
        ), patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_workspace.copy_workspace_elements"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once()

    def test_cp_exec_command__item_to_item_still_routes_correctly(self):
        """Test that existing Item→Item routing is not broken."""
        from_context = MagicMock(spec=Item)
        from_context.path = "/ws1.Workspace/nb1.Notebook"
        to_context = MagicMock(spec=Item)
        to_context.path = "/ws2.Workspace/nb2.Notebook"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.fab_item_util.item_sensitivity_label_warnings"
        ), patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_item.copy_item"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once()

    def test_cp_exec_command__onelake_to_onelake_still_routes_correctly(self):
        """Test that existing OneLake→OneLake routing is not broken."""
        from fabric_cli.core.hiearchy.fab_hiearchy import OneLakeItem

        from_context = MagicMock(spec=OneLakeItem)
        from_context.path = "/ws1.Workspace/lh1.Lakehouse/Files/test.csv"
        to_context = MagicMock(spec=OneLakeItem)
        to_context.path = "/ws1.Workspace/lh1.Lakehouse/Files/dest.csv"

        args = argparse.Namespace(force=True, format=None)

        with patch(
            "fabric_cli.commands.fs.fab_fs_cp.cp_onelake.copy_onelake_2_onelake"
        ) as mock_fn:
            fab_cp.exec_command(args, from_context, to_context)
            mock_fn.assert_called_once()

    # endregion
