from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ectop.app import Ectop
from ectop.constants import STATUS_SYNC_ERROR


@pytest.mark.asyncio
async def test_app_initial_connect_runtime_error():
    mock_client = AsyncMock()
    with patch("ectop.app.EcflowClient", return_value=mock_client):
        mock_client.ping.side_effect = RuntimeError("Connection timeout")
        app = Ectop()
        app.notify = AsyncMock()
        app.query_one = MagicMock()
        await app._initial_connect()
        app.notify.assert_called()


@pytest.mark.asyncio
async def test_app_initial_connect_unexpected_error():
    mock_client = AsyncMock()
    with patch("ectop.app.EcflowClient", return_value=mock_client):
        mock_client.ping.side_effect = Exception("Strange error")
        app = Ectop()
        app.notify = AsyncMock()
        await app._initial_connect()
        app.notify.assert_called()


@pytest.mark.asyncio
async def test_run_client_command_error():
    app = Ectop()
    app.ecflow_client = AsyncMock()
    app.notify = AsyncMock()
    app.ecflow_client.suspend.side_effect = RuntimeError("failed")
    await app._run_client_command("suspend", "/path")
    app.notify.assert_called_with("Command Error: failed", severity="error")


@pytest.mark.asyncio
async def test_action_refresh_error():
    app = Ectop()
    app.notify = AsyncMock()
    mock_tree = MagicMock()
    mock_sb = MagicMock()

    def side_effect(selector, type=None):
        if "#suite_tree" in selector:
            return mock_tree
        if "#status_bar" in selector:
            return mock_sb
        return MagicMock()

    app.query_one = side_effect
    app.ecflow_client = AsyncMock()
    app.ecflow_client.sync_local.side_effect = RuntimeError("Sync failed")
    await app.action_refresh()
    mock_sb.update_status.assert_called_with(app.ecflow_client.host, app.ecflow_client.port, status=STATUS_SYNC_ERROR)
