# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for fabric_cli_v2.context module."""

import json

import pytest

from fabric_cli_v2 import config
from fabric_cli_v2.context import Context
from fabric_cli_v2.types import ElementType, FabricElement, ItemType


@pytest.fixture(autouse=True)
def _tmp_config(tmp_path, monkeypatch):
    """Redirect config to temp directory."""
    monkeypatch.setattr(config, "_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    config.invalidate_cache()
    config.init_defaults()

    # Also redirect context files to the same temp dir
    from fabric_cli_v2 import context as ctx_mod
    monkeypatch.setattr(ctx_mod, "_CONFIG_DIR", tmp_path)

    Context.reset_singleton()
    yield
    Context.reset_singleton()
    config.invalidate_cache()


class TestContext:

    def test_default_path__root(self):
        ctx = Context.get()
        assert ctx.path == "/"

    def test_set_current__updates_path(self):
        ctx = Context.get()
        tenant = FabricElement("root", ElementType.TENANT)
        ws = FabricElement("myws", ElementType.WORKSPACE, parent=tenant)
        ctx.current = ws
        assert ctx.path == "/myws"

    def test_reset__clears_context(self):
        ctx = Context.get()
        tenant = FabricElement("root", ElementType.TENANT)
        ctx.current = FabricElement("ws", ElementType.WORKSPACE, parent=tenant)
        ctx.reset()
        assert ctx.path == "/"

    def test_singleton__returns_same_instance(self):
        a = Context.get()
        b = Context.get()
        assert a is b

    def test_save_and_load__round_trip(self, tmp_path, monkeypatch):
        # Enable persistence
        config.set_value("context_persistence_enabled", "true")

        ctx = Context.get()
        tenant = FabricElement("root", ElementType.TENANT)
        ws = FabricElement("ws1", ElementType.WORKSPACE, id="ws-id", parent=tenant)
        item = FabricElement("nb1", ElementType.ITEM,
                             id="item-id", item_type=ItemType.NOTEBOOK, parent=ws)
        ctx.current = item
        ctx.save()

        # Create a new context and load
        Context.reset_singleton()
        ctx2 = Context.get()
        ctx2.load()
        assert ctx2.current is not None
        assert ctx2.current.name == "nb1"
        assert ctx2.current.element_type == ElementType.ITEM
        assert ctx2.current.item_type == ItemType.NOTEBOOK
        assert ctx2.current.parent.name == "ws1"

    def test_save__disabled_by_config(self, tmp_path):
        config.set_value("context_persistence_enabled", "false")
        ctx = Context.get()
        tenant = FabricElement("root", ElementType.TENANT)
        ctx.current = FabricElement("ws", ElementType.WORKSPACE, parent=tenant)
        ctx.save()
        # No context file should be written
        files = list(tmp_path.glob("context-*.json"))
        assert len(files) == 0

    def test_load__missing_file_is_noop(self):
        config.set_value("context_persistence_enabled", "true")
        ctx = Context.get()
        ctx.load()  # should not raise
        assert ctx.current is None

    def test_serialise_deserialise(self):
        tenant = FabricElement("root", ElementType.TENANT)
        ws = FabricElement("ws1", ElementType.WORKSPACE, id="ws-id", parent=tenant)

        data = Context._serialise(ws)
        restored = Context._deserialise(data)

        assert restored.name == "ws1"
        assert restored.element_type == ElementType.WORKSPACE
        assert restored.id == "ws-id"
        assert restored.parent.name == "root"
