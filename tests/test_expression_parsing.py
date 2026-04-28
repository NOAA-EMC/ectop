# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Comprehensive tests for ecFlow trigger expression parsing in WhyInspector.
"""

from __future__ import annotations

from unittest.mock import patch

import ecflow
import pytest

from ectop.client import EcflowClient
from ectop.constants import (
    EXPR_AND_LABEL,
)
from ectop.widgets.modals.why import DepData, WhyInspector


@pytest.fixture
def real_defs(ecflow_server) -> ecflow.Defs:
    """Provides a real ecflow.Defs object with some nodes populated."""
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))

    defs = ecflow.Defs()
    suite = defs.add_suite("suite")
    suite.add_task("test_node.1") # Dots are allowed, dashes are NOT
    suite.add_task("other_node")
    suite.add_task("aborted_node")

    # Use force=True to avoid "Suite already exists" error if the fixture runs again on same server
    client.load(defs, force=True)

    # Set states via client since we can't set them directly on Defs reliably for testing
    client.force_state("/suite/test_node.1", ecflow.State.complete)
    client.force_state("/suite/other_node", ecflow.State.active)
    client.force_state("/suite/aborted_node", ecflow.State.aborted)

    client.sync_local()
    return client.get_defs()


@pytest.fixture
def client_instance(ecflow_server) -> EcflowClient:
    """Fixture to provide an EcflowClient connected to the test server."""
    host, port = ecflow_server.split(":")
    return EcflowClient(host, int(port))


def test_parse_complex_path(client_instance, real_defs):
    """
    Test parsing paths with special characters like dots.

    Args:
        client_instance: The EcflowClient fixture.
        real_defs: The real ecflow.Defs fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    inspector._parse_expression_data(parent, "/suite/test_node.1 == complete", real_defs)

    # Check that it matched correctly
    assert len(parent.children) == 1
    child = parent.children[0]
    assert "/suite/test_node.1" in child.label
    assert "complete" in child.label
    assert child.is_met is True


def test_parse_aborted_highlighting(client_instance, real_defs):
    """
    Test that aborted nodes get special highlighting.

    Args:
        client_instance: The EcflowClient fixture.
        real_defs: The real ecflow.Defs fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    inspector._parse_expression_data(parent, "/suite/aborted_node == complete", real_defs)

    assert len(parent.children) == 1
    child = parent.children[0]
    assert "aborted" in child.label
    assert "STOPPED HERE" in child.label
    assert "[b red]" in child.label
    assert child.is_met is False


def test_parse_nested_and_or(client_instance, real_defs):
    """
    Test deeply nested AND/OR logic.

    Args:
        client_instance: The EcflowClient fixture.
        real_defs: The real ecflow.Defs fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    expr = "(/suite/test_node.1 == complete) and ((/suite/other_node == active) or (/suite/aborted_node == complete))"
    inspector._parse_expression_data(parent, expr, real_defs)

    # Verify top-level AND
    assert any(child.label == EXPR_AND_LABEL for child in parent.children)


def test_parse_various_operators(client_instance, real_defs):
    """
    Test different comparison operators.

    Args:
        client_instance: The EcflowClient fixture.
        real_defs: The real ecflow.Defs fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)

    operators = ["==", "!=", "<", ">", "<=", ">="]
    for op in operators:
        parent = DepData("Parent")
        inspector._parse_expression_data(parent, f"/suite/other_node {op} complete", real_defs)
        assert len(parent.children) == 1
        child = parent.children[0]
        assert f" {op} " in child.label


def test_parse_not_operator(client_instance, real_defs):
    """
    Test the NOT operator handling in expressions.

    Args:
        client_instance: The EcflowClient fixture.
        real_defs: The real ecflow.Defs fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    inspector._parse_expression_data(parent, "! (/suite/other_node == complete)", real_defs)

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


def test_parse_leaf_negation(client_instance, real_defs):
    """
    Test negation prefix directly on a leaf node.

    Args:
        client_instance: The EcflowClient fixture.
        real_defs: The real ecflow.Defs fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    # ! /suite/test_node.1 == complete -> /suite/test_node.1 is complete.
    # complete == complete is True. ! (True) is False.
    inspector._parse_expression_data(parent, "!/suite/test_node.1 == complete", real_defs)

    # Now "!/suite/..." starts with "!", so it hits the NOT block first.
    assert any("NOT (Must be false)" in child.label for child in parent.children)


def test_gather_dependency_data_limits(client_instance, ecflow_server):
    """
    Test gathering dependency data including limits.

    Args:
        client_instance: The EcflowClient fixture.
        ecflow_server: The ecflow_server fixture.
    """
    host, port = ecflow_server.split(":")
    ecf_client = ecflow.Client(host, int(port))

    defs = ecflow.Defs()
    suite = defs.add_suite("s_limit")
    suite.add_limit("max_jobs", 10)
    task = suite.add_task("t_limit")
    task.add_inlimit("max_jobs", "/s_limit")

    ecf_client.load(defs, force=True)
    ecf_client.sync_local()
    real_defs = ecf_client.get_defs()

    inspector = WhyInspector("/s_limit/t_limit", client_instance)
    node = real_defs.find_abs_node("/s_limit/t_limit")

    dep_data = inspector._gather_dependency_data(node, real_defs)

    # Check "Limits" header added
    assert any(child.label == "Limits" for child in dep_data.children)
    limit_root = next(child for child in dep_data.children if child.label == "Limits")
    assert any("Limit: max_jobs (Path: /s_limit)" in child.label for child in limit_root.children)


def test_gather_dependency_data_times(client_instance, ecflow_server):
    """
    Test gathering dependency data including times.

    Args:
        client_instance: The EcflowClient fixture.
        ecflow_server: The ecflow_server fixture.
    """
    host, port = ecflow_server.split(":")
    ecf_client = ecflow.Client(host, int(port))

    defs = ecflow.Defs()
    suite = defs.add_suite("s_time")
    task = suite.add_task("t_time")
    task.add_time("10:00")
    task.add_date(1, 1, 2024)
    task.add_cron(ecflow.Cron("10:00", days_of_week=[0,1,2,3,4,5,6]))

    ecf_client.load(defs, force=True)
    ecf_client.sync_local()
    real_defs = ecf_client.get_defs()

    inspector = WhyInspector("/s_time/t_time", client_instance)
    node = real_defs.find_abs_node("/s_time/t_time")

    dep_data = inspector._gather_dependency_data(node, real_defs)

    assert any(child.label == "Time Dependencies" for child in dep_data.children)
    time_root = next(child for child in dep_data.children if child.label == "Time Dependencies")
    # Real ecFlow objects when stringified might have prefix 'time ', 'date ', 'cron '
    assert any("10:00" in child.label for child in time_root.children)
    assert any("1.1.2024" in child.label for child in time_root.children)
    assert any("Cron: " in child.label for child in time_root.children)


def test_parse_invalid_expression(client_instance):
    """
    Test WhyInspector with an invalid expression.

    Args:
        client_instance: The EcflowClient fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    # This should be caught by the try-except block in _parse_expression_data
    # Use a string that definitely won't match as a NOT or AND/OR or Leaf.
    # Actually, anything that doesn't match LEAF will become a LITERAL unless it starts with ! or has ' and '/' or '.
    # Let's use something that will cause _evaluate_expr_tree to fail or be a literal.

    # If it's a literal, it's not a "Parse Error", it's just shown as a note.
    # To trigger a "Parse Error", we might need recursion depth or something else that raises.
    # But wait, _evaluate_expr_tree is called inside a try-except.

    with patch.object(inspector, "_evaluate_expr_tree", side_effect=ValueError("Test Error")):
        inspector._parse_expression_data(parent, "/s/t == complete", None)

    assert any("Parse Error" in child.label for child in parent.children)
    assert any("Test Error" in child.label for child in parent.children)


def test_parse_empty_expression(client_instance):
    """
    Test WhyInspector with an empty expression.

    Args:
        client_instance: The EcflowClient fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    met = inspector._parse_expression_data(parent, "", None)

    assert met is True
    assert len(parent.children) == 0


def test_evaluate_non_existent_node(client_instance, real_defs):
    """
    Test evaluating an expression referencing a non-existent node.

    Args:
        client_instance: The EcflowClient fixture.
        real_defs: The real ecflow.Defs fixture.
    """
    inspector = WhyInspector("/dummy", client_instance)
    parent = DepData("Parent")

    met = inspector._parse_expression_data(parent, "/no/such/node == complete", real_defs)

    assert met is False
    assert any("Not found" in child.label for child in parent.children)
