"""Regression tests — ItemType.MAP removal."""

import pytest
from fabric_cli.core.fab_types import ItemType


class TestMapItemRemoval:
    """Verify MAP enum member and its mapping entries are removed."""

    def test_map_not_in_item_type_enum(self):
        assert not hasattr(ItemType, "MAP"), "ItemType.MAP should be removed"

    def test_map_not_in_enum_values(self):
        assert "Map" not in [m.value for m in ItemType]

    def test_map_not_in_format_mapping(self):
        from fabric_cli.core.fab_types import format_mapping
        assert "Map" not in format_mapping

    def test_map_not_in_uri_mapping(self):
        from fabric_cli.core.fab_types import uri_mapping
        assert "Map" not in uri_mapping

    def test_map_not_in_definition_format_mapping(self):
        from fabric_cli.core.fab_types import definition_format_mapping
        assert "Map" not in definition_format_mapping

    def test_other_item_types_still_exist(self):
        """Sanity check — common item types are still present."""
        for name in ("Notebook", "Lakehouse", "SemanticModel", "Report"):
            assert hasattr(ItemType, name.upper()) or name in [m.value for m in ItemType]
