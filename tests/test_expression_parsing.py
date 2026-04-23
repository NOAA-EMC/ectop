# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for trigger expression parsing in WhyInspector.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ectop.widgets.modals.why import DepData, WhyInspector


def test_parse_nested_and_or() -> None:
    """
    Test parsing complex nested AND/OR expressions.
    """
    mock_client = MagicMock()
    inspector = WhyInspector("/node", mock_client)

    mock_defs = MagicMock()
    parent = DepData("Root")
    expr = "(/s/t1 == complete and /s/t2 == active) or /s/t3 == aborted"

    t1 = MagicMock()
    t1.get_state.return_value = "complete"
    t2 = MagicMock()
    t2.get_state.return_value = "active"
    t3 = MagicMock()
    t3.get_state.return_value = "queued"

    mock_defs.find_abs_node.side_effect = lambda p: {"/s/t1": t1, "/s/t2": t2, "/s/t3": t3}.get(p)

    met = inspector._parse_expression_data(parent, expr, mock_defs)

    assert met is True
    assert len(parent.children) > 0


def test_parse_not_operator() -> None:
    """
    Test parsing NOT operator.
    """
    mock_client = MagicMock()
    inspector = WhyInspector("/node", mock_client)
    mock_defs = MagicMock()
    parent = DepData("Root")

    t1 = MagicMock()
    t1.get_state.return_value = "active"
    mock_defs.find_abs_node.return_value = t1

    met = inspector._parse_expression_data(parent, "! /s/t1 == complete", mock_defs)
    assert met is True
