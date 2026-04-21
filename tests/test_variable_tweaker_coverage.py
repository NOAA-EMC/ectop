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
