# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""Tests for log refresh behavior using mounted Textual and real ecFlow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import ecflow
import pytest

from ectop.app import Ectop
from ectop.widgets.content import MainContent
from ectop.widgets.sidebar import SuiteTree


def test_main_content_update_log_full_refresh() -> None:
    """Test that update_log performs a full refresh when no delta is provided."""
    content = MainContent()
    mock_log = MagicMock()
    with patch.object(content, "query_one", return_value=mock_log):
        content.update_log("Initial Content")
    mock_log.clear.assert_called_once()
    mock_log.write.assert_called_with("Initial Content")
    assert content._content_cache["output"] == "Initial Content"
    assert content.last_log_size == len("Initial Content")


def test_main_content_update_log_with_delta() -> None:
    """Test that update_log appends a delta and updates its cache."""
    content = MainContent()
    content._content_cache["output"] = "Initial "
    content.last_log_size = len("Initial ")
    mock_log = MagicMock()
    with patch.object(content, "query_one", return_value=mock_log):
        content.update_log("Initial Content", delta="Content")
    mock_log.clear.assert_not_called()
    mock_log.write.assert_called_with("Content")
    assert content._content_cache["output"] == "Initial Content"
    assert content.last_log_size == len("Initial Content")


def _load_output_task(ecflow_server: str, ecflow_home: Path, output: str) -> tuple[str, str]:
    """Create a task whose output can be fetched from the real test server.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    ecflow_home : Path
        Isolated server home directory.
    output : str
        Contents to make available as the task's job output.

    Returns
    -------
    tuple[str, str]
        Server address and absolute task path.
    """
    host, port_text = ecflow_server.split(":")
    client = ecflow.Client(host, int(port_text))
    client.delete_all(force=True)
    output_path = ecflow_home / "live_output.log"
    output_path.write_text(output, encoding="utf-8")
    defs = ecflow.Defs()
    suite = defs.add_suite("live_log_suite")
    suite.add_variable("ECF_HOME", str(ecflow_home))
    task = suite.add_task("live_log_task")
    task.add_variable("ECF_JOBOUT", str(output_path))
    client.load(defs, force=True)
    return ecflow_server, "/live_log_suite/live_log_task"


@pytest.mark.parametrize(
    ("cached", "server_output", "expected_delta"),
    [
        ("Initial Content", "Initial Content More", " More"),
        ("Initial Content", "Completely Different Content", None),
    ],
)
@pytest.mark.asyncio
async def test_live_log_worker_delta_calculation(
    ecflow_server: str,
    ecflow_home: Path,
    cached: str,
    server_output: str,
    expected_delta: str | None,
) -> None:
    """Test live log delta calculation through the real server and app worker.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    ecflow_home : Path
        Isolated server home directory.
    cached : str
        Existing output cache.
    server_output : str
        Output returned by ecFlow's real file command.
    expected_delta : str | None
        Delta to append, or ``None`` when a full refresh is needed.
    """
    address, path = _load_output_task(ecflow_server, ecflow_home, server_output)
    host, port_text = address.split(":")
    app = Ectop(host, int(port_text), refresh_interval=60)

    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        for _ in range(100):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.02)
        assert tree.snapshot is not None

        content = app.query_one(MainContent)
        content._content_cache["output"] = cached
        content.last_log_size = len(cached)
        with patch.object(content, "update_log", wraps=content.update_log) as update_log:
            worker = app._live_log_worker(path)
            await worker.wait()

        update_log.assert_called_once_with(server_output, delta=expected_delta)
        assert content._content_cache["output"] == server_output
