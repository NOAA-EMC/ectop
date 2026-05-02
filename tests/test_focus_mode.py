# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for Focus Mode in SuiteTree.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import ecflow

from ectop.widgets.sidebar import SuiteTree


def test_focus_mode_filtering():
    """
    Test that _should_show_node correctly filters complete nodes in Focus Mode.
    """
    tree = SuiteTree("Test")

    # Mock ecflow nodes
    complete_node = MagicMock(spec=ecflow.Node)
    complete_node.get_state.return_value = ecflow.State.complete

    active_node = MagicMock(spec=ecflow.Node)
    active_node.get_state.return_value = ecflow.State.active

    # Default (Focus Mode OFF)
    tree.focus_mode = False
    assert tree._should_show_node(complete_node) is True
    assert tree._should_show_node(active_node) is True

    # Focus Mode ON
    tree.focus_mode = True
    assert tree._should_show_node(complete_node) is False
    assert tree._should_show_node(active_node) is True


def test_action_toggle_focus():
    """
    Test the action_toggle_focus method.
    """
    tree = SuiteTree("Test")
    mock_app = MagicMock()
    with patch.object(SuiteTree, "app", return_value=mock_app, new_callable=PropertyMock):
        assert tree.focus_mode is False

        tree.action_toggle_focus()
        assert tree.focus_mode is True
        mock_app.notify.assert_called_with("Focus Mode: ON")

        tree.action_toggle_focus()
        assert tree.focus_mode is False
        mock_app.notify.assert_called_with("Focus Mode: OFF")
