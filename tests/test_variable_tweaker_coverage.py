# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Comprehensive tests for VariableTweaker coverage.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from ectop.widgets.modals.variables import VariableTweaker


@pytest.fixture
def mock_client() -> MagicMock:
    """
    Create a mock EcflowClient.

    Returns
    -------
    MagicMock
        A mock EcflowClient object.
    """
    return MagicMock()


def test_variable_tweaker_logic_node_not_found(mock_client: MagicMock) -> None:
    """
    Test _refresh_vars_logic when the node is not found.

    Parameters
    ----------
    mock_client : MagicMock
        The mock EcflowClient.
    """
    tweaker = VariableTweaker("/non/existent", mock_client)
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        app_mock.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)

        mock_client.get_defs.return_value.find_abs_node.return_value = None

        tweaker._refresh_vars_logic()
        app_mock.notify.assert_called_with("Node not found", severity="error")


def test_variable_tweaker_submit_invalid_format(mock_client: MagicMock) -> None:
    """
    Test _submit_variable_logic with an invalid 'name=value' format.

    Parameters
    ----------
    mock_client : MagicMock
        The mock EcflowClient.
    """
    tweaker = VariableTweaker("/node", mock_client)
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        app_mock.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)

        tweaker._submit_variable_logic("invalid_format")
        app_mock.notify.assert_called_with("Use name=value format to add", severity="warning")


def test_variable_tweaker_delete_inherited(mock_client: MagicMock) -> None:
    """
    Test _delete_variable_logic when trying to delete an inherited variable.

    Parameters
    ----------
    mock_client : MagicMock
        The mock EcflowClient.
    """
    tweaker = VariableTweaker("/node", mock_client)
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        app_mock.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)

        tweaker._delete_variable_logic("inh_PARENT_VAR")
        app_mock.notify.assert_called_with("Cannot delete inherited variables", severity="error")


def test_variable_tweaker_unexpected_error(mock_client: MagicMock) -> None:
    """
    Test unexpected error handling in _refresh_vars_logic.

    Parameters
    ----------
    mock_client : MagicMock
        The mock EcflowClient.
    """
    tweaker = VariableTweaker("/node", mock_client)
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        app_mock.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)

        mock_client.sync_local.side_effect = Exception("Unexpected")

        tweaker._refresh_vars_logic()
        app_mock.notify.assert_called_with("Unexpected Error: Unexpected", severity="error")


def test_variable_tweaker_refresh_logic_success(mock_client: MagicMock) -> None:
    """Test _refresh_vars_logic with node and variables."""
    tweaker = VariableTweaker("/node", mock_client)
    with (
        patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app,
        patch.object(tweaker, "_update_table") as mock_update,
    ):
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        app_mock.call_from_thread = lambda f, *args, **kwargs: f(*args, **kwargs)

        mock_node = MagicMock()
        mock_node.name.return_value = "node"
        mock_node.get_parent.return_value = None

        var1 = MagicMock()
        var1.name.return_value = "VAR1"
        var1.value.return_value = "VAL1"
        mock_node.variables = [var1]

        gen_var = MagicMock()
        gen_var.name.return_value = "GEN_VAR"
        gen_var.value.return_value = "GEN_VAL"
        mock_node.get_generated_variables.return_value = [gen_var]

        mock_client.get_defs.return_value.find_abs_node.return_value = mock_node

        tweaker._refresh_vars_logic()
        mock_update.assert_called_once()
        rows = mock_update.call_args[0][0]
        assert len(rows) == 2
        assert rows[0][0] == "VAR1"
        assert rows[1][0] == "GEN_VAR"


def test_variable_tweaker_submit_change(mock_client: MagicMock) -> None:
    """Test _submit_variable_logic with existing variable (change)."""
    tweaker = VariableTweaker("/node", mock_client)
    tweaker.selected_var_name = "VAR1"
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        # Capture call_from_thread calls
        mock_call = MagicMock()
        app_mock.call_from_thread = mock_call

        with patch.object(tweaker, "refresh_vars"):
            tweaker._submit_variable_logic("VAL2")
            mock_client.alter.assert_called_with("/node", "add_variable", "VAR1", "VAL2")
            # We used call_from_thread(self.refresh_vars)
            mock_call.assert_any_call(tweaker.refresh_vars)


def test_variable_tweaker_submit_add(mock_client: MagicMock) -> None:
    """Test _submit_variable_logic with new variable (add)."""
    tweaker = VariableTweaker("/node", mock_client)
    tweaker.selected_var_name = None
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        # Capture call_from_thread calls
        mock_call = MagicMock()
        app_mock.call_from_thread = mock_call

        with patch.object(tweaker, "refresh_vars"):
            tweaker._submit_variable_logic("NEW_VAR=NEW_VAL")
            mock_client.alter.assert_called_with("/node", "add_variable", "NEW_VAR", "NEW_VAL")
            # We used call_from_thread(self.refresh_vars)
            mock_call.assert_any_call(tweaker.refresh_vars)


def test_variable_tweaker_delete_worker(mock_client: MagicMock) -> None:
    """Test _delete_variable_logic success."""
    tweaker = VariableTweaker("/node", mock_client)
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        app_mock = MagicMock()
        mock_app.return_value = app_mock
        # Capture call_from_thread calls
        mock_call = MagicMock()
        app_mock.call_from_thread = mock_call

        with patch.object(tweaker, "refresh_vars"):
            tweaker._delete_variable_logic("VAR_TO_DELETE")
            mock_client.alter.assert_called_with("/node", "delete_variable", "VAR_TO_DELETE")
            # We used call_from_thread(self.refresh_vars)
            mock_call.assert_any_call(tweaker.refresh_vars)
