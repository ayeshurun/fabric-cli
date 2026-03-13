# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the CommandValidator early failure detection module."""

import os

import pytest

from fabric_cli.core.fab_command_validator import CommandValidator, get_validator
from fabric_cli.core.fab_exceptions import FabricCLIError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def validator():
    """CommandValidator instance pointing at the real command_support.yaml."""
    return CommandValidator()


@pytest.fixture
def custom_validator(tmp_path):
    """CommandValidator with a minimal custom YAML for deterministic tests."""
    yaml_content = """\
---
commands:
  test_cmd:
    supported_elements:
      - workspace
      - tenant
    supported_items:
      - notebook
      - lakehouse
    subcommands:
      sub_a:
        supported_elements:
          - workspace
        supported_items:
          - notebook
        unsupported_items:
          - dashboard
      sub_b:
        supported_items:
          - capacity
          - mirrored_database
"""
    yaml_file = tmp_path / "test_support.yaml"
    yaml_file.write_text(yaml_content)
    return CommandValidator(yaml_path=str(yaml_file))


# ---------------------------------------------------------------------------
# Tests — validate()
# ---------------------------------------------------------------------------


class TestCommandValidatorValidate:

    def test_validate__unknown_command_returns_true(self, validator):
        """Commands not in YAML should pass (no restrictions defined)."""
        assert validator.validate("nonexistent_command") is True

    def test_validate__supported_element_passes(self, custom_validator):
        result = custom_validator.validate(
            "test_cmd", element_type="workspace"
        )
        assert result is True

    def test_validate__unsupported_element_raises(self, custom_validator):
        with pytest.raises(FabricCLIError) as exc_info:
            custom_validator.validate(
                "test_cmd", element_type="onelake"
            )
        assert "onelake" in str(exc_info.value)
        assert "test_cmd" in str(exc_info.value)

    def test_validate__supported_item_passes(self, custom_validator):
        result = custom_validator.validate(
            "test_cmd", item_type="notebook"
        )
        assert result is True

    def test_validate__unsupported_item_raises(self, custom_validator):
        with pytest.raises(FabricCLIError) as exc_info:
            custom_validator.validate(
                "test_cmd", item_type="report"
            )
        assert "report" in str(exc_info.value)

    def test_validate__subcommand_overrides_parent(self, custom_validator):
        # Parent allows "lakehouse", but sub_a only allows "notebook"
        with pytest.raises(FabricCLIError) as exc_info:
            custom_validator.validate(
                "test_cmd", "sub_a", item_type="lakehouse"
            )
        assert "lakehouse" in str(exc_info.value)
        assert "sub_a" in str(exc_info.value)

    def test_validate__subcommand_explicitly_unsupported(self, custom_validator):
        with pytest.raises(FabricCLIError) as exc_info:
            custom_validator.validate(
                "test_cmd", "sub_a", item_type="dashboard"
            )
        assert "dashboard" in str(exc_info.value)
        assert "UnsupportedItemType" in str(exc_info.value)

    def test_validate__subcommand_supported_item_passes(self, custom_validator):
        assert custom_validator.validate(
            "test_cmd", "sub_a", item_type="notebook"
        ) is True

    def test_validate__no_type_specified_passes(self, custom_validator):
        assert custom_validator.validate("test_cmd") is True

    def test_validate__both_element_and_item(self, custom_validator):
        assert custom_validator.validate(
            "test_cmd",
            element_type="workspace",
            item_type="notebook",
        ) is True


# ---------------------------------------------------------------------------
# Tests — is_supported()
# ---------------------------------------------------------------------------


class TestCommandValidatorIsSupported:

    def test_is_supported__returns_true_for_valid(self, custom_validator):
        assert custom_validator.is_supported(
            "test_cmd", item_type="notebook"
        ) is True

    def test_is_supported__returns_false_for_invalid(self, custom_validator):
        assert custom_validator.is_supported(
            "test_cmd", item_type="report"
        ) is False

    def test_is_supported__returns_true_for_unknown_command(self, custom_validator):
        assert custom_validator.is_supported("unknown_cmd") is True


# ---------------------------------------------------------------------------
# Tests — get_supported_items / get_supported_elements / get_unsupported_items
# ---------------------------------------------------------------------------


class TestCommandValidatorIntrospection:

    def test_get_supported_items__command_level(self, custom_validator):
        items = custom_validator.get_supported_items("test_cmd")
        assert "notebook" in items
        assert "lakehouse" in items

    def test_get_supported_items__subcommand_level(self, custom_validator):
        items = custom_validator.get_supported_items("test_cmd", "sub_b")
        assert "capacity" in items
        assert "mirrored_database" in items

    def test_get_supported_elements__command_level(self, custom_validator):
        elements = custom_validator.get_supported_elements("test_cmd")
        assert "workspace" in elements
        assert "tenant" in elements

    def test_get_unsupported_items__subcommand(self, custom_validator):
        items = custom_validator.get_unsupported_items("test_cmd", "sub_a")
        assert "dashboard" in items

    def test_get_supported_items__unknown_command(self, custom_validator):
        assert custom_validator.get_supported_items("nonexistent") == []


# ---------------------------------------------------------------------------
# Tests — real command_support.yaml (integration-level)
# ---------------------------------------------------------------------------


class TestCommandValidatorIntegration:
    """Tests against the actual command_support.yaml shipped with the CLI."""

    def test_fs_start__capacity_supported(self, validator):
        assert validator.validate(
            "fs", "start", item_type="capacity"
        ) is True

    def test_fs_start__notebook_unsupported(self, validator):
        assert validator.is_supported(
            "fs", "start", item_type="notebook"
        ) is False

    def test_fs_ls__workspace_supported(self, validator):
        assert validator.validate(
            "fs", "ls", element_type="workspace"
        ) is True

    def test_fs_rm__dashboard_unsupported(self, validator):
        assert validator.is_supported(
            "fs", "rm", item_type="dashboard"
        ) is False

    def test_job__notebook_supported(self, validator):
        assert validator.validate("job", item_type="notebook") is True

    def test_job__report_unsupported(self, validator):
        assert validator.is_supported("job", item_type="report") is False

    def test_label_set__warehouse_unsupported(self, validator):
        assert validator.is_supported(
            "label", "set", item_type="warehouse"
        ) is False

    def test_table_schema__lakehouse_supported(self, validator):
        assert validator.validate(
            "table", "schema", item_type="lakehouse"
        ) is True

    def test_fs_export__notebook_supported(self, validator):
        assert validator.validate(
            "fs", "export", item_type="notebook"
        ) is True

    def test_fs_import__graph_query_set_unsupported(self, validator):
        assert validator.is_supported(
            "fs", "import", item_type="graph_query_set"
        ) is False

    def test_get_supported_items__fs_start(self, validator):
        items = validator.get_supported_items("fs", "start")
        assert "capacity" in items
        assert "mirrored_database" in items

    def test_get_unsupported_items__fs_rm(self, validator):
        unsupported = validator.get_unsupported_items("fs", "rm")
        assert "dashboard" in unsupported
        assert "paginated_report" in unsupported


# ---------------------------------------------------------------------------
# Tests — singleton
# ---------------------------------------------------------------------------


class TestGetValidator:

    def test_get_validator__returns_instance(self):
        v = get_validator()
        assert isinstance(v, CommandValidator)

    def test_get_validator__returns_same_instance(self):
        v1 = get_validator()
        v2 = get_validator()
        assert v1 is v2
