# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""Real ecFlow and Textual worker coverage for periodic tree refresh."""

from __future__ import annotations

from collections.abc import Callable

import ecflow
import pytest

from ectop.app import Ectop
from ectop.client import EcflowClient
from ectop.constants import STATUS_SYNC_ERROR
from ectop.widgets.sidebar import SuiteTree
from ectop.widgets.statusbar import StatusBar


def _load_task(ecflow_server: str) -> tuple[str, str]:
    """Load one task into the real test server.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.

    Returns
    -------
    tuple[str, str]
        Server address and absolute task path.
    """
    host, port_text = ecflow_server.split(":")
    client = ecflow.Client(host, int(port_text))
    client.delete_all(force=True)
    defs = ecflow.Defs()
    defs.add_suite("refresh_suite").add_task("refresh_task")
    client.load(defs, force=True)
    return ecflow_server, "/refresh_suite/refresh_task"


async def _wait_until(pilot, predicate: Callable[[], bool], message: str) -> None:
    """Poll a UI condition while allowing Textual to process messages.

    Parameters
    ----------
    pilot : textual.pilot.Pilot
        Test driver for a running Textual app.
    predicate : Callable[[], bool]
        Condition to wait for.
    message : str
        Failure message if the condition is not reached.
    """
    for _ in range(150):
        if predicate():
            return
        await pilot.pause(0.02)
    raise AssertionError(message)


@pytest.mark.asyncio
async def test_periodic_refresh_updates_state_with_live_log_disabled(ecflow_server: str) -> None:
    """Refresh real server state independently from live output polling.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    """
    address, path = _load_task(ecflow_server)
    host, port_text = address.split(":")
    app = Ectop(host, int(port_text), refresh_interval=0.08)

    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        await _wait_until(pilot, lambda: tree.snapshot is not None, "initial definitions did not arrive")
        assert not app.query_one("#main_content").is_live
        initial_status = app.query_one(StatusBar).status

        assert app.ecflow_client is not None
        await app.ecflow_client.force_complete(path)
        await _wait_until(
            pilot,
            lambda: tree.snapshot is not None and tree.snapshot.by_path[path].state == "complete",
            "periodic refresh did not publish the completed task",
        )
        status_bar = app.query_one(StatusBar)
        assert status_bar.status == initial_status


@pytest.mark.asyncio
async def test_refresh_failure_retains_last_tree(ecflow_server: str) -> None:
    """Keep the last definitions snapshot when a later refresh fails.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    """
    address, _ = _load_task(ecflow_server)
    host, port_text = address.split(":")
    app = Ectop(host, int(port_text), refresh_interval=60)

    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        await _wait_until(pilot, lambda: tree.snapshot is not None, "initial definitions did not arrive")
        original_snapshot = tree.snapshot
        app.ecflow_client = EcflowClient(host, 1)
        worker = app.action_refresh()
        assert worker is not None
        await worker.wait()
        assert tree.snapshot is original_snapshot
        assert app.query_one(StatusBar).status == STATUS_SYNC_ERROR


@pytest.mark.asyncio
async def test_refresh_ticks_coalesce_to_one_pending_run(ecflow_server: str) -> None:
    """Coalesce many timer ticks while the real refresh worker is active.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    """
    address, _ = _load_task(ecflow_server)
    host, port_text = address.split(":")
    app = Ectop(host, int(port_text), refresh_interval=60)

    async with app.run_test() as pilot:
        await _wait_until(pilot, lambda: not app._refresh_in_flight, "initial refresh did not finish")
        previous_count = app._refresh_run_count
        app._automatic_refresh_tick()
        for _ in range(10):
            app._automatic_refresh_tick()
        assert app._refresh_pending

        await _wait_until(
            pilot,
            lambda: app._refresh_run_count >= previous_count + 2 and not app._refresh_in_flight,
            "the active and coalesced refresh runs did not finish",
        )
        assert app._refresh_run_count == previous_count + 2
        assert not app._refresh_pending
