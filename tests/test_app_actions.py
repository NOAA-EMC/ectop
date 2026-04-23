# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for specific actions in the Ectop app.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ectop.app import Ectop


@pytest.mark.asyncio
async def test_action_refresh() -> None:
    """
    Test the action_refresh worker.
    """
    with patch("ectop.app.EcflowClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_defs = MagicMock()
        mock_defs.get_server_state.return_value = "RUNNING"
        mock_client.get_defs.return_value = mock_defs
        mock_client.server_version.return_value = "5.16.0"
        mock_client.host = "localhost"
        mock_client.port = 3141

        app = Ectop()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)

        async with app.run_test() as pilot:
            worker = app.action_refresh()
            await worker.wait()
            await pilot.pause()

            mock_client.sync_local.assert_called()


@pytest.mark.asyncio
async def test_run_client_command() -> None:
    """
    Test _run_client_command worker.
    """
    with patch("ectop.app.EcflowClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        app = Ectop()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)

        async with app.run_test() as pilot:
            with patch.object(Ectop, "action_refresh", return_value=None):
                worker = app._run_client_command("suspend", "/s/t")
                await worker.wait()
                await pilot.pause()
                mock_client.suspend.assert_called_with("/s/t")
