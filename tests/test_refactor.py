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

from unittest.mock import MagicMock, patch

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
    """Test selecting a nested path through the mounted tree.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    """
    host, port = ecflow_server.split(":")
    client = ecflow.Client(host, int(port))
    client.delete_all(force=True)

    defs = ecflow.Defs()
    defs.add_suite("s1").add_family("f1").add_task("t1")
    client.load(defs, force=True)
    app = Ectop(host, int(port), refresh_interval=60)

    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        for _ in range(100):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.02)
        assert tree.snapshot is not None

        tree.select_by_path("/s1/f1/t1")
        for _ in range(50):
            if app.get_selected_path() == "/s1/f1/t1":
                break
            await pilot.pause(0.02)
        assert app.get_selected_path() == "/s1/f1/t1"
