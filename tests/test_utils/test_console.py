# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the centralized output manager and console utilities."""

import pytest

from fabric_cli.utils.fab_output_manager import (
    OutputManager,
    console,
    console_err,
    output_manager,
    reset_instance,
)


@pytest.fixture(autouse=True)
def _fresh_manager():
    """Reset the OutputManager singleton between tests."""
    reset_instance()
    yield
    reset_instance()


class TestConsoleInstances:
    """Verify shared console instances are configured correctly."""

    def test_console_stdout__not_stderr(self):
        assert console.file is not None
        assert not console.stderr

    def test_console_err_stderr__is_stderr(self):
        assert console_err.stderr


class TestOutputManagerSingleton:
    """Verify singleton accessor and reset behaviour."""

    def test_instance__returns_same_object(self):
        a = output_manager()
        b = output_manager()
        assert a is b

    def test_reset__creates_new_instance(self):
        a = output_manager()
        reset_instance()
        b = output_manager()
        assert a is not b


class TestModeAndFormat:
    """Verify mode and output-format awareness."""

    def test_default_mode__is_commandline(self):
        mgr = output_manager()
        assert mgr.get_mode() == "command_line"
        assert not mgr.is_interactive

    def test_set_interactive_mode(self):
        mgr = output_manager()
        mgr.set_mode("interactive")
        assert mgr.is_interactive

    def test_default_output_format__is_text(self):
        mgr = output_manager()
        assert mgr.get_output_format() == "text"
        assert not mgr.is_json_mode

    def test_set_json_format(self):
        mgr = output_manager()
        mgr.set_output_format("json")
        assert mgr.is_json_mode


class TestDiagnosticOutput:
    """Verify diagnostic helpers write to the correct stream."""

    def test_status__stdout_by_default(self, capsys):
        output_manager().status("All good")
        captured = capsys.readouterr()
        assert "✔" in captured.out
        assert "All good" in captured.out

    def test_status__stderr_when_requested(self, capsys):
        output_manager().status("All good", to_stderr=True)
        captured = capsys.readouterr()
        assert "✔" in captured.err

    def test_warning__always_stderr(self, capsys):
        output_manager().warning("Careful")
        captured = capsys.readouterr()
        assert "!" in captured.err
        assert "Careful" in captured.err

    def test_error__always_stderr(self, capsys):
        output_manager().error("Something broke")
        captured = capsys.readouterr()
        assert "✘" in captured.err
        assert "Something broke" in captured.err

    def test_info__always_stderr(self, capsys):
        output_manager().info("FYI")
        captured = capsys.readouterr()
        assert "ℹ" in captured.err
        assert "FYI" in captured.err


class TestStyledOutput:
    """Verify styled text helpers."""

    def test_plain__stdout(self, capsys):
        output_manager().plain("plain text")
        captured = capsys.readouterr()
        assert "plain text" in captured.out

    def test_muted__stderr_by_default(self, capsys):
        output_manager().muted("quiet text")
        captured = capsys.readouterr()
        assert "quiet text" in captured.err

    def test_muted__stdout_when_requested(self, capsys):
        output_manager().muted("quiet text", to_stderr=False)
        captured = capsys.readouterr()
        assert "quiet text" in captured.out

    def test_fabric__stdout(self, capsys):
        output_manager().fabric("brand message")
        captured = capsys.readouterr()
        assert "brand message" in captured.out


class TestPrintVersion:
    """Verify version output."""

    def test_print_version__stdout(self, capsys):
        output_manager().print_version()
        captured = capsys.readouterr()
        assert "fab version" in captured.out
