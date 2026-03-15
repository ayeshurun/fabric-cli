# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for fabric_cli_v2.output module."""

import json
from io import StringIO

import pytest

from fabric_cli_v2 import output


class TestOutput:

    def test_print_json(self, capsys):
        output.print_json({"key": "value"})
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["key"] == "value"

    def test_print_table(self, capsys):
        rows = [{"name": "ws1", "id": "123"}, {"name": "ws2", "id": "456"}]
        output.print_table(rows, columns=["name", "id"])
        captured = capsys.readouterr()
        assert "ws1" in captured.out
        assert "ws2" in captured.out

    def test_print_table__empty(self, capsys):
        output.print_table([])
        assert capsys.readouterr().out == ""

    def test_print_items__text_compact(self, capsys):
        items = [{"displayName": "nb1", "type": "Notebook"}]
        output.print_items(items, output_format="text")
        captured = capsys.readouterr()
        assert "nb1" in captured.out

    def test_print_items__json(self, capsys):
        items = [{"displayName": "nb1", "type": "Notebook"}]
        output.print_items(items, output_format="json")
        data = json.loads(capsys.readouterr().out)
        assert data["value"][0]["displayName"] == "nb1"

    def test_print_items__empty(self, capsys):
        output.print_items([], output_format="text")
        assert capsys.readouterr().out == ""

    def test_print_error(self, capsys):
        output.print_error("something broke")
        captured = capsys.readouterr()
        assert "something broke" in captured.err

    def test_print_warning(self, capsys):
        output.print_warning("careful")
        captured = capsys.readouterr()
        assert "careful" in captured.err

    def test_print_success(self, capsys):
        output.print_success("done")
        captured = capsys.readouterr()
        assert "done" in captured.out
