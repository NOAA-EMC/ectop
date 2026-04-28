# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import os
import tempfile
import pytest
import ecflow
import uuid
from ectop.client import EcflowClient

@pytest.fixture
def client_instance(ecflow_server):
    host, port = ecflow_server.split(":")
    return EcflowClient(host, int(port))

@pytest.mark.asyncio
async def test_client_init(ecflow_server):
    host, port = ecflow_server.split(":")
    client = EcflowClient(host, int(port))
    assert client.host == host
    assert client.port == int(port)

@pytest.mark.asyncio
async def test_client_ping_success(client_instance):
    await client_instance.ping()

@pytest.mark.asyncio
async def test_client_sync_local_success(client_instance):
    await client_instance.sync_local()

@pytest.mark.asyncio
async def test_client_get_defs(client_instance):
    # Must sync to populate local defs
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert isinstance(defs, ecflow.Defs)

@pytest.mark.asyncio
async def test_client_server_version(client_instance):
    version = await client_instance.server_version()
    assert isinstance(version, str)
    assert len(version) > 0

@pytest.mark.asyncio
async def test_client_version(client_instance):
    version = await client_instance.version()
    assert isinstance(version, str)
    assert len(version) > 0

@pytest.mark.asyncio
async def test_client_load_defs_and_begin(client_instance):
    suite_name = f"s_{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test.def")
        with open(def_file, "w") as f:
            f.write(f"suite {suite_name}\n  task t1\nendsuite\n")

        await client_instance.load_defs(def_file)
        await client_instance.begin_suite(suite_name)

        await client_instance.sync_local()
        defs = await client_instance.get_defs()
        assert defs.find_suite(suite_name) is not None

@pytest.mark.asyncio
async def test_client_force_complete(client_instance):
    suite_name = f"s_{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test_force.def")
        with open(def_file, "w") as f:
            f.write(f"suite {suite_name}\n  task t_force\nendsuite\n")

        await client_instance.load_defs(def_file)
        await client_instance.force_complete(f"/{suite_name}/t_force")

        await client_instance.sync_local()
        defs = await client_instance.get_defs()
        node = defs.find_abs_node(f"/{suite_name}/t_force")
        assert node.get_state() == ecflow.State.complete

@pytest.mark.asyncio
async def test_client_suspend_resume(client_instance):
    suite_name = f"s_{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test_sr.def")
        with open(def_file, "w") as f:
            f.write(f"suite {suite_name}\n  task t_sr\nendsuite\n")

        await client_instance.load_defs(def_file)
        await client_instance.suspend(f"/{suite_name}/t_sr")

        await client_instance.sync_local()
        defs = await client_instance.get_defs()
        node = defs.find_abs_node(f"/{suite_name}/t_sr")
        assert node.is_suspended()

        await client_instance.resume(f"/{suite_name}/t_sr")
        await client_instance.sync_local()
        defs = await client_instance.get_defs()
        node = defs.find_abs_node(f"/{suite_name}/t_sr")
        assert not node.is_suspended()

@pytest.mark.asyncio
async def test_client_requeue(client_instance):
    suite_name = f"s_{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test_requeue.def")
        with open(def_file, "w") as f:
            f.write(f"suite {suite_name}\n  task t_requeue\nendsuite\n")

        await client_instance.load_defs(def_file)
        await client_instance.begin_suite(suite_name)
        await client_instance.force_complete(f"/{suite_name}/t_requeue")

        await client_instance.sync_local()
        defs = await client_instance.get_defs()
        assert defs.find_abs_node(f"/{suite_name}/t_requeue").get_state() == ecflow.State.complete

        await client_instance.requeue(f"/{suite_name}/t_requeue")
        await client_instance.sync_local()
        defs = await client_instance.get_defs()
        assert defs.find_abs_node(f"/{suite_name}/t_requeue").get_state() == ecflow.State.queued

@pytest.mark.asyncio
async def test_client_server_control(client_instance):
    # Halt and restart
    await client_instance.halt_server()
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert str(defs.get_server_state()) == "HALTED"

    await client_instance.restart_server()
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert str(defs.get_server_state()) == "RUNNING"
