# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for fabric_cli_v2.types module."""

import pytest

from fabric_cli_v2.types import (
    ElementType,
    FabricElement,
    ItemType,
    OneLakeItemType,
    OutputFormat,
)


class TestItemType:

    def test_from_string__exact_match(self):
        assert ItemType.from_string("Notebook") == ItemType.NOTEBOOK

    def test_from_string__case_insensitive(self):
        assert ItemType.from_string("notebook") == ItemType.NOTEBOOK
        assert ItemType.from_string("NOTEBOOK") == ItemType.NOTEBOOK

    def test_from_string__enum_name(self):
        assert ItemType.from_string("DATA_PIPELINE") == ItemType.DATA_PIPELINE

    def test_from_string__unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown item type"):
            ItemType.from_string("NonExistentType")

    def test_api_path__notebook(self):
        assert ItemType.NOTEBOOK.api_path == "notebooks"

    def test_api_path__semantic_model(self):
        assert ItemType.SEMANTIC_MODEL.api_path == "semanticModels"

    def test_api_path__lakehouse(self):
        assert ItemType.LAKEHOUSE.api_path == "lakehouses"


class TestFabricElement:

    def test_path__single_node(self):
        tenant = FabricElement("root", ElementType.TENANT)
        ws = FabricElement("myws", ElementType.WORKSPACE, id="ws-123", parent=tenant)
        assert ws.path == "/myws"

    def test_path__nested(self):
        tenant = FabricElement("root", ElementType.TENANT)
        ws = FabricElement("ws1", ElementType.WORKSPACE, parent=tenant)
        item = FabricElement("nb1", ElementType.ITEM,
                             item_type=ItemType.NOTEBOOK, parent=ws)
        assert item.path == "/ws1/nb1"

    def test_repr(self):
        e = FabricElement("test", ElementType.WORKSPACE)
        assert "test" in repr(e)
        assert "Workspace" in repr(e)

    def test_extra_dict(self):
        e = FabricElement("x", ElementType.ITEM, extra={"key": "val"})
        assert e.extra["key"] == "val"

    def test_extra_default_empty(self):
        e = FabricElement("x", ElementType.ITEM)
        assert e.extra == {}
