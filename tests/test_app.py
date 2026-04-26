# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ectop.app import Ectop


@pytest.mark.asyncio
async def test_app_instantiation() -> None:
    # Use a dummy host/port to avoid needing a real server for basic instantiation
    app = Ectop(host="dummy", port=1234)
    assert app.host == "dummy"
    assert app.port == 1234


@pytest.mark.asyncio
async def test_app_handles_runtime_error() -> None:
    # Use a mocked client for error path testing
    with patch("ectop.app.EcflowClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.sync_local.side_effect = RuntimeError("Mock error")

        app = Ectop()
        # Mocking app.query_one because it's called during status updates on error
        app.query_one = MagicMock()

        with patch.object(app, "notify") as mock_notify:
            await app.action_refresh()
            # Wait for any scheduled workers and async tasks
            import asyncio
            for _ in range(10):
                if mock_notify.called:
                    break
                await asyncio.sleep(0.1)
            mock_notify.assert_called()


@pytest.mark.asyncio
async def test_app_actions() -> None:
    app = Ectop()
    # Check that basic actions can be triggered without crashing
    with patch.object(app, "action_refresh"):
        app.action_refresh()
