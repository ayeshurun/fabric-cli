# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from argparse import Namespace

import pytest

import fabric_cli.utils.fab_item_util as item_utils
from fabric_cli.client import fab_api_item as item_api
from fabric_cli.commands.fs.export import fab_fs_export_item as _export_item
from fabric_cli.core import fab_constant, fab_state_config
from fabric_cli.core.fab_types import OneLakeItemType
from fabric_cli.core.hiearchy.fab_hiearchy import Item, OneLakeItem, Tenant, Workspace


def test_extract_paths():
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="item_name",
        id="item_id",
        parent=workspace,
        item_type="Lakehouse",
    )
    root_folder = OneLakeItem(
        "Files", "0000", parent=item, nested_type=OneLakeItemType.FOLDER
    )
    lvl1_folder = OneLakeItem(
        "path", "0000", parent=root_folder, nested_type=OneLakeItemType.FOLDER
    )
    lvl2_folder = OneLakeItem(
        "to", "0000", parent=lvl1_folder, nested_type=OneLakeItemType.FOLDER
    )
    lvl3_folder = OneLakeItem(
        "item", "0000", parent=lvl2_folder, nested_type=OneLakeItemType.FILE
    )
    path_id, path_name = item_utils.extract_paths(lvl3_folder)
    assert path_id == "workspace_id/item_id/Files/path/to/item"
    assert (
        path_name == "workspace_name.Workspace/item_name.Lakehouse/Files/path/to/item"
    )


def test_obtain_id_names_for_onelake():
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="item_name",
        id="item_id",
        parent=workspace,
        item_type="Lakehouse",
    )
    root_folder = OneLakeItem(
        "Files", "0000", parent=item, nested_type=OneLakeItemType.FOLDER
    )
    lvl1_folder = OneLakeItem(
        "path", "0000", parent=root_folder, nested_type=OneLakeItemType.FOLDER
    )
    lvl2_folder = OneLakeItem(
        "to", "0000", parent=lvl1_folder, nested_type=OneLakeItemType.FOLDER
    )
    from_item = OneLakeItem(
        "item_from", "0000", parent=lvl2_folder, nested_type=OneLakeItemType.FILE
    )
    to_item = OneLakeItem(
        "item_to", "0000", parent=lvl2_folder, nested_type=OneLakeItemType.FILE
    )
    from_path_id, from_path_name, to_path_id, to_path_name = (
        item_utils.obtain_id_names_for_onelake(from_item, to_item)
    )
    assert from_path_id == "workspace_id/item_id/Files/path/to/item_from"
    assert (
        from_path_name
        == "workspace_name.Workspace/item_name.Lakehouse/Files/path/to/item_from"
    )
    assert to_path_id == "workspace_id/item_id/Files/path/to/item_to"
    assert (
        to_path_name
        == "workspace_name.Workspace/item_name.Lakehouse/Files/path/to/item_to"
    )


def test_get_item_with_definition(monkeypatch):
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    non_export_item = Item(
        name="lh_name",
        id="lh_id",
        parent=workspace,
        item_type="Lakehouse",
    )

    export_item = Item(
        name="nt_name",
        id="ntid",
        parent=workspace,
        item_type="Notebook",
    )

    def mock_export_item(*args, **kwargs):
        return {"item_exported": "item"}

    monkeypatch.setattr(_export_item, "export_single_item", mock_export_item)

    def mock_get_item(*args, **kwargs):
        args = Namespace()
        args.text = json.dumps({"item_non_exported": "item"})
        return args

    monkeypatch.setattr(item_api, "get_item", mock_get_item)

    _args = Namespace()
    item = item_utils.get_item_with_definition(non_export_item, _args)
    assert item == {"item_non_exported": "item"}

    item = item_utils.get_item_with_definition(export_item, _args)
    assert item == {"item_exported": "item"}


def test_build_item_payload__without_definition():
    """Test building payload without definition (used by mkdir)"""
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="notebook_name",
        id="notebook_id",
        parent=workspace,
        item_type="Notebook",
    )

    payload = item_utils.build_item_payload(item, description="Created by fab")

    assert payload == {
        "type": "Notebook",
        "description": "Created by fab",
        "folderId": None,
        "displayName": "notebook_name",
    }


def test_build_item_payload__notebook_with_py_format():
    """Test building Notebook payload with .py format"""
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="notebook_name",
        id="notebook_id",
        parent=workspace,
        item_type="Notebook",
    )
    definition = {
        "parts": [
            {"path": "test.py", "payload": "base64data", "payloadType": "InlineBase64"}
        ]
    }

    payload = item_utils.build_item_payload(
        item, definition=definition, input_format=".py"
    )

    assert payload["type"] == "Notebook"
    assert payload["description"] == "Imported from fab"
    assert payload["displayName"] == "notebook_name"
    assert payload["definition"]["parts"] == definition["parts"]
    # .py format should not have format key
    assert "format" not in payload["definition"]


def test_build_item_payload__notebook_default_format():
    """Test building Notebook payload with default format (fabricGitSource)"""
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="notebook_name",
        id="notebook_id",
        parent=workspace,
        item_type="Notebook",
    )
    definition = {
        "parts": [
            {
                "path": "test.ipynb",
                "payload": "base64data",
                "payloadType": "InlineBase64",
            }
        ]
    }

    # Call without input_format to get default
    payload = item_utils.build_item_payload(item, definition=definition)

    assert payload["type"] == "Notebook"
    assert payload["definition"]["format"] == "fabricGitSource"
    assert payload["definition"]["parts"] == definition["parts"]


def test_build_item_payload__notebook_with_ipynb_format():
    """Test building Notebook payload with .ipynb format"""
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="notebook_name",
        id="notebook_id",
        parent=workspace,
        item_type="Notebook",
    )
    definition = {
        "parts": [
            {
                "path": "test.ipynb",
                "payload": "base64data",
                "payloadType": "InlineBase64",
            }
        ]
    }

    payload = item_utils.build_item_payload(
        item, definition=definition, input_format=".ipynb"
    )

    assert payload["type"] == "Notebook"
    assert payload["definition"]["format"] == "ipynb"
    assert payload["definition"]["parts"] == definition["parts"]


def test_build_item_payload__spark_job_definition():
    """Test building SparkJobDefinition payload"""
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="sjd_name",
        id="sjd_id",
        parent=workspace,
        item_type="SparkJobDefinition",
    )
    definition = {
        "parts": [
            {"path": "main.py", "payload": "base64data", "payloadType": "InlineBase64"}
        ]
    }

    payload = item_utils.build_item_payload(item, definition=definition)

    assert payload["type"] == "SparkJobDefinition"
    assert payload["definition"]["format"] == "SparkJobDefinitionV1"
    assert payload["definition"]["parts"] == definition["parts"]


def test_build_item_payload__report():
    """Test building Report payload (no format wrapper)"""
    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="report_name",
        id="report_id",
        parent=workspace,
        item_type="Report",
    )
    definition = {
        "parts": [
            {
                "path": "report.json",
                "payload": "base64data",
                "payloadType": "InlineBase64",
            }
        ]
    }

    payload = item_utils.build_item_payload(item, definition=definition)

    assert payload["type"] == "Report"
    # Report should use definition directly without format wrapper
    assert payload["definition"] == definition


def test_build_item_payload__unsupported_item_type():
    """Test building payload for unsupported item type raises error"""
    from fabric_cli.core.fab_exceptions import FabricCLIError

    tenant = Tenant(name="tenant_name", id="0000")
    workspace = Workspace(
        name="workspace_name", id="workspace_id", parent=tenant, type="Workspace"
    )
    item = Item(
        name="lakehouse_name",
        id="lakehouse_id",
        parent=workspace,
        item_type="Lakehouse",
    )
    definition = {"parts": []}

    with pytest.raises(FabricCLIError) as exc_info:
        item_utils.build_item_payload(item, definition=definition)

    assert exc_info.value.status_code == fab_constant.ERROR_UNSUPPORTED_COMMAND
