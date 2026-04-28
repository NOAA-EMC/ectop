# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
# .. note:: warning: "If you modify features, API, or usage, you MUST update the documentation immediately."
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ectop import Ectop  # noqa: E402


@pytest.mark.asyncio
async def test_app_instantiation():
    """Basic test to check if the App can be instantiated."""
    app = Ectop()
    assert app is not None


@pytest.mark.asyncio
async def test_app_handles_runtime_error():
    """Verify that the app handles a RuntimeError from the client gracefully."""
    # We need to mock the client
    mock_client = AsyncMock()
    mock_client.ping.side_effect = RuntimeError("Mock server error")

    with patch("ectop.app.EcflowClient", return_value=mock_client):
        app = Ectop()
        # Mock call_from_thread to avoid thread-check issues in run_test
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)
        # Mock notify and check it was called instead of inspecting app._notifications
        # which is bypassed by the mock.
        with patch.object(app, "notify") as mock_notify:
            async with app.run_test() as pilot:
                # In on_mount, _initial_connect is called.
                # We wait for any workers to finish
                await pilot.pause()
                # Check notifications in the app
                mock_notify.assert_called()
                args, _ = mock_notify.call_args
                assert "Connection Failed" in args[0]


@pytest.mark.asyncio
async def test_app_actions():
    """Verify that app actions (suspend, resume, etc.) correctly call the client."""
    mock_client = AsyncMock()
    mock_client.get_defs.return_value = MagicMock()
    with patch("ectop.app.EcflowClient", return_value=mock_client):
        app = Ectop()
        # Mock call_from_thread to avoid thread-check issues in run_test
        app.call_from_thread = lambda callback, *args, **kwargs: callback(*args, **kwargs)

        async with app.run_test() as pilot:
            # Mock get_selected_path
            with patch.object(Ectop, "get_selected_path", return_value="/suite/task"):
                # Test Suspend
                app.action_suspend()
                await pilot.pause()
                mock_client.suspend.assert_called_with("/suite/task")

                # Test Resume
                app.action_resume()
                await pilot.pause()
                mock_client.resume.assert_called_with("/suite/task")

                # Test Kill
                app.action_kill()
                await pilot.pause()
                mock_client.kill.assert_called_with("/suite/task")

                # Test Force Complete
                app.action_force()
                await pilot.pause()
                mock_client.force_complete.assert_called_with("/suite/task")
