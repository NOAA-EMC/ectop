# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""Tests for the EcflowClient class using real ecflow objects and server."""

import os
import socket
import subprocess
import time
from collections.abc import Generator

import ecflow
import pytest

from ectop.client import EcflowClient


def get_free_port() -> int:
    """Get a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def ecflow_server() -> Generator[tuple[str, int], None, None]:
    """Fixture to start and stop an ecFlow server."""
    port = get_free_port()
    host = "localhost"

    # ecFlow server needs ECF_HOME to be set
    ecf_home = f"/tmp/ectop_test_server_{port}"
    os.makedirs(ecf_home, exist_ok=True)

    env = os.environ.copy()
    env["ECF_PORT"] = str(port)
    env["ECF_HOME"] = ecf_home
    # Disable authentication for testing
    open(os.path.join(ecf_home, f"localhost.{port}.ecf.lists"), "w").close()

    # Start the server
    process = subprocess.Popen(
        ["ecflow_server", "--port", str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Wait for server to be ready
    client = ecflow.Client(host, port)
    max_retries = 20
    for i in range(max_retries):
        try:
            client.ping()
            break
        except RuntimeError:
            if i == max_retries - 1:
                process.terminate()
                pytest.fail("Failed to start ecFlow server for testing")
            time.sleep(0.5)

    yield host, port

    # Shutdown server
    try:
        client.terminate_server()
    except RuntimeError:
        process.terminate()
    process.wait(timeout=5)


@pytest.mark.asyncio
async def test_client_init():
    """Test EcflowClient initialization with real ecflow.Client."""
    client = EcflowClient("localhost", 3141)
    assert client.host == "localhost"
    assert client.port == 3141
    assert isinstance(client.client, ecflow.Client)


@pytest.mark.asyncio
async def test_client_ping_failure():
    """Test ping failure when no server is running on a specific port."""
    # Using a likely unused port
    client = EcflowClient("localhost", 1024)
    with pytest.raises(RuntimeError, match="Failed to ping ecFlow server"):
        await client.ping()


@pytest.mark.asyncio
async def test_client_server_interaction(ecflow_server):
    """Test real interaction with a running ecFlow server."""
    host, port = ecflow_server
    client = EcflowClient(host, port)

    # Test ping
    await client.ping()

    # Test version
    v = await client.version()
    assert isinstance(v, str)

    sv = await client.server_version()
    assert isinstance(sv, str)

    # Test Defs interaction
    await client.sync_local()
    defs = await client.get_defs()
    assert defs is not None
    assert len(list(defs.suites)) == 0

    # Add a suite via the underlying client to test retrieval
    new_defs = ecflow.Defs()
    new_defs.add_suite("test_suite")
    client.client.load(new_defs)

    await client.sync_local()
    defs = await client.get_defs()
    assert defs is not None
    suites = list(defs.suites)
    assert len(suites) == 1
    assert suites[0].name() == "test_suite"


@pytest.mark.asyncio
async def test_client_node_ops_failure(ecflow_server):
    """Test node operations failure on non-existent paths."""
    host, port = ecflow_server
    client = EcflowClient(host, port)

    with pytest.raises(RuntimeError, match="Failed to suspend /nonexistent"):
        await client.suspend("/nonexistent")

    with pytest.raises(RuntimeError, match="Failed to resume /nonexistent"):
        await client.resume("/nonexistent")

    with pytest.raises(RuntimeError, match="Failed to kill /nonexistent"):
        await client.kill("/nonexistent")

    with pytest.raises(RuntimeError, match="Failed to force complete /nonexistent"):
        await client.force_complete("/nonexistent")


@pytest.mark.asyncio
async def test_client_alter_failure(ecflow_server):
    """Test alter failure on non-existent node."""
    host, port = ecflow_server
    client = EcflowClient(host, port)

    with pytest.raises(RuntimeError, match="Failed to alter /nonexistent"):
        await client.alter("/nonexistent", "change", "variable", "value")


@pytest.mark.asyncio
async def test_client_requeue_failure(ecflow_server):
    """Test requeue failure on non-existent node."""
    host, port = ecflow_server
    client = EcflowClient(host, port)

    with pytest.raises(RuntimeError, match="Failed to requeue /nonexistent"):
        await client.requeue("/nonexistent")


@pytest.mark.asyncio
async def test_client_server_control(ecflow_server):
    """Test server restart/halt (just call them, we're not verifying state here)."""
    host, port = ecflow_server
    client = EcflowClient(host, port)

    await client.restart_server()
    await client.halt_server()
    # Resume it for other tests if they use the same module scope
    await client.restart_server()
