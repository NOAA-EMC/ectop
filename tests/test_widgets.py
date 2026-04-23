# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for UI widgets in ectop.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from ectop.widgets.search import SearchBox


def test_searchbox_cancel() -> None:
    """
    Test that SearchBox cancel clears and hides the box.
    """
    with patch.object(SearchBox, "app", new_callable=PropertyMock) as mock_app_prop:
        mock_app = MagicMock()
        mock_tree = MagicMock()
        mock_app.query_one.return_value = mock_tree
        mock_app_prop.return_value = mock_app

        sb = SearchBox()
        sb.value = "some search"
        sb.add_class("visible")

        sb.action_cancel()

        assert sb.value == ""
        assert "visible" not in sb.classes


def test_statusbar_initial_state() -> None:
    """
    Check StatusBar initial state.
    """
    from ectop.widgets.statusbar import StatusBar

    sb = StatusBar()
    assert sb.server_info == "Disconnected"
