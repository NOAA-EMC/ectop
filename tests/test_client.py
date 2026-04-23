# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the EcflowClient wrapper.
"""

from __future__ import annotations

import ecflow
import pytest

from ectop.client import EcflowClient


@pytest.mark.asyncio
async def test_client_init() -> None:
    """
    Test EcflowClient initialization.
    """
    client = EcflowClient("localhost", 3141)
    assert client.host == "localhost"
    assert client.port == 3141


@pytest.mark.asyncio
async def test_client_ping_integration(ecflow_server: tuple[str, int]) -> None:
    """
    Test pinging a real ecFlow server.

    Parameters
    ----------
    ecflow_server : tuple[str, int]
        The host and port of the test server.
    """
    host, port = ecflow_server
    client = EcflowClient(host, port)
    await client.ping()


@pytest.mark.asyncio
async def test_client_sync_and_get_defs_integration(ecflow_server: tuple[str, int]) -> None:
    """
    Test syncing and retrieving definitions from a real server.

    Parameters
    ----------
    ecflow_server : tuple[str, int]
        The host and port of the test server.
    """
    host, port = ecflow_server

    # Load a dummy suite using a raw ecflow client
    defs = ecflow.Defs()
    suite = defs.add_suite("test_suite")
    suite.add_task("task1")

    raw_client = ecflow.Client(host, port)
    raw_client.load(defs)

    raw_client.sync_local()
    server_defs = raw_client.get_defs()
    assert server_defs is not None
    assert any(s.name() == "test_suite" for s in server_defs.suites)


@pytest.mark.asyncio
async def test_client_file_retrieval_integration(ecflow_server: tuple[str, int]) -> None:
    """
    Test retrieving a file (script) from a real server.

    Parameters
    ----------
    ecflow_server : tuple[str, int]
        The host and port of the test server.
    """
    host, port = ecflow_server
    client = EcflowClient(host, port)

    defs = ecflow.Defs()
    suite = defs.add_suite("file_suite")
    suite.add_task("task1")

    raw_client = ecflow.Client(host, port)
    raw_client.load(defs)

    with pytest.raises(RuntimeError, match="Failed to retrieve"):
        await client.file("/file_suite/task1", "script")


@pytest.mark.asyncio
async def test_client_version_integration(ecflow_server: tuple[str, int]) -> None:
    """
    Test getting version information from a real server.

    Parameters
    ----------
    ecflow_server : tuple[str, int]
        The host and port of the test server.
    """
    host, port = ecflow_server
    client = EcflowClient(host, port)

    version = await client.version()
    assert isinstance(version, str)
    assert len(version) > 0

    s_version = await client.server_version()
    assert isinstance(s_version, str)
    assert len(s_version) > 0
