# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for error handling paths in the main Ectop app.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ectop.app import Ectop


@pytest.mark.asyncio
async def test_app_initial_connect_runtime_error():
    """Test _initial_connect error handling for RuntimeError."""
    mock_client_class = MagicMock()
    # Ensure it raises error when instantiated
    mock_client_class.side_effect = RuntimeError("Connection timeout")

    with patch("ectop.app.EcflowClient", mock_client_class):
        app = Ectop()
        # Mock call_from_thread to execute immediately
        app.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)
        # Mock notify
        app.notify = MagicMock()
        # Mock query_one for tree
        app.query_one = MagicMock()

        # Call directly instead of via on_mount
        app._initial_connect()

        # Verify notification was sent
        app.notify.assert_any_call("Connection Failed: Connection timeout", severity="error", timeout=10)


@pytest.mark.asyncio
async def test_app_initial_connect_unexpected_error():
    """Test _initial_connect error handling for generic Exception."""
    mock_client_class = MagicMock()
    mock_client_class.side_effect = Exception("Strange error")

    with patch("ectop.app.EcflowClient", mock_client_class):
        app = Ectop()
        app.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)
        app.notify = MagicMock()

        app._initial_connect()

        app.notify.assert_any_call("Unexpected Error: Strange error", severity="error")


@pytest.mark.asyncio
async def test_run_client_command_error():
    """Test _run_client_command error handling."""
    app = Ectop()
    app.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)
    app.notify = MagicMock()

    mock_client = MagicMock()
    mock_client.suspend.side_effect = RuntimeError("Failed to suspend")
    app.ecflow_client = mock_client

    app._run_client_command("suspend", "/path")

    app.notify.assert_any_call("Command Error: Failed to suspend", severity="error")


@pytest.mark.asyncio
async def test_action_refresh_error():
    """Test action_refresh error handling."""
    app = Ectop()
    app.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)
    app.notify = MagicMock()
    # Mock status_bar and tree
    app.query_one = MagicMock()

    mock_client = MagicMock()
    mock_client.sync_local.side_effect = RuntimeError("Sync failed")
    app.ecflow_client = mock_client

    app.action_refresh()

    # Check that it notified about the error
    found = False
    for call in app.notify.call_args_list:
        if "Refresh Error: Sync failed" in str(call[0][0]):
            found = True
            break
    assert found
