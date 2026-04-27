# .. note:: warning: "If you modify features, API, or usage, you MUST update the documentation immediately."
from unittest.mock import MagicMock, patch

import pytest

from ectop.client import EcflowClient  # noqa: E402


@pytest.mark.asyncio
async def test_client_init():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient("myhost", 1234)
        mock_client.assert_called_with("myhost", 1234)
        assert client.host == "myhost"
        assert client.port == 1234


@pytest.mark.asyncio
async def test_client_init_failure():
    with patch("ectop.client.ecflow.Client", side_effect=RuntimeError("Init failed")):
        with pytest.raises(RuntimeError, match="Failed to initialize ecFlow client"):
            EcflowClient("badhost", 1234)


@pytest.mark.asyncio
async def test_client_ping_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.ping()
        # Since we use a persistent client instance, we check if only one Client was created
        assert mock_client.call_count == 1
        # And if ping was called on that instance
        mock_client.return_value.ping.assert_called_once()


@pytest.mark.asyncio
async def test_client_ping_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.ping.side_effect = RuntimeError("Connection refused")
        with pytest.raises(RuntimeError, match="Failed to ping ecFlow server"):
            await client.ping()


@pytest.mark.asyncio
async def test_client_sync_local_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.sync_local()
        # sync_local uses the main client instance
        mock_client.return_value.sync_local.assert_called_once()


@pytest.mark.asyncio
async def test_client_sync_local_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.sync_local.side_effect = RuntimeError("Sync error")
        with pytest.raises(RuntimeError, match="Failed to sync with ecFlow server"):
            await client.sync_local()


@pytest.mark.asyncio
async def test_client_get_defs():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_defs = MagicMock()
        mock_client.return_value.get_defs.return_value = mock_defs
        assert await client.get_defs() == mock_defs


@pytest.mark.asyncio
async def test_client_file_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.get_file.return_value = "file content"
        assert await client.file("/path", "jobout") == "file content"
        mock_client.return_value.get_file.assert_called_with("/path", "jobout")


@pytest.mark.asyncio
async def test_client_file_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.get_file.side_effect = RuntimeError("File not found")
        with pytest.raises(RuntimeError, match="Failed to retrieve jobout for /path"):
            await client.file("/path", "jobout")


@pytest.mark.asyncio
async def test_client_suspend_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.suspend("/path")
        mock_client.return_value.suspend.assert_called_with("/path")


@pytest.mark.asyncio
async def test_client_suspend_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.suspend.side_effect = RuntimeError("Error")
        with pytest.raises(RuntimeError, match="Failed to suspend /path"):
            await client.suspend("/path")


@pytest.mark.asyncio
async def test_client_resume_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.resume("/path")
        mock_client.return_value.resume.assert_called_with("/path")


@pytest.mark.asyncio
async def test_client_resume_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.resume.side_effect = RuntimeError("Error")
        with pytest.raises(RuntimeError, match="Failed to resume /path"):
            await client.resume("/path")


@pytest.mark.asyncio
async def test_client_kill_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.kill("/path")
        mock_client.return_value.kill.assert_called_with("/path")


@pytest.mark.asyncio
async def test_client_kill_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.kill.side_effect = RuntimeError("Error")
        with pytest.raises(RuntimeError, match="Failed to kill /path"):
            await client.kill("/path")


@pytest.mark.asyncio
async def test_client_force_complete_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.force_complete("/path")
        mock_client.return_value.force_complete.assert_called_with("/path")


@pytest.mark.asyncio
async def test_client_force_complete_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.force_complete.side_effect = RuntimeError("Error")
        with pytest.raises(RuntimeError, match="Failed to force complete /path"):
            await client.force_complete("/path")


@pytest.mark.asyncio
async def test_client_alter_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.alter("/path", "change", "var", "val")
        mock_client.return_value.alter.assert_called_with("/path", "change", "var", "val")


@pytest.mark.asyncio
async def test_client_alter_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.alter.side_effect = RuntimeError("Error")
        with pytest.raises(RuntimeError, match="Failed to alter /path"):
            await client.alter("/path", "change", "var", "val")


@pytest.mark.asyncio
async def test_client_requeue_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.requeue("/path")
        mock_client.return_value.requeue.assert_called_with("/path")


@pytest.mark.asyncio
async def test_client_requeue_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.requeue.side_effect = RuntimeError("Error")
        with pytest.raises(RuntimeError, match="Failed to requeue /path"):
            await client.requeue("/path")


@pytest.mark.asyncio
async def test_client_server_control():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()

        # Restart
        await client.restart_server()
        mock_client.return_value.restart_server.assert_called_once()

        # Halt
        await client.halt_server()
        mock_client.return_value.halt_server.assert_called_once()


@pytest.mark.asyncio
async def test_client_versions():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()

        mock_client.return_value.version.return_value = "v1"
        assert await client.version() == "v1"

        mock_client.return_value.server_version.return_value = "v2"
        assert await client.server_version() == "v2"


@pytest.mark.asyncio
async def test_client_version_failures():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()

        mock_client.return_value.version.side_effect = RuntimeError("fail")
        with pytest.raises(RuntimeError, match="Failed to get client version"):
            await client.version()

        mock_client.return_value.server_version.side_effect = RuntimeError("fail")
        with pytest.raises(RuntimeError, match="Failed to get server version"):
            await client.server_version()


@pytest.mark.asyncio
async def test_client_server_control_failures():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()

        mock_client.return_value.restart_server.side_effect = RuntimeError("fail")
        with pytest.raises(RuntimeError, match="Failed to restart server"):
            await client.restart_server()

        mock_client.return_value.halt_server.side_effect = RuntimeError("fail")
        with pytest.raises(RuntimeError, match="Failed to halt server"):
            await client.halt_server()


@pytest.mark.asyncio
async def test_client_load_defs_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.load_defs("test.def")
        mock_client.return_value.load.assert_called_with("test.def")


@pytest.mark.asyncio
async def test_client_load_defs_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.load.side_effect = RuntimeError("Load error")
        with pytest.raises(RuntimeError, match="Failed to load definition file test.def"):
            await client.load_defs("test.def")


@pytest.mark.asyncio
async def test_client_begin_suite_success():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        await client.begin_suite("test_suite")
        mock_client.return_value.begin_suite.assert_called_with("test_suite")


@pytest.mark.asyncio
async def test_client_begin_suite_failure():
    with patch("ectop.client.ecflow.Client") as mock_client:
        client = EcflowClient()
        mock_client.return_value.begin_suite.side_effect = RuntimeError("Begin error")
        with pytest.raises(RuntimeError, match="Failed to begin suite test_suite"):
            await client.begin_suite("test_suite")
