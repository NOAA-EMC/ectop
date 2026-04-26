# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest
from ectop.app import Ectop
from ectop.constants import STATUS_SYNC_ERROR

@pytest.mark.asyncio
async def test_app_initial_connect_runtime_error(ecflow_server):
    app = Ectop(host="localhost", port=1)
    app.notify = MagicMock()
    app.query_one = MagicMock()
    await app._initial_connect()
    app.notify.assert_called()

@pytest.mark.asyncio
async def test_action_refresh_error(ecflow_server):
    host, port = ecflow_server
    app = Ectop(host=host, port=port)
    app.notify = MagicMock()
    mock_sb = MagicMock()
    def side_effect(selector, type=None):
        if "#status_bar" in selector: return mock_sb
        return MagicMock()
    app.query_one = side_effect
    app.client.port = 1
    await app.action_refresh()
    mock_sb.update_status.assert_called_with(app.client.host, 1, status=STATUS_SYNC_ERROR)
