# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for SuiteTree search optimization.
"""

from __future__ import annotations

import unittest.mock as mock

import ecflow
import pytest
from textual.app import App

from ectop.widgets.sidebar import SuiteTree


@pytest.mark.asyncio
async def test_search_cache_background_building():
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
async def test_find_and_select_fallback():
    """
    Test that find_and_select builds the cache if it's missing (fallback).
    """

    class TestApp(App):
        def compose(self):
            yield SuiteTree("Test")

    app = TestApp()
    async with app.run_test():
        tree = app.query_one(SuiteTree)

        real_defs = ecflow.Defs()
        real_defs.add_suite("suite")

        tree.defs = real_defs
        tree._all_paths_cache = None

        # This should trigger the fallback logic.
        # We mock _select_by_path_logic because it's now called by find_and_select.
        with mock.patch.object(tree, "_select_by_path_logic") as mock_select:
            tree.find_and_select("suite")
            # find_and_select is now a worker
            import asyncio

            for _ in range(10):
                if mock_select.called:
                    break
                await asyncio.sleep(0.1)

            assert mock_select.called
        # all_paths_cache might contain duplicates if the traversal is not careful or
        # depending on ecFlow version behavior of get_all_nodes() on Defs vs Suites.
        # We check for existence of the path.
        assert "/suite" in tree._all_paths_cache
