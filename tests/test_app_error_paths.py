# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""
Tests for error paths and robustness in the Ectop app.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ectop.app import Ectop
from ectop.client import EcflowClient
from ectop.constants import STATUS_SYNC_ERROR


@pytest.fixture
def client_instance(ecflow_server):
    """
    Fixture to provide an EcflowClient connected to the test server.

    Args:
        ecflow_server: The host:port of the test server.

    Returns:
        EcflowClient: A client instance.
    """
    host, port = ecflow_server.split(":")
    return EcflowClient(host, int(port))


@pytest.fixture
def app(client_instance):
    """
    Fixture to provide an Ectop app connected to the test server.

    Args:
        client_instance: The client instance.

    Returns:
        Ectop: An app instance.
    """
    app = Ectop(host=client_instance.host, port=client_instance.port)
    app.ecflow_client = client_instance
    return app


@pytest.mark.asyncio
async def test_app_initial_connect_success(app):
    """
    Test initial connection success with a real server.

    Args:
        app: The Ectop app fixture.
    """
    async with app.run_test() as pilot:
        worker = app._initial_connect()
        await worker.wait()
        await pilot.pause(0.1)
        assert app.ecflow_client is not None


@pytest.mark.asyncio
async def test_run_client_command_error(app):
    """
    Test client command error handling with a real client instance.

    Args:
        app: The Ectop app fixture.
    """
    app.notify = MagicMock()
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        worker = app._run_client_command("suspend", "/non_existent")
        await worker.wait()
        app.notify.assert_called()
        args, kwargs = app.notify.call_args
        assert "Error" in args[0] or kwargs.get("severity") == "error"


@pytest.mark.asyncio
async def test_action_refresh_error(app):
    """
    Test action_refresh handles connection errors correctly.

    Args:
        app: The Ectop app fixture.
    """
    app.notify = MagicMock()
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        app.ecflow_client = EcflowClient("localhost", 1)
        worker = app.action_refresh()
        assert worker is not None
        await worker.wait()
        status_bar = app.query_one("#status_bar")
        assert status_bar.status == STATUS_SYNC_ERROR
        app.notify.assert_called()


@pytest.mark.asyncio
async def test_lost_connection_during_command(app):
    """
    Simulate a lost connection during a client command.

    Args:
        app: The Ectop app fixture.
    """
    app.notify = MagicMock()
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        app.ecflow_client = EcflowClient("localhost", 1)
        worker = app._run_client_command("suspend", "/some/path")
        await worker.wait()
        app.notify.assert_called()
        assert "Failed to suspend" in str(app.notify.call_args)
        args, kwargs = app.notify.call_args
        assert kwargs.get("severity") == "error"


@pytest.mark.asyncio
async def test_initial_connect_failure():
    """
    Test app behavior when initial connection fails.
    """
    # Use a port that is definitely not listening
    app = Ectop(host="localhost", port=1)
    app.notify = MagicMock()

    async with app.run_test():
        worker = app._initial_connect()
        await worker.wait()
        app.notify.assert_called()
        assert "Connection Failed" in str(app.notify.call_args)
        assert "failed" in str(app.query_one("#suite_tree").root.label).lower()
