# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for config initialization optimization."""


class TestInitDefaults:
    """Test suite for config initialization optimization."""

    def test_init_defaults__no_write_when_unchanged(self, tmp_path, monkeypatch):
        """Test that init_defaults skips writing when config already has all defaults."""
        import json

        from fabric_cli.core import fab_constant, fab_state_config

        # Create a config file with all defaults already set
        config_data = dict(fab_constant.CONFIG_DEFAULT_VALUES)
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(fab_state_config, "config_file", str(config_file))

        # Track write calls
        original_write = fab_state_config.write_config
        write_calls = []

        def tracking_write(data):
            write_calls.append(data)
            original_write(data)

        monkeypatch.setattr(fab_state_config, "write_config", tracking_write)

        fab_state_config.init_defaults()

        # Should NOT have written since nothing changed
        assert len(write_calls) == 0, "Should skip write when config unchanged"
