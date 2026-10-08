# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Regression tests for native command query results and diagnostics."""

import inspect
import json
from argparse import Namespace
from typing import Any
from unittest.mock import Mock, patch

import pytest
from requests.structures import CaseInsensitiveDict

from fabric_cli.client.fab_api_types import ApiResponse
from fabric_cli.commands.acls import fab_acls_get
from fabric_cli.commands.api import fab_api_request
from fabric_cli.commands.find import fab_find
from fabric_cli.commands.fs.ls import fab_fs_ls_folder
from fabric_cli.core import fab_constant
from fabric_cli.core.fab_decorators import handle_exceptions
from fabric_cli.core.fab_exceptions import FabricAPIError, FabricCLIError
from fabric_cli.core.hiearchy.fab_folder import Folder
from fabric_cli.core.hiearchy.fab_item import Item
from fabric_cli.utils import fab_cmd_get_utils, fab_cmd_ls_utils, fab_jmespath


def _args(**values: Any) -> Namespace:
    defaults = {
        "command": "api",
        "command_path": "api",
        "output_format": "json",
        "compact_json": True,
        "output": None,
        "query": None,
        "endpoint": "workspaces",
        "input": None,
        "file_path": None,
        "show_headers": False,
        "long": False,
        "params": None,
        "search_text": "",
    }
    defaults.update(values)
    return Namespace(**defaults)


def _response(status: int, text: str) -> ApiResponse:
    return ApiResponse(status, text, text.encode(), CaseInsensitiveDict())


def _assert_result(capsys: pytest.CaptureFixture[str], expected: Any) -> str:
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "Success"
    wrapped = expected if isinstance(expected, list) else [expected]
    assert output["result"]["data"] == wrapped
    if not isinstance(expected, list):
        assert type(output["result"]["data"][0]) is type(expected)
    return captured.err


@pytest.mark.parametrize("value", [False, 0, [], {}, "", None])
def test_api_query_preserves_native_result(
    value: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(query=["text.value"])
    with (
        patch.object(
            fab_api_request.fabric_api,
            "do_request",
            return_value=_response(200, json.dumps({"value": value})),
        ),
        patch.object(fab_jmespath, "search", wraps=fab_jmespath.search) as search,
    ):
        fab_api_request.exec_command(args)
    search.assert_called_once()
    _assert_result(capsys, value)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
@pytest.mark.parametrize(
    "body",
    [
        '{"errorCode":"TestFailure","message":"access denied","requestId":"test-request"}',
        "Service unavailable",
        "",
    ],
)
def test_api_http_failure_cannot_be_projected_into_success(
    status: int, body: str, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(query=["`false`"], output_query="`null`")
    with (
        patch.object(
            fab_api_request.fabric_api,
            "do_request",
            return_value=_response(status, body),
        ),
        patch.object(fab_jmespath, "search") as search,
    ):
        exit_code = handle_exceptions()(fab_api_request.exec_command)(args)
    assert exit_code != 0
    search.assert_not_called()
    captured = capsys.readouterr()
    failure = json.loads(captured.out)
    assert failure["status"] == "Failure"
    assert str(status) in failure["result"]["message"]
    assert body in failure["result"]["message"]


@pytest.mark.parametrize("command", ["get", "acl", "ls"])
@pytest.mark.parametrize("value", [False, 0, [], {}, "", None])
def test_read_commands_emit_native_query_results(
    command: str, value: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(command=command, query="`" + json.dumps(value) + "`")
    with patch.object(fab_jmespath, "search", wraps=fab_jmespath.search) as search:
        if command == "get":
            fab_cmd_get_utils.query_and_export({"id": "item"}, args, "item")
        elif command == "acl":
            fab_acls_get._process_query_and_export([], "workspace", args)
        else:
            fab_cmd_ls_utils.format_and_print_output([], args, False)
    search.assert_called_once()
    _assert_result(capsys, value)


@pytest.mark.parametrize("compact", [False, True])
def test_onelake_acl_disabled_security_preserves_failure_and_advisory(
    compact: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(command="acl", query="`false`", compact_json=compact)
    context = Mock()
    context.workspace.name = "workspace.Workspace"
    context.workspace.id = "workspace-id"
    context.item.name = "lakehouse.Lakehouse"
    context.item.id = "lakehouse-id"
    error = FabricAPIError(
        '{"errorCode":"BadRequest","message":"Security is disabled"}'
    )

    @handle_exceptions()
    def run(command_args: Namespace) -> None:
        fab_acls_get._get_acls_onelake(context, command_args)

    with (
        patch.object(
            fab_acls_get.api_onelake, "acl_list_data_access_roles", side_effect=error
        ),
        patch.object(fab_jmespath, "search") as search,
    ):
        exit_code = run(args)
    assert exit_code != 0
    search.assert_not_called()
    captured = capsys.readouterr()
    failure = json.loads(captured.out)
    assert failure["status"] == "Failure"
    assert (
        failure["result"]["error_code"]
        == fab_constant.ERROR_UNIVERSAL_SECURITY_DISABLED
    )
    assert "open /workspace.Workspace/lakehouse.Lakehouse" in captured.err
    assert "enable it" in captured.err
    assert (len(captured.out.splitlines()) == 1) is compact


def test_ls_projection_retains_hidden_collection_diagnostics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = _args(command="ls", query=["length(@)"])
    fab_cmd_ls_utils.format_and_print_output(
        [], args, False, hidden_data=[".capacities"]
    )
    result = json.loads(capsys.readouterr().out)["result"]
    assert result["data"] == [0]
    assert result["hidden_data"] == [".capacities"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("length(@)", 1),
        ("[?name == 'missing']", []),
        ("`false`", False),
        ("`0`", 0),
        ("missing", None),
        ("[].id", ["item-id"]),
        (None, [{"name": "notebook", "id": "item-id", "type": "Notebook"}]),
    ],
)
def test_folder_ls_applies_query_once_and_preserves_default_rows(
    query: str | None, expected: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(command="ls", query=[query] if query else None)
    rows = [{"name": "notebook", "id": "item-id", "type": "Notebook"}]
    with (
        patch.object(fab_fs_ls_folder.utils_fs, "get_ws_elements", return_value=[]),
        patch.object(fab_fs_ls_folder.utils_fs, "sort_ws_elements", return_value=rows),
        patch.object(fab_jmespath, "search", wraps=fab_jmespath.search) as search,
    ):
        fab_fs_ls_folder.exec(Mock(spec=Folder), args)
    assert search.call_count == (1 if query else 0)
    _assert_result(capsys, expected)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("[].id", ["item-id"]),
        ("[0]", {"name": "notebook.Notebook", "id": "item-id"}),
        (None, [{"name": "notebook.Notebook"}]),
    ],
)
def test_folder_ls_queries_ids_before_default_column_projection(
    query: str | None, expected: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = Folder("parent", "folder-id", Mock(spec=Folder))
    item = Item("notebook", "item-id", folder, "Notebook")
    args = _args(command="ls", query=[query] if query else None, long=False)
    with (
        patch.object(fab_fs_ls_folder.utils_fs, "get_ws_elements", return_value=[item]),
        patch.object(fab_jmespath, "search", wraps=fab_jmespath.search) as search,
    ):
        fab_fs_ls_folder.exec(folder, args)
    assert search.call_count == (1 if query else 0)
    _assert_result(capsys, expected)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("`false`", False),
        ("length(@)", 0),
        ("`null`", None),
        ("`{}`", {}),
        ('`""`', ""),
        ("[]", []),
        (None, []),
    ],
)
def test_find_empty_json_results_accept_all_query_types(
    query: str | None, expected: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(command="find", query=query)
    with (
        patch.object(fab_find, "_fetch_results", return_value=([], None)),
        patch.object(fab_jmespath, "search", wraps=fab_jmespath.search) as search,
    ):
        fab_find._find_commandline(args, {})
    assert search.call_count == (1 if query else 0)
    diagnostics = _assert_result(capsys, expected)
    assert "No items found" not in diagnostics


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("length(@)", 1),
        ("[0]", {"name": "notebook", "type": "Notebook", "workspace": None}),
        ("[0].name", "notebook"),
        ("`false`", False),
        ("missing", None),
        ("[?name == 'missing']", []),
    ],
)
def test_find_nonempty_json_results_accept_all_query_types(
    query: str, expected: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(command="find", query=query)
    with patch.object(
        fab_find,
        "_fetch_results",
        return_value=([{"displayName": "notebook", "type": "Notebook"}], None),
    ):
        fab_find._find_commandline(args, {})
    diagnostics = _assert_result(capsys, expected)
    assert "No items found" not in diagnostics


def test_find_json_collects_pages_without_truncation_or_prompts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    name = "long notebook name " * 40
    args = _args(command="find", fab_mode=fab_constant.FAB_MODE_INTERACTIVE)
    with (
        patch.object(
            fab_find,
            "_fetch_results",
            side_effect=[
                ([{"displayName": name, "type": "Notebook"}], "next"),
                ([{"displayName": "second", "type": "Notebook"}], None),
            ],
        ) as fetch,
        patch("builtins.input") as prompt,
    ):
        inspect.unwrap(fab_find.find_command)(args)
    prompt.assert_not_called()
    assert fetch.call_count == 2
    _assert_result(
        capsys,
        [
            {"name": name, "type": "Notebook", "workspace": None},
            {"name": "second", "type": "Notebook", "workspace": None},
        ],
    )


@pytest.mark.parametrize("interactive", [False, True])
@pytest.mark.parametrize("value", [False, 0, None])
def test_find_scalar_text_is_not_reported_as_empty(
    interactive: bool, value: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(
        command="find", output_format="text", query="`" + json.dumps(value) + "`"
    )
    with (
        patch.object(fab_find, "_fetch_results", return_value=([], None)),
        patch.object(fab_find.utils_ui, "print_output_format") as output,
    ):
        if interactive:
            fab_find._find_interactive(args, {})
        else:
            fab_find._find_commandline(args, {})
    output.assert_called_once()
    assert output.call_args.kwargs["data"] is value
    assert "No items found" not in capsys.readouterr().err


def test_find_empty_text_preserves_no_items_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = _args(command="find", output_format="text")
    with patch.object(fab_find, "_fetch_results", return_value=([], None)):
        fab_find._find_commandline(args, {})
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "No items found" in captured.err


@pytest.mark.parametrize("helper", ["environment", "mirroreddb"])
@pytest.mark.parametrize("raises", [True, False])
def test_metadata_omissions_remain_visible_after_query(
    helper: str, raises: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(command="get", query="id")
    failure = FabricCLIError("metadata unavailable", "TestFailure")
    with (
        patch.object(
            fab_cmd_get_utils.item_api,
            "get_item",
            side_effect=failure if raises else None,
            return_value=_response(403, "metadata unavailable"),
        ),
        patch.object(
            fab_cmd_get_utils.mirroring_api,
            "get_mirroring_status",
            side_effect=failure if raises else None,
            return_value=_response(403, "metadata unavailable"),
        ),
        patch.object(
            fab_cmd_get_utils.mirroring_api,
            "get_table_mirroring_status",
            side_effect=failure if raises else None,
            return_value=_response(403, "metadata unavailable"),
        ),
    ):
        if helper == "environment":
            data = fab_cmd_get_utils.get_environment_metadata({"id": "item"}, args)
        else:
            data = fab_cmd_get_utils.get_mirroreddb_metadata({"id": "item"}, args)
        fab_cmd_get_utils.query_and_export(data, args, "item")
    diagnostics = _assert_result(capsys, "item")
    assert diagnostics.count("Could not retrieve") == (
        4 if helper == "environment" else 2
    )
    assert ("metadata unavailable" if raises else "403") in diagnostics
