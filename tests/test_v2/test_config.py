# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for fabric_cli_v2.config module."""

import json

import pytest

from fabric_cli_v2 import config


@pytest.fixture(autouse=True)
def _tmp_config(tmp_path, monkeypatch):
    """Redirect config to a temporary directory."""
    monkeypatch.setattr(config, "_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    config.invalidate_cache()
    yield
    config.invalidate_cache()


class TestConfig:

    def test_init_defaults__creates_file(self, tmp_path):
        config.init_defaults()
        assert (tmp_path / "config.json").exists()

    def test_init_defaults__contains_all_keys(self):
        config.init_defaults()
        data = config.read_all()
        for key in config.DEFAULTS:
            assert key in data

    def test_get__returns_default(self):
        config.init_defaults()
        assert config.get("output_format") == "text"

    def test_set_value__persists(self, tmp_path):
        config.init_defaults()
        config.set_value("output_format", "json")
        assert config.get("output_format") == "json"

        # Verify on disk
        config.invalidate_cache()
        assert config.get("output_format") == "json"

    def test_reset__restores_defaults(self):
        config.init_defaults()
        config.set_value("output_format", "json")
        config.reset()
        assert config.get("output_format") == "text"

    def test_get__missing_key_returns_none(self):
        config.init_defaults()
        assert config.get("nonexistent_key") is None

    def test_read_all__corrupted_file(self, tmp_path):
        (tmp_path / "config.json").write_text("not json!")
        data = config.read_all()
        # Should fall back to defaults
        assert "output_format" in data

    def test_init_defaults__backfills_new_keys(self, tmp_path):
        # Write a partial config
        (tmp_path / "config.json").write_text(
            json.dumps({"output_format": "json"})
        )
        config.invalidate_cache()
        config.init_defaults()
        data = config.read_all()
        assert data["output_format"] == "json"  # preserved
        assert "cache_enabled" in data  # backfilled

    def test_valid_values__output_format(self):
        assert "text" in config.VALID_VALUES["output_format"]
        assert "json" in config.VALID_VALUES["output_format"]
