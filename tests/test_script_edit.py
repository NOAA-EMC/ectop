# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the script editing workflow in ectop.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ectop.app import Ectop


@pytest.fixture
def mock_app():
    """
    Fixture for Ectop app with a mocked EcflowClient.
    """
    with patch("ectop.app.EcflowClient", autospec=True) as mock_client_cls:
        app = Ectop()
        # Mock the instance created by the app
        app.ecflow_client = mock_client_cls.return_value
        # Ensure async methods are AsyncMocks
        app.ecflow_client.file = AsyncMock()
        app.ecflow_client.alter = AsyncMock()
        yield app


@pytest.mark.asyncio
async def test_edit_script_worker_logic(mock_app) -> None:
    """
    Test the edit script worker logic using the pilot driver.

    Returns:
        None
    """
    node_path = "/suite/task"
    content = "test content"
    mock_app.ecflow_client.file.return_value = content

    async with mock_app.run_test():
        # Mock _run_editor to avoid launching a real process
        with patch.object(mock_app, "_run_editor", new_callable=AsyncMock) as mock_run_editor:
            await mock_app._edit_script_worker(node_path)

            # Verify dependencies were called
            mock_app.ecflow_client.file.assert_called_with(node_path, "script")
            mock_run_editor.assert_called_once()
            args, _ = mock_run_editor.call_args
            temp_path = args[0]
            assert os.path.exists(temp_path)
            assert args[1] == node_path
            assert args[2] == content

            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)


@pytest.mark.asyncio
async def test_finish_edit_logic(mock_app) -> None:
    """
    Test the finish edit logic to ensure it updates the server correctly.

    Returns:
        None
    """
    node_path = "/suite/task"
    old_content = "old content"
    new_content = "new content"

    # Use a real temporary file
    fd, temp_path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w") as f:
            f.write(new_content)

        async with mock_app.run_test():
            with patch.object(mock_app, "_prompt_requeue") as mock_prompt:
                await mock_app._finish_edit(temp_path, node_path, old_content)

                mock_app.ecflow_client.alter.assert_called_once_with(node_path, "change", "script", "", new_content)
                mock_prompt.assert_called_once_with(node_path)

                # Verify temp file was deleted by the method
                assert not os.path.exists(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_run_editor_async(tmp_path: Path) -> None:
    """
    Test that _run_editor correctly executes the process asynchronously.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        None
    """
    app = Ectop()
    # We need to ensure ecflow_client is not None or mock its check
    app.ecflow_client = MagicMock()

    temp_file = tmp_path / "test.ecf"
    temp_file.write_text("content")

    # Mock editor that just touches a file to prove it ran
    done_file = tmp_path / "done"
    editor_script = tmp_path / "editor.sh"
    editor_script.write_text(f"#!/bin/sh\ntouch {done_file}")
    editor_script.chmod(0o755)

    with patch.dict(os.environ, {"EDITOR": str(editor_script)}):
        async with app.run_test():
            with patch.object(app, "_finish_edit", new_callable=AsyncMock) as mock_finish:
                await app._run_editor(str(temp_file), "/path", "old")

                assert done_file.exists()
                mock_finish.assert_called_once()
