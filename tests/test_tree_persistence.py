# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Integration tests for tree state persistence across refreshes.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pytest

from ectop.app import Ectop
from ectop.widgets.sidebar import SuiteTree

if TYPE_CHECKING:
    from pathlib import Path

    from textual.widgets.tree import TreeNode


@pytest.fixture
def app_with_server(ecflow_server: str) -> Ectop:
    """
    Fixture to provide an Ectop app connected to the test server.

    Args:
        ecflow_server: The host:port string from the ecflow_server fixture.

    Returns:
        The initialized Ectop application instance.
    """
    host, port = ecflow_server.split(":")
    return Ectop(host=host, port=int(port))


@pytest.mark.asyncio
async def test_cursor_persistence_after_refresh(app_with_server: Ectop, tmp_path: Path) -> None:
    """
    Test that the cursor position is restored after a tree refresh.

    Args:
        app_with_server: The application instance.
        tmp_path: Temporary path for definition files.
    """
    app = app_with_server
    # Use a unique suite name to avoid conflicts with other tests using the session-scoped server
    suite_name = f"persist_{random.randint(0, 10000)}"

    # 1. Load a nested suite
    defs_content = f"""
suite {suite_name}
  family f1
    task t1
  endfamily
endsuite
"""
    defs_file = tmp_path / "persistence.def"
    defs_file.write_text(defs_content)

    async with app.run_test() as pilot:
        # Wait for initial connect and refresh
        await pilot.pause()

        # Load the defs
        await app.ecflow_client.load_defs(str(defs_file))
        await app.action_refresh()
        await pilot.pause()

        tree = app.query_one("#suite_tree", SuiteTree)

        target_path = f"/{suite_name}/f1/t1"

        # Manually trigger expansion to make sure t1 is created
        tree._select_by_path_logic(target_path)

        def find_in_node(node: TreeNode[str]) -> TreeNode[str] | None:
            """
            Recursively find a tree node by its data path.

            Args:
                node: The starting node for the search.

            Returns:
                The matching TreeNode or None if not found.
            """
            if node.data == target_path:
                return node
            for child in node.children:
                res = find_in_node(child)
                if res:
                    return res
            return None

        # Verify initial selection
        found_node = find_in_node(tree.root)

        assert found_node is not None, f"Node {target_path} not found in tree"
        tree.select_node(found_node)
        assert tree.cursor_node == found_node

        # 3. Trigger a refresh
        await app.action_refresh()
        await pilot.pause()

        # 4. Verify the cursor is back at target_path
        new_found_node = find_in_node(tree.root)
        assert new_found_node is not None, f"Node {target_path} not found after refresh"
        assert tree.cursor_node == new_found_node
        assert tree.cursor_node.data == target_path

        # Verify it's actually expanded as well
        parent = tree.cursor_node.parent
        assert parent is not None
        assert parent.is_expanded is True

        grandparent = parent.parent
        assert grandparent is not None
        assert grandparent.is_expanded is True
