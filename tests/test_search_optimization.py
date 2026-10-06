# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""
Tests for SuiteTree search optimization.
"""

from __future__ import annotations

import ecflow
import pytest
from textual.app import App

from ectop.widgets.sidebar import SuiteTree


@pytest.mark.asyncio
async def test_search_cache_background_building() -> None:
    """
    Test that the search cache is built in the background after update_tree.
    """

    class TestApp(App):
        def compose(self):
            yield SuiteTree("Test")

    app = TestApp()
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)

        # Real ecFlow Defs and Suites
        real_defs = ecflow.Defs()
        real_defs.add_suite("suite")

        # Update tree
        tree.update_tree("localhost", 3141, real_defs)

        # Wait for worker to complete
        await pilot.pause()

        assert hasattr(tree, "_all_paths_cache")
        assert tree._all_paths_cache == ["/suite"]


@pytest.mark.asyncio
async def test_find_and_select_after_snapshot_build():
    """
    Test that find_and_select builds the cache if it's missing (fallback).
    """

    class TestApp(App):
        def compose(self):
            yield SuiteTree("Test")

    app = TestApp()
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)

        real_defs = ecflow.Defs()
        real_defs.add_suite("suite")

        tree.defs = real_defs
        tree._all_paths_cache = None
        tree.find_and_select("suite")
        for _ in range(40):
            if tree.cursor_node and tree.cursor_node.data == "/suite":
                break
            await pilot.pause(0.05)

        assert tree.cursor_node is not None
        assert tree.cursor_node.data == "/suite"
        assert "/suite" in tree._all_paths_cache
