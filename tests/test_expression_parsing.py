# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Comprehensive tests for ecFlow trigger expression parsing in WhyInspector.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ectop.constants import (
    EXPR_AND_LABEL,
)
from ectop.widgets.modals.why import DepData, WhyInspector


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_defs() -> MagicMock:
    defs = MagicMock()
    nodes = {}

    def add_node(path, state):
        node = MagicMock()
        node.get_state.return_value = state
        nodes[path] = node
        return node

    add_node("/suite/test-node.1", "complete")
    add_node("/suite/other_node", "active")
    add_node("/suite/aborted_node", "aborted")

    defs.find_abs_node.side_effect = lambda p: nodes.get(p)
    return defs


def test_parse_complex_path(mock_client, mock_defs):
    """Test parsing paths with special characters like - and ."""
    inspector = WhyInspector("/dummy", mock_client)
    parent = DepData("Parent")

    inspector._parse_expression_data(parent, "/suite/test-node.1 == complete", mock_defs)

    # Check that it matched correctly
    assert len(parent.children) == 1
    child = parent.children[0]
    assert "/suite/test-node.1" in child.label
    assert "complete" in child.label
    assert child.is_met is True


def test_parse_aborted_highlighting(mock_client, mock_defs):
    """Test that aborted nodes get special highlighting."""
    inspector = WhyInspector("/dummy", mock_client)
    parent = DepData("Parent")

    inspector._parse_expression_data(parent, "/suite/aborted_node == complete", mock_defs)

    assert len(parent.children) == 1
    child = parent.children[0]
    assert "aborted" in child.label
    assert "STOPPED HERE" in child.label
    assert "[b red]" in child.label
    assert child.is_met is False


def test_parse_nested_and_or(mock_client, mock_defs):
    """Test deeply nested AND/OR logic."""
    inspector = WhyInspector("/dummy", mock_client)
    parent = DepData("Parent")

    expr = "(/suite/test-node.1 == complete) and ((/suite/other_node == active) or (/suite/aborted_node == complete))"
    inspector._parse_expression_data(parent, expr, mock_defs)

    # Verify top-level AND
    assert any(child.label == EXPR_AND_LABEL for child in parent.children)


def test_parse_various_operators(mock_client, mock_defs):
    """Test different comparison operators."""
    inspector = WhyInspector("/dummy", mock_client)

    operators = ["==", "!=", "<", ">", "<=", ">="]
    for op in operators:
        parent = DepData("Parent")
        inspector._parse_expression_data(parent, f"/suite/other_node {op} complete", mock_defs)
        assert len(parent.children) == 1
        child = parent.children[0]
        assert f" {op} " in child.label


def test_parse_not_operator(mock_client, mock_defs):
    """Test the NOT operator handling in expressions."""
    inspector = WhyInspector("/dummy", mock_client)
    parent = DepData("Parent")

    inspector._parse_expression_data(parent, "! (/suite/other_node == complete)", mock_defs)

    # Check top-level NOT node
    assert any("NOT (Must be false)" in child.label for child in parent.children)
    not_node = next(child for child in parent.children if "NOT (Must be false)" in child.label)

    # Check that it recursed to the child
    assert len(not_node.children) == 1
    inner = not_node.children[0]
    # Inner expression is /suite/other_node == complete.
    # other_node is active. active == complete is False.
    assert "/suite/other_node" in inner.label
    assert inner.is_met is False
    assert not_node.is_met is True  # NOT (False) is True


def test_parse_leaf_negation(mock_client, mock_defs):
    """Test negation prefix directly on a leaf node."""
    inspector = WhyInspector("/dummy", mock_client)
    parent = DepData("Parent")

    # ! /suite/test-node.1 == complete -> /suite/test-node.1 is complete.
    # complete == complete is True. ! (True) is False.
    inspector._parse_expression_data(parent, "!/suite/test-node.1 == complete", mock_defs)

    # Now "!/suite/..." starts with "!", so it hits the NOT block first.
    assert any("NOT (Must be false)" in child.label for child in parent.children)


def test_gather_dependency_data_limits(mock_client):
    """Test gathering dependency data including limits."""
    inspector = WhyInspector("/dummy", mock_client)
    mock_node = MagicMock()

    limit = MagicMock()
    limit.name.return_value = "max_jobs"
    limit.value.return_value = "/limits"
    mock_node.inlimits = [limit]
    mock_node.get_why.return_value = ""
    mock_node.get_trigger.return_value = None
    mock_node.get_complete.return_value = None
    mock_node.get_times.return_value = []
    mock_node.get_dates.return_value = []
    mock_node.get_crons.return_value = []

    dep_data = inspector._gather_dependency_data(mock_node, MagicMock())

    # Check "Limits" header added
    assert any(child.label == "Limits" for child in dep_data.children)
    limit_root = next(child for child in dep_data.children if child.label == "Limits")
    assert any("Limit: max_jobs (Path: /limits)" in child.label for child in limit_root.children)


def test_gather_dependency_data_times(mock_client):
    """Test gathering dependency data including times."""
    inspector = WhyInspector("/dummy", mock_client)
    mock_node = MagicMock()

    mock_node.get_why.return_value = ""
    mock_node.get_trigger.return_value = None
    mock_node.get_complete.return_value = None
    mock_node.inlimits = []
    mock_node.get_times.return_value = ["10:00"]
    mock_node.get_dates.return_value = ["01.01.2024"]
    mock_node.get_crons.return_value = ["0 10 * * *"]

    dep_data = inspector._gather_dependency_data(mock_node, MagicMock())

    assert any(child.label == "Time Dependencies" for child in dep_data.children)
    time_root = next(child for child in dep_data.children if child.label == "Time Dependencies")
    assert any("Time: 10:00" in child.label for child in time_root.children)
    assert any("Date: 01.01.2024" in child.label for child in time_root.children)
    assert any("Cron: 0 10 * * *" in child.label for child in time_root.children)
