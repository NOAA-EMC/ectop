import asyncio
import os
import shutil
import socket
import subprocess
import tempfile
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


def get_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def ecflow_server():
    """
    Fixture to start a real ecFlow server for integration testing.
    """
    ecflow_server_bin = shutil.which("ecflow_server")
    if not ecflow_server_bin:
        pytest.skip("ecflow_server binary not found")

    port = get_free_port()
    # Ensure it's in the allowed range 1024-49151
    if not (1024 <= port <= 49151):
        # If not, just try 3141 or another free one.
        # This is rare but possible.
        port = 3141
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
        except OSError:
            # Fallback to a simple loop if needed, but get_free_port usually works fine
            pass

    tmp_dir = tempfile.mkdtemp()
    env = os.environ.copy()
    env["ECF_PORT"] = str(port)
    env["ECF_HOME"] = tmp_dir
    env["LANG"] = "C"
    env["ECF_LISTS"] = ""

    # Start server
    process = subprocess.Popen(
        [ecflow_server_bin, f"--port={port}"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server to be ready
    try:
        import ecflow
    except ImportError:
        process.terminate()
        process.wait()
        shutil.rmtree(tmp_dir)
        pytest.skip("ecflow python module not found")

    client = ecflow.Client("localhost", port)
    max_retries = 30
    connected = False
    for _ in range(max_retries):
        try:
            client.ping()
            connected = True
            break
        except RuntimeError:
            if process.poll() is not None:
                break
            time.sleep(0.5)

    if not connected:
        process.terminate()
        process.wait()
        shutil.rmtree(tmp_dir)
        raise RuntimeError(f"ecflow_server failed to start on port {port}")

    yield f"localhost:{port}"

    # Shutdown
    try:
        client.halt_server()
        client.terminate_server()
    except Exception:
        pass

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

    shutil.rmtree(tmp_dir)
