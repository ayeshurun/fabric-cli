# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from argparse import Namespace
from unittest.mock import patch

import pytest


def _opt_in_appended(mock_flag, deploy_mod):
    """Return the flags appended via append_feature_flag, excluding the always-on
    flags the handler enables by default, preserving call order."""
    return [
        call.args[0]
        for call in mock_flag.call_args_list
        if call.args[0] not in deploy_mod._ALWAYS_ON_FEATURE_FLAGS
    ]


class TestDeployFeatureFlags:
    """
    Tests for enabling fabric-cicd feature flags via the --feature_flags argument.
    These tests mock the fabric-cicd library so they do not require recorded HTTP
    cassettes.
    """

    def _run_deploy(self, tmp_path, feature_flags, mock_fab_set_state_config):
        """Invoke deploy_with_config_file with fabric-cicd mocked, returning the
        (append_feature_flag mock, deploy_with_config mock) for assertions."""
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod
        from fabric_cli.core import fab_constant

        # disable debug mode so fabric-cicd file logging is disabled during the run
        mock_fab_set_state_config(fab_constant.FAB_DEBUG_ENABLED, "false")

        args = Namespace(
            config=str(tmp_path / "config.yml"),
            target_env="dev",
            params=None,
            feature_flags=feature_flags,
        )

        with (
            patch.object(deploy_mod, "append_feature_flag") as mock_flag,
            patch.object(
                deploy_mod, "deploy_with_config", return_value=None
            ) as mock_deploy,
            patch.object(deploy_mod, "disable_file_logging"),
            patch.object(deploy_mod, "configure_external_file_logging"),
            patch.object(
                deploy_mod, "create_fabric_token_credential", return_value=None
            ),
        ):
            deploy_mod.deploy_with_config_file(args)

        return mock_flag, mock_deploy

    def test_deploy_experimental_features_enabled_by_default_success(
        self, tmp_path, mock_fab_set_state_config
    ):
        """enable_experimental_features is always appended, regardless of flags."""
        mock_flag, _ = self._run_deploy(tmp_path, None, mock_fab_set_state_config)

        appended = [call.args[0] for call in mock_flag.call_args_list]
        assert "disable_print_identity" in appended
        assert "enable_experimental_features" in appended

    def test_deploy_single_feature_flag_success(
        self, tmp_path, mock_fab_set_state_config
    ):
        """A single flag name is appended."""
        mock_flag, _ = self._run_deploy(
            tmp_path,
            "enable_shortcut_publish",
            mock_fab_set_state_config,
        )

        appended = [call.args[0] for call in mock_flag.call_args_list]
        assert "enable_shortcut_publish" in appended

    def test_deploy_multiple_feature_flags_comma_separated_success(
        self, tmp_path, mock_fab_set_state_config
    ):
        """Multiple comma-separated flag names are all appended."""
        mock_flag, _ = self._run_deploy(
            tmp_path,
            "enable_shortcut_publish,enable_bulk_publish",
            mock_fab_set_state_config,
        )

        appended = [call.args[0] for call in mock_flag.call_args_list]
        assert "enable_shortcut_publish" in appended
        assert "enable_bulk_publish" in appended

    def test_deploy_comma_separated_with_whitespace_success(
        self, tmp_path, mock_fab_set_state_config
    ):
        """Whitespace around comma-separated flag names is ignored."""
        mock_flag, _ = self._run_deploy(
            tmp_path,
            "enable_shortcut_publish, enable_bulk_publish",
            mock_fab_set_state_config,
        )

        appended = [call.args[0] for call in mock_flag.call_args_list]
        assert "enable_shortcut_publish" in appended
        assert "enable_bulk_publish" in appended

    def test_deploy_experimental_flag_passed_explicitly_is_skipped_success(
        self, tmp_path, mock_fab_set_state_config
    ):
        """Passing enable_experimental_features explicitly is skipped by the
        handler; the default gate still enables it exactly once."""
        mock_flag, _ = self._run_deploy(
            tmp_path,
            "enable_experimental_features",
            mock_fab_set_state_config,
        )

        appended = [call.args[0] for call in mock_flag.call_args_list]
        assert appended.count("enable_experimental_features") == 1

    def test_deploy_absent_feature_flags_is_noop_success(
        self, tmp_path, mock_fab_set_state_config
    ):
        """Without --feature_flags, no extra feature flags are appended."""
        mock_flag, _ = self._run_deploy(tmp_path, None, mock_fab_set_state_config)

        appended = [call.args[0] for call in mock_flag.call_args_list]
        # only the always-on flags, none of the fabric-cicd feature flags
        assert "enable_shortcut_publish" not in appended
        assert "enable_bulk_publish" not in appended


class TestApplyFeatureFlags:
    """Unit tests targeting the _apply_feature_flags handler directly so
    validation errors surface with their original error code."""

    def test_unknown_flag_raises_invalid_input_failure(self):
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod
        from fabric_cli.core import fab_constant
        from fabric_cli.core.fab_exceptions import FabricCLIError

        args = Namespace(feature_flags="not_a_real_flag")

        with patch.object(deploy_mod, "append_feature_flag"):
            with pytest.raises(FabricCLIError) as exc_info:
                deploy_mod._apply_feature_flags(args)

        assert exc_info.value.status_code == fab_constant.ERROR_INVALID_INPUT

    def test_valid_flags_appended_success(self):
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod

        args = Namespace(
            feature_flags="enable_shortcut_publish,enable_bulk_publish"
        )

        with patch.object(deploy_mod, "append_feature_flag") as mock_flag:
            deploy_mod._apply_feature_flags(args)

        opt_in = _opt_in_appended(mock_flag, deploy_mod)
        assert opt_in == ["enable_shortcut_publish", "enable_bulk_publish"]

    def test_bracketed_value_appended_success(self):
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod

        # surrounding brackets are tolerated and ignored
        args = Namespace(
            feature_flags="[enable_shortcut_publish,enable_bulk_publish]"
        )

        with patch.object(deploy_mod, "append_feature_flag") as mock_flag:
            deploy_mod._apply_feature_flags(args)

        opt_in = _opt_in_appended(mock_flag, deploy_mod)
        assert opt_in == ["enable_shortcut_publish", "enable_bulk_publish"]

    def test_always_on_flags_enabled_by_default_success(self):
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod

        # without --feature_flags the handler still enables the always-on flags
        args = Namespace(feature_flags=None)

        with patch.object(deploy_mod, "append_feature_flag") as mock_flag:
            deploy_mod._apply_feature_flags(args)

        appended = [call.args[0] for call in mock_flag.call_args_list]
        assert set(appended) == deploy_mod._ALWAYS_ON_FEATURE_FLAGS
        assert _opt_in_appended(mock_flag, deploy_mod) == []

    def test_experimental_flag_is_skipped_success(self):
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod

        args = Namespace(feature_flags="enable_experimental_features")

        with patch.object(deploy_mod, "append_feature_flag") as mock_flag:
            deploy_mod._apply_feature_flags(args)

        appended = [call.args[0] for call in mock_flag.call_args_list]
        # the gate flag is enabled once by default and not re-appended
        assert appended.count("enable_experimental_features") == 1
        assert _opt_in_appended(mock_flag, deploy_mod) == []

    def test_disable_print_identity_flag_is_skipped_success(self):
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod

        # disable_print_identity is always enabled by the CLI; passing it via
        # --feature_flags is skipped rather than re-appended or rejected.
        args = Namespace(feature_flags="disable_print_identity")

        with patch.object(deploy_mod, "append_feature_flag") as mock_flag:
            deploy_mod._apply_feature_flags(args)

        appended = [call.args[0] for call in mock_flag.call_args_list]
        assert appended.count("disable_print_identity") == 1
        assert _opt_in_appended(mock_flag, deploy_mod) == []

    def test_always_on_flags_mixed_with_real_flag_success(self):
        import fabric_cli.commands.fs.deploy.fab_fs_deploy_config_file as deploy_mod

        # always-on flags are skipped; only the real opt-in flag is appended
        args = Namespace(
            feature_flags="disable_print_identity,enable_shortcut_publish,enable_experimental_features"
        )

        with patch.object(deploy_mod, "append_feature_flag") as mock_flag:
            deploy_mod._apply_feature_flags(args)

        opt_in = _opt_in_appended(mock_flag, deploy_mod)
        assert opt_in == ["enable_shortcut_publish"]
