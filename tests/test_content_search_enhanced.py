# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for enhanced content search in MainContent.
"""

from __future__ import annotations

import pytest
from textual.widgets import Input

from ectop.app import Ectop
from ectop.widgets.content import MainContent


@pytest.mark.asyncio
async def test_content_search_highlighting_and_navigation():
    """
    Test that searching in MainContent highlights matches and cycles through them.
    """
    app = Ectop()
    async with app.run_test() as pilot:
        # Increase timeout for the pilot
        pilot._timeout = 10

        content_area = app.query_one(MainContent)

        # Manually set some content for testing
        test_content = "line 1: apple\nline 2: banana\nline 3: apple again"
        content_area._content_cache["output"] = test_content
        content_area.update_log(test_content)

        # Open search box directly via action to avoid keybinding issues in test
        content_area.action_search()

        search_input = content_area.query_one("#content_search", Input)

        # Wait for search box to be visible
        await pilot.pause()
        assert "hidden" not in search_input.classes

        # Search for "apple"
        search_input.value = "apple"
        # Manually trigger the submit logic to be sure
        content_area.on_input_submitted(Input.Submitted(search_input, "apple"))

        # Wait for background worker and UI update
        # _run_search_worker is a threaded worker, we might need a bit more time
        import asyncio

        for _ in range(20):
            if content_area.search_query == "apple":
                break
            await asyncio.sleep(0.1)

        # Verify search results
        assert content_area.search_query == "apple"
        assert len(content_area.search_results) == 2
        assert content_area.current_result_index == 0

        # Navigate to next match
        content_area.action_search_next()
        assert content_area.current_result_index == 1

        # Navigate to previous match (cycles back)
        content_area.action_search_prev()
        assert content_area.current_result_index == 0

        # Close search - should clear state
        content_area.action_search()
        await pilot.pause()
        assert content_area.search_query == ""
        assert len(content_area.search_results) == 0
