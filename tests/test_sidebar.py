# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
# .. note:: warning: "If you modify features, API, or usage, you MUST update the documentation immediately."
"""
Tests for the Sidebar (SuiteTree) widget using live ecFlow server.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import random
from unittest.mock import MagicMock, PropertyMock, patch

import ecflow
import pytest
from rich.text import Text

from ectop.widgets.sidebar import SuiteTree


@pytest.fixture
def live_defs(ecflow_server: str) -> ecflow.Defs:
    """
    Load a test definition to the live server and return it.

    Args:
        ecflow_server: The host:port of the live ecFlow server.

    Returns:
        ecflow.Defs: The definitions fetched from the server.

    Raises:
        RuntimeError: If server communication fails.
    """
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))

    # Create a unique suite name to avoid cross-test interference
    suffix = random.randint(0, 1000000)
    s1_name = f"s1_{suffix}"
    s2_name = f"s2_{suffix}"

    defs = ecflow.Defs()
    s1 = defs.add_suite(s1_name)
    s1.add_task("t1")
    s2 = defs.add_suite(s2_name)
    s2.add_task("t2a")

    # Load and begin
    client.load(defs)
    client.begin_all_suites()

    # Force states
    client.force_state(f"/{s1_name}", ecflow.State.complete)
    client.force_state(f"/{s2_name}", ecflow.State.active)
    client.force_state(f"/{s2_name}/t2a", ecflow.State.queued)

    # Sync and return
    client.sync_local()
    return client.get_defs()


def test_update_tree(live_defs: ecflow.Defs) -> None:
    """
    Test that update_tree clears and repopulates the tree.

    Args:
        live_defs: The ecFlow definitions from the live server.

    Returns:
        None
    """
    tree = SuiteTree("Test")
    tree.clear = MagicMock()
    tree.root = MagicMock()

    with patch.object(SuiteTree, "_add_node_to_ui"), patch.object(SuiteTree, "_build_caches_and_populate") as mock_worker:
        tree.update_tree("localhost", 3141, live_defs)

        tree.clear.assert_called_once()
        assert tree.defs == live_defs
        mock_worker.assert_called_once()


def test_load_children(live_defs: ecflow.Defs) -> None:
    """
    Test that _load_children calls the worker.

    Args:
        live_defs: The ecFlow definitions from the live server.

    Returns:
        None
    """
    tree = SuiteTree("Test")
    tree.defs = live_defs
    suite = list(live_defs.suites)[0]
    path = suite.get_abs_node_path()

    ui_node = MagicMock()
    ui_node.data = path
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

        mock_app.call_from_thread.assert_any_call(placeholder.remove)
        mock_worker.assert_called_with(ui_node, path)


def test_load_children_worker(live_defs: ecflow.Defs) -> None:
    """
    Test that the worker correctly schedules node additions.

    Args:
        live_defs: The ecFlow definitions from the live server.

    Returns:
        None
    """
    tree = SuiteTree("Test")
    tree.defs = live_defs
    # Find s2 which has t2a
    s2 = None
    for s in live_defs.suites:
        if "s2_" in s.name():
            s2 = s
            break
    assert s2 is not None
    path = s2.get_abs_node_path()

    ui_node = MagicMock()
    ui_node.data = path

    with (
        patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(SuiteTree, "_add_nodes_batch"),
    ):
        mock_app = MagicMock()
        mock_app._thread_id = -1
        mock_app_prop.return_value = mock_app

        tree._load_children_worker(ui_node, path)

        mock_app.call_from_thread.assert_called_once()
        args, _ = mock_app.call_from_thread.call_args
        assert args[0] == tree._add_nodes_batch
        assert args[1] == ui_node
        assert len(args[2]) == 1
        assert args[2][0].name() == "t2a"


def test_select_by_path(live_defs: ecflow.Defs) -> None:
    """
    Test that select_by_path expands and selects the correct node.

    Args:
        live_defs: The ecFlow definitions from the live server.

    Returns:
        None
    """
    tree = SuiteTree("Test")
    tree.defs = live_defs
    tree.root = MagicMock()
    tree.root.data = "/"

    s2 = None
    for s in live_defs.suites:
        if "s2_" in s.name():
            s2 = s
            break
    assert s2 is not None
    s2_path = s2.get_abs_node_path()
    t2a_path = f"{s2_path}/t2a"

    # Mock children of root
    child_s2 = MagicMock()
    child_s2.data = s2_path
    tree.root.children = [child_s2]

    # Mock children of s2
    child_t2a = MagicMock()
    child_t2a.data = t2a_path
    child_s2.children = [child_t2a]

    with (
        patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(SuiteTree, "_load_children") as mock_load,
        patch.object(SuiteTree, "_select_and_reveal") as mock_select,
    ):
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        tree._select_by_path_logic(t2a_path)

        assert mock_load.call_count >= 2
        mock_app.call_from_thread.assert_any_call(child_s2.expand)
        mock_app.call_from_thread.assert_called_with(mock_select, child_t2a)


def test_find_and_select_caching(live_defs: ecflow.Defs) -> None:
    """
    Test that find_and_select uses the path cache.

    Args:
        live_defs: The ecFlow definitions from the live server.

    Returns:
        None
    """
    tree = SuiteTree("Test")
    tree.defs = live_defs
    with patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop:
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        tree.root = MagicMock()

        with (
            patch.object(SuiteTree, "cursor_node", new=None),
            patch.object(SuiteTree, "_select_by_path_logic") as mock_select_logic,
            patch.object(SuiteTree, "_add_node_to_ui"),
        ):
            tree._build_caches_and_populate()

            # Search for t2a
            tree._find_and_select_logic("t2a")
            assert tree._all_paths_cache is not None

            # Find the actual path of t2a in cache
            t2a_path = None
            for p in tree._all_paths_cache:
                if p.endswith("/t2a"):
                    t2a_path = p
                    break
            assert t2a_path is not None

            mock_select_logic.assert_called_with(t2a_path)

            mock_select_logic.reset_mock()
            tree.update_tree("localhost", 3141, None)
            assert tree._all_paths_cache is None


def test_should_show_node(live_defs: ecflow.Defs) -> None:
    """
    Test the filtering logic for nodes.

    Args:
        live_defs: The ecFlow definitions from the live server.

    Returns:
        None
    """
    tree = SuiteTree("Test")
    tree.defs = live_defs
    tree.filters = [None, "complete", "active", "queued"]

    s1 = None
    s2 = None
    for s in live_defs.suites:
        if "s1_" in s.name():
            s1 = s
        if "s2_" in s.name():
            s2 = s

    assert s1 is not None
    assert s2 is not None
    task2a = list(s2.nodes)[0]  # queued

    tree._build_caches_and_populate()

    # No filter
    tree.current_filter = None
    assert tree._should_show_node(s1) is True

    # Check actual states
    s1_state = str(s1.get_state())
    s2_state = str(s2.get_state())
    t2a_state = str(task2a.get_state())

    tree.current_filter = s1_state
    assert tree._should_show_node(s1) is True

    if s2_state != s1_state:
        tree.current_filter = s1_state
        assert tree._should_show_node(s2) is False

    tree.current_filter = t2a_state
    assert tree._should_show_node(task2a) is True
    assert tree._should_show_node(s2) is True


def test_action_cycle_filter() -> None:
    """
    Test cycling through status filters.

    Returns:
        None
    """
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


def test_populate_tree_worker(live_defs: ecflow.Defs) -> None:
    """
    Test the background worker for tree population.

    Args:
        live_defs: The ecFlow definitions from the live server.

    Returns:
        None
    """
    tree = SuiteTree("Test")
    tree.defs = live_defs
    tree.root = MagicMock()

    with patch.object(tree, "_should_show_node", return_value=True), patch.object(tree, "_safe_call") as mock_safe:
        tree._populate_tree_worker()
        assert mock_safe.call_count >= 1
        args, _ = mock_safe.call_args
        assert args[0] == tree._add_nodes_batch
        assert args[1] == tree.root
        assert len(args[2]) >= 2
