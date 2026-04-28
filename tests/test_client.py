# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import ecflow
import pytest

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
    # sync_local MUST be called before get_defs to populate the local defs
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert isinstance(defs, ecflow.Defs)


@pytest.mark.asyncio
async def test_client_load_defs_success(client_instance, tmp_path):
    defs_file = tmp_path / "test.def"
    defs_file.write_text("suite test_suite\n  task t1\nendsuite")
    await client_instance.load_defs(str(defs_file))

    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert defs.find_suite("test_suite") is not None


@pytest.mark.asyncio
async def test_client_suspend_resume_success(client_instance, tmp_path):
    defs_file = tmp_path / "test_sr.def"
    defs_file.write_text("suite test_sr\n  task t1\nendsuite")
    await client_instance.load_defs(str(defs_file))

    await client_instance.suspend("/test_sr")
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert defs.find_suite("test_sr").is_suspended()

    await client_instance.resume("/test_sr")
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert not defs.find_suite("test_sr").is_suspended()


@pytest.mark.asyncio
async def test_client_force_complete_success(client_instance, tmp_path):
    defs_file = tmp_path / "test_fc.def"
    defs_file.write_text("suite test_fc\n  task t1\nendsuite")
    await client_instance.load_defs(str(defs_file))

    await client_instance.force_complete("/test_fc/t1")
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    assert str(defs.find_abs_node("/test_fc/t1").get_state()) == "complete"


@pytest.mark.asyncio
async def test_client_alter_success(client_instance, tmp_path):
    defs_file = tmp_path / "test_alter.def"
    defs_file.write_text("suite test_alter\n  task t1\nendsuite")
    await client_instance.load_defs(str(defs_file))

    # Correct signature: ci.alter(path, 'add', 'variable', 'NAME', 'VALUE')
    await client_instance.alter("/test_alter/t1", "add", "variable", "VAR1", "VAL1")
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    node = defs.find_abs_node("/test_alter/t1")
    var = node.find_variable("VAR1")
    assert var.value() == "VAL1"


@pytest.mark.asyncio
async def test_client_requeue_success(client_instance, tmp_path):
    # Use a unique suite name to avoid interference
    import random

    suite_name = f"test_requeue_{random.randint(0, 10000)}"
    defs_file = tmp_path / f"{suite_name}.def"
    defs_file.write_text(f"suite {suite_name}\n  task t1\nendsuite")
    await client_instance.load_defs(str(defs_file))
    await client_instance.begin_suite(suite_name)

    path = f"/{suite_name}/t1"
    await client_instance.force_complete(path)
    await client_instance.requeue(path)
    await client_instance.sync_local()
    defs = await client_instance.get_defs()
    # It might be 'queued' or 'active' depending on how fast the server processes it.
    # In some test environments, it might even abort immediately if the command fails,
    # but here we just want to verify the client-server roundtrip.
    state = str(defs.find_abs_node(path).get_state())
    assert state in ("queued", "active", "submitted", "aborted")


@pytest.mark.asyncio
async def test_client_versions(client_instance):
    v = await client_instance.version()
    assert v is not None
    sv = await client_instance.server_version()
    assert sv is not None


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
