# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""ecFlow Client Wrapper for ectop.

If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import ecflow

if TYPE_CHECKING:
    from ecflow import Defs


class EcflowClient:
    """A wrapper around the ecflow.Client to provide a cleaner API and error handling.

    If you modify features, API, or usage, you MUST update the documentation immediately.

    Attributes:
        host: The hostname of the ecFlow server.
        port: The port number of the ecFlow server.
        client: The underlying ecFlow client instance.
    """

    def __init__(self, host: str = "localhost", port: int = 3141) -> None:
        """Initialize the EcflowClient.

        Args:
            host: The hostname of the ecFlow server, by default "localhost".
            port: The port number of the ecFlow server, by default 3141.

        Raises:
            RuntimeError: If the ecFlow client cannot be initialized.
        """
        self.host: str = host
        self.port: int = port
        try:
            self.client: ecflow.Client = ecflow.Client(host, port)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to initialize ecFlow client for {host}:{port}: {e}") from e

    async def ping(self) -> None:
        """Ping the ecFlow server to check connectivity.

        Raises:
            RuntimeError: If the server is unreachable or the ping fails.

        Note:
            This is a non-blocking call that uses asyncio.to_thread.
        """
        try:
            await asyncio.to_thread(self.client.ping)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to ping ecFlow server at {self.host}:{self.port}: {e}") from e

    async def sync_local(self) -> None:
        """Synchronize the local definition with the server.

        Raises:
            RuntimeError: If synchronization fails.

        Note:
            This is a non-blocking call that uses asyncio.to_thread.
        """
        try:
            await asyncio.to_thread(self.client.sync_local)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to sync with ecFlow server: {e}") from e

    async def get_defs(self) -> Defs | None:
        """Retrieve the current definitions from the client.

        Returns:
            The ecFlow definitions, or None if not available.

        Raises:
            RuntimeError: If the definitions cannot be retrieved.
        """
        try:
            return await asyncio.to_thread(self.client.get_defs)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get definitions from client: {e}") from e

    async def file(self, path: str, file_type: str) -> str:
        """Retrieve a file (log, script, job) for a specific node.

        Args:
            path: The absolute path to the node.
            file_type: The type of file to retrieve ('jobout', 'script', 'job').

        Returns:
            The content of the requested file.

        Raises:
            RuntimeError: If the file cannot be retrieved.
        """
        try:
            return await asyncio.to_thread(self.client.get_file, path, file_type)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to retrieve {file_type} for {path}: {e}") from e

    async def suspend(self, path: str) -> None:
        """Suspend a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be suspended.
        """
        try:
            await asyncio.to_thread(self.client.suspend, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to suspend {path}: {e}") from e

    async def resume(self, path: str) -> None:
        """Resume a suspended node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be resumed.
        """
        try:
            await asyncio.to_thread(self.client.resume, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to resume {path}: {e}") from e

    async def kill(self, path: str) -> None:
        """Kill a running task.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be killed.
        """
        try:
            await asyncio.to_thread(self.client.kill, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to kill {path}: {e}") from e

    async def force_complete(self, path: str) -> None:
        """Force a node to the complete state.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node state cannot be forced.
        """
        try:
            await asyncio.to_thread(self.client.force_state, path, ecflow.State.complete)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to force complete {path}: {e}") from e

    async def alter(self, path: str, alter_type: str, name: str, value: str = "") -> None:
        """Alter a node attribute or variable.

        Args:
            path: The absolute path to the node.
            alter_type: The type of alteration (e.g., 'change', 'add', 'delete').
            name: The name of the attribute or variable.
            value: The new value, by default "".

        Raises:
            RuntimeError: If the alteration fails.
        """
        try:
            await asyncio.to_thread(self.client.alter, path, alter_type, name, value)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to alter {path} ({alter_type} {name}={value}): {e}") from e

    async def requeue(self, path: str) -> None:
        """Requeue a node.

        Args:
            path: The absolute path to the node.

        Raises:
            RuntimeError: If the node cannot be requeued.
        """
        try:
            await asyncio.to_thread(self.client.requeue, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to requeue {path}: {e}") from e

    async def restart_server(self) -> None:
        """Restart the ecFlow server (resume from HALTED state).

        Raises:
            RuntimeError: If the server cannot be restarted.
        """
        try:
            await asyncio.to_thread(self.client.restart_server)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to restart server: {e}") from e

    async def halt_server(self) -> None:
        """Halt the ecFlow server (suspend scheduling).

        Raises:
            RuntimeError: If the server cannot be halted.
        """
        try:
            await asyncio.to_thread(self.client.halt_server)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to halt server: {e}") from e

    async def version(self) -> str:
        """Retrieve the ecFlow client version.

        Returns:
            The client version string.

        Raises:
            RuntimeError: If the version cannot be retrieved.
        """
        try:
            # Client version is typically local and non-blocking, but keeping it async for consistency
            return str(await asyncio.to_thread(self.client.version))
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get client version: {e}") from e

    async def server_version(self) -> str:
        """Retrieve the ecFlow server version.

        Returns:
            The server version string.

        Raises:
            RuntimeError: If the server version cannot be retrieved.
        """
        try:
            return str(await asyncio.to_thread(self.client.server_version))
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get server version: {e}") from e
