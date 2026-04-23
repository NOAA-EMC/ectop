# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for miscellaneous features in ectop.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from ectop.widgets.sidebar import SuiteTree


def test_search_logic() -> None:
    """
    Test the search logic in SuiteTree.
    """
    with patch.object(SuiteTree, "app", new_callable=PropertyMock) as mock_app_prop:
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app

        tree = SuiteTree("label")
        tree.defs = MagicMock()
        tree._all_paths_cache = ["/s/task1", "/s/task2"]

        with patch.object(tree, "_select_by_path_logic") as mock_select:
            tree._find_and_select_logic("task2")
            mock_select.assert_called_with("/s/task2")
