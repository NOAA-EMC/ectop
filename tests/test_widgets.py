# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import MagicMock, PropertyMock, patch

from textual.widgets import RichLog, Static

from ectop.widgets.content import MainContent
from ectop.widgets.modals.confirm import ConfirmModal
from ectop.widgets.search import SearchBox
from ectop.widgets.statusbar import StatusBar


def test_statusbar_update() -> None:
    """Test that the status bar updates its internal state."""
    sb = StatusBar()
    sb.update_status("myhost", 1234, "Connected")
    assert sb.server_info == "myhost:1234"
    assert sb.status == "Connected"
    assert sb.last_sync != "Never"


def test_searchbox_cancel() -> None:
    """Test that SearchBox cancel clears and hides the box."""
    with patch("textual.widgets.Input.app") as mock_app:
        sb = SearchBox()
        sb.value = "some search"
        sb.add_class("visible")

        sb.action_cancel()

        assert sb.value == ""
        assert "visible" not in sb.classes
        mock_app.set_focus.assert_called_once()


def test_confirm_modal() -> None:
    """Test that ConfirmModal calls the callback on confirm."""
    callback = MagicMock()
    with patch("textual.screen.Screen.app") as mock_app:
        modal = ConfirmModal("Are you sure?", callback)

        modal.action_confirm()

        callback.assert_called_once()
        mock_app.pop_screen.assert_called_once()


def test_confirm_modal_close() -> None:
    """Test that ConfirmModal does not call callback on close."""
    callback = MagicMock()
    with patch("textual.screen.Screen.app") as mock_app:
        modal = ConfirmModal("Are you sure?", callback)

        modal.action_close()

        callback.assert_not_called()
        mock_app.pop_screen.assert_called_once()


def test_main_content_updates() -> None:
    """
    Test that MainContent updates its tabs correctly.

    Returns
    -------
    None
    """
    mc = MainContent()
    mock_log = MagicMock(spec=RichLog)
    mock_script = MagicMock(spec=Static)
    mock_job = MagicMock(spec=Static)

    def mock_query_one(selector, *args):
        if selector == "#log_output":
            return mock_log
        if selector == "#view_script":
            return mock_script
        if selector == "#view_job":
            return mock_job
        return MagicMock()

    mc.query_one = MagicMock(side_effect=mock_query_one)

    # Test script update
    mc.update_script("echo hello")
    mock_script.update.assert_called_once()

    # Test job update
    mc.update_job("echo job")
    mock_job.update.assert_called_once()

    # Test show error on Static
    mc.show_error("#view_script", "Error message")
    mock_script.update.assert_called_with("[italic red]Error message[/]")

    # Test show error on RichLog
    mc.show_error("#log_output", "Log error")
    mock_log.write.assert_called_with("[italic red]Log error[/]")


def test_main_content_search_logic() -> None:
    """Test the search match feedback logic in MainContent."""
    mc = MainContent()
    # Use patch.object with PropertyMock for app and active
    with (
        patch.object(MainContent, "app", new_callable=PropertyMock) as mock_app_prop,
        patch.object(MainContent, "active", new_callable=PropertyMock) as mock_active_prop,
    ):
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app

        mc._content_cache = {
            "output": "line 1\nline 2 with match\nline 3 with match",
            "script": "echo hello",
            "job": "echo job",
        }

        # Test match found
        mock_event = MagicMock()
        mock_event.input.id = "content_search"
        mock_event.value = "match"
        mock_active_prop.return_value = "tab_output"

        mc.on_input_submitted(mock_event)
        mock_app.notify.assert_called_with("Found 2 matches for 'match' in Output", severity="information")

        # Test no match found
        mock_app.notify.reset_mock()
        mock_event.value = "missing"
        mc.on_input_submitted(mock_event)
        mock_app.notify.assert_called_with("No matches found for 'missing' in Output", severity="warning")

        # Test search in different tab
        mock_app.notify.reset_mock()
        mock_active_prop.return_value = "tab_script"
        mock_event.value = "hello"
        mc.on_input_submitted(mock_event)
        mock_app.notify.assert_called_with("Found 1 matches for 'hello' in Script", severity="information")


def test_main_content_cache_clearing() -> None:
    """Test that cache is cleared when show_error is called."""
    mc = MainContent()
    mc.query_one = MagicMock()
    mc._content_cache = {"output": "some logs", "script": "some script", "job": "some job"}

    mc.show_error("#log_output", "error")
    assert mc._content_cache["output"] == ""
    assert mc._content_cache["script"] == "some script"

    mc.show_error("#view_script", "error")
    assert mc._content_cache["script"] == ""

    mc.show_error("#view_job", "error")
    assert mc._content_cache["job"] == ""
