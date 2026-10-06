# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
from __future__ import annotations

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
    app = Ectop(host=client_instance.host, port=client_instance.port, refresh_interval=60)
    app.ecflow_client = client_instance
    return app


@pytest.mark.asyncio
async def test_action_restart_server(app: Ectop) -> None:
    """Test action_restart_server correctly halts and restarts the server."""
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        worker = app.action_halt_server()
        await worker.wait()
        await app.ecflow_client.sync_local()
        defs = await app.ecflow_client.get_defs()
        assert str(defs.get_server_state()) == "HALTED"

        worker = app.action_restart_server()
        await worker.wait()
        await app.ecflow_client.sync_local()
        defs = await app.ecflow_client.get_defs()
        assert str(defs.get_server_state()) == "RUNNING"


@pytest.mark.asyncio
async def test_action_refresh_logic(app: Ectop, tmp_path) -> None:
    """Test action_refresh correctly updates the app state from the server."""
    defs_content = "suite s1\n  task t1\nendsuite"
    defs_file = tmp_path / "test_refresh.def"
    defs_file.write_text(defs_content)
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        await app.ecflow_client.load_defs(str(defs_file))
        worker = app.action_refresh()
        assert worker is not None
        await worker.wait()
        await pilot.pause(0.1)
        tree = app.query_one("#suite_tree")
        assert tree.snapshot is not None
        assert "/s1/t1" in tree.snapshot.by_path
        assert app.query_one("#status_bar").last_sync != "Never"


@pytest.mark.asyncio
async def test_run_client_command_success(app: Ectop, tmp_path) -> None:
    """Test _run_client_command correctly performs operations on the server."""
    defs_content = "suite s2\n  task t1\nendsuite"
    defs_file = tmp_path / "test_command.def"
    defs_file.write_text(defs_content)
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        await app.ecflow_client.load_defs(str(defs_file))

        worker = app._run_client_command("suspend", "/s2")
        await worker.wait()
        await app.ecflow_client.sync_local()
        defs = await app.ecflow_client.get_defs()
        assert defs.find_suite("s2").is_suspended()

        worker = app._run_client_command("resume", "/s2")
        await worker.wait()
        await app.ecflow_client.sync_local()
        defs = await app.ecflow_client.get_defs()
        assert not defs.find_suite("s2").is_suspended()


@pytest.mark.asyncio
async def test_action_force_aborted(app: Ectop, tmp_path) -> None:
    """Test action_force_aborted correctly marks a node as aborted."""
    suite_name = "test_app_fa"
    defs_file = tmp_path / f"{suite_name}.def"
    defs_file.write_text(f"suite {suite_name}\n  task t1\nendsuite")
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        await app.ecflow_client.load_defs(str(defs_file))
        worker = app._run_client_command("force_aborted", f"/{suite_name}/t1")
        await worker.wait()
        await app.ecflow_client.sync_local()
        defs = await app.ecflow_client.get_defs()
        assert str(defs.find_abs_node(f"/{suite_name}/t1").get_state()) == "aborted"


@pytest.mark.asyncio
async def test_action_run(app: Ectop, tmp_path) -> None:
    """Test action_run correctly executes a node."""
    suite_name = "test_app_run"
    defs_file = tmp_path / f"{suite_name}.def"
    defs_file.write_text(f"suite {suite_name}\n  task t1\nendsuite")
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        await app.ecflow_client.load_defs(str(defs_file))
        await app.ecflow_client.begin_suite(suite_name)
        worker = app._run_client_command("run", f"/{suite_name}/t1")
        await worker.wait()
        await app.ecflow_client.sync_local()
        defs = await app.ecflow_client.get_defs()
        state = str(defs.find_abs_node(f"/{suite_name}/t1").get_state())
        assert state in ("active", "submitted", "complete", "aborted")
