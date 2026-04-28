# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import MagicMock, patch

import pytest

from ectop.app import Ectop
from ectop.client import EcflowClient
from ectop.constants import STATUS_SYNC_ERROR


@pytest.fixture
def client_instance(ecflow_server):
    """Fixture to provide an EcflowClient connected to the test server."""
    host, port = ecflow_server.split(":")
    return EcflowClient(host, int(port))


@pytest.fixture
def app(client_instance):
    """Fixture to provide an Ectop app connected to the test server."""
    app = Ectop(host=client_instance.host, port=client_instance.port)
    app.ecflow_client = client_instance
    return app


@pytest.mark.asyncio
async def test_app_initial_connect_success(app):
    """Test initial connection success with a real server."""
    await app._initial_connect()
    assert app.ecflow_client is not None


@pytest.mark.asyncio
async def test_run_client_command_error(app):
    """Test client command error handling with a real client instance."""
    app.notify = MagicMock()
    # Attempting to suspend a non-existent node should trigger an error from the server
    await app._run_client_command("suspend", "/non_existent")
    app.notify.assert_called()
    args, kwargs = app.notify.call_args
    assert "Error" in args[0] or kwargs.get("severity") == "error"


@pytest.mark.asyncio
async def test_action_refresh_error(app):
    """Test action_refresh handles connection errors correctly."""
    app.notify = MagicMock()
    mock_sb = MagicMock()

    # We mock query_one to return our mock status bar
    with patch.object(app, "query_one", return_value=mock_sb):
        # We manually break the client to simulate a connection error
        with patch.object(app.ecflow_client, "sync_local", side_effect=RuntimeError("Sync failed")):
            await app.action_refresh()
            mock_sb.update_status.assert_called_with(app.ecflow_client.host, app.ecflow_client.port, status=STATUS_SYNC_ERROR)
            app.notify.assert_called()
            assert "Sync failed" in str(app.notify.call_args)
