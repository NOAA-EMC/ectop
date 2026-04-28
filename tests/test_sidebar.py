# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the Sidebar (SuiteTree) widget.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

import random
import string
from unittest.mock import MagicMock, PropertyMock, patch

import ecflow
import pytest
from rich.text import Text

from ectop.widgets.sidebar import SuiteTree


@pytest.fixture
def unique_suite_names():
    def _generator(n):
        return ["s" + "".join(random.choices(string.ascii_lowercase, k=8)) for _ in range(n)]

    return _generator


@pytest.fixture
def test_setup(ecflow_server, unique_suite_names):
    """
    Setup a unique set of suites for a test.
    Returns (suite_names, defs)
    """
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))
    client.restart_server()

    names = unique_suite_names(2)
    s1_name, s2_name = names[0], names[1]

    defs = ecflow.Defs()
    suite1 = defs.add_suite(s1_name)
    suite1.add_task("t1")

    suite2 = defs.add_suite(s2_name)
    suite2.add_task("t2a")

    client.load(defs, force=True)
    client.begin_all_suites()

    client.force_state(f"/{s1_name}/t1", ecflow.State.complete)
    client.force_state(f"/{s2_name}", ecflow.State.active)
    client.force_state(f"/{s2_name}/t2a", ecflow.State.aborted)

    client.sync_local()
    return names, client.get_defs()


def test_update_tree(test_setup) -> None:
    """
    Test that update_tree clears and repopulates the tree.
    """
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.clear = MagicMock()
    tree.root = MagicMock()

    # Mock _add_node_to_ui and _build_caches_and_populate to avoid Textual internals and threading
    with patch.object(SuiteTree, "_add_node_to_ui"), patch.object(SuiteTree, "_build_caches_and_populate") as mock_worker:
        tree.update_tree("localhost", 3141, real_defs)

        tree.clear.assert_called_once()
        assert tree.defs == real_defs
        mock_worker.assert_called_once()


def test_load_children(test_setup) -> None:
    """
    Test that _load_children calls the worker.
    """
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.defs = real_defs

    # Find a suite path from real_defs
    suite_path = f"/{names[0]}"

    ui_node = MagicMock()
    ui_node.data = suite_path
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
        mock_worker.assert_called_with(ui_node, suite_path)


def test_load_children_worker(test_setup) -> None:
    """
    Test that the worker correctly schedules node additions.
    """
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.defs = real_defs

    suite_path = f"/{names[1]}"
    ui_node = MagicMock()
    ui_node.data = suite_path

    with (
        patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(SuiteTree, "_add_nodes_batch"),
    ):
        mock_app = MagicMock()
        # Mock _thread_id to simulate being on a different thread
        mock_app._thread_id = -1
        mock_app_prop.return_value = mock_app

        tree._load_children_worker(ui_node, suite_path)

        # Should have called call_from_thread with _add_nodes_batch
        mock_app.call_from_thread.assert_called_once()
        args, _ = mock_app.call_from_thread.call_args
        assert args[0] == tree._add_nodes_batch
        assert args[1] == ui_node
        assert len(args[2]) == 1
        assert args[2][0].name() == "t2a"


def test_select_by_path(test_setup) -> None:
    """
    Test that select_by_path expands and selects the correct node.
    """
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.defs = real_defs
    tree.root = MagicMock()
    tree.root.data = "/"

    suite_path = f"/{names[1]}"
    task_path = suite_path + "/t2a"

    # Mock children of root
    child_suite = MagicMock()
    child_suite.data = suite_path
    tree.root.children = [child_suite]

    # Mock children of suite
    child_t2a = MagicMock()
    child_t2a.data = task_path
    child_suite.children = [child_t2a]

    with (
        patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(SuiteTree, "_load_children") as mock_load,
        patch.object(SuiteTree, "_select_and_reveal") as mock_select,
    ):
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        # Use logic method for synchronous test
        tree._select_by_path_logic(task_path)

        # Should have called _load_children for root and suite
        assert mock_load.call_count >= 2
        mock_app.call_from_thread.assert_any_call(child_suite.expand)
        mock_app.call_from_thread.assert_called_with(mock_select, child_t2a)


def test_find_and_select_caching(test_setup) -> None:
    """
    Test that find_and_select uses the path cache.
    """
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.defs = real_defs

    task_path = f"/{names[1]}/t2a"

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
            # Check if ANY path in all_paths_cache matches our expectation
            matching_paths = [p for p in tree._all_paths_cache if p.endswith("/t2a")]
            assert task_path in matching_paths
            # mock_select_logic should be called with some path that matched
            assert mock_select_logic.called
            called_path = mock_select_logic.call_args[0][0]
            assert called_path.endswith("/t2a")

            # Update defs - cache should persist until update_tree is called
            mock_select_logic.reset_mock()
            tree._find_and_select_logic("t2a")
            assert mock_select_logic.called

            # update_tree should clear cache
            tree.update_tree("localhost", 3141, None)
            assert tree._all_paths_cache is None


def test_should_show_node(test_setup) -> None:
    """Test the filtering logic for nodes."""
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.defs = real_defs
    tree.filters = [None, "complete", "active", "aborted"]

    # We must trigger build_caches_and_populate to use the cache
    tree._build_caches_and_populate()

    suite1 = real_defs.find_suite(names[0])  # s1/t1 is complete
    suite2 = real_defs.find_suite(names[1])  # s2 is active, s2/t2a is aborted
    task2a = real_defs.find_abs_node(f"/{names[1]}/t2a")

    # No filter
    tree.current_filter = None
    assert tree._should_show_node(suite1) is True

    # State match
    tree.current_filter = "complete"
    assert tree._should_show_node(suite1) is True
    assert tree._should_show_node(suite2) is False

    # Parent matches because child matches
    tree.current_filter = "aborted"
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


def test_populate_tree_worker(test_setup) -> None:
    """Test the background worker for tree population."""
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.defs = real_defs
    tree.root = MagicMock()

    with patch.object(tree, "_should_show_node", return_value=True), patch.object(tree, "_safe_call") as mock_safe:
        tree._populate_tree_worker()
        # Should be at least 1 call to _add_nodes_batch
        assert mock_safe.call_count >= 1
        args, _ = mock_safe.call_args
        assert args[0] == tree._add_nodes_batch
        assert args[1] == tree.root

        # Verify our suites are in the batch (they might be among others)
        batch_suites = [s.name() for s in args[2]]
        assert names[0] in batch_suites
        assert names[1] in batch_suites
