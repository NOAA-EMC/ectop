from __future__ import annotations

import asyncio
import os
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
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
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


def get_free_port() -> int:
    import random

    while True:
        port = random.randint(1024, 49151)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue


@pytest.fixture(scope="session")
def ecflow_server():
    port = get_free_port()
    host = "localhost"
    ecf_home = os.path.abspath("pytest_ecf_home")
    if not os.path.exists(ecf_home):
        os.makedirs(ecf_home)
    env = os.environ.copy()
    env["ECF_PORT"] = str(port)
    env["ECF_HOME"] = ecf_home
    import sys

    ecflow_server_bin = os.path.join(os.path.dirname(sys.executable), "ecflow_server")
    if not os.path.exists(ecflow_server_bin):
        ecflow_server_bin = "ecflow_server"

    server_proc = subprocess.Popen(
        [ecflow_server_bin, "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    import ecflow

    client = ecflow.Client(host, port)
    max_retries = 10
    success = False
    for _i in range(max_retries):
        try:
            client.ping()
            success = True
            break
        except RuntimeError:
            time.sleep(1)

    if not success:
        server_proc.terminate()
        raise RuntimeError(f"Failed to start ecFlow server on port {port}")

    yield host, port

    server_proc.terminate()
    server_proc.wait()
    import shutil

    if os.path.exists(ecf_home):
        shutil.rmtree(ecf_home)
