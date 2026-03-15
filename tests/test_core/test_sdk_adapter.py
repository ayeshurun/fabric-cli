# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the FabricSDKAdapter proof of concept."""

import pytest

from fabric_cli.typer_poc.sdk_adapter import FabricSDKAdapter


class TestFabricSDKAdapter:
    """Tests for the SDK adapter PoC — fallback mode (no real SDK installed)."""

    def test_init__without_credential_sdk_not_available(self):
        adapter = FabricSDKAdapter()
        assert adapter.sdk_available is False

    def test_list_workspaces__fallback(self):
        adapter = FabricSDKAdapter()
        result = adapter.list_workspaces()
        assert result["_fallback"] is True
        assert result["uri"] == "workspaces"

    def test_get_workspace__fallback(self):
        adapter = FabricSDKAdapter()
        result = adapter.get_workspace("test-ws-id")
        assert result["_fallback"] is True
        assert "workspaces/test-ws-id" in result["uri"]

    def test_list_items__fallback(self):
        adapter = FabricSDKAdapter()
        result = adapter.list_items("test-ws-id")
        assert result["_fallback"] is True
        assert "workspaces/test-ws-id/items" in result["uri"]

    def test_get_item__fallback(self):
        adapter = FabricSDKAdapter()
        result = adapter.get_item("test-ws-id", "test-item-id")
        assert result["_fallback"] is True
        assert "workspaces/test-ws-id/items/test-item-id" in result["uri"]

    def test_list_capacities__fallback(self):
        adapter = FabricSDKAdapter()
        result = adapter.list_capacities()
        assert result["_fallback"] is True
        assert result["uri"] == "capacities"
