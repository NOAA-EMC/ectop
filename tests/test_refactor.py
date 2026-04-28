# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for refactored logic and new features.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import ecflow
import pytest

from ectop.app import Ectop
from ectop.client import EcflowClient
from ectop.constants import EXPR_AND_LABEL, EXPR_OR_LABEL
from ectop.widgets.modals.why import DepData, WhyInspector
from ectop.widgets.sidebar import SuiteTree


@pytest.fixture
def app() -> Ectop:
    """
    Create a mock Ectop app.

    Returns:
        Ectop: A mock Ectop application instance.
    """
    app = Ectop()
    # Mock notify and copy_to_clipboard to avoid AsyncMock issues
    app.notify = MagicMock()
    app.copy_to_clipboard = MagicMock()
    return app


def test_action_requeue(app: Ectop) -> None:
    """
    Test action_requeue calls the client.

    Args:
        app: The Ectop app fixture.
    """
    with (
        patch.object(app, "_run_client_command", new_callable=MagicMock) as mock_run,
        patch.object(app, "get_selected_path", return_value="/s1/t1"),
    ):
        app.action_requeue()
        mock_run.assert_called_once_with("requeue", "/s1/t1")


def test_action_copy_path() -> None:
    """
    Test action_copy_path copies to clipboard and notifies the user.
    """
    # Test with clipboard support
    app = MagicMock()
    app.get_selected_path.return_value = "/s1/t1"
    Ectop.action_copy_path(app)
    app.copy_to_clipboard.assert_called_once_with("/s1/t1")
    app.notify.assert_called_once_with("Copied to clipboard: /s1/t1")

    # Test without clipboard support
    app_no_clip = MagicMock()
    del app_no_clip.copy_to_clipboard
    app_no_clip.get_selected_path.return_value = "/s1/t1"
    Ectop.action_copy_path(app_no_clip)
    app_no_clip.notify.assert_called_once_with("Node path: /s1/t1")


def test_why_inspector_nested_parsing(ecflow_server) -> None:
    """
    Test WhyInspector handles nested parentheses and operators.

    Args:
        ecflow_server: The ecflow_server fixture.
    """
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))

    defs = ecflow.Defs()
    suite = defs.add_suite("s")
    suite.add_task("a")
    suite.add_task("b")
    client.load(defs, force=True)

    client.force_state("/s/a", ecflow.State.complete)
    client.force_state("/s/b", ecflow.State.aborted)
    client.sync_local()

    real_defs = client.get_defs()

    ectop_client = EcflowClient(host, int(port))
    inspector = WhyInspector("/dummy", ectop_client)

    parent_data = DepData("Parent")

    # Complex expression: ((/s/a == complete) or (/s/b == complete)) and (/s/a != aborted)
    expr = "((/s/a == complete) or (/s/b == complete)) and (/s/a != aborted)"

    inspector._parse_expression_data(parent_data, expr, real_defs)

    # Check that AND was added at top level
    assert any(child.label == EXPR_AND_LABEL for child in parent_data.children)
    and_node = next(child for child in parent_data.children if child.label == EXPR_AND_LABEL)
    # Check that OR was added under AND
    assert any(child.label == EXPR_OR_LABEL for child in and_node.children)


@pytest.mark.asyncio
async def test_suite_tree_select_by_path_worker(ecflow_server) -> None:
    """
    Test SuiteTree.select_by_path uses worker logic.

    Args:
        ecflow_server: The ecflow_server fixture.
    """
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))

    defs = ecflow.Defs()
    defs.add_suite("s1")
    client.load(defs, force=True)
    client.sync_local()
    real_defs = client.get_defs()

    tree = SuiteTree("Test")
    tree.defs = real_defs

    # Mock UI node
    mock_ui_suite = MagicMock()
    mock_ui_suite.data = "/s1"

    with (
        patch.object(type(tree.root), "children", new_callable=PropertyMock) as mock_children,
        patch.object(SuiteTree, "app", new=MagicMock()) as mock_app,
        patch.object(tree, "_load_children"),
        patch.object(tree, "_select_and_reveal"),
    ):
        mock_children.return_value = [mock_ui_suite]

        # We call the logic method directly for synchronous testing
        tree._select_by_path_logic("/s1")

        # It should have found the suite and called _select_and_reveal via call_from_thread
        mock_app.call_from_thread.assert_any_call(tree._select_and_reveal, mock_ui_suite)
