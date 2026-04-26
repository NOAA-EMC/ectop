# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import MagicMock, PropertyMock, patch
import ecflow
from ectop.widgets.sidebar import SuiteTree

def test_search_logic() -> None:
    with patch("textual.widgets.Tree._clear_line_cache"):
        tree = SuiteTree("label")
        tree.host = "localhost"
        tree.port = 3141
        tree._root = MagicMock()
        tree.select_node = MagicMock()
        tree.scroll_to_node = MagicMock()
        with (
            patch.object(SuiteTree, "cursor_node", new_callable=PropertyMock) as mock_cursor,
            patch.object(SuiteTree, "app", new=MagicMock()),
        ):
            mock_cursor.return_value = None
            defs = ecflow.Defs()
            suite = defs.add_suite("suite")
            suite.add_task("task1")
            suite.add_task("post_proc")
            with patch.object(SuiteTree, "defs", new_callable=PropertyMock) as mock_defs_prop:
                mock_defs_prop.return_value = defs
                tree._all_paths_cache = ["/suite", "/suite/task1", "/suite/post_proc"]
                tree._current_filter = None
                with patch.object(tree, "_select_by_path_logic") as mock_select:
                    tree._find_and_select_logic("task")
                    mock_select.assert_called_with("/suite/task1")
                with patch.object(tree, "_select_by_path_logic") as mock_select:
                    tree._find_and_select_logic("POST")
                    mock_select.assert_called_with("/suite/post_proc")
                with patch.object(tree, "_select_by_path_logic") as mock_select:
                    tree._find_and_select_logic("missing")
                    mock_select.assert_not_called()
