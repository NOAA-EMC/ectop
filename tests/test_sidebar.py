# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the SuiteTree widget.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from ectop.widgets.sidebar import SuiteTree


def test_suite_tree_initialization() -> None:
    """
    Test SuiteTree initialization.
    """
    tree = SuiteTree("label")
    assert tree.host == ""
    assert tree.port == 0
    assert tree.defs is None


def test_should_show_node_no_filter() -> None:
    """
    Test _should_show_node with no filter.
    """
    tree = SuiteTree("label")
    mock_node = MagicMock()
    assert tree._should_show_node(mock_node) is True


def test_should_show_node_with_filter() -> None:
    """
    Test _should_show_node with a filter.
    """
    tree = SuiteTree("label")
    tree.current_filter = "aborted"

    mock_node = MagicMock()
    mock_node.get_state.return_value = "aborted"
    assert tree._should_show_node(mock_node) is True

    mock_node.get_state.return_value = "active"
    mock_node.nodes = []
    assert tree._should_show_node(mock_node) is False


def test_search_logic() -> None:
    """
    Test the search logic in SuiteTree.
    """
    with patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop:
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app

        tree = SuiteTree("label")
        tree.defs = MagicMock()
        tree._all_paths_cache = ["/s/task1", "/s/task2"]

        with patch.object(tree, "_select_by_path_logic") as mock_select:
            tree._find_and_select_logic("task2")
            mock_select.assert_called_with("/s/task2")
