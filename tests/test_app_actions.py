# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ectop.app import Ectop
from ectop.client import EcflowClient


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
async def test_action_restart_server(app: Ectop) -> None:
    """Test action_restart_server correctly halts and restarts the server."""
    # First halt it
    await app.action_halt_server()
    await app.ecflow_client.sync_local()
    defs = await app.ecflow_client.get_defs()
    assert str(defs.get_server_state()) == "HALTED"

    # Now restart it
    await app.action_restart_server()
    await app.ecflow_client.sync_local()
    defs = await app.ecflow_client.get_defs()
    assert str(defs.get_server_state()) == "RUNNING"


@pytest.mark.asyncio
async def test_action_refresh_logic(app: Ectop, tmp_path) -> None:
    """Test action_refresh correctly updates the app state from the server."""
    # Load some defs
    defs_content = "suite s1\n  task t1\nendsuite"
    defs_file = tmp_path / "test_refresh.def"
    defs_file.write_text(defs_content)
    await app.ecflow_client.load_defs(str(defs_file))

    # Mock UI components that action_refresh queries
    mock_tree = MagicMock()
    mock_sb = MagicMock()

    def side_effect(selector, type=None):
        if "#suite_tree" in selector:
            return mock_tree
        if "#status_bar" in selector:
            return mock_sb
        return MagicMock()

    with patch.object(app, "query_one", side_effect=side_effect), patch.object(app, "notify"):
        await app.action_refresh()

    await app.ecflow_client.sync_local()
    defs = await app.ecflow_client.get_defs()
    assert defs.find_suite("s1") is not None
    # Verify UI was updated
    mock_tree.update_tree.assert_called()
    mock_sb.update_status.assert_called()


@pytest.mark.asyncio
async def test_run_client_command_success(app: Ectop, tmp_path) -> None:
    """Test _run_client_command correctly performs operations on the server."""
    defs_content = "suite s2\n  task t1\nendsuite"
    defs_file = tmp_path / "test_command.def"
    defs_file.write_text(defs_content)
    await app.ecflow_client.load_defs(str(defs_file))

    await app._run_client_command("suspend", "/s2")
    await app.ecflow_client.sync_local()
    defs = await app.ecflow_client.get_defs()
    assert defs.find_suite("s2").is_suspended()

    await app._run_client_command("resume", "/s2")
    await app.ecflow_client.sync_local()
    defs = await app.ecflow_client.get_defs()
    assert not defs.find_suite("s2").is_suspended()
