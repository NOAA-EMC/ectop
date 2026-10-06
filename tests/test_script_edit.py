# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""Integration coverage for editing scripts through a configured editor."""

from __future__ import annotations

import asyncio
import shlex
import sys
import uuid
from pathlib import Path

import ecflow
import pytest

from ectop.app import Ectop
from ectop.client import EcflowClient


def _create_editor(tmp_path: Path, source: str) -> Path:
    """Create an executable Python editor used by subprocess integration tests.

    Parameters
    ----------
    tmp_path : Path
        Test temporary directory.
    source : str
        Python program to run as the editor.

    Returns
    -------
    Path
        Executable editor script path.
    """
    path = tmp_path / "editor with spaces.py"
    path.write_text(f"#!{sys.executable}\n{source}", encoding="utf-8")
    path.chmod(0o755)
    return path


def _load_script_node(ecflow_server: str, ecflow_home: Path, ecflow_files: Path) -> tuple[str, str]:
    """Load a task with a real script into the test ecFlow server.

    Parameters
    ----------
    ecflow_server : str
        Address of the real ecFlow test server.
    ecflow_home : Path
        Isolated ecFlow home directory.
    ecflow_files : Path
        Script search directory configured for the test server.

    Returns
    -------
    tuple[str, str]
        Server address and absolute task path.
    """
    host, port_text = ecflow_server.split(":")
    server = ecflow.Client(host, int(port_text))
    server.delete_all(force=True)
    suite_name = f"edit_suite_{uuid.uuid4().hex[:8]}"
    task_name = "edit_task"
    suite_dir = ecflow_files / suite_name
    suite_dir.mkdir(parents=True, exist_ok=True)
    (suite_dir / f"{task_name}.ecf").write_text("#!/bin/sh\necho original\n", encoding="utf-8")

    defs = ecflow.Defs()
    suite = defs.add_suite(suite_name)
    suite.add_variable("ECF_HOME", str(ecflow_home))
    suite.add_variable("ECF_FILES", str(ecflow_files))
    suite.add_task(task_name)
    server.load(defs, force=True)
    server.restart_server()
    server.begin_suite(suite_name)
    server.job_generation(f"/{suite_name}/{task_name}")
    return ecflow_server, f"/{suite_name}/{task_name}"


@pytest.mark.asyncio
async def test_editor_command_arguments_and_successful_server_update(
    tmp_path: Path, ecflow_server: str, ecflow_home: Path, ecflow_files: Path
) -> None:
    """Honor quoted editor arguments and apply successful changed content.

    Parameters
    ----------
    tmp_path : Path
        Test temporary directory.
    ecflow_server : str
        Address of the real ecFlow test server.
    ecflow_home : Path
        Isolated ecFlow home directory.
    ecflow_files : Path
        Script search directory configured for the test server.
    """
    address, node_path = _load_script_node(ecflow_server, ecflow_home, ecflow_files)
    editor = _create_editor(
        tmp_path,
        "import pathlib, sys\n"
        "assert sys.argv[1] == 'argument with spaces'\n"
        "pathlib.Path(sys.argv[2]).write_text('edited by integration test\\n')\n",
    )
    temp_script = tmp_path / "task.ecf"
    temp_script.write_text("original\n", encoding="utf-8")
    app = Ectop()
    host, port_text = address.split(":")
    source_path = EcflowClient(host, int(port_text)).script_source_path_sync(node_path)

    async with app.run_test():
        app.ecflow_client = EcflowClient(host, int(port_text))
        app._prompt_requeue = lambda _path: None
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("EDITOR", f'{shlex.quote(sys.executable)} {shlex.quote(str(editor))} "argument with spaces"')
            await app._run_editor(str(temp_script), node_path, "original\n", source_path)

    assert not temp_script.exists()
    assert Path(source_path).read_text(encoding="utf-8") == "edited by integration test\n"
    host, port_text = address.split(":")
    updated_defs = ecflow.Client(host, int(port_text))
    updated_defs.sync_local()
    assert updated_defs.get_defs().find_abs_node(node_path) is not None
    assert "edited by integration test" in updated_defs.get_file(node_path, "script")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "editor_override", "expected"),
    [
        ("pass\n", None, "No changes detected"),
        ("raise SystemExit(7)\n", None, "status 7"),
        ("pass\n", "missing-editor-executable", "Failed to start"),
    ],
)
async def test_editor_failure_and_unchanged_content_never_alter_server(
    tmp_path: Path, source: str, editor_override: str | None, expected: str
) -> None:
    """Handle unchanged, non-zero, and missing-editor outcomes with cleanup.

    Parameters
    ----------
    tmp_path : Path
        Test temporary directory.
    source : str
        Editor program body.
    editor_override : str | None
        Explicit editor command for the missing-executable case.
    expected : str
        Expected error or notification text.
    """
    editor = _create_editor(tmp_path, source)
    temp_script = tmp_path / "task.ecf"
    temp_script.write_text("original\n", encoding="utf-8")
    source_script = tmp_path / "source.ecf"
    source_script.write_text("original\n", encoding="utf-8")
    app = Ectop()

    async with app.run_test() as pilot:
        command = editor_override or f"{shlex.quote(sys.executable)} {shlex.quote(str(editor))}"
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("EDITOR", command)
            if expected == "No changes detected":
                await app._run_editor(str(temp_script), "/suite/task", "original\n", str(source_script))
            else:
                with pytest.raises((RuntimeError, FileNotFoundError), match=expected):
                    await app._run_editor(str(temp_script), "/suite/task", "original\n", str(source_script))
        await pilot.pause()

    assert not temp_script.exists()
    assert source_script.read_text(encoding="utf-8") == "original\n"


@pytest.mark.asyncio
async def test_editor_interruption_cleans_temp_file(tmp_path: Path) -> None:
    """Terminate an interrupted editor process and remove its temporary file.

    Parameters
    ----------
    tmp_path : Path
        Test temporary directory.
    """
    marker = tmp_path / "started"
    editor = _create_editor(
        tmp_path,
        "import pathlib, sys, time\n" f"pathlib.Path({str(marker)!r}).write_text('started')\n" "time.sleep(30)\n",
    )
    temp_script = tmp_path / "task.ecf"
    temp_script.write_text("original\n", encoding="utf-8")
    source_script = tmp_path / "source.ecf"
    source_script.write_text("original\n", encoding="utf-8")
    app = Ectop()

    async with app.run_test():
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("EDITOR", f"{shlex.quote(sys.executable)} {shlex.quote(str(editor))}")
            running = asyncio.create_task(app._run_editor(str(temp_script), "/suite/task", "original\n", str(source_script)))
            for _ in range(100):
                if marker.exists():
                    break
                await asyncio.sleep(0.01)
            assert marker.exists()
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running

    assert not temp_script.exists()
    assert source_script.read_text(encoding="utf-8") == "original\n"
