# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from fabric_cli.commands.tables.fab_tables_load import exec_command
from fabric_cli.core.hiearchy.fab_hiearchy import OneLakeItem


def _create_mock_onelake_item(local_path="Files/data.csv", path_id="/ws-id/item-id/Files/data.csv"):
    mock = MagicMock(spec=OneLakeItem)
    mock.local_path = local_path
    mock.path_id = path_id
    return mock


def _create_mock_response(status_code=202, resource_type="file"):
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.headers = {"x-ms-resource-type": resource_type}
    return mock_response


@patch("fabric_cli.commands.tables.fab_tables_load.utils_ui")
@patch("fabric_cli.commands.tables.fab_tables_load.tables_api")
@patch("fabric_cli.commands.tables.fab_tables_load.onelake_api")
@patch("fabric_cli.commands.tables.fab_tables_load.handle_context")
def test_exec_command__schema_included_in_payload(
    mock_handle_context, mock_onelake_api, mock_tables_api, mock_utils_ui
):
    """When args.schema is set, schemaName should be included in the load table payload."""
    file_context = _create_mock_onelake_item()
    mock_handle_context.get_command_context.return_value = file_context

    mock_onelake_api.get_properties.return_value = _create_mock_response(resource_type="file")
    mock_tables_api.load_table.return_value = _create_mock_response(status_code=202)

    args = Namespace(
        file="Files/data.csv",
        mode="overwrite",
        format=None,
        extension=None,
        schema="dbo",
        table_name="my_table",
        ws_id="ws-123",
        lakehouse_id="lh-456",
    )
    context = _create_mock_onelake_item()

    exec_command(args, context)

    # Verify load_table was called
    mock_tables_api.load_table.assert_called_once()
    call_args = mock_tables_api.load_table.call_args
    payload = json.loads(call_args.kwargs.get("payload") or call_args[1].get("payload") or call_args[0][1])

    assert payload["schemaName"] == "dbo"


@patch("fabric_cli.commands.tables.fab_tables_load.utils_ui")
@patch("fabric_cli.commands.tables.fab_tables_load.tables_api")
@patch("fabric_cli.commands.tables.fab_tables_load.onelake_api")
@patch("fabric_cli.commands.tables.fab_tables_load.handle_context")
def test_exec_command__no_schema_omits_schema_from_payload(
    mock_handle_context, mock_onelake_api, mock_tables_api, mock_utils_ui
):
    """When args.schema is None, schemaName should NOT be in the load table payload."""
    file_context = _create_mock_onelake_item()
    mock_handle_context.get_command_context.return_value = file_context

    mock_onelake_api.get_properties.return_value = _create_mock_response(resource_type="file")
    mock_tables_api.load_table.return_value = _create_mock_response(status_code=202)

    args = Namespace(
        file="Files/data.csv",
        mode="overwrite",
        format=None,
        extension=None,
        schema=None,
        table_name="my_table",
        ws_id="ws-123",
        lakehouse_id="lh-456",
    )
    context = _create_mock_onelake_item()

    exec_command(args, context)

    mock_tables_api.load_table.assert_called_once()
    call_args = mock_tables_api.load_table.call_args
    payload = json.loads(call_args.kwargs.get("payload") or call_args[1].get("payload") or call_args[0][1])

    assert "schemaName" not in payload


@patch("fabric_cli.commands.tables.fab_tables_load.utils_ui")
@patch("fabric_cli.commands.tables.fab_tables_load.tables_api")
@patch("fabric_cli.commands.tables.fab_tables_load.onelake_api")
@patch("fabric_cli.commands.tables.fab_tables_load.handle_context")
def test_exec_command__schema_with_parquet_format(
    mock_handle_context, mock_onelake_api, mock_tables_api, mock_utils_ui
):
    """Schema-enabled lakehouse with parquet format should include both schemaName and correct format."""
    file_context = _create_mock_onelake_item()
    mock_handle_context.get_command_context.return_value = file_context

    mock_onelake_api.get_properties.return_value = _create_mock_response(resource_type="file")
    mock_tables_api.load_table.return_value = _create_mock_response(status_code=200)

    args = Namespace(
        file="Files/data.parquet",
        mode="overwrite",
        format="format=parquet",
        extension=None,
        schema="sales",
        table_name="orders",
        ws_id="ws-123",
        lakehouse_id="lh-456",
    )
    context = _create_mock_onelake_item()

    exec_command(args, context)

    mock_tables_api.load_table.assert_called_once()
    call_args = mock_tables_api.load_table.call_args
    payload = json.loads(call_args.kwargs.get("payload") or call_args[1].get("payload") or call_args[0][1])

    assert payload["schemaName"] == "sales"
    assert payload["formatOptions"]["format"] == "Parquet"


@patch("fabric_cli.commands.tables.fab_tables_load.utils_ui")
@patch("fabric_cli.commands.tables.fab_tables_load.tables_api")
@patch("fabric_cli.commands.tables.fab_tables_load.onelake_api")
@patch("fabric_cli.commands.tables.fab_tables_load.handle_context")
def test_exec_command__folder_with_schema(
    mock_handle_context, mock_onelake_api, mock_tables_api, mock_utils_ui
):
    """Folder load with schema should include schemaName and recursive flag."""
    file_context = _create_mock_onelake_item()
    mock_handle_context.get_command_context.return_value = file_context

    mock_onelake_api.get_properties.return_value = _create_mock_response(resource_type="directory")
    mock_tables_api.load_table.return_value = _create_mock_response(status_code=202)

    args = Namespace(
        file="Files/csv_folder",
        mode="append",
        format=None,
        extension=None,
        schema="dbo",
        table_name="my_table",
        ws_id="ws-123",
        lakehouse_id="lh-456",
    )
    context = _create_mock_onelake_item()

    exec_command(args, context)

    mock_tables_api.load_table.assert_called_once()
    call_args = mock_tables_api.load_table.call_args
    payload = json.loads(call_args.kwargs.get("payload") or call_args[1].get("payload") or call_args[0][1])

    assert payload["schemaName"] == "dbo"
    assert payload["pathType"] == "Folder"
    assert payload["recursive"] is True
    assert payload["mode"] == "Append"
