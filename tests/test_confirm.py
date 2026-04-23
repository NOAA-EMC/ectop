# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for ConfirmModal widget.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from ectop.widgets.modals.confirm import ConfirmModal


def test_confirm_modal_init() -> None:
    """
    Test ConfirmModal initialization.
    """
    callback = MagicMock()
    modal = ConfirmModal("Are you sure?", callback)
    assert modal.message == "Are you sure?"


def test_confirm_modal_confirm() -> None:
    """
    Test confirming the action.
    """
    with patch.object(ConfirmModal, "app", new_callable=PropertyMock) as mock_app_prop:
        callback = MagicMock()
        modal = ConfirmModal("msg", callback)
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app

        modal.action_confirm()
        callback.assert_called_once()


def test_confirm_modal_cancel() -> None:
    """
    Test cancelling the action.
    """
    with patch.object(ConfirmModal, "app", new_callable=PropertyMock) as mock_app_prop:
        callback = MagicMock()
        modal = ConfirmModal("msg", callback)
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app

        modal.action_close()
        callback.assert_not_called()
