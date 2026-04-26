# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations
from unittest.mock import MagicMock, PropertyMock, patch
import ecflow
import pytest
from ectop.widgets.sidebar import SuiteTree

@pytest.fixture
def real_node():
    defs = ecflow.Defs()
    return defs.add_suite("s1")

def test_should_show_node_no_filter(real_node):
    tree = SuiteTree("label")
    tree.current_filter = None
    assert tree._should_show_node(real_node) is True

def test_should_show_node_match(real_node):
    tree = SuiteTree("label")
    tree.current_filter = "unknown"
    assert tree._should_show_node(real_node) is True
