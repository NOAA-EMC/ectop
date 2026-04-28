from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from ectop.app import Ectop


@pytest.fixture
def mock_app():
    app = Ectop()
    app.ecflow_client = AsyncMock()
    return app


@pytest.mark.asyncio
async def test_edit_script_worker_success(mock_app):
    node_path = "/suite/task"
    content = "test content"
    mock_app.ecflow_client.file.return_value = content

    with (
        patch("tempfile.NamedTemporaryFile") as mock_temp,
        patch.object(mock_app, "_run_editor") as mock_run_editor,
    ):
        mock_file = MagicMock()
        mock_file.name = "/tmp/fake.ecf"
        mock_temp.return_value.__enter__.return_value = mock_file

        await mock_app._edit_script_worker(node_path)

        mock_app.ecflow_client.file.assert_called_with(node_path, "script")
        mock_run_editor.assert_called_with("/tmp/fake.ecf", node_path, content)


@pytest.mark.asyncio
async def test_finish_edit_updates_server(mock_app):
    node_path = "/suite/task"
    old_content = "old content"
    new_content = "new content"
    temp_path = "/tmp/fake.ecf"
    with (
        patch("builtins.open", mock_open(read_data=new_content)),
        patch("os.path.exists", return_value=True),
        patch("os.unlink"),
        patch.object(mock_app, "_prompt_requeue"),
    ):
        await mock_app._finish_edit(temp_path, node_path, old_content)
        mock_app.ecflow_client.alter.assert_called_with(node_path, "change", "script", "", new_content)
