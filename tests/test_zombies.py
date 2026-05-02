# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for Zombie Management Dashboard.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from ectop.client import EcflowClient
from ectop.widgets.modals.zombies import ZombieDashboard


@pytest.mark.asyncio
async def test_zombie_refresh():
    """
    Test that action_refresh fetches zombies and updates the table.
    """
    mock_client = MagicMock(spec=EcflowClient)

    # Mock ecflow.Zombie
    zombie = MagicMock()
    zombie.path = MagicMock(return_value="/s1/t1")
    zombie.calls = MagicMock(return_value="zombie")
    zombie.user = MagicMock(return_value="user")
    zombie.host = MagicMock(return_value="host")
    zombie.rid = MagicMock(return_value="123")
    zombie.try_no = MagicMock(return_value=1)
    zombie.allowed = MagicMock(return_value="time")

    mock_client.zombie_get = AsyncMock(return_value=[zombie])

    dashboard = ZombieDashboard(mock_client)

    # Mock DataTable and other components
    mock_table = MagicMock()
    mock_table.cursor_row = None

    mock_app = MagicMock()
    with patch.object(dashboard, "query_one", return_value=mock_table), patch.object(
        ZombieDashboard, "app", return_value=mock_app, new_callable=PropertyMock
    ):
        await dashboard.action_refresh()

        mock_client.zombie_get.assert_called_once()
        mock_table.clear.assert_called_once()
        mock_table.add_row.assert_called_once()
        args, kwargs = mock_table.add_row.call_args
        assert args[0] == "/s1/t1"
