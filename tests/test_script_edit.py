# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations
import os
from unittest.mock import MagicMock, patch
import pytest
import ecflow
from ectop.app import Ectop

@pytest.fixture
def app(ecflow_server):
    host, port = ecflow_server
    return Ectop(host=host, port=port)

@pytest.mark.asyncio
async def test_action_edit_script_no_selection(app):
    with patch.object(app, "get_selected_path", return_value=None), patch.object(app, "notify") as mock_notify:
        await app.action_edit_script()
        mock_notify.assert_called_with("No node selected", severity="warning")

@pytest.mark.asyncio
async def test_action_edit_script_failure(app):
    defs = ecflow.Defs()
    defs.add_suite("s").add_task("t")
    c = ecflow.Client(app.client.host, app.client.port)
    c.load(defs)
    with patch.object(app, "get_selected_path", return_value="/s/t"), patch.object(app, "notify") as mock_notify:
        await app.action_edit_script()
        mock_notify.assert_called()
        args, _ = mock_notify.call_args
        assert "Error" in args[0]
