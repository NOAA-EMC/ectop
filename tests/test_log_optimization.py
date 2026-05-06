# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for log optimization logic in MainContent and Ectop app.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import RichLog

from ectop.app import Ectop
from ectop.widgets.content import MainContent


def test_main_content_update_log_full_refresh():
    """
    Test that update_log performs a full refresh when no delta is provided.
    """
    content = MainContent()
    # Mocking query_one to return a Mock RichLog
    mock_log = MagicMock(spec=RichLog)
    with patch.object(content, "query_one", return_value=mock_log):
        content.update_log("Initial Content")
        mock_log.clear.assert_called_once()
        mock_log.write.assert_called_with("Initial Content")
        assert content._content_cache["output"] == "Initial Content"
        assert content.last_log_size == len("Initial Content")


def test_main_content_update_log_with_delta():
    """
    Test that update_log correctly appends a delta and updates cache.
    """
    content = MainContent()
    content._content_cache["output"] = "Initial "
    content.last_log_size = len("Initial ")

    mock_log = MagicMock(spec=RichLog)
    with patch.object(content, "query_one", return_value=mock_log):
        content.update_log("Initial Content", delta="Content")
        mock_log.clear.assert_not_called()
        mock_log.write.assert_called_with("Content")
        assert content._content_cache["output"] == "Initial Content"
        assert content.last_log_size == len("Initial Content")


@pytest.mark.asyncio
async def test_live_log_worker_delta_calculation():
    """
    Test that _live_log_worker correctly offloads delta calculation.
    """
    from unittest.mock import AsyncMock

    app = Ectop()
    app.ecflow_client = MagicMock()
    app.ecflow_client.file = AsyncMock(return_value="Initial Content More")

    content_area = MagicMock(spec=MainContent)
    content_area._content_cache = {"output": "Initial Content"}
    content_area.last_log_size = len("Initial Content")

    with patch.object(app, "query_one", return_value=content_area):
        await app._live_log_worker("/some/path")

        # Verify delta was calculated: " More"
        content_area.update_log.assert_called_once_with("Initial Content More", delta=" More")


@pytest.mark.asyncio
async def test_live_log_worker_no_delta_calculation():
    """
    Test that _live_log_worker handles cases where no incremental update is possible.
    """
    from unittest.mock import AsyncMock

    app = Ectop()
    app.ecflow_client = MagicMock()
    app.ecflow_client.file = AsyncMock(return_value="Completely Different Content")

    content_area = MagicMock(spec=MainContent)
    content_area._content_cache = {"output": "Initial Content"}
    content_area.last_log_size = len("Initial Content")

    with patch.object(app, "query_one", return_value=content_area):
        await app._live_log_worker("/some/path")

        # delta should be None
        content_area.update_log.assert_called_once_with("Completely Different Content", delta=None)
