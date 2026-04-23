# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""ecFlow Client Wrapper for ectop."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import ecflow

if TYPE_CHECKING:
    from ecflow import Defs


class EcflowClient:
    """
    A wrapper around the ecflow.Client to provide a cleaner API and error handling.
    """

    def __init__(self, host: str = "localhost", port: int = 3141) -> None:
        """
        Initialize the EcflowClient.

        Parameters
        ----------
        host : str
            The hostname of the ecFlow server.
        port : int
            The port of the ecFlow server.
        """
        self.host: str = host
        self.port: int = port

    def _get_client(self) -> ecflow.Client:
        """
        Create a new ecflow.Client instance.

        Returns
        -------
        ecflow.Client
            A new ecflow client instance.
        """
        return ecflow.Client(self.host, self.port)

    async def ping(self) -> None:
        """
        Ping the ecFlow server.

        Raises
        ------
        RuntimeError
            If the ping fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.ping)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to ping ecFlow server at {self.host}:{self.port}: {e}") from e

    async def sync_local(self) -> None:
        """
        Synchronize definition.

        Raises
        ------
        RuntimeError
            If synchronization fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.sync_local)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to sync with ecFlow server: {e}") from e

    async def get_defs(self) -> Defs | None:
        """
        Retrieve definitions.

        Returns
        -------
        Defs | None
            The ecFlow definitions or None if unavailable.

        Raises
        ------
        RuntimeError
            If retrieval fails.
        """
        try:
            client = self._get_client()
            return await asyncio.to_thread(client.get_defs)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get definitions from client: {e}") from e

    async def file(self, path: str, file_type: str) -> str:
        """
        Retrieve a file.

        Parameters
        ----------
        path : str
            Absolute path to the node.
        file_type : str
            Type of file (e.g., 'jobout', 'script', 'job').

        Returns
        -------
        str
            The content of the file.

        Raises
        ------
        RuntimeError
            If retrieval fails.
        """
        try:
            client = self._get_client()
            return await asyncio.to_thread(client.get_file, path, file_type)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to retrieve {file_type} for {path}: {e}") from e

    async def suspend(self, path: str) -> None:
        """
        Suspend a node.

        Parameters
        ----------
        path : str
            Absolute path to the node.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.suspend, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to suspend {path}: {e}") from e

    async def resume(self, path: str) -> None:
        """
        Resume a node.

        Parameters
        ----------
        path : str
            Absolute path to the node.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.resume, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to resume {path}: {e}") from e

    async def kill(self, path: str) -> None:
        """
        Kill a task.

        Parameters
        ----------
        path : str
            Absolute path to the node.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.kill, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to kill {path}: {e}") from e

    async def force_complete(self, path: str) -> None:
        """
        Force complete a node.

        Parameters
        ----------
        path : str
            Absolute path to the node.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.force_state, path, ecflow.State.complete)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to force complete {path}: {e}") from e

    async def alter(self, path: str, alter_type: str, name: str, value: str = "") -> None:
        """
        Alter a node attribute.

        Parameters
        ----------
        path : str
            Absolute path to the node.
        alter_type : str
            Type of alteration.
        name : str
            Name of the attribute.
        value : str
            New value.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.alter, path, alter_type, name, value)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to alter {path} ({alter_type} {name}={value}): {e}") from e

    async def requeue(self, path: str) -> None:
        """
        Requeue a node.

        Parameters
        ----------
        path : str
            Absolute path to the node.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.requeue, path)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to requeue {path}: {e}") from e

    async def restart_server(self) -> None:
        """
        Restart the ecFlow server scheduling.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.restart_server)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to restart server: {e}") from e

    async def halt_server(self) -> None:
        """
        Halt the ecFlow server scheduling.

        Raises
        ------
        RuntimeError
            If the operation fails.
        """
        try:
            client = self._get_client()
            await asyncio.to_thread(client.halt_server)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to halt server: {e}") from e

    async def version(self) -> str:
        """
        Get the client version.

        Returns
        -------
        str
            The ecFlow client version.

        Raises
        ------
        RuntimeError
            If retrieval fails.
        """
        try:
            client = self._get_client()
            return str(await asyncio.to_thread(client.version))
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get client version: {e}") from e

    async def server_version(self) -> str:
        """
        Get the server version.

        Returns
        -------
        str
            The ecFlow server version.

        Raises
        ------
        RuntimeError
            If retrieval fails.
        """
        try:
            client = self._get_client()
            return str(await asyncio.to_thread(client.server_version))
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get server version: {e}") from e
