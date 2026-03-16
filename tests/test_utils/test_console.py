# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the centralized rich console utility module."""

import pytest

from fabric_cli.utils.console import (
    console,
    console_err,
    print_error,
    print_error_panel,
    print_fabric,
    print_file_written,
    print_info,
    print_muted,
    print_plain,
    print_success,
    print_table,
    print_warning,
)


class TestConsoleInstances:
    """Verify shared console instances are configured correctly."""

    def test_console_stdout__not_stderr(self):
        assert console.file is not None
        assert not console.stderr

    def test_console_err_stderr__is_stderr(self):
        assert console_err.stderr


class TestPrintSuccess:
    """Tests for print_success helper."""

    def test_print_success__stdout(self, capsys):
        print_success("All good")
        captured = capsys.readouterr()
        assert "✔" in captured.out
        assert "All good" in captured.out

    def test_print_success__stderr(self, capsys):
        print_success("All good", to_stderr=True)
        captured = capsys.readouterr()
        assert "✔" in captured.err


class TestPrintError:
    """Tests for print_error helper."""

    def test_print_error__stderr_by_default(self, capsys):
        print_error("Something broke")
        captured = capsys.readouterr()
        assert "✘" in captured.err
        assert "Something broke" in captured.err

    def test_print_error__stdout_when_requested(self, capsys):
        print_error("Something broke", to_stderr=False)
        captured = capsys.readouterr()
        assert "Something broke" in captured.out


class TestPrintWarning:
    """Tests for print_warning helper."""

    def test_print_warning__stderr_by_default(self, capsys):
        print_warning("Careful")
        captured = capsys.readouterr()
        assert "!" in captured.err
        assert "Careful" in captured.err


class TestPrintInfo:
    """Tests for print_info helper."""

    def test_print_info__stderr_by_default(self, capsys):
        print_info("FYI")
        captured = capsys.readouterr()
        assert "ℹ" in captured.err
        assert "FYI" in captured.err


class TestPrintMuted:
    """Tests for print_muted helper."""

    def test_print_muted__stdout_by_default(self, capsys):
        print_muted("quiet text")
        captured = capsys.readouterr()
        assert "quiet text" in captured.out


class TestPrintFabric:
    """Tests for print_fabric helper."""

    def test_print_fabric__stdout(self, capsys):
        print_fabric("brand message")
        captured = capsys.readouterr()
        assert "brand message" in captured.out


class TestPrintPlain:
    """Tests for print_plain helper."""

    def test_print_plain__stdout(self, capsys):
        print_plain("plain text")
        captured = capsys.readouterr()
        assert "plain text" in captured.out

    def test_print_plain__stderr(self, capsys):
        print_plain("plain text", to_stderr=True)
        captured = capsys.readouterr()
        assert "plain text" in captured.err


class TestPrintErrorPanel:
    """Tests for print_error_panel helper."""

    def test_print_error_panel__basic(self, capsys):
        print_error_panel("Request failed")
        captured = capsys.readouterr()
        assert "Request failed" in captured.err

    def test_print_error_panel__with_reason_and_suggestion(self, capsys):
        print_error_panel(
            "Auth failed",
            reason="Token expired",
            suggestion="Run `fab auth login`",
        )
        captured = capsys.readouterr()
        assert "Token expired" in captured.err
        assert "fab auth login" in captured.err


class TestPrintTable:
    """Tests for print_table helper."""

    def test_print_table__basic(self, capsys):
        rows = [{"name": "ws1", "type": "Workspace"}, {"name": "ws2", "type": "Workspace"}]
        print_table(rows)
        captured = capsys.readouterr()
        assert "ws1" in captured.out
        assert "ws2" in captured.out

    def test_print_table__empty_rows(self, capsys):
        print_table([])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_table__custom_columns(self, capsys):
        rows = [{"name": "ws1", "type": "Workspace", "id": "123"}]
        print_table(rows, columns=["name", "type"])
        captured = capsys.readouterr()
        assert "ws1" in captured.out
        # id column should not appear since we only specified name and type
        assert "123" not in captured.out


class TestPrintFileWritten:
    """Tests for print_file_written helper."""

    def test_print_file_written__basic(self, capsys):
        print_file_written("/tmp/config.yaml")
        captured = capsys.readouterr()
        assert "File written" in captured.out
        assert "/tmp/config.yaml" in captured.out

    def test_print_file_written__overwritten(self, capsys):
        print_file_written("/tmp/config.yaml", overwritten=True)
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "overwritten" in combined.lower() or "File written" in combined
