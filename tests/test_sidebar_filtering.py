# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""Tests for SuiteTree filtering against real ecFlow definitions."""

from __future__ import annotations

import ecflow
import pytest

from ectop.app import Ectop
from ectop.widgets.sidebar import SuiteTree


def _load_filter_definitions(ecflow_server: str) -> tuple[str, str, str, str]:
    """Load a nested suite with one aborted task into the real test server.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.

    Returns
    -------
    tuple[str, str, str, str]
        Server address, suite path, family path, and aborted task path.
    """
    host, port_text = ecflow_server.split(":")
    client = ecflow.Client(host, int(port_text))
    client.delete_all(force=True)
    defs = ecflow.Defs()
    suite = defs.add_suite("filter_suite")
    family = suite.add_family("filter_family")
    family.add_task("aborted_task")
    family.add_task("other_task")
    client.load(defs, force=True)
    client.begin_all_suites()
    client.force_state("/filter_suite/filter_family/aborted_task", ecflow.State.aborted)
    client.force_state("/filter_suite/filter_family/other_task", ecflow.State.complete)
    client.sync_local()
    return (
        ecflow_server,
        "/filter_suite",
        "/filter_suite/filter_family",
        "/filter_suite/filter_family/aborted_task",
    )


def test_should_show_node_filters_real_snapshot(ecflow_server: str) -> None:
    """Include ancestors of matching nodes and hide unrelated nodes.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    """
    address, suite_path, family_path, aborted_path = _load_filter_definitions(ecflow_server)
    host, port_text = address.split(":")
    client = ecflow.Client(host, int(port_text))
    client.sync_local()
    definitions = client.get_defs()
    tree = SuiteTree("filter test")
    tree.update_tree(host, int(port_text), definitions)

    tree.current_filter = None
    assert tree._should_show_node(definitions.find_abs_node(aborted_path)) is True
    assert tree._should_show_node(definitions.find_abs_node("/filter_suite/filter_family/other_task")) is True

    tree.current_filter = "aborted"
    assert tree._should_show_node(definitions.find_abs_node(aborted_path)) is True
    assert tree._should_show_node(definitions.find_abs_node(family_path)) is True
    assert tree._should_show_node(definitions.find_abs_node(suite_path)) is True
    assert tree._should_show_node(definitions.find_abs_node("/filter_suite/filter_family/other_task")) is False

    tree.current_filter = "complete"
    assert tree._should_show_node(definitions.find_abs_node(aborted_path)) is False


@pytest.mark.asyncio
async def test_action_cycle_filter_uses_real_app(ecflow_server: str) -> None:
    """Cycle status filters in a mounted Textual app with a real server.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    """
    address, _suite_path, _family_path, aborted_path = _load_filter_definitions(ecflow_server)
    host, port_text = address.split(":")
    app = Ectop(host, int(port_text), refresh_interval=60)

    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        for _ in range(100):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.02)
        assert tree.snapshot is not None
        assert tree.current_filter is None
        tree.action_cycle_filter()
        assert tree.current_filter == "aborted"
        assert aborted_path in tree._visible_paths(tree.snapshot)
