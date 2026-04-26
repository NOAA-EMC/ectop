# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import ecflow
from ectop.app import Ectop

@pytest.fixture
def app(ecflow_server):
    host, port = ecflow_server
    return Ectop(host=host, port=port)

@pytest.mark.asyncio
async def test_action_restart_server(app):
    with patch.object(app, "action_refresh", new_callable=AsyncMock) as mock_refresh:
        await app.action_restart_server()
        mock_refresh.assert_called_once()

@pytest.mark.asyncio
async def test_run_client_command_success(app):
    defs = ecflow.Defs()
    defs.add_suite("s").add_task("t")
    c = ecflow.Client(app.client.host, app.client.port)
    c.load(defs)
    with patch.object(app, "action_refresh", new_callable=AsyncMock) as mock_refresh:
        await app._run_client_command("suspend", "/s/t")
        mock_refresh.assert_called_once()
        await app.client.sync_local()
        d = await app.client.get_defs()
        assert d.find_abs_node("/s/t").is_suspended()
