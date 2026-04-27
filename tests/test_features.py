# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import MagicMock, PropertyMock, patch

from ectop.widgets.sidebar import SuiteTree


def test_search_logic() -> None:
    """Test the search logic in SuiteTree."""
    # Create mock nodes
    node1 = MagicMock()
    node1.label = "task1"
    node1.data = "/suite/task1"
    node1.parent = None

    node2 = MagicMock()
    node2.label = "post_proc"
    node2.data = "/suite/post_proc"
    node2.parent = None

    # Use actual instantiation to avoid missing internal attributes
    # but mock the necessary methods to avoid full TUI startup
    with patch("textual.widgets.Tree._clear_line_cache"):
        tree = SuiteTree("label")
        tree.host = "localhost"
        tree.port = 3141

        # In newer Textual, root might be a property or managed differently
        # We just need it to exist for the code to not crash
        tree._root = MagicMock()

        # Mock methods used in find_and_select
        tree.select_node = MagicMock()
        tree.scroll_to_node = MagicMock()

        with (
            patch.object(SuiteTree, "cursor_node", new_callable=PropertyMock) as mock_cursor,
            patch.object(SuiteTree, "app", new=MagicMock()),
        ):
            mock_cursor.return_value = None
            # Mocking the definition walk
            suite = MagicMock()
            suite.get_abs_node_path.return_value = "/suite"
            node1_ecf = MagicMock()
            node1_ecf.get_abs_node_path.return_value = "/suite/task1"
            node2_ecf = MagicMock()
            node2_ecf.get_abs_node_path.return_value = "/suite/post_proc"
            suite.get_all_nodes.return_value = [node1_ecf, node2_ecf]

            mock_defs = MagicMock()
            mock_defs.suites = [suite]

            # Use patch.object to set defs to avoid reactive logic issues in unit test
            with patch.object(SuiteTree, "defs", new_callable=PropertyMock) as mock_defs_prop:
                mock_defs_prop.return_value = mock_defs
                tree._all_paths_cache = ["/suite", "/suite/task1", "/suite/post_proc"]
                tree._search_paths_lower = [p.lower() for p in tree._all_paths_cache]
                tree._current_filter = None

                # Test substring match
                with patch.object(tree, "_select_by_path_logic") as mock_select:
                    tree._find_and_select_logic("task")
                    mock_select.assert_called_with("/suite/task1")

                # Test case insensitive
                with patch.object(tree, "_select_by_path_logic") as mock_select:
                    tree._find_and_select_logic("POST")
                    mock_select.assert_called_with("/suite/post_proc")

                # Test no match
                with patch.object(tree, "_select_by_path_logic") as mock_select:
                    tree._find_and_select_logic("missing")
                    mock_select.assert_not_called()
