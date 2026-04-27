"""
Performance tests for SuiteTree to verify node addition batching.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from ectop.widgets.sidebar import SuiteTree


def test_load_children_worker_batching() -> None:
    """Test that _load_children_worker batches many children into multiple calls."""
    tree = SuiteTree("Test")
    mock_defs = MagicMock()
    tree.defs = mock_defs

    parent_node = MagicMock()
    children = []
    for i in range(125):
        child = MagicMock()
        child.name.return_value = f"t{i}"
        child.get_state.return_value = "queued"
        children.append(child)

    parent_node.nodes = children
    mock_defs.find_abs_node.return_value = parent_node

    ui_node = MagicMock()
    ui_node.data = "/parent"

    with patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop, patch.object(SuiteTree, "_add_nodes_batch"):
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app

        tree._load_children_worker(ui_node, "/parent")

        # Total 125 children. Batch size is 50.
        # Calls should be: 50, 50, 25. Total 3 calls.
        assert mock_app.call_from_thread.call_count == 3

        calls = mock_app.call_from_thread.call_args_list
        assert len(calls[0][0][2]) == 50
        assert len(calls[1][0][2]) == 50
        assert len(calls[2][0][2]) == 25

        for call in calls:
            assert call[0][0] == tree._add_nodes_batch
