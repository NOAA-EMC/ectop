# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
ecFlow Client Wrapper for ectop.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING

import ecflow

if TYPE_CHECKING:
    from ecflow import Defs


class EcflowClient:
    """
    A wrapper around the ecflow.Client to provide a cleaner API and error handling.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.

    Attributes:
        host: The hostname of the ecFlow server.
        port: The port number of the ecFlow server.
        client: The underlying ecFlow client instance.
    """

    def __init__(self, host: str = "localhost", port: int = 3141) -> None:
        """
        Initialize the EcflowClient.

        Args:
            host: The hostname of the ecFlow server. Defaults to "localhost".
            port: The port number of the ecFlow server. Defaults to 3141.

        Raises:
            RuntimeError: If the ecFlow client cannot be initialized.
        """
        self.host: str = host
        self.port: int = port
        self._lock: threading.Lock = threading.Lock()
        try:
            self.client: ecflow.Client = ecflow.Client(host, port)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to initialize ecFlow client for {host}:{port}: {e}") from e

    async def ping(self) -> None:
        """
        Ping the ecFlow server to check connectivity.

        Raises:
            RuntimeError: If the server is unreachable or the ping fails.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """

        def _ping() -> None:
            # We create a new client instance for thread-safety as per memory
            client = ecflow.Client(self.host, self.port)
            client.ping()

        try:
            await asyncio.to_thread(_ping)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to ping ecFlow server at {self.host}:{self.port}: {e}") from e

    async def sync_local(self) -> None:
        """
        Synchronize the local definition with the server.

        Raises:
            RuntimeError: If synchronization fails.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
            It uses a threading lock to protect the persistent client instance.
        """

        def _sync() -> None:
            # Using the main client here as sync_local affects its internal state
            # which is then retrieved by get_defs.
            # NOTE: If we really want to be thread-safe and use new clients,
            # we'd need to return the Defs from here or handle it differently.
            # For now, let's stick to using the persistent client for stateful operations
            # but wrap it in to_thread and protect it with a lock.
            with self._lock:
                self.client.sync_local()

        try:
            await asyncio.to_thread(_sync)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to sync with ecFlow server: {e}") from e

    async def get_defs(self) -> Defs | None:
        """
        Retrieve the current definitions from the client.

        Returns:
            The ecFlow definitions, or None if not available.

        Raises:
            RuntimeError: If the definitions cannot be retrieved.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
            It uses a threading lock to protect the persistent client instance.
        """

        def _get_defs() -> Defs | None:
            with self._lock:
                return self.client.get_defs()

        try:
            return await asyncio.to_thread(_get_defs)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get definitions from client: {e}") from e

    async def file(self, path: str, file_type: str) -> str:
        """
        Retrieve a file (log, script, job) for a specific node.

        Args:
            path: The absolute path to the node.
            file_type: The type of file to retrieve ('jobout', 'script', 'job').

        Returns:
            The content of the requested file.

        Raises:
            RuntimeError: If the file cannot be retrieved.
        """

        def _get_file() -> str:
            client = ecflow.Client(self.host, self.port)
            return client.get_file(path, file_type)

        try:
            return await asyncio.to_thread(_get_file)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to retrieve {file_type} for {path}: {e}") from e

    async def suspend(self, path: str) -> None:
        """
        Suspend a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be suspended.
        """

        def _suspend() -> None:
            client = ecflow.Client(self.host, self.port)
            client.suspend(path)

        try:
            await asyncio.to_thread(_suspend)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to suspend {path}: {e}") from e

    async def resume(self, path: str) -> None:
        """
        Resume a suspended node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be resumed.
        """

        def _resume() -> None:
            client = ecflow.Client(self.host, self.port)
            client.resume(path)

        try:
            await asyncio.to_thread(_resume)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to resume {path}: {e}") from e

    async def kill(self, path: str) -> None:
        """
        Kill a running task.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be killed.
        """

        def _kill() -> None:
            client = ecflow.Client(self.host, self.port)
            client.kill(path)

        try:
            await asyncio.to_thread(_kill)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to kill {path}: {e}") from e

    async def force_complete(self, path: str) -> None:
        """
        Force a node to the complete state.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node state cannot be forced.
        """

        def _force_complete() -> None:
            # Compatibility fix from memory: use force_state if force_complete is missing
            client = ecflow.Client(self.host, self.port)
            try:
                client.force_complete(path)
            except AttributeError:
                client.force_state(path, ecflow.State.complete)

        try:
            await asyncio.to_thread(_force_complete)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to force complete {path}: {e}") from e

    async def alter(self, path: str, alter_type: str, name: str, value: str = "") -> None:
        """
        Alter a node attribute or variable.

        Args:
            path: The absolute path to the node.
            alter_type: The type of alteration (e.g., 'change', 'add', 'delete').
            name: The name of the attribute or variable.
            value: The new value. Defaults to "".

        Raises:
            RuntimeError: If the alteration fails.
        """

        def _alter() -> None:
            client = ecflow.Client(self.host, self.port)
            client.alter(path, alter_type, name, value)

        try:
            await asyncio.to_thread(_alter)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to alter {path} ({alter_type} {name}={value}): {e}") from e

    async def requeue(self, path: str) -> None:
        """
        Requeue a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be requeued.
        """

        def _requeue() -> None:
            client = ecflow.Client(self.host, self.port)
            client.requeue(path)

        try:
            await asyncio.to_thread(_requeue)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to requeue {path}: {e}") from e

    async def restart_server(self) -> None:
        """
        Restart the ecFlow server (resume from HALTED state).

        Raises:
            RuntimeError: If the server cannot be restarted.
        """

        def _restart() -> None:
            client = ecflow.Client(self.host, self.port)
            client.restart_server()

        try:
            await asyncio.to_thread(_restart)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to restart server: {e}") from e

    async def halt_server(self) -> None:
        """
        Halt the ecFlow server (suspend scheduling).

        Raises:
            RuntimeError: If the server cannot be halted.
        """

        def _halt() -> None:
            client = ecflow.Client(self.host, self.port)
            client.halt_server()

        try:
            await asyncio.to_thread(_halt)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to halt server: {e}") from e

    async def version(self) -> str:
        """
        Retrieve the ecFlow client version.

        Returns:
            The client version string.

        Raises:
            RuntimeError: If the version cannot be retrieved.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
            It uses a threading lock to protect the persistent client instance.
        """

        def _version() -> str:
            with self._lock:
                return str(self.client.version())

        try:
            return await asyncio.to_thread(_version)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get client version: {e}") from e

    async def server_version(self) -> str:
        """
        Retrieve the ecFlow server version.

        Returns:
            The server version string.

        Raises:
            RuntimeError: If the server version cannot be retrieved.
        """

        def _server_version() -> str:
            client = ecflow.Client(self.host, self.port)
            return str(client.server_version())

        try:
            return await asyncio.to_thread(_server_version)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get server version: {e}") from e

    async def load_defs(self, filepath: str) -> None:
        """
        Load an ecFlow definition file to the server.

        Args:
            filepath: The path to the .def file.

        Raises:
            RuntimeError: If the file cannot be loaded.
        """

        def _load() -> None:
            client = ecflow.Client(self.host, self.port)
            client.load(filepath)

        try:
            await asyncio.to_thread(_load)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to load definition file {filepath}: {e}") from e

    async def begin_suite(self, name: str) -> None:
        """
        Begin playback of a suite.

        Args:
            name: The name of the suite to begin.

        Raises:
            RuntimeError: If the suite cannot be started.
        """

        def _begin() -> None:
            client = ecflow.Client(self.host, self.port)
            client.begin_suite(name)

        try:
            await asyncio.to_thread(_begin)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to begin suite {name}: {e}") from e
