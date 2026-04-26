# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import MagicMock
import ecflow
import pytest
from ectop.app import Ectop, EctopCommands
from ectop.widgets.content import MainContent
from ectop.widgets.sidebar import SuiteTree
from ectop.widgets.statusbar import StatusBar

def test_status_bar_update() -> None:
    sb = StatusBar()
    sb.update_status("myhost", 1234, "Connected")
    assert sb.server_info == "myhost:1234"
    assert sb.status == "Connected"

def test_suite_tree_filtering() -> None:
    tree = SuiteTree("Test")
    defs = ecflow.Defs()
    suite = defs.add_suite("suite")
    task1 = suite.add_task("task1")
    tree.defs = defs
    tree.current_filter = "unknown"
    assert tree._should_show_node(task1) is True
    tree.current_filter = "active"
    assert tree._should_show_node(task1) is False
