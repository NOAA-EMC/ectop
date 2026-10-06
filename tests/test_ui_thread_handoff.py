# If you modify features, API, or usage, you MUST update the documentation immediately.
"""Verify that Textual worker results are delivered only on the UI thread."""

from __future__ import annotations

import threading

import pytest
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Static

from ectop.utils import safe_call_app


class HandoffApp(App[None]):
    """Small real Textual app used to exercise worker-to-UI dispatch."""

    def __init__(self) -> None:
        """Initialize the callback thread identifiers.

        Returns
        -------
        None
            The app is initialized with no delivered callback.
        """
        super().__init__()
        self.source_thread_id: int | None = None
        self.callback_thread_id: int | None = None

    def compose(self) -> ComposeResult:
        """Compose the app's test widget.

        Returns
        -------
        ComposeResult
            The static widget used by the pilot app.
        """
        yield Static("ready")

    @work(thread=True, group="handoff")
    def deliver_from_worker(self) -> None:
        """Ask Textual to deliver the callback from a worker thread.

        Returns
        -------
        None
            The callback result is stored on the app instance.
        """
        self.source_thread_id = threading.get_ident()
        safe_call_app(self, self.record_callback_thread)

    def record_callback_thread(self) -> None:
        """Record the thread on which Textual runs the callback.

        Returns
        -------
        None
            The current thread identifier is stored on the app instance.
        """
        self.callback_thread_id = threading.get_ident()


@pytest.mark.asyncio
async def test_worker_callback_runs_on_textual_ui_thread() -> None:
    """Deliver a worker callback through the running app's event loop.

    Returns
    -------
    None
        The test asserts worker and callback thread identifiers.
    """
    app = HandoffApp()
    async with app.run_test() as pilot:
        app.deliver_from_worker()
        for _ in range(20):
            if app.callback_thread_id is not None:
                break
            await pilot.pause(0.05)

        assert app.source_thread_id is not None
        assert app.callback_thread_id == app._thread_id
        assert app.source_thread_id != app.callback_thread_id


@pytest.mark.asyncio
async def test_stopped_app_discards_callback() -> None:
    """Do not invoke UI callbacks after the Textual app has shut down.

    Returns
    -------
    None
        The test asserts that the callback is discarded after shutdown.
    """
    app = HandoffApp()
    async with app.run_test() as pilot:
        await pilot.pause()

    called = False

    def callback() -> None:
        nonlocal called
        called = True

    assert safe_call_app(app, callback) is None
    assert called is False
