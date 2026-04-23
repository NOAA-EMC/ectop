# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for error handling paths in the main Ectop app.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ectop.app import Ectop


@pytest.mark.asyncio
async def test_action_refresh_error() -> None:
    """
    Test error handling in action_refresh.
    """
    with patch("ectop.app.EcflowClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.sync_local.side_effect = RuntimeError("Sync failed")

        app = Ectop()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)

        async with app.run_test() as pilot:
            worker = app.action_refresh()
            await worker.wait()
            await pilot.pause()

            assert len(app._notifications) > 0


@pytest.mark.asyncio
async def test_load_node_error() -> None:
    """
    Test error handling in _load_node_worker.
    """
    with patch("ectop.app.EcflowClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.file.side_effect = RuntimeError("File not found")

        app = Ectop()
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)

        async with app.run_test() as pilot:
            worker = app._load_node_worker("/s/t")
            await worker.wait()
            await pilot.pause()

            assert app.query_one("#main_content") is not None
