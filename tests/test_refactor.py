# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for refactored logic and new features.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from ectop.app import Ectop
from ectop.constants import EXPR_AND_LABEL, EXPR_OR_LABEL
from ectop.widgets.modals.why import DepData, WhyInspector
from ectop.widgets.sidebar import SuiteTree


@pytest.fixture
def app() -> Ectop:
    """Create a mock Ectop app."""
    app = Ectop()
    # Mock notify and copy_to_clipboard to avoid AsyncMock issues
    app.notify = MagicMock()
    app.copy_to_clipboard = MagicMock()
    return app


def test_action_requeue(app: Ectop) -> None:
    """Test action_requeue calls the client."""
    with (
        patch.object(app, "_run_client_command") as mock_run,
        patch.object(app, "get_selected_path", return_value="/s1/t1"),
    ):
        app.action_requeue()
        mock_run.assert_called_once_with("requeue", "/s1/t1")


def test_action_copy_path() -> None:
    """Test action_copy_path copies to clipboard and notifies the user."""
    # Test with clipboard support
    app = MagicMock()
    app.get_selected_path.return_value = "/s1/t1"
    Ectop.action_copy_path(app)
    app.copy_to_clipboard.assert_called_once_with("/s1/t1")
    app.notify.assert_called_once_with("Copied to clipboard: /s1/t1")

    # Test without clipboard support
    app_no_clip = MagicMock()
    del app_no_clip.copy_to_clipboard
    app_no_clip.get_selected_path.return_value = "/s1/t1"
    Ectop.action_copy_path(app_no_clip)
    app_no_clip.notify.assert_called_once_with("Node path: /s1/t1")


def test_why_inspector_nested_parsing() -> None:
    """Test WhyInspector handles nested parentheses and operators."""
    mock_client = MagicMock()
    # Explicitly mock any potential async methods as sync mocks to avoid
    # AsyncMock being automatically created for undefined attributes
    mock_client.sync_local = MagicMock()
    inspector = WhyInspector("/path", mock_client)

    parent_data = DepData("Parent")
    defs = MagicMock()

    # Mock nodes
    node_a = MagicMock()
    node_a.get_state.return_value = "complete"
    node_b = MagicMock()
    node_b.get_state.return_value = "aborted"

    defs.find_abs_node.side_effect = lambda p: {"/a": node_a, "/b": node_b}.get(p)

    # Complex expression: (a == complete or b == complete) and (a != aborted)
    expr = "((/a == complete) or (/b == complete)) and (/a != aborted)"

    inspector._parse_expression_data(parent_data, expr, defs)

    # Check that AND was added at top level
    assert any(child.label == EXPR_AND_LABEL for child in parent_data.children)
    and_node = next(child for child in parent_data.children if child.label == EXPR_AND_LABEL)
    # Check that OR was added under AND
    assert any(child.label == EXPR_OR_LABEL for child in and_node.children)


@pytest.mark.asyncio
async def test_suite_tree_select_by_path_worker() -> None:
    """Test SuiteTree.select_by_path uses worker logic."""
    tree = SuiteTree("Test")
    tree.defs = MagicMock()

    # Mock node structure
    suite = MagicMock()
    suite.get_abs_node_path.return_value = "/s1"
    suite.data = "/s1"
    suite.nodes = []
    tree.defs.suites = [suite]
    tree.defs.find_abs_node.return_value = suite

    with (
        patch.object(type(tree.root), "children", new_callable=PropertyMock) as mock_children,
        patch.object(SuiteTree, "app", new=MagicMock()) as mock_app,
        patch.object(tree, "_load_children"),
        patch.object(tree, "_select_and_reveal"),
    ):
        mock_children.return_value = [suite]

        # We call the logic method directly for synchronous testing
        tree._select_by_path_logic("/s1")

        mock_app.call_from_thread.assert_any_call(tree._select_and_reveal, suite)
