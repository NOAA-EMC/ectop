# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import MagicMock, PropertyMock, patch
import ecflow
import pytest
from rich.text import Text
from ectop.widgets.sidebar import SuiteTree

@pytest.fixture
def real_defs():
    defs = ecflow.Defs()
    defs.add_suite("s1")
    defs.add_suite("s2").add_task("t2a")
    return defs

def test_update_tree(real_defs):
    tree = SuiteTree("Test")
    tree.clear = MagicMock()
    tree.root = MagicMock()
    with patch.object(SuiteTree, "_add_node_to_ui"), patch.object(SuiteTree, "_populate_tree_worker") as mock_worker:
        tree.update_tree("localhost", 3141, real_defs)
        tree.clear.assert_called_once()
        assert tree.defs == real_defs
        mock_worker.assert_called_once()

def test_should_show_node(real_defs):
    tree = SuiteTree("Test")
    suite1 = real_defs.find_suite("s1")
    tree.current_filter = None
    assert tree._should_show_node(suite1) is True
    tree.current_filter = "unknown"
    assert tree._should_show_node(suite1) is True
    tree.current_filter = "complete"
    assert tree._should_show_node(suite1) is False
