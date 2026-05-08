# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Integration tests for node data loading in Ectop.
"""

from __future__ import annotations

import asyncio
import random
import string
from unittest.mock import AsyncMock, patch

import ecflow
import pytest

from ectop.app import Ectop
from ectop.widgets.content import MainContent
from ectop.widgets.sidebar import SuiteTree


@pytest.mark.asyncio
async def test_node_parallel_loading_integrated(ecflow_server: str) -> None:
    """
    Test that node data (logs, scripts, jobs) are loaded correctly and in parallel.

    Args:
        ecflow_server: The host:port of the live ecFlow server.
    """
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))
    client.delete_all()

    suite_name = "s_" + "".join(random.choices(string.ascii_lowercase, k=8))

    defs = ecflow.Defs()
    suite = defs.add_suite(suite_name)
    suite.add_task("t1")
    client.load(defs, force=True)

    task_path = f"/{suite_name}/t1"

    # Pre-initialize client mock to control file returns
    mock_client = AsyncMock()
    mock_client.file = AsyncMock(side_effect=lambda p, t: f"Content for {t}")
    mock_client.sync_local = AsyncMock()
    mock_client.get_defs = AsyncMock(return_value=defs)
    mock_client.server_version = AsyncMock(return_value="5.0.0")
    mock_client.host = host
    mock_client.port = int(port)

    with patch("ectop.app.EcflowClient", return_value=mock_client):
        app = Ectop(host=host, port=int(port))
        # Ensure we use the mock
        app.ecflow_client = mock_client
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)

        async with app.run_test() as pilot:
            # Wait for tree to populate
            tree = app.query_one(SuiteTree)
            tree.update_tree(host, int(port), defs)
            await pilot.pause(0.2)

            # Select the node
            await asyncio.to_thread(tree._select_by_path_logic, task_path)
            await pilot.pause(0.2)

            # Manually trigger load node (which uses our parallel loader)
            # We'll call the worker directly with the path to be sure
            await app._load_node_worker(task_path)

            # Wait for UI updates
            await pilot.pause(0.5)

            content_area = app.query_one(MainContent)

            # Verify all types were fetched
            assert mock_client.file.call_count >= 3

            # Verify UI updates
            # We check the content cache in MainContent as a more robust way to verify data reached the UI
            assert "Content for script" in content_area._content_cache.get("script", "")
            assert "Content for job" in content_area._content_cache.get("job", "")
            assert "Content for jobout" in content_area._content_cache.get("output", "")
