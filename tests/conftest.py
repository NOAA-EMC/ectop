# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import asyncio
import os
import random
import socket
import subprocess
import time
from functools import wraps

import pytest
import textual


def mock_work(*args, **kwargs):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            if asyncio.iscoroutine(result):
                # Run the coroutine in the current loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We are already in a loop (pytest-asyncio)
                        # We can't use run_until_complete here.
                        # We return the task and let the test await it if needed,
                        # but most tests don't.
                        return asyncio.create_task(result)
                    else:
                        return loop.run_until_complete(result)
                except RuntimeError:
                    return asyncio.run(result)
            return result

        return wrapper

    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    return decorator


textual.work = mock_work


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
def ecflow_server(tmp_path_factory, free_port):
    """
    Start a real ecFlow server for integration testing.

    Yields:
        str: The host:port string of the running server.
    """
    import ecflow

    ecf_home = tmp_path_factory.mktemp("ecf_home")
    port = free_port
    host = "localhost"

    env = os.environ.copy()
    env["ECF_PORT"] = str(port)
    env["ECF_HOME"] = str(ecf_home)
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
