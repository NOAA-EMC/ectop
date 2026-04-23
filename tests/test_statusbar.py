# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the StatusBar widget.
"""

from __future__ import annotations

from ectop.widgets.statusbar import StatusBar


def test_statusbar_initial_state() -> None:
    """
    Test initial state of StatusBar.
    """
    bar = StatusBar()
    assert bar.server_info == "Disconnected"
    assert bar.status == "Unknown"
    assert bar.server_version == "Unknown"


def test_statusbar_update() -> None:
    """
    Test updating StatusBar values.
    """
    bar = StatusBar()
    bar.update_status("h", 1, "RUNNING", "v1")
    assert bar.server_info == "h:1"
    assert bar.status == "RUNNING"


def test_statusbar_render() -> None:
    """
    Test rendering the status bar.
    """
    bar = StatusBar()
    bar.update_status("localhost", 3141, "RUNNING", "5.16.0")
    rendered = bar.render()
    assert "RUNNING" in rendered.plain
