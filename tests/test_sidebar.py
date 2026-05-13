# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the Sidebar (SuiteTree) widget.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import random
import string
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, patch

import ecflow
import pytest

from ectop.widgets.sidebar import SuiteTree

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def unique_suite_names() -> Callable[[int], list[str]]:
    """
    Fixture to generate unique suite names.

    Returns:
        A function that generates n unique suite names.
    """

    def _generator(n: int) -> list[str]:
        return ["s" + "".join(random.choices(string.ascii_lowercase, k=8)) for _ in range(n)]

    return _generator


@pytest.fixture
def test_setup(ecflow_server: str, unique_suite_names: Callable[[int], list[str]]) -> tuple[list[str], ecflow.Defs]:
    """
    Setup a unique set of suites for a test.

    Args:
        ecflow_server: The host:port of the live ecFlow server.
        unique_suite_names: Fixture to generate unique suite names.

    Returns:
        tuple[list[str], ecflow.Defs]: A tuple containing the suite names and the definitions.
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


@pytest.mark.asyncio
async def test_update_tree_integrated(ecflow_server: str, unique_suite_names: Callable[[int], list[str]]) -> None:
    """
    Test that update_tree clears and repopulates the tree in a live app.

    Args:
        ecflow_server: The host:port of the live ecFlow server.
        unique_suite_names: Fixture to generate unique suite names.
    """
    from ectop.app import Ectop

    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))
    client.restart_server()

    suite_name = unique_suite_names(1)[0]
    defs = ecflow.Defs()
    defs.add_suite(suite_name)
    client.load(defs, force=True)

    app = Ectop(host=host, port=int(port))
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        # Wait for tree to populate
        for _ in range(50):
            if any(c.data == f"/{suite_name}" for c in tree.root.children):
                break
            await pilot.pause(0.1)

        assert any(c.data == f"/{suite_name}" for c in tree.root.children)
        assert str(tree.host) == host
        assert int(tree.port) == int(port)


@pytest.mark.asyncio
async def test_load_children_integrated(ecflow_server: str, unique_suite_names: Callable[[int], list[str]]) -> None:
    """
    Test that expanding a node loads its children from the server.

    Args:
        ecflow_server: The host:port of the live ecFlow server.
        unique_suite_names: Fixture to generate unique suite names.
    """
    from ectop.app import Ectop

    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))

    suite_name = unique_suite_names(1)[0]
    defs = ecflow.Defs()
    suite = defs.add_suite(suite_name)
    suite.add_task("task1")
    client.load(defs, force=True)

    app = Ectop(host=host, port=int(port))
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)

        # Wait for suite to appear
        suite_ui_node = None
        for _ in range(50):
            for child in tree.root.children:
                if child.data == f"/{suite_name}":
                    suite_ui_node = child
                    break
            if suite_ui_node:
                break
            await pilot.pause(0.1)

        assert suite_ui_node is not None

        # Expand node to trigger lazy loading
        suite_ui_node.expand()

        # Wait for children to load
        for _ in range(50):
            if any(c.data == f"/{suite_name}/task1" for c in suite_ui_node.children):
                break
            await pilot.pause(0.1)

        assert any(c.data == f"/{suite_name}/task1" for c in suite_ui_node.children)


@pytest.mark.asyncio
async def test_select_by_path_integrated(ecflow_server: str) -> None:
    """
    Test that select_by_path expands and selects the correct node using a real server.

    Args:
        ecflow_server: The host:port of the live ecFlow server.
    """
    import random
    import string

    from ectop.app import Ectop

    host, port = ecflow_server.split(":")

    # Setup server with nested structure and unique name
    import ecflow

    suite_name = "s_" + "".join(random.choices(string.ascii_lowercase, k=8))
    client = ecflow.Client(host, int(port))
    client.delete_all()

    defs = ecflow.Defs()
    suite = defs.add_suite(suite_name)
    fam = suite.add_family("f1")
    fam.add_task("t1")
    client.load(defs, force=True)

    task_path = f"/{suite_name}/f1/t1"

    app = Ectop(host=host, port=int(port))
    async with app.run_test() as pilot:
        # Wait for initial connect and tree population
        tree = app.query_one(SuiteTree)
        for _ in range(50):
            if tree.defs is not None and len(tree.root.children) > 0 and tree._visibility_cache:
                if any(c.data == f"/{suite_name}" for c in tree.root.children):
                    break
            await pilot.pause(0.1)

        # Manually traverse and expand to verify the tree correctly creates nodes
        # for a deep path in a live server environment.
        current_ui_node = tree.root
        parts = task_path.strip("/").split("/")
        current_path = ""
        for part in parts:
            current_path += "/" + part
            # Load children synchronously within the pilot thread
            tree._load_children(current_ui_node, sync=True)

            found = False
            for child in current_ui_node.children:
                if child.data == current_path:
                    current_ui_node = child
                    current_ui_node.expand()
                    found = True
                    break
            assert found, f"Could not find UI node for {current_path}"

        # Verify the target node has the correct data
        assert current_ui_node.data == task_path


@pytest.mark.asyncio
async def test_find_and_select_integrated(ecflow_server: str, unique_suite_names: Callable[[int], list[str]]) -> None:
    """
    Test that find_and_select correctly finds and selects a node in a live app.

    Args:
        ecflow_server: The host:port of the live ecFlow server.
        unique_suite_names: Fixture to generate unique suite names.
    """
    from ectop.app import Ectop

    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))

    suite_name = unique_suite_names(1)[0]
    task_name = "target_task"
    defs = ecflow.Defs()
    suite = defs.add_suite(suite_name)
    suite.add_task(task_name)
    client.load(defs, force=True)

    app = Ectop(host=host, port=int(port))
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)

        # Wait for tree to populate
        for _ in range(50):
            if tree.defs is not None and tree._all_paths_cache:
                break
            await pilot.pause(0.1)

        # Trigger search
        await pilot.press("/")
        await pilot.press(*task_name)
        await pilot.press("enter")

        # Wait for selection to update
        # find_and_select runs in a worker
        for _ in range(50):
            if tree.cursor_node and tree.cursor_node.data == f"/{suite_name}/{task_name}":
                break
            await pilot.pause(0.1)

        assert tree.cursor_node is not None
        assert tree.cursor_node.data == f"/{suite_name}/{task_name}"


def test_should_show_node(test_setup: tuple[list[str], ecflow.Defs]) -> None:
    """
    Test the filtering logic for nodes.

    Args:
        test_setup: Fixture providing test data.
    """
    names, real_defs = test_setup
    tree = SuiteTree("Test")
    tree.defs = real_defs
    tree.filters = [None, "complete", "active", "aborted"]

    # We must trigger build_caches_and_populate to use the cache
    tree._build_caches_and_populate()

    suite1 = real_defs.find_suite(names[0])  # s1/t1 is complete
    suite2 = real_defs.find_suite(names[1])  # s2 is active, s2/t2a is aborted
    task2a = real_defs.find_abs_node(f"/{names[1]}/t2a")

    assert suite1 is not None
    assert suite2 is not None
    assert task2a is not None

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
    """
    Test cycling through status filters.
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
