# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from ectop.widgets.modals.variables import VariableTweaker


@pytest.fixture
def mock_client():
    mock = MagicMock()
    # Mock async methods using AsyncMock
    mock.sync_local = AsyncMock()
    mock.get_defs = AsyncMock()
    mock.alter = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_variable_tweaker_logic_node_not_found(mock_client):
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)

        # Setup mock_client for this specific test
        mock_defs = MagicMock()
        mock_defs.find_abs_node.return_value = None
        mock_client.get_defs.return_value = mock_defs

        await tweaker._refresh_vars_logic()
        app_mock.notify.assert_called_with("Node not found", severity="error")


@pytest.mark.asyncio
async def test_variable_tweaker_refresh_logic_success(mock_client):
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)

        # Setup defs and node
        mock_defs = MagicMock()
        mock_node = MagicMock()
        mock_node.variables = []
        mock_node.get_generated_variables.return_value = []
        mock_node.get_parent.return_value = None
        mock_defs.find_abs_node.return_value = mock_node

        mock_client.get_defs.return_value = mock_defs

        with patch.object(tweaker, "_update_table") as mock_update:
            await tweaker._refresh_vars_logic()
            mock_update.assert_called()


@pytest.mark.asyncio
async def test_variable_tweaker_submit_change(mock_client):
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)
        tweaker.selected_var_name = "VAR1"
        tweaker.query_one = MagicMock()
        with patch.object(tweaker, "refresh_vars"):
            await tweaker._submit_variable_logic("VAL1")
            mock_client.alter.assert_called()


@pytest.mark.asyncio
async def test_variable_tweaker_submit_add(mock_client):
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)
        tweaker.query_one = MagicMock()
        with patch.object(tweaker, "refresh_vars"):
            await tweaker._submit_variable_logic("VAR2=VAL2")
            mock_client.alter.assert_called()


@pytest.mark.asyncio
async def test_variable_tweaker_delete_worker(mock_client):
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)
        with patch.object(tweaker, "refresh_vars"):
            await tweaker._delete_variable_logic("VAR1")
            mock_client.alter.assert_called_with("/node", "delete_variable", "VAR1")
