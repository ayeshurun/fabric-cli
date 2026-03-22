# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

import fabric_cli.core.fab_state_config as state_config
from fabric_cli.utils.fab_output_manager import OutputManager


def render_rich_arg(arg):
    """Convert a Rich renderable (e.g. Table) to plain text for test assertions.

    If *arg* is already a string it is returned as-is.  Otherwise it is
    rendered through a headless Rich Console so that the result is a plain
    string that can be searched with ``in``, split, etc.
    """
    if isinstance(arg, str):
        return arg
    try:
        from rich.console import Console as _Console

        from fabric_cli.utils.fab_output_manager import FAB_THEME

        buf = StringIO()
        _Console(file=buf, width=300, no_color=True, theme=FAB_THEME).print(arg)
        return buf.getvalue()
    except Exception:
        return str(arg)


@pytest.fixture
def mock_questionary_print():
    """Mock OutputManager._safe_print — the single gateway for data output.

    In the original codebase ``questionary.print`` was used for ALL data
    output (text, tables, grey/muted messages) regardless of target
    stream, while ``prompt_toolkit.print_formatted_text`` handled
    status/done and warning messages separately.

    In the refactored architecture ``_safe_print`` serves the same role:
    every data/display call routes through it, while status, warning and
    error calls go directly to the console.  Patching ``_safe_print``
    therefore captures exactly the same set of calls the old mock did.
    """
    with patch.object(OutputManager, '_safe_print') as mock:
        yield mock


@pytest.fixture
def mock_print_warning():
    """Mock OutputManager.warning (covers both print_warning and log_warning callers)."""
    with patch("fabric_cli.utils.fab_output_manager.OutputManager.warning") as mock:
        yield mock


@pytest.fixture
def mock_os_path_exists():
    with patch("os.path.exists") as mock:
        yield mock


@pytest.fixture
def mock_json_load():
    with patch("json.load") as mock:
        yield mock


@pytest.fixture
def mock_os_remove():
    with patch("os.remove") as mock:
        yield mock


@pytest.fixture
def mock_glob_glob():
    with patch("glob.glob") as mock:
        yield mock


@pytest.fixture
def mock_fab_set_state_config():
    original_values = {}

    def _set_config(key: str, value: str):
        # Store original value if it exists
        try:
            original_values[key] = state_config.get_config(key)
        except KeyError:
            # Key didn't exist before, mark it for deletion after test
            original_values[key] = None

        # Set the new value
        state_config.set_config(key, value)

    yield _set_config

    # Restore original values after test
    for key, original_value in original_values.items():
        # Restore original value
        state_config.set_config(key, original_value)


@pytest.fixture
def reset_context():
    """Reset the Context singleton before test to prevent state leakage."""
    from fabric_cli.core.fab_context import Context

    context_instance = Context()
    context_instance._context = None
    context_instance._command = None
    context_instance._loading_context = False

    yield context_instance
