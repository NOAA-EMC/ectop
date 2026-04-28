# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for newly added features in ectop.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from unittest.mock import MagicMock

import ecflow
import pytest

from ectop.app import Ectop, EctopCommands
from ectop.widgets.content import MainContent
from ectop.widgets.sidebar import SuiteTree
from ectop.widgets.statusbar import StatusBar


def test_status_bar_update() -> None:
    """Test that the status bar updates its internal state correctly."""
    sb = StatusBar()
    sb.update_status("myhost", 1234, "Connected")
    assert sb.server_info == "myhost:1234"
    assert sb.status == "Connected"
    assert sb.last_sync != "Never"


def test_status_bar_render() -> None:
    """Test that the status bar renders correctly."""
    sb = StatusBar()
    sb.update_status("myhost", 1234, "Connected")
    rendered = sb.render()
    assert "myhost:1234" in str(rendered)
    assert "Connected" in str(rendered)


@pytest.mark.asyncio
async def test_ectop_commands_provider() -> None:
    """Test the EctopCommands provider yields hits."""
    app = Ectop()
    # Mock some basic app properties/methods needed by the provider
    app.action_refresh = MagicMock()

    provider = EctopCommands(app)

    # We need to mock the matcher
    matcher = MagicMock()
    matcher.match.return_value = 1.0
    matcher.highlight.return_value = "Refresh Tree"
    provider.matcher = MagicMock(return_value=matcher)

    hits = []
    async for hit in provider.search("refresh"):
        hits.append(hit)

    assert len(hits) > 0
    assert any(h.match_display == "Refresh Tree" for h in hits)


def test_suite_tree_filtering(ecflow_server) -> None:
    """Test SuiteTree filtering logic using real ecFlow objects."""
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))
    client.restart_server()

    defs = ecflow.Defs()
    suite = defs.add_suite("suite")
    suite.add_task("task1")

    client.load(defs, force=True)
    client.begin_all_suites()
    client.force_state("/suite/task1", ecflow.State.aborted)
    client.sync_local()

    real_defs = client.get_defs()

    tree = SuiteTree("Test")
    tree.defs = real_defs
    tree.filters = [None, "aborted", "active"]
    tree._build_caches_and_populate()

    # Test _should_show_node
    tree.current_filter = "aborted"
    real_task1 = real_defs.find_abs_node("/suite/task1")
    real_suite = real_defs.find_suite("suite")

    assert tree._should_show_node(real_task1) is True
    assert tree._should_show_node(real_suite) is True  # Should show because child matches

    tree.current_filter = "active"
    assert tree._should_show_node(real_task1) is False
    assert tree._should_show_node(real_suite) is False


def test_main_content_search_toggle() -> None:
    """Test MainContent search toggle."""
    mc = MainContent()
    # We need to compose to have access to widgets
    from textual.app import App

    class DummyApp(App):
        def compose(self):
            yield mc

    # Manual trigger of action_search (it usually works through binding)
    # But mc is not fully mounted yet in a unit test without async app.run_test()
    # Let's mock query_one
    mc.query_one = MagicMock()
    search_input = MagicMock()
    search_input.classes = ["hidden"]
    mc.query_one.return_value = search_input

    mc.action_search()
    search_input.remove_class.assert_called_with("hidden")
    search_input.focus.assert_called()
