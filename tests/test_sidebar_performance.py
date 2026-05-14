# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Performance tests for SuiteTree to verify node addition batching.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ectop.widgets.sidebar import SuiteTree


@pytest.mark.asyncio
async def test_load_children_worker_batching_integrated(ecflow_server: str) -> None:
    """Test that _load_children_worker batches many children into multiple calls using a real server."""
    import ecflow

    from ectop.app import Ectop

    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))

    suite_name = "large_suite"
    defs = ecflow.Defs()
    suite = defs.add_suite(suite_name)
    # Add 125 tasks to test batching (batch size is 50)
    for i in range(125):
        suite.add_task(f"t{i}")
    client.load(defs, force=True)

    app = Ectop(host=host, port=int(port))
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)

        # Wait for suite to appear
        suite_ui_node = None
        for _ in range(50):
            for child in tree.root.children:
                if child.data == f"/{suite_name}":
                    suite_ui_node = child
                    break
            if suite_ui_node:
                break
            await pilot.pause(0.1)

        assert suite_ui_node is not None

        # We want to verify that _add_nodes_batch is called 3 times.
        # We can patch it on the tree instance.
        with patch.object(tree, "_add_nodes_batch", wraps=tree._add_nodes_batch) as mock_batch:
            # Expand node to trigger lazy loading
            suite_ui_node.expand()

            # Wait for children to load
            for _ in range(50):
                if len(suite_ui_node.children) >= 125:
                    break
                await pilot.pause(0.1)

            # Total 125 children. Batch size is 50.
            # Calls should be: 50, 50, 25. Total 3 calls.
            assert mock_batch.call_count == 3
            assert len(suite_ui_node.children) == 125
