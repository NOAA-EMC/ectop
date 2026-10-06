# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""
Performance tests for SuiteTree to verify node addition batching.
"""

from __future__ import annotations

import math
import time
from unittest.mock import patch

import ecflow
import pytest
from textual.app import App, ComposeResult

from ectop.widgets.sidebar import SuiteTree


class PerformanceTreeApp(App[None]):
    """Host a suite tree for large in-memory ecFlow definitions."""

    def compose(self) -> ComposeResult:
        """Compose the tree used for performance measurements.

        Returns
        -------
        ComposeResult
            The suite tree widget.
        """
        yield SuiteTree("ecFlow", id="suite_tree")


def build_large_definitions() -> ecflow.Defs:
    """Build real definitions containing ten thousand tasks.

    Returns
    -------
    ecflow.Defs
        Definitions with one suite, one hundred families, and ten thousand tasks.
    """
    defs = ecflow.Defs()
    suite = defs.add_suite("performance_suite")
    for family_index in range(100):
        family = suite.add_family(f"family_{family_index:03}")
        for task_index in range(100):
            family.add_task(f"task_{task_index:03}")
    return defs


@pytest.mark.asyncio
async def test_ten_thousand_node_filters_reuse_snapshot_indexes() -> None:
    """Keep every filter/focus rebuild correct and below the one-second p95.

    Returns
    -------
    None
        The test asserts indexed membership, selection retention, and latency.
    """
    defs = build_large_definitions()
    app = PerformanceTreeApp()
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        tree.update_tree("localhost", 3141, defs)
        for _ in range(80):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.025)

        snapshot = tree.snapshot
        assert snapshot is not None
        assert len(snapshot.nodes) == 10_101
        assert snapshot.by_path["/performance_suite/family_000/task_000"].parent_path == "/performance_suite/family_000"
        assert "/performance_suite" in snapshot.visible_by_state["unknown"]

        latencies: list[float] = []
        filters = [None, "aborted", "active", "queued", "submitted", "suspended"] * 4
        for index, filter_state in enumerate(filters):
            started = time.perf_counter()
            tree.current_filter = filter_state
            tree.focus_mode = index % 2 == 0
            await pilot.pause(0.01)
            latencies.append(time.perf_counter() - started)

            visible = tree._visible_paths(snapshot)
            if filter_state is None:
                expected = set(snapshot.paths)
            else:
                expected = set(snapshot.visible_by_state.get(filter_state, frozenset()))
            if tree.focus_mode:
                expected.intersection_update(snapshot.focus_visible_paths)
            assert visible == expected

        p95 = sorted(latencies)[math.ceil(len(latencies) * 0.95) - 1]
        assert p95 < 1.0

        tree.current_filter = "unknown"
        tree.focus_mode = False
        tree.select_by_path("/performance_suite/family_000/task_000")
        await pilot.pause(0.05)
        selected_path = "/performance_suite/family_000/task_000"
        assert tree.cursor_node is not None and tree.cursor_node.data == selected_path

        tree.current_filter = "unknown"
        await pilot.pause(0.05)
        assert tree.cursor_node is not None and tree.cursor_node.data == selected_path


@pytest.mark.asyncio
async def test_stale_definition_snapshot_cannot_replace_new_tree() -> None:
    """Reject a completed snapshot whose generation has been superseded.

    Returns
    -------
    None
        The test asserts that a newer snapshot remains installed.
    """
    old_defs = ecflow.Defs()
    old_defs.add_suite("old_suite")
    new_defs = ecflow.Defs()
    new_defs.add_suite("new_suite")

    app = PerformanceTreeApp()
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        tree.update_tree("localhost", 3141, old_defs)
        for _ in range(40):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.025)
        old_snapshot = tree.snapshot
        assert old_snapshot is not None

        tree.update_tree("localhost", 3141, new_defs)
        for _ in range(40):
            if tree.snapshot is not None and tree.snapshot.generation > old_snapshot.generation:
                break
            await pilot.pause(0.025)
        current_snapshot = tree.snapshot
        assert current_snapshot is not None
        assert "/new_suite" in current_snapshot.by_path

        tree._install_snapshot(old_snapshot)
        assert tree.snapshot is current_snapshot
        assert [node.data for node in tree.root.children] == ["/new_suite"]


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
