# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Test configuration and global fixtures for ectop.
"""

from __future__ import annotations

import os
import random
import shutil
import socket
import subprocess
import time
from collections.abc import Generator

import pytest


def get_free_port() -> int:
    """Find a free port on localhost in the range 1024-49151.

    Returns:
        int: A free port number.
    """
    for _ in range(10):
        port = random.randint(1024, 49151)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Could not find a free port in range 1024-49151")


@pytest.fixture(scope="module")
def ecflow_server() -> Generator[tuple[str, int], None, None]:
    """
    Start a real ecFlow server for integration testing.

    Yields:
        tuple[str, int]: A tuple containing the host and port of the server.
    """
    host = "localhost"
    port = get_free_port()
    ecf_home = os.path.abspath("tests/ecf_home")
    if os.path.exists(ecf_home):
        shutil.rmtree(ecf_home)
    os.makedirs(ecf_home, exist_ok=True)

    # ecFlow server needs a lists file
    lists_file = os.path.join(ecf_home, "ecf.lists")
    with open(lists_file, "w"):
        pass

    env = os.environ.copy()
    env["ECF_HOME"] = ecf_home
    env["ECF_PORT"] = str(port)
    env["ECF_LISTS"] = lists_file

    # Start the server
    process = subprocess.Popen(
        ["ecflow_server", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to start
    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except (TimeoutError, ConnectionRefusedError):
            time.sleep(0.1)
    else:
        # If it failed, grab the output
        stdout, stderr = process.communicate(timeout=2)
        process.terminate()
        raise RuntimeError(f"ecFlow server failed to start on port {port}. STDOUT: {stdout} STDERR: {stderr}")

    yield host, port

    # Shutdown server
    subprocess.run(["ecflow_client", "--halt", "yes", "--port", str(port)], env=env, check=False)
    subprocess.run(["ecflow_client", "--terminate", "yes", "--port", str(port)], env=env, check=False)
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

    if os.path.exists(ecf_home):
        shutil.rmtree(ecf_home)
