# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""Real-server tests for the Zombie Management Dashboard."""

from __future__ import annotations

import pytest
from textual.widgets import DataTable

from ectop.app import Ectop
from ectop.client import EcflowClient
from ectop.widgets.modals.zombies import ZombieDashboard


@pytest.mark.asyncio
async def test_zombie_refresh(ecflow_server: str) -> None:
    """Refresh the dashboard from a real ecFlow server and update its table.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    """
    host, port_text = ecflow_server.split(":")
    client = EcflowClient(host, int(port_text))
    app = Ectop(host, int(port_text), refresh_interval=60)
    dashboard = ZombieDashboard(client)

    async with app.run_test() as pilot:
        app.push_screen(dashboard)
        for _ in range(50):
            if dashboard.is_mounted:
                break
            await pilot.pause(0.02)
        assert dashboard.is_mounted

        worker = dashboard.action_refresh()
        assert worker is not None
        await worker.wait()
        actual_zombies = await client.zombie_get()
        table = dashboard.query_one(DataTable)
        assert [zombie.path_to_task() for zombie in dashboard._zombies] == [zombie.path_to_task() for zombie in actual_zombies]
        assert table.row_count == len(actual_zombies)
