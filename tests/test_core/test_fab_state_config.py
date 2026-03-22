# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import os
import tempfile

import fabric_cli.core.fab_state_config as cfg
from fabric_cli.core import fab_constant


def test_read_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = os.path.join(tmpdir, "tmp_test.txt")
        with open(tmp_file, "w") as file:
            file.write('{"key": "value"}')
            file.flush()  # flush the buffer to write the data to the file before reading it
        with open(tmp_file, "r") as file:
            data = cfg.read_config(file.name)
            assert data == {"key": "value"}


def test_read_config_missing_file():
    with tempfile.NamedTemporaryFile("w") as fp:
        fp.close()  # close the file to delete it
        data = cfg.read_config(fp.name)
        assert data == {}


def test_read_config_bad_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = os.path.join(tmpdir, "tmp_test.txt")
        with open(tmp_file, "w") as file:
            file.write('{"key": "value"')
            file.flush()
        data = cfg.read_config(tmp_file)
        assert data == {}


def test_write_config(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = os.path.join(tmpdir, "tmp_test.txt")
        with open(tmp_file, "w") as file:
            file.flush()
        monkeypatch.setattr(cfg, "config_file", tmp_file)
        cfg.write_config({"key": "value"})
        data = cfg.read_config(tmp_file)
        assert data == {"key": "value"}


def test_get_set_config(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = os.path.join(tmpdir, "tmp_cfg.txt")
        with open(cfg_file, "w") as cfg_fp:
            cfg_fp.write('{"key": "value"}')
            cfg_fp.flush()
        monkeypatch.setattr(cfg, "config_file", cfg_file)
        cfg.set_config("key2", "value2")
        assert cfg.get_config("key") == "value"
        assert cfg.get_config("key2") == "value2"


def test_list_configs(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = os.path.join(tmpdir, "tmp_test.txt")
        with open(tmp_file, "w") as file:
            file.write('{"key": "value"}')
            file.flush()
        monkeypatch.setattr(cfg, "config_file", tmp_file)
        cfg.set_config("key2", "value2")
        assert cfg.list_configs() == {"key": "value", "key2": "value2"}


# region init_defaults migration

def test_init_defaults__removes_mode_key(monkeypatch):
    """If an existing config file contains 'mode', init_defaults must delete it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, "config.json")
        old_config = {
            fab_constant.FAB_MODE: fab_constant.FAB_MODE_INTERACTIVE,
            fab_constant.FAB_CACHE_ENABLED: "true",
        }
        with open(config_file, "w") as f:
            json.dump(old_config, f)

        monkeypatch.setattr(cfg, "config_file", config_file)

        cfg.init_defaults()

        result = cfg.read_config(config_file)
        assert fab_constant.FAB_MODE not in result
        assert result[fab_constant.FAB_CACHE_ENABLED] == "true"


def test_init_defaults__no_mode_key_works(monkeypatch):
    """Config without 'mode' should initialize cleanly without errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, "config.json")
        with open(config_file, "w") as f:
            json.dump({fab_constant.FAB_DEBUG_ENABLED: "true"}, f)

        monkeypatch.setattr(cfg, "config_file", config_file)

        cfg.init_defaults()

        result = cfg.read_config(config_file)
        assert fab_constant.FAB_MODE not in result
        assert result[fab_constant.FAB_DEBUG_ENABLED] == "true"


def test_init_defaults__applies_missing_defaults(monkeypatch):
    """init_defaults must fill in missing default values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, "config.json")
        with open(config_file, "w") as f:
            json.dump({}, f)

        monkeypatch.setattr(cfg, "config_file", config_file)

        cfg.init_defaults()

        result = cfg.read_config(config_file)
        for key, default_val in fab_constant.CONFIG_DEFAULT_VALUES.items():
            assert result.get(key) == default_val, (
                f"Expected default for '{key}' = '{default_val}', got '{result.get(key)}'"
            )


def test_init_defaults__preserves_user_overrides(monkeypatch):
    """User-set values must not be overwritten by defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, "config.json")
        user_config = {fab_constant.FAB_CACHE_ENABLED: "false"}
        with open(config_file, "w") as f:
            json.dump(user_config, f)

        monkeypatch.setattr(cfg, "config_file", config_file)

        cfg.init_defaults()

        result = cfg.read_config(config_file)
        assert result[fab_constant.FAB_CACHE_ENABLED] == "false"

# endregion
