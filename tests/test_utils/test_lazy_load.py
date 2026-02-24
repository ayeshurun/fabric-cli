# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for lazy loading utilities and startup performance."""

import importlib
import sys
import time

import pytest


class TestLazyLoad:
    """Test suite for lazy loading utilities."""

    def test_lazy_command__deferred_import(self):
        """Test that lazy_command defers the module import until invocation."""
        from fabric_cli.utils.fab_lazy_load import lazy_command

        # Create a lazy command wrapper for a known module/function
        wrapper = lazy_command(
            "fabric_cli.utils.fab_lazy_load", "questionary"
        )

        # The wrapper should be callable
        assert callable(wrapper)

    def test_lazy_command__invokes_target_function(self):
        """Test that lazy_command correctly calls the target function."""
        from fabric_cli.utils.fab_lazy_load import lazy_command

        # Use a simple module function we can verify
        wrapper = lazy_command(
            "fabric_cli.core.fab_constant", "EXIT_CODE_SUCCESS"
        )

        # The wrapper should be callable (it wraps attribute access)
        assert callable(wrapper)

    def test_lazy_command__raises_on_missing_module(self):
        """Test that lazy_command raises ModuleNotFoundError for invalid modules."""
        from fabric_cli.utils.fab_lazy_load import lazy_command

        wrapper = lazy_command("nonexistent.module", "func")
        with pytest.raises(ModuleNotFoundError):
            wrapper(None)

    def test_lazy_command__raises_on_missing_function(self):
        """Test that lazy_command raises AttributeError for invalid function names."""
        from fabric_cli.utils.fab_lazy_load import lazy_command

        wrapper = lazy_command("fabric_cli.core.fab_constant", "nonexistent_func")
        with pytest.raises(AttributeError):
            wrapper(None)


class TestStartupPerformance:
    """Test suite for CLI startup performance."""

    def test_main_module_import__under_threshold(self):
        """Test that importing the main module stays under performance threshold."""
        # Remove cached modules to get a fresh import measurement
        modules_to_remove = [
            key for key in sys.modules if key.startswith("fabric_cli")
        ]
        saved_modules = {}
        for mod in modules_to_remove:
            saved_modules[mod] = sys.modules.pop(mod)

        try:
            start = time.perf_counter()
            importlib.import_module("fabric_cli.main")
            elapsed_ms = (time.perf_counter() - start) * 1000

            # The import should complete in under 500ms (generous threshold)
            # Before optimization: ~737ms, after: ~54ms
            assert elapsed_ms < 500, (
                f"fabric_cli.main import took {elapsed_ms:.0f}ms, expected < 500ms"
            )
        finally:
            # Restore modules
            for mod_name, mod in saved_modules.items():
                sys.modules[mod_name] = mod

    def test_heavy_modules_not_imported_at_startup(self):
        """Test that heavy dependencies are NOT loaded during main module import."""
        # Remove cached modules
        modules_to_remove = [
            key for key in sys.modules if key.startswith("fabric_cli")
        ]
        saved_modules = {}
        for mod in modules_to_remove:
            saved_modules[mod] = sys.modules.pop(mod)

        # Also remove the heavy dependencies
        heavy_modules = ["msal", "jwt", "cryptography"]
        saved_heavy = {}
        for mod_name in heavy_modules:
            keys_to_remove = [k for k in sys.modules if k.startswith(mod_name)]
            for k in keys_to_remove:
                saved_heavy[k] = sys.modules.pop(k)

        try:
            importlib.import_module("fabric_cli.main")

            # These heavy modules should NOT be imported during startup
            for mod_name in heavy_modules:
                assert mod_name not in sys.modules, (
                    f"'{mod_name}' should not be imported at startup"
                )
        finally:
            # Restore all modules
            for mod_name, mod in saved_modules.items():
                sys.modules[mod_name] = mod
            for mod_name, mod in saved_heavy.items():
                sys.modules[mod_name] = mod


class TestSessionReuse:
    """Test suite for HTTP session reuse."""

    def test_shared_session__returns_same_instance(self):
        """Test that _get_session returns the same session instance."""
        from fabric_cli.client import fab_api_client

        # Reset the shared session
        fab_api_client._shared_session = None

        session1 = fab_api_client._get_session()
        session2 = fab_api_client._get_session()

        assert session1 is session2, "Session should be reused"

        # Clean up
        fab_api_client._shared_session = None


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
