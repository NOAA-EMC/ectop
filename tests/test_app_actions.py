from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ectop.app import Ectop


@pytest.fixture
def app() -> Ectop:
    app = Ectop(host="localhost", port=3141)
    app.ecflow_client = AsyncMock()
    return app


@pytest.mark.asyncio
async def test_action_restart_server(app: Ectop) -> None:
    with patch.object(app, "action_refresh", new_callable=AsyncMock) as mock_refresh:
        await app.action_restart_server()
        app.ecflow_client.restart_server.assert_called_once()
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_action_halt_server(app: Ectop) -> None:
    with patch.object(app, "action_refresh", new_callable=AsyncMock) as mock_refresh:
        await app.action_halt_server()
        app.ecflow_client.halt_server.assert_called_once()
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_action_refresh_logic(app: Ectop) -> None:
    mock_tree = AsyncMock()
    mock_sb = AsyncMock()

    def side_effect(selector, type=None):
        if "#suite_tree" in selector:
            return mock_tree
        if "#status_bar" in selector:
            return mock_sb
        return MagicMock()

    with patch.object(app, "query_one", side_effect=side_effect):
        app.ecflow_client.get_defs.return_value.get_server_state.return_value = "RUNNING"
        app.ecflow_client.server_version.return_value = "5.11.4"
        await app.action_refresh()
        app.ecflow_client.sync_local.assert_called_once()
        mock_sb.update_status.assert_called()


@pytest.mark.asyncio
async def test_action_load_node_worker(app: Ectop) -> None:
    mock_mc = AsyncMock()
    with patch.object(app, "get_selected_path", return_value="/s/t"), patch.object(app, "query_one", return_value=mock_mc):
        app.ecflow_client.file.side_effect = ["logs", "script", "job"]
        await app._load_node_worker("/s/t")
        assert app.ecflow_client.file.call_count == 3
        mock_mc.update_log.assert_called()


@pytest.mark.asyncio
async def test_run_client_command_success(app: Ectop) -> None:
    with patch.object(app, "action_refresh", new_callable=AsyncMock) as mock_refresh:
        await app._run_client_command("suspend", "/s/t")
        app.ecflow_client.suspend.assert_called_with("/s/t")
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_run_client_command_error(app: Ectop) -> None:
    app.ecflow_client.suspend.side_effect = RuntimeError("failed")
    with patch.object(app, "notify") as mock_notify:
        await app._run_client_command("suspend", "/s/t")
        mock_notify.assert_called_with("Command Error: failed", severity="error")


@pytest.mark.asyncio
async def test_live_log_tick(app: Ectop) -> None:
    mock_mc = AsyncMock()
    mock_mc.is_live = True
    mock_mc.active = "tab_output"
    with patch.object(app, "query_one", return_value=mock_mc), patch.object(app, "get_selected_path", return_value="/s/t"):
        app.ecflow_client.file.return_value = "new logs"
        await app._live_log_worker("/s/t")
        app.ecflow_client.file.assert_called_with("/s/t", "jobout")
        mock_mc.update_log.assert_called_with("new logs", append=True)
