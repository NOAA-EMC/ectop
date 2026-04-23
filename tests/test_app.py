# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the main Ectop application class.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ectop import Ectop


@pytest.mark.asyncio
async def test_app_instantiation() -> None:
    """
    Test that the Ectop app can be instantiated.
    """
    app = Ectop()
    assert app is not None


@pytest.mark.asyncio
async def test_app_handles_runtime_error() -> None:
    """
    Test that the app handles connection errors gracefully.
    """
    with patch("ectop.app.EcflowClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.ping.side_effect = RuntimeError("Mock server error")

        app = Ectop()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)
        async with app.run_test() as pilot:
            worker = app._initial_connect()
            await worker.wait()
            await pilot.pause()
            assert len(app._notifications) > 0
            notification = list(app._notifications)[0]
            assert "Connection Failed" in str(notification.message)


@pytest.mark.asyncio
async def test_app_actions() -> None:
    """
    Test various node actions in the app.
    """
    with patch("ectop.app.EcflowClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_defs.return_value = None

        app = Ectop()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)

        with patch.object(Ectop, "_initial_connect", return_value=None):
            async with app.run_test() as pilot:
                with patch.object(Ectop, "get_selected_path", return_value="/suite/task"):
                    with patch.object(Ectop, "action_refresh", return_value=None):
                        worker = app._run_client_command("suspend", "/suite/task")
                        await worker.wait()
                        await pilot.pause()
                        mock_client.suspend.assert_called_with("/suite/task")
