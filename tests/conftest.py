# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
import os
import random
import socket
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def free_port():
    """Find a free port on localhost in the range allowed by ecFlow."""
    # ecFlow requires 1024-49151
    while True:
        port = random.randint(1024, 49151)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue


@pytest.fixture(scope="session")
def ecflow_home(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create an isolated home directory for the real test server.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Factory for session-scoped temporary directories.

    Returns
    -------
    Path
        The isolated ecFlow server home directory.
    """
    return tmp_path_factory.mktemp("ecf_home")


@pytest.fixture(scope="session")
def ecflow_files(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create the script-search directory used by the real test server.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Factory for session-scoped temporary directories.

    Returns
    -------
    Path
        The server's ecFlow script-search directory.
    """
    path = tmp_path_factory.mktemp("ecf_files")
    return path


@pytest.fixture(scope="session")
def ecflow_server(ecflow_home: Path, ecflow_files: Path, free_port: int) -> str:
    """
    Start a real ecFlow server for integration testing.

    Yields:
        str: The host:port string of the running server.
    """
    import ecflow

    port = free_port
    host = "localhost"

    env = os.environ.copy()
    env["ECF_PORT"] = str(port)
    env["ECF_HOME"] = str(ecflow_home)
    env["ECF_FILES"] = str(ecflow_files)
    # Ensure it doesn't try to use any existing lists or config
    env["ECF_LISTS"] = ""

    # Start server
    proc = subprocess.Popen(
        ["ecflow_server", "--port", str(port)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    # Wait for server to start
    client = ecflow.Client(host, port)
    retries = 30
    connected = False
    while retries > 0:
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            raise RuntimeError(f"ecflow_server died on port {port}\nSTDOUT: {stdout}\nSTDERR: {stderr}") from None
        try:
            client.ping()
            connected = True
            break
        except RuntimeError:
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                raise RuntimeError(f"ecflow_server died on port {port}\nSTDOUT: {stdout}\nSTDERR: {stderr}") from None
            time.sleep(1)
            retries -= 1

    if not connected:
        proc.kill()
        stdout, stderr = proc.communicate()
        raise RuntimeError(f"Failed to start ecFlow server on port {port}\nSTDOUT: {stdout}\nSTDERR: {stderr}")

    yield f"{host}:{port}"

    # Shutdown
    try:
        # Halt and terminate via client to be graceful
        client.halt_server()
        client.terminate_server()
    except Exception:
        # Best effort shutdown
        pass

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
