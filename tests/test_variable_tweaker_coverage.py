# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from ectop.widgets.modals.variables import VariableTweaker


@pytest.fixture
def mock_client():
    """Fixture to provide a mocked EcflowClient for variable tweaker tests."""
    client = AsyncMock()
    # Ensure get_defs returns a synchronous mock (not a coroutine)
    client.get_defs.return_value = MagicMock()
    return client


@pytest.mark.asyncio
async def test_variable_tweaker_logic_node_not_found(mock_client):
    """Test variable tweaker handles node not found error."""
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)
        mock_client.get_defs.return_value.find_abs_node.return_value = None
        await tweaker._refresh_vars_logic()
        app_mock.notify.assert_called()


@pytest.mark.asyncio
async def test_variable_tweaker_refresh_logic_success(mock_client):
    """Test variable tweaker successfully refreshes variables."""
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

        mock_client.get_defs.return_value = mock_defs
        mock_defs.find_abs_node.return_value = mock_node

        with patch.object(tweaker, "_update_table") as mock_update:
            await tweaker._refresh_vars_logic()
            mock_update.assert_called()


@pytest.mark.asyncio
async def test_variable_tweaker_submit_change(mock_client):
    """Test variable tweaker successfully submits a variable change."""
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)
        tweaker.selected_var_name = "VAR1"
        tweaker.query_one = MagicMock()
        with patch.object(tweaker, "refresh_vars", new_callable=MagicMock):
            await tweaker._submit_variable_logic("VAL1")
            mock_client.alter.assert_called_with("/node", "add", "variable", "VAR1", "VAL1")


@pytest.mark.asyncio
async def test_variable_tweaker_submit_add(mock_client):
    """Test variable tweaker successfully adds a new variable."""
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)
        tweaker.query_one = MagicMock()
        with patch.object(tweaker, "refresh_vars", new_callable=MagicMock):
            await tweaker._submit_variable_logic("VAR2=VAL2")
            mock_client.alter.assert_called_with("/node", "add", "variable", "VAR2", "VAL2")


@pytest.mark.asyncio
async def test_variable_tweaker_delete_worker(mock_client):
    """Test variable tweaker successfully deletes a variable."""
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        tweaker = VariableTweaker("/node", mock_client)
        with patch.object(tweaker, "refresh_vars", new_callable=MagicMock):
            await tweaker._delete_variable_logic("VAR1")
            mock_client.alter.assert_called_with("/node", "delete", "variable", "VAR1")
