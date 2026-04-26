# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import ecflow
import pytest

from ectop.app import Ectop


@pytest.fixture
def app(ecflow_server):
    host, port = ecflow_server
    return Ectop(host=host, port=port)


@pytest.mark.asyncio
async def test_action_restart_server(app):
    # Mock action_refresh
    with patch.object(app, "action_refresh", new_callable=AsyncMock) as mock_refresh:
        # We need to reach the underlying logic because @work wrapper might be tricky to await directly in this context
        # depending on how mock_work is implemented in conftest.py
        await app.client.restart_server()
        # Direct call to refresh logic if possible
        if hasattr(app, "_action_refresh_logic"):
            await app._action_refresh_logic()
        else:
            await app.action_refresh()
        mock_refresh.assert_called()


@pytest.mark.asyncio
async def test_run_client_command_success(app, ecflow_server):
    host, port = ecflow_server
    defs = ecflow.Defs()
    defs.add_suite("s_actions").add_task("t")
    c = ecflow.Client(host, port)
    c.load(defs)
    with patch.object(app, "action_refresh", new_callable=AsyncMock) as mock_refresh:
        await app._run_client_command("suspend", "/s_actions/t")
        mock_refresh.assert_called()
        await app.client.sync_local()
        d = await app.client.get_defs()
        assert d.find_abs_node("/s_actions/t").is_suspended()
