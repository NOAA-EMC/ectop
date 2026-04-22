# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for Ectop action methods.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ectop.app import Ectop


@pytest.fixture
def app() -> Ectop:
    """Create an Ectop app instance with mocked components."""
    app = Ectop(host="localhost", port=3141)
    app.ecflow_client = AsyncMock()
    return app


def test_action_restart_server(app: Ectop) -> None:
    """Test action_restart_server calls client and refresh."""
    with patch.object(app, "action_refresh") as mock_refresh, patch.object(app, "call_from_thread") as mock_call:
        app.action_restart_server()
        app.ecflow_client.restart_server.assert_called_once()
        mock_refresh.assert_called_once()
        mock_call.assert_called()


def test_action_halt_server(app: Ectop) -> None:
    """Test action_halt_server calls client and refresh."""
    with patch.object(app, "action_refresh") as mock_refresh, patch.object(app, "call_from_thread") as mock_call:
        app.action_halt_server()
        app.ecflow_client.halt_server.assert_called_once()
        mock_refresh.assert_called_once()
        mock_call.assert_called()


@pytest.mark.asyncio
async def test_action_refresh_logic(app: Ectop) -> None:
    """Test the logic inside action_refresh."""
    # We need to mock query_one for tree and status_bar
    mock_tree = AsyncMock()
    mock_sb = AsyncMock()

    def side_effect(selector, type=None):
        if "#suite_tree" in selector:
            return mock_tree
        if "#status_bar" in selector:
            return mock_sb
        return AsyncMock()

    with patch.object(app, "query_one", side_effect=side_effect), patch.object(app, "call_from_thread") as mock_call:
        app.ecflow_client.get_defs.return_value.get_server_state.return_value = "RUNNING"
        app.ecflow_client.server_version.return_value = "5.11.4"

        app.action_refresh()

        app.ecflow_client.sync_local.assert_called_once()
        # Verify version was fetched
        app.ecflow_client.server_version.assert_called_once()
        # Verify status_bar update was called via call_from_thread
        # We check the arguments passed to call_from_thread
        calls = [c.args for c in mock_call.call_args_list]
        # One of the calls should be status_bar.update_status
        assert any(mock_sb.update_status in call for call in calls)


def test_action_toggle_live(app: Ectop) -> None:
    """Test action_toggle_live toggles is_live state."""
    mock_mc = AsyncMock()
    mock_mc.is_live = False

    with patch.object(app, "query_one", return_value=mock_mc), patch.object(app, "notify"):
        app.action_toggle_live()
        assert mock_mc.is_live is True

        app.action_toggle_live()
        assert mock_mc.is_live is False


def test_action_copy_path(app: Ectop) -> None:
    """Test action_copy_path with and without selection."""
    with (
        patch.object(app, "get_selected_path") as mock_get_path,
        patch.object(app, "notify") as mock_notify,
        patch.object(app, "copy_to_clipboard") as mock_copy,
    ):
        # Case 1: No selection
        mock_get_path.return_value = None
        app.action_copy_path()
        mock_notify.assert_called_with("No node selected", severity="warning")

        # Case 2: Selection exists
        mock_get_path.return_value = "/suite/task"
        app.action_copy_path()
        mock_copy.assert_called_with("/suite/task")
        mock_notify.assert_called_with("Copied to clipboard: /suite/task")


def test_action_commands(app: Ectop) -> None:
    """Test generic client commands like suspend, resume, kill, force, requeue."""
    with patch.object(app, "get_selected_path", return_value="/s/t"), patch.object(app, "_run_client_command") as mock_run:
        app.action_suspend()
        mock_run.assert_called_with("suspend", "/s/t")

        app.action_resume()
        mock_run.assert_called_with("resume", "/s/t")

        app.action_kill()
        mock_run.assert_called_with("kill", "/s/t")

        app.action_force()
        mock_run.assert_called_with("force_complete", "/s/t")

        app.action_requeue()
        mock_run.assert_called_with("requeue", "/s/t")


def test_action_load_node_worker(app: Ectop) -> None:
    """Test action_load_node worker with successful file fetches."""
    mock_mc = AsyncMock()
    with (
        patch.object(app, "get_selected_path", return_value="/s/t"),
        patch.object(app, "query_one", return_value=mock_mc),
        patch.object(app, "call_from_thread") as mock_call,
    ):
        app.ecflow_client.file.side_effect = ["logs", "script", "job"]
        app.action_load_node()

        assert app.ecflow_client.file.call_count == 3
        # Verify update methods were called via call_from_thread
        calls = [c.args for c in mock_call.call_args_list]
        assert any(mock_mc.update_log in call for call in calls)
        assert any(mock_mc.update_script in call for call in calls)
        assert any(mock_mc.update_job in call for call in calls)


def test_action_load_node_worker_errors(app: Ectop) -> None:
    """Test action_load_node worker with missing files."""
    mock_mc = AsyncMock()
    with (
        patch.object(app, "get_selected_path", return_value="/s/t"),
        patch.object(app, "query_one", return_value=mock_mc),
        patch.object(app, "call_from_thread") as mock_call,
    ):
        app.ecflow_client.file.side_effect = RuntimeError("File not found")
        app.action_load_node()

        # Should have called show_error for each missing file type
        calls = [c.args for c in mock_call.call_args_list]
        assert any(mock_mc.show_error in call for call in calls)


def test_run_client_command_success(app: Ectop) -> None:
    """Test _run_client_command success path."""
    with patch.object(app, "call_from_thread"), patch.object(app, "action_refresh") as mock_refresh:
        app._run_client_command("suspend", "/s/t")
        app.ecflow_client.suspend.assert_called_with("/s/t")
        mock_refresh.assert_called_once()


def test_run_client_command_error(app: Ectop) -> None:
    """Test _run_client_command error path."""
    app.ecflow_client.suspend.side_effect = RuntimeError("failed")
    with patch.object(app, "call_from_thread") as mock_call:
        app._run_client_command("suspend", "/s/t")
        # Should have notified error
        mock_call.assert_called()
        args = [c.args for c in mock_call.call_args_list]
        assert any(app.notify in arg and "Command Error: failed" in arg for arg in args)


def test_action_why_variables(app: Ectop) -> None:
    """Test action_why and action_variables push screens."""
    with patch.object(app, "get_selected_path", return_value="/s/t"), patch.object(app, "push_screen") as mock_push:
        app.action_why()
        mock_push.assert_called()

        mock_push.reset_mock()
        app.action_variables()
        mock_push.assert_called()


def test_live_log_tick(app: Ectop) -> None:
    """Test _live_log_tick logic."""
    mock_mc = AsyncMock()
    mock_mc.is_live = True
    mock_mc.active = "tab_output"

    with (
        patch.object(app, "query_one", return_value=mock_mc),
        patch.object(app, "get_selected_path", return_value="/s/t"),
        patch.object(app, "call_from_thread") as mock_call,
    ):
        app.ecflow_client.file.return_value = "new logs"
        app._live_log_tick()

        app.ecflow_client.file.assert_called_with("/s/t", "jobout")
        mock_call.assert_called_with(mock_mc.update_log, "new logs", append=True)
