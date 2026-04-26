# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations
import unittest.mock as mock
import ecflow
import pytest
from textual.app import App
from ectop.widgets.sidebar import SuiteTree

@pytest.mark.asyncio
async def test_search_cache_background_building():
    class TestApp(App):
        def compose(self): yield SuiteTree("Test")
    app = TestApp()
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        defs = ecflow.Defs()
        defs.add_suite("suite")
        tree.update_tree("localhost", 3141, defs)
        await pilot.pause()
        assert "/suite" in tree._all_paths_cache

@pytest.mark.asyncio
async def test_find_and_select_fallback():
    class TestApp(App):
        def compose(self): yield SuiteTree("Test")
    app = TestApp()
    async with app.run_test():
        tree = app.query_one(SuiteTree)
        defs = ecflow.Defs()
        defs.add_suite("suite")
        tree.defs = defs
        tree._all_paths_cache = None
        with mock.patch.object(tree, "_select_by_path_logic") as mock_select:
            tree.find_and_select("suite")
            import asyncio
            for _ in range(10):
                if mock_select.called: break
                await asyncio.sleep(0.1)
            assert mock_select.called
        assert "/suite" in tree._all_paths_cache
