# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import os
import tempfile
import pytest
import ecflow
from ectop.client import EcflowClient

@pytest.mark.asyncio
async def test_client_init(ecflow_server):
    host = ecflow_server["host"]
    port = ecflow_server["port"]
    client = EcflowClient(host, port)
    assert client.host == host
    assert client.port == port

@pytest.mark.asyncio
async def test_client_ping_success(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])
    await client.ping()

@pytest.mark.asyncio
async def test_client_sync_local_success(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])
    await client.sync_local()

@pytest.mark.asyncio
async def test_client_get_defs(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])
    # Must sync to populate local defs
    await client.sync_local()
    defs = await client.get_defs()
    # Using isinstance with ecflow.Defs as per core protocol
    assert isinstance(defs, ecflow.Defs)

@pytest.mark.asyncio
async def test_client_server_version(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])
    version = await client.server_version()
    assert isinstance(version, str)
    assert len(version) > 0

@pytest.mark.asyncio
async def test_client_version(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])
    version = await client.version()
    assert isinstance(version, str)
    assert len(version) > 0

@pytest.mark.asyncio
async def test_client_load_defs_and_begin(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])

    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test.def")
        with open(def_file, "w") as f:
            f.write("suite s1\n  task t1\nendsuite\n")

        await client.load_defs(def_file)
        await client.begin_suite("s1")

        await client.sync_local()
        defs = await client.get_defs()
        assert defs.find_suite("s1") is not None

@pytest.mark.asyncio
async def test_client_force_complete(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])

    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test_force.def")
        with open(def_file, "w") as f:
            f.write("suite s_force\n  task t_force\nendsuite\n")

        await client.load_defs(def_file)
        # We don't necessarily need to begin it to force complete,
        # but let's make sure it exists in defs
        await client.force_complete("/s_force/t_force")

        # Sync to get updated state
        await client.sync_local()
        defs = await client.get_defs()
        node = defs.find_abs_node("/s_force/t_force")
        assert node.get_state() == ecflow.State.complete

@pytest.mark.asyncio
async def test_client_suspend_resume(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])

    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test_sr.def")
        with open(def_file, "w") as f:
            f.write("suite s_sr\n  task t_sr\nendsuite\n")

        await client.load_defs(def_file)
        await client.suspend("/s_sr/t_sr")

        await client.sync_local()
        defs = await client.get_defs()
        node = defs.find_abs_node("/s_sr/t_sr")
        assert node.is_suspended()

        await client.resume("/s_sr/t_sr")
        await client.sync_local()
        defs = await client.get_defs()
        node = defs.find_abs_node("/s_sr/t_sr")
        assert not node.is_suspended()

@pytest.mark.asyncio
async def test_client_requeue(ecflow_server):
    client = EcflowClient(ecflow_server["host"], ecflow_server["port"])

    with tempfile.TemporaryDirectory() as tmp_dir:
        def_file = os.path.join(tmp_dir, "test_requeue.def")
        with open(def_file, "w") as f:
            f.write("suite s_requeue\n  task t_requeue\nendsuite\n")

        await client.load_defs(def_file)
        await client.begin_suite("s_requeue")
        await client.force_complete("/s_requeue/t_requeue")

        await client.sync_local()
        defs = await client.get_defs()
        assert defs.find_abs_node("/s_requeue/t_requeue").get_state() == ecflow.State.complete

        await client.requeue("/s_requeue/t_requeue")
        await client.sync_local()
        defs = await client.get_defs()
        assert defs.find_abs_node("/s_requeue/t_requeue").get_state() == ecflow.State.queued
