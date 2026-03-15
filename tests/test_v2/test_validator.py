# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for fabric_cli_v2.validator module."""

import pytest

from fabric_cli_v2.validator import CommandValidator


@pytest.fixture
def validator():
    """Validator using real command_support.yaml."""
    return CommandValidator()


@pytest.fixture
def custom_validator(tmp_path):
    """Validator with custom YAML for deterministic tests."""
    yaml_content = """\
---
commands:
  test_cmd:
    supported_elements:
      - workspace
    supported_items:
      - notebook
    subcommands:
      sub_a:
        supported_items:
          - notebook
        unsupported_items:
          - dashboard
"""
    p = tmp_path / "test.yaml"
    p.write_text(yaml_content)
    return CommandValidator(yaml_path=str(p))


class TestValidator:

    def test_unknown_command__passes(self, custom_validator):
        assert custom_validator.validate("unknown") is True

    def test_supported_element__passes(self, custom_validator):
        assert custom_validator.validate("test_cmd", element_type="workspace") is True

    def test_unsupported_element__raises(self, custom_validator):
        with pytest.raises(ValueError, match="onelake"):
            custom_validator.validate("test_cmd", element_type="onelake")

    def test_supported_item__passes(self, custom_validator):
        assert custom_validator.validate("test_cmd", item_type="notebook") is True

    def test_unsupported_item__raises(self, custom_validator):
        with pytest.raises(ValueError, match="report"):
            custom_validator.validate("test_cmd", item_type="report")

    def test_explicitly_unsupported__raises(self, custom_validator):
        with pytest.raises(ValueError, match="dashboard"):
            custom_validator.validate("test_cmd", "sub_a", item_type="dashboard")

    def test_is_supported__returns_bool(self, custom_validator):
        assert custom_validator.is_supported("test_cmd", item_type="notebook") is True
        assert custom_validator.is_supported("test_cmd", item_type="report") is False

    def test_get_supported_items(self, custom_validator):
        items = custom_validator.get_supported_items("test_cmd")
        assert "notebook" in items


class TestValidatorIntegration:
    """Tests against real command_support.yaml."""

    def test_fs_start__capacity(self, validator):
        assert validator.validate("fs", "start", item_type="capacity") is True

    def test_fs_start__notebook(self, validator):
        assert validator.is_supported("fs", "start", item_type="notebook") is False

    def test_job__notebook(self, validator):
        assert validator.validate("job", item_type="notebook") is True
