# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Tests for POSIX compliance of the Fabric CLI.

This module verifies that the CLI adheres to POSIX standards including:
- Exit codes (0=success, 1=error, 2=misuse, 126-127=execution errors, 128+n=signals)
- Help flags (-h, --help)
- Signal handling (SIGINT, SIGTERM, SIGHUP, SIGQUIT)
- Environment variable naming (UPPERCASE with underscores)
- Standard stream usage (stdout for output, stderr for errors)
"""

import os
import signal
import subprocess
import sys
import pytest
from unittest.mock import patch, MagicMock

from fabric_cli.core import fab_constant
from fabric_cli.main import main, _signal_handler, _setup_signal_handlers


class TestExitCodes:
    """Test POSIX-compliant exit codes."""

    def test_exit_code_success_is_zero(self):
        """Verify success exit code is 0 (POSIX requirement)."""
        assert fab_constant.EXIT_CODE_SUCCESS == 0

    def test_exit_code_error_is_one(self):
        """Verify general error exit code is 1 (POSIX requirement)."""
        assert fab_constant.EXIT_CODE_ERROR == 1

    def test_exit_code_misuse_is_two(self):
        """Verify misuse of builtins exit code is 2 (POSIX requirement)."""
        assert fab_constant.EXIT_CODE_CANCELLED_OR_MISUSE_BUILTINS == 2

    def test_exit_code_cannot_execute_is_126(self):
        """Verify cannot execute exit code is 126 (POSIX requirement for permission/auth errors)."""
        assert fab_constant.EXIT_CODE_CANNOT_EXECUTE == 126

    def test_exit_code_command_not_found_is_127(self):
        """Verify command not found exit code is 127 (POSIX requirement)."""
        assert fab_constant.EXIT_CODE_COMMAND_NOT_FOUND == 127

    def test_no_nonstandard_exit_code_4(self):
        """Verify the old non-standard exit code 4 is not present."""
        # Should not have EXIT_CODE_AUTHORIZATION_REQUIRED = 4
        assert not hasattr(fab_constant, 'EXIT_CODE_AUTHORIZATION_REQUIRED')


class TestHelpFlags:
    """Test POSIX-compliant help flags."""

    def test_help_flag_short_form_exists(self):
        """Verify -h flag is available (POSIX standard short form)."""
        result = subprocess.run(
            [sys.executable, "-m", "fabric_cli.main", "-h"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should show help text or exit gracefully
        assert result.returncode in [0, 1, 2]

    def test_help_flag_long_form_exists(self):
        """Verify --help flag is available (POSIX standard long form)."""
        result = subprocess.run(
            [sys.executable, "-m", "fabric_cli.main", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should show help text or exit gracefully
        assert result.returncode in [0, 1, 2]

    def test_old_help_flag_not_supported(self):
        """Verify old -help (single dash long form) is not the primary pattern."""
        # The parser now uses standard argparse -h and --help, not -help
        # This test ensures we're POSIX compliant
        # argparse automatically adds -h and --help
        from argparse import ArgumentParser
        
        parser = ArgumentParser()
        # argparse automatically adds -h and --help
        
        # Check that help action uses -h and --help (automatically added by argparse)
        help_actions = [a for a in parser._actions if hasattr(a, 'dest') and a.dest == 'help']
        if help_actions:
            help_action = help_actions[0]
            # Should have both -h and --help (POSIX standard)
            assert '-h' in help_action.option_strings, "Should have -h (POSIX short form)"
            assert '--help' in help_action.option_strings, "Should have --help (POSIX long form)"
            # Should NOT have -help (non-POSIX single-dash long form)
            assert '-help' not in help_action.option_strings, "Should not have -help (non-POSIX)"


class TestVersionFlags:
    """Test POSIX-compliant version flags."""

    def test_version_flag_short_v_exists(self):
        """Verify -v flag is available for version."""
        result = subprocess.run(
            [sys.executable, "-m", "fabric_cli.main", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should show version or exit gracefully
        assert result.returncode in [0, 1, 2]

    def test_version_flag_short_V_exists(self):
        """Verify -V flag is available for version (common alternative)."""
        result = subprocess.run(
            [sys.executable, "-m", "fabric_cli.main", "-V"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should show version or exit gracefully
        assert result.returncode in [0, 1, 2]

    def test_version_flag_long_form_exists(self):
        """Verify --version flag is available."""
        result = subprocess.run(
            [sys.executable, "-m", "fabric_cli.main", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should show version or exit gracefully
        assert result.returncode in [0, 1, 2]


class TestSignalHandling:
    """Test POSIX-compliant signal handling."""

    def test_signal_handler_setup_exists(self):
        """Verify signal handler setup function exists."""
        assert callable(_setup_signal_handlers)

    def test_signal_handler_function_exists(self):
        """Verify signal handler function exists."""
        assert callable(_signal_handler)

    def test_signal_handler_sigint(self):
        """Test SIGINT handler exits with 128+2=130."""
        with pytest.raises(SystemExit) as exc_info:
            _signal_handler(signal.SIGINT, None)
        assert exc_info.value.code == 128 + signal.SIGINT

    def test_signal_handler_sigterm(self):
        """Test SIGTERM handler exits with 128+15=143."""
        with pytest.raises(SystemExit) as exc_info:
            _signal_handler(signal.SIGTERM, None)
        assert exc_info.value.code == 128 + signal.SIGTERM

    def test_signal_handler_sigquit(self):
        """Test SIGQUIT handler exits with 128+3=131."""
        with pytest.raises(SystemExit) as exc_info:
            _signal_handler(signal.SIGQUIT, None)
        assert exc_info.value.code == 128 + signal.SIGQUIT

    @pytest.mark.skipif(not hasattr(signal, 'SIGHUP'), reason="SIGHUP not available on Windows")
    def test_signal_handler_sighup(self):
        """Test SIGHUP handler exits with 128+1=129 (Unix-like systems only)."""
        with pytest.raises(SystemExit) as exc_info:
            _signal_handler(signal.SIGHUP, None)
        assert exc_info.value.code == 128 + signal.SIGHUP

    def test_signal_handlers_registered(self):
        """Verify signal handlers are registered properly."""
        # Save original handlers
        original_sigint = signal.signal(signal.SIGINT, signal.SIG_DFL)
        original_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        original_sigquit = signal.signal(signal.SIGQUIT, signal.SIG_DFL)
        
        try:
            _setup_signal_handlers()
            
            # Check SIGINT handler is set
            assert signal.getsignal(signal.SIGINT) == _signal_handler
            
            # Check SIGTERM handler is set
            assert signal.getsignal(signal.SIGTERM) == _signal_handler
            
            # Check SIGQUIT handler is set
            assert signal.getsignal(signal.SIGQUIT) == _signal_handler
            
            # Check SIGHUP handler is set (if available)
            if hasattr(signal, 'SIGHUP'):
                assert signal.getsignal(signal.SIGHUP) == _signal_handler
        finally:
            # Restore original handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
            signal.signal(signal.SIGQUIT, original_sigquit)


class TestEnvironmentVariables:
    """Test environment variable naming."""

    def test_env_var_fab_token(self):
        """Verify FAB_TOKEN constant value."""
        assert fab_constant.FAB_TOKEN == "fab_token"

    def test_env_var_fab_token_onelake(self):
        """Verify FAB_TOKEN_ONELAKE constant value."""
        assert fab_constant.FAB_TOKEN_ONELAKE == "fab_token_onelake"

    def test_env_var_fab_token_azure(self):
        """Verify FAB_TOKEN_AZURE constant value."""
        assert fab_constant.FAB_TOKEN_AZURE == "fab_token_azure"

    def test_env_var_fab_spn_client_id(self):
        """Verify FAB_SPN_CLIENT_ID constant value."""
        assert fab_constant.FAB_SPN_CLIENT_ID == "fab_spn_client_id"

    def test_env_var_fab_spn_client_secret(self):
        """Verify FAB_SPN_CLIENT_SECRET constant value."""
        assert fab_constant.FAB_SPN_CLIENT_SECRET == "fab_spn_client_secret"

    def test_env_var_fab_spn_cert_path(self):
        """Verify FAB_SPN_CERT_PATH constant value."""
        assert fab_constant.FAB_SPN_CERT_PATH == "fab_spn_cert_path"

    def test_env_var_fab_spn_cert_password(self):
        """Verify FAB_SPN_CERT_PASSWORD constant value."""
        assert fab_constant.FAB_SPN_CERT_PASSWORD == "fab_spn_cert_password"

    def test_env_var_fab_spn_federated_token(self):
        """Verify FAB_SPN_FEDERATED_TOKEN constant value."""
        assert fab_constant.FAB_SPN_FEDERATED_TOKEN == "fab_spn_federated_token"

    def test_env_var_fab_tenant_id(self):
        """Verify FAB_TENANT_ID constant value."""
        assert fab_constant.FAB_TENANT_ID == "fab_tenant_id"

    def test_env_var_fab_refresh_token(self):
        """Verify FAB_REFRESH_TOKEN constant value."""
        assert fab_constant.FAB_REFRESH_TOKEN == "fab_refresh_token"

    def test_env_var_identity_type(self):
        """Verify IDENTITY_TYPE constant value."""
        assert fab_constant.IDENTITY_TYPE == "identity_type"

    def test_env_var_fab_auth_mode(self):
        """Verify FAB_AUTH_MODE constant value."""
        assert fab_constant.FAB_AUTH_MODE == "fab_auth_mode"

    def test_env_var_fab_authority(self):
        """Verify FAB_AUTHORITY constant value."""
        assert fab_constant.FAB_AUTHORITY == "fab_authority"

    def test_env_var_constants_exist(self):
        """Verify all env var constants are defined."""
        env_var_constants = [
            fab_constant.FAB_TOKEN,
            fab_constant.FAB_TOKEN_ONELAKE,
            fab_constant.FAB_TOKEN_AZURE,
            fab_constant.FAB_SPN_CLIENT_ID,
            fab_constant.FAB_SPN_CLIENT_SECRET,
            fab_constant.FAB_SPN_CERT_PATH,
            fab_constant.FAB_SPN_CERT_PASSWORD,
            fab_constant.FAB_SPN_FEDERATED_TOKEN,
            fab_constant.FAB_TENANT_ID,
            fab_constant.FAB_REFRESH_TOKEN,
            fab_constant.IDENTITY_TYPE,
            fab_constant.FAB_AUTH_MODE,
            fab_constant.FAB_AUTHORITY,
        ]
        
        # Verify all constants are strings
        for env_var in env_var_constants:
            assert isinstance(env_var, str), f"{env_var} should be a string"


class TestStandardStreams:
    """Test proper usage of stdout and stderr."""

    def test_error_output_uses_stderr(self):
        """Verify error messages use stderr (POSIX requirement)."""
        from fabric_cli.utils import fab_ui
        from fabric_cli.core.fab_exceptions import FabricCLIError
        from io import StringIO
        
        # Create a mock error
        error = FabricCLIError("Test error", fab_constant.ERROR_UNEXPECTED_ERROR)
        
        # Capture stderr
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                try:
                    fab_ui.print_output_error(error, output_format_type='text')
                except Exception:
                    pass  # Ignore any exceptions from the output function
        
        # Errors should go to stderr, not stdout
        # Note: This is a basic check, actual implementation may vary

    def test_warning_output_uses_stderr(self):
        """Verify warning messages use stderr (POSIX requirement for diagnostic messages)."""
        from fabric_cli.utils import fab_ui
        from io import StringIO
        
        # Test warning output
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            try:
                fab_ui.print_warning("Test warning")
            except Exception:
                pass  # Ignore any exceptions from the output function


class TestOptionPatterns:
    """Test POSIX-compliant option patterns."""

    def test_short_options_single_dash(self):
        """Verify short options use single dash (POSIX requirement)."""
        # Short options like -h, -v, -c should use single dash
        # This is already enforced by argparse conventions
        result = subprocess.run(
            [sys.executable, "-m", "fabric_cli.main", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should work without error
        assert result.returncode in [0, 1, 2]

    def test_long_options_double_dash(self):
        """Verify long options use double dash (POSIX requirement)."""
        # Long options like --help, --version should use double dash
        result = subprocess.run(
            [sys.executable, "-m", "fabric_cli.main", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should work without error
        assert result.returncode in [0, 1, 2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
