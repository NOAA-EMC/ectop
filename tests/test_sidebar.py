# .. note:: warning: "If you modify features, API, or usage, you MUST update the documentation immediately."
"""
Tests for the Sidebar (SuiteTree) widget.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from rich.text import Text

from ectop.widgets.sidebar import SuiteTree


@pytest.fixture
def mock_defs() -> MagicMock:
    """
    Create a mock ecFlow definition with some suites.

    Returns
    -------
    MagicMock
        A mock Defs object.
    """
    defs = MagicMock()
    suite1 = MagicMock()
    suite1.name.return_value = "s1"
    suite1.get_abs_node_path.return_value = "/s1"
    suite1.get_state.return_value = "complete"
    suite1.nodes = []

    suite2 = MagicMock()
    suite2.name.return_value = "s2"
    suite2.get_abs_node_path.return_value = "/s2"
    suite2.get_state.return_value = "active"

    task2a = MagicMock()
    task2a.name.return_value = "t2a"
    task2a.get_abs_node_path.return_value = "/s2/t2a"
    task2a.get_state.return_value = "queued"
    task2a.nodes = []

    suite2.nodes = [task2a]
    suite2.get_all_nodes.return_value = [task2a]

    suite1.get_parent.return_value = None
    suite2.get_parent.return_value = None
    task2a.get_parent.return_value = suite2

    defs.suites = [suite1, suite2]
    defs.find_abs_node.side_effect = lambda p: {"/s1": suite1, "/s2": suite2, "/s2/t2a": task2a}.get(p)

    return defs


def test_update_tree(mock_defs: MagicMock) -> None:
    """
    Test that update_tree clears and repopulates the tree.

    Parameters
    ----------
    mock_defs : MagicMock
        The mock ecFlow definitions.
    """
    tree = SuiteTree("Test")
    tree.clear = MagicMock()
    tree.root = MagicMock()

    # Mock _add_node_to_ui and _build_caches_and_populate to avoid Textual internals and threading
    with patch.object(SuiteTree, "_add_node_to_ui"), patch.object(SuiteTree, "_build_caches_and_populate") as mock_worker:
        tree.update_tree("localhost", 3141, mock_defs)

        tree.clear.assert_called_once()
        assert tree.defs == mock_defs
        mock_worker.assert_called_once()


def test_load_children(mock_defs: MagicMock) -> None:
    """
    Test that _load_children calls the worker.

    Parameters
    ----------
    mock_defs : MagicMock
        The mock ecFlow definitions.
    """
    tree = SuiteTree("Test")
    tree.defs = mock_defs

    ui_node = MagicMock()
    ui_node.data = "/s2"
    placeholder = MagicMock()
    placeholder.label = Text("loading...")
    ui_node.children = [placeholder]

    with (
        patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(SuiteTree, "_load_children_worker") as mock_worker,
    ):
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        tree._load_children(ui_node)

        # placeholder.remove is now called via call_from_thread
        mock_app.call_from_thread.assert_any_call(placeholder.remove)
        mock_worker.assert_called_with(ui_node, "/s2")


def test_load_children_worker(mock_defs: MagicMock) -> None:
    """
    Test that the worker correctly schedules node additions.

    Parameters
    ----------
    mock_defs : MagicMock
        The mock ecFlow definitions.
    """
    tree = SuiteTree("Test")
    tree.defs = mock_defs

    ui_node = MagicMock()
    ui_node.data = "/s2"

    with (
        patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(SuiteTree, "_add_nodes_batch"),
    ):
        mock_app = MagicMock()
        # Mock _thread_id to simulate being on a different thread
        mock_app._thread_id = -1
        mock_app_prop.return_value = mock_app

        tree._load_children_worker(ui_node, "/s2")

        # Should have called call_from_thread with _add_nodes_batch
        mock_app.call_from_thread.assert_called_once()
        args, _ = mock_app.call_from_thread.call_args
        assert args[0] == tree._add_nodes_batch
        assert args[1] == ui_node
        assert len(args[2]) == 1
        assert args[2][0].name() == "t2a"


def test_select_by_path(mock_defs: MagicMock) -> None:
    """
    Test that select_by_path expands and selects the correct node.

    Parameters
    ----------
    mock_defs : MagicMock
        The mock ecFlow definitions.
    """
    tree = SuiteTree("Test")
    tree.defs = mock_defs
    tree.root = MagicMock()
    tree.root.data = "/"

    # Mock children of root
    child_s2 = MagicMock()
    child_s2.data = "/s2"
    tree.root.children = [child_s2]

    # Mock children of s2
    child_t2a = MagicMock()
    child_t2a.data = "/s2/t2a"
    child_s2.children = [child_t2a]

    with (
        patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(SuiteTree, "_load_children") as mock_load,
        patch.object(SuiteTree, "_select_and_reveal") as mock_select,
    ):
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        # Use logic method for synchronous test
        tree._select_by_path_logic("/s2/t2a")

        # Should have called _load_children for root and s2
        assert mock_load.call_count >= 2
        mock_app.call_from_thread.assert_any_call(child_s2.expand)
        mock_app.call_from_thread.assert_called_with(mock_select, child_t2a)


def test_find_and_select_caching(mock_defs: MagicMock) -> None:
    """
    Test that find_and_select uses the path cache.

    Parameters
    ----------
    mock_defs : MagicMock
        The mock ecFlow definitions.
    """
    tree = SuiteTree("Test")
    tree.defs = mock_defs
    with patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop:
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        tree.root = MagicMock()

        with (
            patch.object(SuiteTree, "cursor_node", new=None),
            patch.object(SuiteTree, "_select_by_path_logic") as mock_select_logic,
            patch.object(SuiteTree, "_add_node_to_ui"),
        ):
            # Manually trigger cache build for logic test
            tree._build_caches_and_populate()

            tree._find_and_select_logic("t2a")
            assert tree._all_paths_cache is not None
            assert "/s2/t2a" in tree._all_paths_cache
            # mock_select_logic should be called
            mock_select_logic.assert_called_with("/s2/t2a")

            # Modify defs - but cache should persist until update_tree is called
            tree.defs.suites = []
            mock_select_logic.reset_mock()
            tree._find_and_select_logic("t2a")
            mock_select_logic.assert_called_with("/s2/t2a")  # Still works from cache

            # update_tree should clear cache
            tree.update_tree("localhost", 3141, None)
            assert tree._all_paths_cache is None


def test_should_show_node(mock_defs: MagicMock) -> None:
    """Test the filtering logic for nodes."""
    tree = SuiteTree("Test")
    tree.defs = mock_defs
    tree.filters = [None, "complete", "active", "queued"]
    suite1 = mock_defs.suites[0]  # complete
    suite2 = mock_defs.suites[1]  # active
    task2a = suite2.nodes[0]  # queued

    # Pre-build cache
    tree._build_caches_and_populate()

    # No filter
    tree.current_filter = None
    assert tree._should_show_node(suite1) is True

    # State match
    tree.current_filter = "complete"
    assert tree._should_show_node(suite1) is True
    assert tree._should_show_node(suite2) is False

    # Parent matches because child matches
    tree.current_filter = "queued"
    assert tree._should_show_node(suite2) is True
    assert tree._should_show_node(task2a) is True


def test_action_cycle_filter() -> None:
    """Test cycling through status filters."""
    tree = SuiteTree("Test")
    with patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop:
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        tree.filters = [None, "aborted", "active"]
        tree.current_filter = None

        tree.action_cycle_filter()
        assert tree.current_filter == "aborted"
        mock_app.notify.assert_called_with("Filter: aborted")

        tree.action_cycle_filter()
        assert tree.current_filter == "active"

        tree.action_cycle_filter()
        assert tree.current_filter is None
        mock_app.notify.assert_called_with("Filter: All")


def test_populate_tree_worker(mock_defs: MagicMock) -> None:
    """Test the background worker for tree population."""
    tree = SuiteTree("Test")
    tree.defs = mock_defs
    tree.root = MagicMock()

    with patch.object(tree, "_should_show_node", return_value=True), patch.object(tree, "_safe_call") as mock_safe:
        tree._populate_tree_worker()
        # Should be 1 call to _add_nodes_batch for 2 suites (batch size 50)
        assert mock_safe.call_count == 1
        args, _ = mock_safe.call_args
        assert args[0] == tree._add_nodes_batch
        assert args[1] == tree.root
        assert len(args[2]) == 2
