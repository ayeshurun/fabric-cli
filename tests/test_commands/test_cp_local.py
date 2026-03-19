# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import argparse
import os
import platform
from unittest.mock import patch

import pytest

import fabric_cli.commands.fs.fab_fs_export as fab_export
from fabric_cli.core import fab_constant as constant
from fabric_cli.core import fab_handle_context as handle_context
from fabric_cli.core.fab_types import ItemType
from fabric_cli.core.hiearchy.fab_hiearchy import LocalPath
from tests.test_commands.commands_parser import CLIExecutor
from tests.test_commands.conftest import export_item_with_extension_parameters


class TestCPLocal:
    """E2E tests for cp command with local file system paths (import/export semantics)."""

    # region Item → Local (export via cp)

    @export_item_with_extension_parameters
    def test_cp_item_to_local__export_success(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        tmp_path,
        item_type,
        expected_file_extension,
    ):
        """Export a Fabric item to a local directory via cp."""
        # Setup
        item = item_factory(item_type)

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()

        # Execute command
        cli_executor.exec_command(
            f"cp {item.full_path} {str(tmp_path)} --force"
        )

        # Assert
        export_path = tmp_path / f"{item.display_name}.{item_type.value}"
        assert export_path.is_dir()
        files = list(export_path.iterdir())
        assert len(files) == 2
        assert any(file.suffix == expected_file_extension for file in files)
        assert any(file.name == ".platform" for file in files)
        mock_print_done.assert_called()

    @export_item_with_extension_parameters
    def test_cp_item_to_local__export_home_directory_path_success(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        tmp_path,
        monkeypatch,
        item_type,
        expected_file_extension,
    ):
        """Export a Fabric item to ~/path via cp."""
        # Setup
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        home_dir_env = "USERPROFILE" if platform.system() == "Windows" else "HOME"
        monkeypatch.setenv(home_dir_env, str(home_dir))
        item = item_factory(item_type)
        output_dir = home_dir / "test_cp_export"
        output_dir.mkdir()

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()

        # Execute command using ~/path notation
        cli_executor.exec_command(
            f"cp {item.full_path} ~/test_cp_export --force"
        )

        # Assert
        export_path = output_dir / f"{item.display_name}.{item_type.value}"
        assert export_path.is_dir()
        files = list(export_path.iterdir())
        assert len(files) == 2
        assert any(file.suffix == expected_file_extension for file in files)
        assert any(file.name == ".platform" for file in files)
        mock_print_done.assert_called()

    def test_cp_item_to_local__export_with_format_success(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        tmp_path,
    ):
        """Export a Fabric item with --format flag via cp."""
        # Setup
        item = item_factory(ItemType.NOTEBOOK)

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()

        # Execute command
        cli_executor.exec_command(
            f"cp {item.full_path} {str(tmp_path)} --force --format .py"
        )

        # Assert
        export_path = tmp_path / f"{item.display_name}.Notebook"
        assert export_path.is_dir()
        files = list(export_path.iterdir())
        assert any(file.suffix == ".py" for file in files)
        mock_print_done.assert_called()

    def test_cp_item_to_local__rename_on_export_success(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        tmp_path,
    ):
        """Export a Fabric item with rename: cp item renamed_dir.Notebook."""
        # Setup
        item = item_factory(ItemType.NOTEBOOK)
        renamed_target = tmp_path / "Renamed.Notebook"

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()

        # Execute command – target doesn't exist but parent does and name has dot-suffix
        cli_executor.exec_command(
            f"cp {item.full_path} {str(renamed_target)} --force"
        )

        # Assert – the exported folder should be renamed
        assert renamed_target.is_dir()
        mock_print_done.assert_called()

    def test_cp_item_to_local__nonexistent_path_failure(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        assert_fabric_cli_error,
    ):
        """Cp item to nonexistent local directory raises error."""
        # Setup
        item = item_factory(ItemType.NOTEBOOK)

        # Execute command
        cli_executor.exec_command(
            f"cp {item.full_path} /nonexistent/path --force"
        )

        # Assert
        assert_fabric_cli_error(constant.ERROR_INVALID_PATH)

    # endregion

    # region Local → Item (import via cp)

    def test_cp_local_to_item__import_update_success(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        mock_print_grey,
        tmp_path,
    ):
        """Import (update) a local directory to an existing Fabric item via cp."""
        # Setup – create item then export to get local content
        item = item_factory(ItemType.NOTEBOOK)
        _export_item(item.full_path, output=str(tmp_path))

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()
        mock_print_grey.reset_mock()

        # Execute command – cp local content back to the same item
        cli_executor.exec_command(
            f"cp {str(tmp_path)}/{item.name} {item.full_path} --force"
        )

        # Assert
        mock_print_done.assert_called()

    def test_cp_local_to_item__import_with_format_success(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        mock_print_grey,
        tmp_path,
    ):
        """Import with --format flag via cp."""
        # Setup
        item = item_factory(ItemType.NOTEBOOK)
        _export_item(item.full_path, output=str(tmp_path))

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()
        mock_print_grey.reset_mock()

        # Execute command
        cli_executor.exec_command(
            f"cp {str(tmp_path)}/{item.name} {item.full_path} --force --format .ipynb"
        )

        # Assert
        mock_print_done.assert_called()

    @export_item_with_extension_parameters
    def test_cp_local_to_item__import_home_directory_path_success(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        mock_print_grey,
        tmp_path,
        monkeypatch,
        item_type,
        expected_file_extension,
    ):
        """Import from ~/path via cp."""
        # Setup
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        home_dir_env = "USERPROFILE" if platform.system() == "Windows" else "HOME"
        monkeypatch.setenv(home_dir_env, str(home_dir))
        item = item_factory(item_type)
        _export_item(item.full_path, output=str(home_dir))

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()
        mock_print_grey.reset_mock()

        # Execute command using ~/item.name notation
        cli_executor.exec_command(
            f"cp ~/{item.name} {item.full_path} --force"
        )

        # Assert
        mock_print_done.assert_called()

    def test_cp_local_to_item__nonexistent_local_path_failure(
        self,
        item_factory,
        cli_executor: CLIExecutor,
        assert_fabric_cli_error,
    ):
        """Cp from nonexistent local path to item raises error."""
        # Setup
        item = item_factory(ItemType.NOTEBOOK)

        # Execute command
        cli_executor.exec_command(
            f"cp /nonexistent/path/nb.Notebook {item.full_path} --force"
        )

        # Assert
        assert_fabric_cli_error(constant.ERROR_INVALID_PATH)

    # endregion

    # region Local → Workspace (import via cp)

    def test_cp_local_to_workspace__import_success(
        self,
        item_factory,
        workspace,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        mock_print_grey,
        tmp_path,
    ):
        """Import a local item directory to a workspace via cp."""
        # Setup – create an item, export it, then import via cp to the workspace
        item = item_factory(ItemType.NOTEBOOK)
        _export_item(item.full_path, output=str(tmp_path))

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()
        mock_print_grey.reset_mock()

        # Execute command – cp local exported dir to the workspace
        cli_executor.exec_command(
            f"cp {str(tmp_path)}/{item.name} {workspace.full_path} --force"
        )

        # Assert
        mock_print_done.assert_called()

    # endregion

    # region Local → Folder (import via cp)

    def test_cp_local_to_folder__import_success(
        self,
        item_factory,
        folder_factory,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        mock_print_grey,
        tmp_path,
    ):
        """Import a local item directory to a folder via cp."""
        # Setup
        folder = folder_factory()
        item = item_factory(ItemType.NOTEBOOK)
        _export_item(item.full_path, output=str(tmp_path))

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()
        mock_print_grey.reset_mock()

        # Execute command – cp local exported dir to the folder
        cli_executor.exec_command(
            f"cp {str(tmp_path)}/{item.name} {folder.full_path} --force"
        )

        # Assert
        mock_print_done.assert_called()

    # endregion

    # region Workspace → Local (export via cp)

    def test_cp_workspace_to_local__export_success(
        self,
        item_factory,
        workspace,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        tmp_path,
    ):
        """Export a workspace to a local directory via cp."""
        # Setup – create items in the workspace
        notebook = item_factory(ItemType.NOTEBOOK)
        sjd = item_factory(ItemType.SPARK_JOB_DEFINITION)

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()

        with patch("questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = [
                notebook.name,
                sjd.name,
            ]

            # Execute command
            cli_executor.exec_command(
                f"cp {workspace.full_path} {str(tmp_path)} --force"
            )

            # Assert
            mock_print_done.assert_called()
            mock_print_warning.assert_called_once()

    def test_cp_workspace_to_local__recursive_export_success(
        self,
        item_factory,
        folder_factory,
        workspace,
        cli_executor: CLIExecutor,
        mock_print_done,
        mock_print_warning,
        tmp_path,
    ):
        """Export workspace with --recursive flag via cp."""
        # Setup
        notebook = item_factory(ItemType.NOTEBOOK)
        f1 = folder_factory()
        sjd = item_factory(ItemType.SPARK_JOB_DEFINITION, path=f1.full_path)

        # Reset mock
        mock_print_done.reset_mock()
        mock_print_warning.reset_mock()

        with patch("questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = [
                notebook.name,
                f1.name,
            ]

            # Execute command
            cli_executor.exec_command(
                f"cp {workspace.full_path} {str(tmp_path)} --force --recursive"
            )

            # Assert
            mock_print_done.assert_called()

    def test_cp_workspace_to_local__nonexistent_path_failure(
        self,
        item_factory,
        workspace,
        cli_executor: CLIExecutor,
        assert_fabric_cli_error,
    ):
        """Cp workspace to nonexistent local directory raises error."""
        # Setup
        item_factory(ItemType.NOTEBOOK)

        # Execute command
        cli_executor.exec_command(
            f"cp {workspace.full_path} /nonexistent/path --force"
        )

        # Assert
        assert_fabric_cli_error(constant.ERROR_INVALID_PATH)

    # endregion

    # region Parser & registration

    def test_cp_parser_has_format_flag(self, cli_executor: CLIExecutor):
        """Test that cp parser accepts --format flag."""
        cp_parser = cli_executor._parser.choices.get("cp")
        assert cp_parser is not None

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

    # region LocalPath expanduser

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

    # endregion


# region Helper functions

def _export_item(path, output, force=True):
    """Export a Fabric item to a local directory (setup helper for import tests)."""
    args = argparse.Namespace(
        command="export",
        acl_subcommand="export",
        command_path="export",
        path=path,
        output=output,
        force=force,
    )
    context = handle_context.get_command_context(args.path)
    fab_export.exec_command(args, context)


# endregion
