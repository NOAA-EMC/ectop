# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import ecflow
import pytest
import os

from ectop.client import EcflowClient


@pytest.mark.asyncio
async def test_client_init(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    assert client.host == host
    assert client.port == port


@pytest.mark.asyncio
async def test_client_ping_success(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    await client.ping()


@pytest.mark.asyncio
async def test_client_ping_failure():
    client = EcflowClient("localhost", 1)
    with pytest.raises(RuntimeError, match="Failed to ping ecFlow server"):
        await client.ping()


@pytest.mark.asyncio
async def test_client_sync_local_success(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    await client.sync_local()


@pytest.mark.asyncio
async def test_client_sync_local_failure():
    client = EcflowClient("localhost", 1)
    with pytest.raises(RuntimeError, match="Failed to sync with ecFlow server"):
        await client.sync_local()


@pytest.mark.asyncio
async def test_client_get_defs(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    await client.sync_local()
    defs = await client.get_defs()
    assert isinstance(defs, ecflow.Defs)


@pytest.mark.asyncio
async def test_client_file_failure(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    with pytest.raises(RuntimeError, match="Failed to retrieve"):
        await client.file("/nonexistent", "script")


@pytest.mark.asyncio
async def test_client_node_operations(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    defs = ecflow.Defs()
    suite = defs.add_suite("test_suite")
    suite.add_task("t1")
    ecf_client = ecflow.Client(host, port)
    ecf_client.load(defs)
    await client.suspend("/test_suite")
    await client.sync_local()
    d = await client.get_defs()
    assert d.find_suite("test_suite").is_suspended()
    await client.resume("/test_suite")
    await client.sync_local()
    d = await client.get_defs()
    assert not d.find_suite("test_suite").is_suspended()
    await client.requeue("/test_suite")
    await client.force_complete("/test_suite/t1")
    await client.sync_local()
    d = await client.get_defs()
    assert d.find_task("/test_suite/t1").get_state() == ecflow.State.complete
    await client.alter("/test_suite", "add", "variable", "FOO", "BAR")
    await client.sync_local()
    d = await client.get_defs()
    assert d.find_suite("test_suite").find_variable("FOO").value() == "BAR"


@pytest.mark.asyncio
async def test_client_server_control(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    await client.halt_server()
    await client.restart_server()


@pytest.mark.asyncio
async def test_client_versions(ecflow_server):
    host, port = ecflow_server
    client = EcflowClient(host, port)
    assert isinstance(await client.version(), str)
    assert isinstance(await client.server_version(), str)
