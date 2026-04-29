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

    def ping_sync(self) -> None:
        """
        Synchronously ping the ecFlow server.

        Raises:
            RuntimeError: If the server is unreachable or the ping fails.
        """
        with self._lock:
            try:
                self.client.ping()
            except RuntimeError as e:
                raise RuntimeError(f"Failed to ping ecFlow server at {self.host}:{self.port}: {e}") from e

    async def ping(self) -> None:
        """
        Ping the ecFlow server to check connectivity.

        Raises:
            RuntimeError: If the server is unreachable or the ping fails.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.ping_sync)

    def sync_local_sync(self) -> None:
        """
        Synchronously synchronize the local definition with the server.

        Raises:
            RuntimeError: If synchronization fails.
        """
        with self._lock:
            try:
                self.client.sync_local()
            except RuntimeError as e:
                raise RuntimeError(f"Failed to sync with ecFlow server: {e}") from e

    async def sync_local(self) -> None:
        """
        Synchronize the local definition with the server.

        Raises:
            RuntimeError: If synchronization fails.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.sync_local_sync)

    def get_defs_sync(self) -> Defs | None:
        """
        Synchronously retrieve the current definitions from the client.

        Returns:
            The ecFlow definitions, or None if not available.

        Raises:
            RuntimeError: If the definitions cannot be retrieved.
        """
        with self._lock:
            try:
                return self.client.get_defs()
            except RuntimeError as e:
                raise RuntimeError(f"Failed to get definitions from client: {e}") from e

    async def get_defs(self) -> Defs | None:
        """
        Retrieve the current definitions from the client.

        Returns:
            The ecFlow definitions, or None if not available.

        Raises:
            RuntimeError: If the definitions cannot be retrieved.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        return await asyncio.to_thread(self.get_defs_sync)

    def file_sync(self, path: str, file_type: str) -> str:
        """
        Synchronously retrieve a file (log, script, job) for a specific node.

        Args:
            path: The absolute path to the node.
            file_type: The type of file to retrieve ('jobout', 'script', 'job').

        Returns:
            The content of the requested file.

        Raises:
            RuntimeError: If the file cannot be retrieved.
        """
        with self._lock:
            try:
                return self.client.get_file(path, file_type)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to retrieve {file_type} for {path}: {e}") from e

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

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        return await asyncio.to_thread(self.file_sync, path, file_type)

    def suspend_sync(self, path: str) -> None:
        """
        Synchronously suspend a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be suspended.
        """
        with self._lock:
            try:
                self.client.suspend(path)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to suspend {path}: {e}") from e

    async def suspend(self, path: str) -> None:
        """
        Suspend a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be suspended.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.suspend_sync, path)

    def resume_sync(self, path: str) -> None:
        """
        Synchronously resume a suspended node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be resumed.
        """
        with self._lock:
            try:
                self.client.resume(path)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to resume {path}: {e}") from e

    async def resume(self, path: str) -> None:
        """
        Resume a suspended node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be resumed.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.resume_sync, path)

    def kill_sync(self, path: str) -> None:
        """
        Synchronously kill a running task.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be killed.
        """
        with self._lock:
            try:
                self.client.kill(path)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to kill {path}: {e}") from e

    async def kill(self, path: str) -> None:
        """
        Kill a running task.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be killed.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.kill_sync, path)

    def force_complete_sync(self, path: str) -> None:
        """
        Synchronously force a node to the complete state.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node state cannot be forced.
        """
        with self._lock:
            try:
                try:
                    self.client.force_complete(path)
                except AttributeError:
                    self.client.force_state(path, ecflow.State.complete)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to force complete {path}: {e}") from e

    async def force_complete(self, path: str) -> None:
        """
        Force a node to the complete state.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node state cannot be forced.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.force_complete_sync, path)

    def alter_sync(self, path: str, alter_type: str, attr_type: str, name: str = "", value: str | None = None) -> None:
        """
        Synchronously alter a node attribute or variable.

        Args:
            path: The absolute path to the node.
            alter_type: The type of alteration (e.g., 'change', 'add', 'delete').
            attr_type: The type of attribute (e.g., 'variable', 'label').
            name: The name of the attribute or variable.
            value: The new value. Defaults to None.

        Raises:
            RuntimeError: If the alteration fails.
        """
        with self._lock:
            try:
                if value is None:
                    self.client.alter(path, alter_type, attr_type, name)
                else:
                    self.client.alter(path, alter_type, attr_type, name, value)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to alter {path} ({alter_type} {attr_type} {name}={value}): {e}") from e

    async def alter(self, path: str, alter_type: str, attr_type: str, name: str = "", value: str | None = None) -> None:
        """
        Alter a node attribute or variable.

        Args:
            path: The absolute path to the node.
            alter_type: The type of alteration (e.g., 'change', 'add', 'delete').
            attr_type: The type of attribute (e.g., 'variable', 'label').
            name: The name of the attribute or variable.
            value: The new value. Defaults to None.

        Raises:
            RuntimeError: If the alteration fails.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.alter_sync, path, alter_type, attr_type, name, value)

    def requeue_sync(self, path: str) -> None:
        """
        Synchronously requeue a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be requeued.
        """
        with self._lock:
            try:
                self.client.requeue(path)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to requeue {path}: {e}") from e

    async def requeue(self, path: str) -> None:
        """
        Requeue a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be requeued.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.requeue_sync, path)

    def restart_server_sync(self) -> None:
        """
        Synchronously restart the ecFlow server.

        Raises:
            RuntimeError: If the server cannot be restarted.
        """
        with self._lock:
            try:
                self.client.restart_server()
            except RuntimeError as e:
                raise RuntimeError(f"Failed to restart server: {e}") from e

    async def restart_server(self) -> None:
        """
        Restart the ecFlow server (resume from HALTED state).

        Raises:
            RuntimeError: If the server cannot be restarted.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.restart_server_sync)

    def halt_server_sync(self) -> None:
        """
        Synchronously halt the ecFlow server.

        Raises:
            RuntimeError: If the server cannot be halted.
        """
        with self._lock:
            try:
                self.client.halt_server()
            except RuntimeError as e:
                raise RuntimeError(f"Failed to halt server: {e}") from e

    async def halt_server(self) -> None:
        """
        Halt the ecFlow server (suspend scheduling).

        Raises:
            RuntimeError: If the server cannot be halted.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.halt_server_sync)

    def version_sync(self) -> str:
        """
        Synchronously retrieve the ecFlow client version.

        Returns:
            The client version string.

        Raises:
            RuntimeError: If the version cannot be retrieved.
        """
        with self._lock:
            try:
                return str(self.client.version())
            except RuntimeError as e:
                raise RuntimeError(f"Failed to get client version: {e}") from e

    async def version(self) -> str:
        """
        Retrieve the ecFlow client version.

        Returns:
            The client version string.

        Raises:
            RuntimeError: If the version cannot be retrieved.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        return await asyncio.to_thread(self.version_sync)

    def server_version_sync(self) -> str:
        """
        Synchronously retrieve the ecFlow server version.

        Returns:
            The server version string.

        Raises:
            RuntimeError: If the server version cannot be retrieved.
        """
        with self._lock:
            try:
                return str(self.client.server_version())
            except RuntimeError as e:
                raise RuntimeError(f"Failed to get server version: {e}") from e

    async def server_version(self) -> str:
        """
        Retrieve the ecFlow server version.

        Returns:
            The server version string.

        Raises:
            RuntimeError: If the server version cannot be retrieved.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        return await asyncio.to_thread(self.server_version_sync)

    def load_defs_sync(self, filepath: str) -> None:
        """
        Synchronously load an ecFlow definition file to the server.

        Args:
            filepath: The path to the .def file.

        Raises:
            RuntimeError: If the file cannot be loaded.
        """
        with self._lock:
            try:
                self.client.load(filepath)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to load definition file {filepath}: {e}") from e

    async def load_defs(self, filepath: str) -> None:
        """
        Load an ecFlow definition file to the server.

        Args:
            filepath: The path to the .def file.

        Raises:
            RuntimeError: If the file cannot be loaded.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.load_defs_sync, filepath)

    def begin_suite_sync(self, name: str) -> None:
        """
        Synchronously begin playback of a suite.

        Args:
            name: The name of the suite to begin.

        Raises:
            RuntimeError: If the suite cannot be started.
        """
        with self._lock:
            try:
                self.client.begin_suite(name)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to begin suite {name}: {e}") from e

    async def begin_suite(self, name: str) -> None:
        """
        Begin playback of a suite.

        Args:
            name: The name of the suite to begin.

        Raises:
            RuntimeError: If the suite cannot be started.

        Notes:
            This is an async method that runs the blocking call in a separate thread.
        """
        await asyncio.to_thread(self.begin_suite_sync, name)
