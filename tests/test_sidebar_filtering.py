# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for SuiteTree filtering logic and cycle action.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from ectop.widgets.sidebar import SuiteTree


@pytest.fixture
def mock_node() -> MagicMock:
    """
    Create a mock ecFlow node.

    Returns
    -------
    MagicMock
        A mock ecFlow node object.
    """
    node = MagicMock()
    node.get_state.return_value = "active"
    node.nodes = []
    return node


def test_should_show_node_no_filter(mock_node: MagicMock) -> None:
    """
    Test _should_show_node when no filter is active.

    Parameters
    ----------
    mock_node : MagicMock
        The mock ecFlow node.
    """
    tree = SuiteTree("label")
    tree.current_filter = None
    assert tree._should_show_node(mock_node) is True


def test_should_show_node_match(mock_node: MagicMock) -> None:
    """
    Test _should_show_node when the node state matches the filter.

    Parameters
    ----------
    mock_node : MagicMock
        The mock ecFlow node.
    """
    tree = SuiteTree("label")
    tree.current_filter = "active"
    assert tree._should_show_node(mock_node) is True


def test_should_show_node_mismatch(mock_node: MagicMock) -> None:
    """
    Test _should_show_node when the node state doesn't match the filter.

    Parameters
    ----------
    mock_node : MagicMock
        The mock ecFlow node.
    """
    tree = SuiteTree("label")
    tree.current_filter = "aborted"
    assert tree._should_show_node(mock_node) is False


def test_should_show_node_recursive_match(mock_node: MagicMock) -> None:
    """
    Test _should_show_node when a child node matches the filter.

    Parameters
    ----------
    mock_node : MagicMock
        The mock ecFlow node.
    """
    tree = SuiteTree("label")
    tree.current_filter = "aborted"

    # Parent is active, child is aborted
    mock_node.get_state.return_value = "active"
    child = MagicMock()
    child.get_state.return_value = "aborted"
    child.nodes = []
    mock_node.nodes = [child]

    assert tree._should_show_node(mock_node) is True


@pytest.mark.asyncio
async def test_action_cycle_filter() -> None:
    """Test action_cycle_filter cycles through filters and calls update_tree."""
    tree = SuiteTree("label")
    with patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app:
        mock_app.return_value = MagicMock()
        tree.defs = MagicMock()
        tree.host = "localhost"
        tree.port = 3141

        # Mock update_tree to avoid background workers starting
        with patch.object(SuiteTree, "update_tree") as mock_update:
            # Initial filter is None
            assert tree.current_filter is None

            tree.action_cycle_filter()
            # Next filter in TREE_FILTERS should be 'aborted'
            assert tree.current_filter == "aborted"
            mock_update.assert_called_with("localhost", 3141, tree.defs)
