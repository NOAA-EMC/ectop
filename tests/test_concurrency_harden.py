# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Concurrency tests for EcflowClient to ensure the threading lock works.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from ectop.client import EcflowClient


@pytest.mark.asyncio
async def test_client_concurrent_sync() -> None:
    """Test that concurrent sync_local calls are serialized by the lock."""
    with patch("ectop.client.ecflow.Client") as mock_client_cls:
        mock_client_instance = mock_client_cls.return_value
        client = EcflowClient()
        client._lock = MagicMock()

        await asyncio.gather(client.sync_local(), client.sync_local(), client.sync_local())

        assert client._lock.__enter__.call_count == 3
        assert client._lock.__exit__.call_count == 3
        assert mock_client_instance.sync_local.call_count == 3


@pytest.mark.asyncio
async def test_client_concurrent_mixed_ops() -> None:
    """Test that different stateful operations are serialized by the same lock."""
    with patch("ectop.client.ecflow.Client") as mock_client_cls:
        mock_client_instance = mock_client_cls.return_value
        client = EcflowClient()
        client._lock = MagicMock()

        await asyncio.gather(client.sync_local(), client.get_defs(), client.version())

        assert client._lock.__enter__.call_count == 3
        assert client._lock.__exit__.call_count == 3

        assert mock_client_instance.sync_local.call_count == 1
        assert mock_client_instance.get_defs.call_count == 1
        assert mock_client_instance.version.call_count == 1
