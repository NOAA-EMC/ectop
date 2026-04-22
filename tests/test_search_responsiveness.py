from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult

from ectop.widgets.content import MainContent


class MockApp(App):
    def compose(self) -> ComposeResult:
        yield MainContent(id="main_content")


@pytest.mark.asyncio
async def test_reactive_content_updates():
    """Test that reactive content updates in MainContent trigger watchers."""
    app = MockApp()
    async with app.run_test() as pilot:
        mc = app.query_one(MainContent)

        # Update script content reactively
        mc.script_content = "echo 'hello world'"
        await pilot.pause()

        # Verify it was rendered in the static widget
        # The watcher updates the static widget #view_script
        # Check if the content is in the cache which the watcher updates
        assert mc._content_cache["script"] == "echo 'hello world'"


@pytest.mark.asyncio
async def test_non_blocking_search():
    """Test that search runs in a worker and eventually notifies."""
    app = MockApp()
    async with app.run_test() as pilot:
        mc = app.query_one(MainContent)

        # Set some content to search
        mc.log_content = "line 1\nline 2\nneedle\nline 4"
        await pilot.pause()

        # Trigger search
        search_input = mc.query_one("#content_search")
        search_input.value = "needle"

        # We need to mock notify to see if it's called from the worker
        app.notify = MagicMock()

        await search_input.action_submit()

        # Wait a bit for the worker to complete
        # Since it's a thread worker, we might need a small sleep or multiple pauses
        await pilot.pause(0.2)

        # Check if notify was called
        app.notify.assert_called_once()
        args, kwargs = app.notify.call_args
        assert "Found 1 matches" in args[0]
        assert "Output" in args[0]
