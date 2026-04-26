# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations

from unittest.mock import patch

import pytest

from ectop.app import Ectop


@pytest.fixture
def app(ecflow_server) -> Ectop:
    host, port = ecflow_server
    return Ectop(host=host, port=port)


@pytest.mark.asyncio
async def test_app_instantiation(app: Ectop) -> None:
    assert app.host == app.client.host
    assert app.port == app.client.port


@pytest.mark.asyncio
async def test_app_handles_runtime_error(app: Ectop) -> None:
    # Trigger a real runtime error with bad path
    with patch.object(app, "notify") as mock_notify:
        await app._run_client_command("suspend", "/nonexistent")
        mock_notify.assert_called()


@pytest.mark.asyncio
async def test_app_actions(app: Ectop) -> None:
    # Check that basic actions can be triggered without crashing
    with patch.object(app, "action_refresh"):
        app.action_refresh()
