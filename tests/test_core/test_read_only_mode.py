# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from argparse import Namespace
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fabric_cli.client import fab_api_catalog, fab_api_client, fab_api_item
from fabric_cli.commands.config import fab_config_set
from fabric_cli.core import fab_constant, fab_read_only, fab_state_config
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.fab_parser_setup import get_global_parser_and_subparsers
from fabric_cli.main import _execute_command
from fabric_cli.utils.fab_storage import write_to_storage

_WORKSPACE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_ITEM_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
_ITEM_PATH = f"workspaces/{_WORKSPACE_ID}/items/{_ITEM_ID}"
MockTransport = tuple[MagicMock, MagicMock, MagicMock]


@pytest.fixture(autouse=True)
def read_only_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate configuration and enable read-only mode for each test."""
    monkeypatch.setattr(fab_state_config, "config_file", str(tmp_path / "config.json"))
    fab_state_config.init_defaults()
    fab_state_config.set_config(fab_constant.FAB_READ_ONLY_MODE, "true")


@pytest.fixture
def mock_transport() -> Iterator[MockTransport]:
    """Stub authentication and HTTP without permitting live requests."""
    with (
        patch("fabric_cli.core.fab_auth.FabAuth") as auth,
        patch.object(fab_api_client, "_get_session") as get_session,
    ):
        auth.return_value.get_access_token.return_value = "test-token"
        session = MagicMock()
        session.request.return_value = MagicMock(
            status_code=200, headers={}, text="{}", content=b"{}"
        )
        get_session.return_value = session
        yield auth, get_session, session


@pytest.mark.parametrize("method", ["post", "PUT", "patch", "delete", "options"])
@pytest.mark.parametrize("audience", [None, "fabric", "storage", "azure", "powerbi"])
def test_remote_writes_blocked_before_authentication(
    method: str, audience: str | None, mock_transport: MockTransport
) -> None:
    auth, get_session, session = mock_transport
    args = Namespace(
        uri="workspaces",
        method=method,
        audience=audience,
        raw_response=True,
        json_file="/nonexistent/input.json",
    )
    with pytest.raises(FabricCLIError) as exc:
        fab_api_client.do_request(args)
    assert exc.value.status_code == fab_constant.ERROR_READ_ONLY_MODE
    auth.assert_not_called()
    get_session.assert_not_called()
    session.request.assert_not_called()


@pytest.mark.parametrize("method", ["get", "HEAD"])
@pytest.mark.parametrize("audience", [None, "fabric", "storage", "azure", "powerbi"])
def test_remote_reads_allowed(
    method: str, audience: str | None, mock_transport: MockTransport
) -> None:
    _, _, session = mock_transport
    response = fab_api_client.do_request(
        Namespace(uri="workspaces", method=method, audience=audience)
    )
    assert response.status_code == 200
    session.request.assert_called_once()
    assert session.request.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize(
    "uri",
    [
        "catalog/search",
        f"{_ITEM_PATH}/getDefinition",
        f"/{_ITEM_PATH.upper()}/getDefinition?format=ipynb",
        f"workspaces/{_WORKSPACE_ID}/items/bulkExportDefinitions?beta=true",
    ],
)
def test_supported_read_posts_allowed(uri: str, mock_transport: MockTransport) -> None:
    _, _, session = mock_transport
    response = fab_api_client.do_request(
        Namespace(uri=uri, method="POST", audience="fabric"), json={}
    )
    assert response.status_code == 200
    session.request.assert_called_once()


@pytest.mark.parametrize(
    "uri",
    [
        "catalog/search/../delete",
        "catalog/search/extra",
        "catalog/search%2f..%2fdelete",
        "https://example.com/catalog/search",
        "//example.com/catalog/search",
        "catalog/\nsearch",
        f"{_ITEM_PATH}/updateDefinition",
        f"{_ITEM_PATH}/getDefinition/../updateDefinition",
        f"{_ITEM_PATH}/jobs/instances",
        f"{_ITEM_PATH}/getDefinition/extra",
        f"workspaces/{_WORKSPACE_ID}/items/bulkImportDefinitions",
    ],
)
def test_read_post_allowlist_rejects_other_paths(
    uri: str, mock_transport: MockTransport
) -> None:
    with pytest.raises(FabricCLIError) as exc:
        fab_api_client.do_request(Namespace(uri=uri, method="post"))
    assert exc.value.status_code == fab_constant.ERROR_READ_ONLY_MODE
    mock_transport[2].request.assert_not_called()


@pytest.mark.parametrize("audience", ["storage", "azure", "powerbi"])
def test_read_post_exceptions_apply_only_to_fabric(
    audience: str, mock_transport: MockTransport
) -> None:
    with pytest.raises(FabricCLIError):
        fab_api_client.do_request(
            Namespace(uri="catalog/search", method="post", audience=audience)
        )
    mock_transport[2].request.assert_not_called()


@pytest.mark.parametrize(
    "header", ["X-HTTP-Method-Override", "x-http-method", "X-Method-Override"]
)
def test_method_override_blocked(header: str, mock_transport: MockTransport) -> None:
    with pytest.raises(FabricCLIError):
        fab_api_client.do_request(
            Namespace(uri="workspaces", method="get", headers={header: "DELETE"})
        )
    mock_transport[2].request.assert_not_called()


@pytest.mark.parametrize("value", ["false", None])
def test_disabled_mode_preserves_write_behavior(
    value: str | None, mock_transport: MockTransport
) -> None:
    fab_state_config.set_config(fab_constant.FAB_READ_ONLY_MODE, value)
    _, _, session = mock_transport
    response = fab_api_client.do_request(Namespace(uri="workspaces", method="post"))
    assert response.status_code == 200
    assert "allow_redirects" not in session.request.call_args.kwargs


def test_supported_read_clients_use_allowlist(mock_transport: MockTransport) -> None:
    args = Namespace(ws_id=_WORKSPACE_ID, id=_ITEM_ID, format="ipynb")
    assert fab_api_item.get_item_definition(args).status_code == 200
    assert fab_api_item.bulk_export_definitions(args, "{}").status_code == 200
    assert fab_api_catalog.search(args, {"search": "test"}).status_code == 200
    assert mock_transport[2].request.call_count == 3


@pytest.mark.parametrize(
    "command",
    [
        ["api", "-X", "delete", "workspaces"],
        ["api", "-X", "post", "workspaces"],
        ["api", "-X", "put", "-A", "storage", "workspace/item/Files/new"],
        ["deploy", "--config", "/nonexistent/config.yml", "--force"],
    ],
)
def test_cli_writes_return_structured_error(
    command: list[str], mock_transport: MockTransport
) -> None:
    parser, subparsers = get_global_parser_and_subparsers()
    args = parser.parse_args(command)
    with patch("fabric_cli.utils.fab_ui.print_output_error") as print_error:
        assert (
            _execute_command(args, subparsers, parser) == fab_constant.EXIT_CODE_ERROR
        )
    error = print_error.call_args.args[0]
    assert error.status_code == fab_constant.ERROR_READ_ONLY_MODE
    mock_transport[0].assert_not_called()
    mock_transport[2].request.assert_not_called()


@pytest.mark.parametrize("force", [False, True])
def test_deploy_blocked_before_prompt_and_external_client(force: bool) -> None:
    from fabric_cli.commands.fs import fab_fs_deploy

    with (
        patch.object(fab_fs_deploy, "deploy_with_config_file") as deploy,
        patch.object(fab_fs_deploy.fab_ui, "prompt_confirm") as prompt,
        pytest.raises(FabricCLIError) as exc,
    ):
        fab_fs_deploy.exec_command(Namespace(force=force, target_env="test"))
    assert exc.value.status_code == fab_constant.ERROR_READ_ONLY_MODE
    deploy.assert_not_called()
    prompt.assert_not_called()


def test_deploy_allowed_when_mode_disabled() -> None:
    from fabric_cli.commands.fs import fab_fs_deploy

    fab_state_config.set_config(fab_constant.FAB_READ_ONLY_MODE, "false")
    with patch.object(fab_fs_deploy, "deploy_with_config_file") as deploy:
        args = Namespace(force=True, target_env="test")
        fab_fs_deploy.exec_command(args)
    deploy.assert_called_once_with(args)


def test_local_export_and_configuration_changes_allowed(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "definition.json"
    write_to_storage(
        Namespace(),
        {"type": "local", "path": str(destination)},
        {"definition": "test"},
        export=True,
    )
    assert json.loads(destination.read_text()) == {"definition": "test"}
    with patch("fabric_cli.utils.fab_ui.print_output_format"):
        fab_config_set.exec_command(
            Namespace(key=fab_constant.FAB_READ_ONLY_MODE, value="false")
        )
    assert not fab_read_only.is_enabled()


def test_read_only_configuration_defaults_to_disabled() -> None:
    fab_state_config.write_config({})
    fab_state_config.init_defaults()
    assert fab_state_config.get_config(fab_constant.FAB_READ_ONLY_MODE) == "false"
    assert fab_constant.FAB_CONFIG_KEYS_TO_VALID_VALUES[
        fab_constant.FAB_READ_ONLY_MODE
    ] == ["false", "true"]
