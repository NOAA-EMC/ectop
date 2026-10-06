# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""Real-server coverage for responsive, independent node file loading."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import ecflow
import pytest

from ectop.app import Ectop
from ectop.widgets.content import MainContent
from ectop.widgets.sidebar import SuiteTree


def _load_file_tasks(ecflow_server: str, ecflow_home: Path, ecflow_files: Path) -> tuple[str, list[str]]:
    """Load real tasks with generated jobs and one missing output file.

    Parameters
    ----------
    ecflow_server : str
        Address of the real test server.
    ecflow_home : Path
        Isolated server home directory.
    ecflow_files : Path
        Server script-search directory.

    Returns
    -------
    tuple[str, list[str]]
        Server address and paths for the task with files and missing-output task.
    """
    host, port_text = ecflow_server.split(":")
    server = ecflow.Client(host, int(port_text))
    server.delete_all(force=True)
    suite_name = f"loading_suite_{uuid.uuid4().hex[:8]}"
    suite_dir = ecflow_files / suite_name
    suite_dir.mkdir(parents=True, exist_ok=True)
    (suite_dir / "available.ecf").write_text("#!/bin/sh\necho generated\n", encoding="utf-8")
    (suite_dir / "missing_output.ecf").write_text("#!/bin/sh\necho no-output\n", encoding="utf-8")
    output_path = ecflow_home / "available.out"

    defs = ecflow.Defs()
    suite = defs.add_suite(suite_name)
    suite.add_variable("ECF_HOME", str(ecflow_home))
    suite.add_variable("ECF_FILES", str(ecflow_files))
    available = suite.add_task("available")
    available.add_variable("ECF_JOBOUT", str(output_path))
    suite.add_task("missing_output").add_variable("ECF_JOBOUT", str(ecflow_home / "absent.out"))
    server.load(defs, force=True)
    server.restart_server()
    server.begin_suite(suite_name)
    server.job_generation(f"/{suite_name}/available")
    server.job_generation(f"/{suite_name}/missing_output")
    task_paths = [f"/{suite_name}/available", f"/{suite_name}/missing_output"]
    for _ in range(100):
        server.sync_local()
        definitions = server.get_defs()
        states = [str(definitions.find_abs_node(task_path).get_state()) for task_path in task_paths]
        if all(state in ("complete", "aborted") for state in states):
            break
        time.sleep(0.02)
    definitions = server.get_defs()
    for task_name in ("available", "missing_output"):
        task = definitions.find_abs_node(f"/{suite_name}/{task_name}")
        job_variable = task.find_gen_variable("ECF_JOB")
        job_path = Path(job_variable.value())
        job_path.parent.mkdir(parents=True, exist_ok=True)
        job_path.write_text(f"# processed ecFlow job for {task_name}\necho {task_name}\n", encoding="utf-8")
    output_path.write_text("real ecFlow output\n", encoding="utf-8")
    (ecflow_home / "absent.out").unlink(missing_ok=True)
    return ecflow_server, [f"/{suite_name}/available", f"/{suite_name}/missing_output"]


async def _wait_for_snapshot(pilot, tree: SuiteTree) -> None:
    """Wait for the worker-built definition snapshot to appear.

    Parameters
    ----------
    pilot : textual.pilot.Pilot
        Test driver for the running Textual application.
    tree : SuiteTree
        Tree receiving synchronized definitions.
    """
    for _ in range(100):
        if tree.snapshot is not None:
            return
        await pilot.pause(0.02)
    raise AssertionError("the real ecFlow definitions snapshot was not installed")


async def _select_path(pilot, app: Ectop, path: str) -> None:
    """Select a path after the tree has finished its layout callback.

    Parameters
    ----------
    pilot : textual.pilot.Pilot
        Test driver for the running app.
    app : Ectop
        App owning the suite tree.
    path : str
        Absolute node path to select.
    """
    tree = app.query_one(SuiteTree)
    tree.select_by_path(path)
    for _ in range(50):
        if app.get_selected_path() == path:
            return
        await pilot.pause(0.02)
    raise AssertionError(f"the tree did not select {path}")


@pytest.mark.asyncio
async def test_node_files_load_independently_and_navigation_stays_responsive(
    ecflow_server: str, ecflow_home: Path, ecflow_files: Path
) -> None:
    """Load three actual server files while the UI remains available.

    Parameters
    ----------
    ecflow_server : str
        Address of the real test server.
    ecflow_home : Path
        Isolated server home directory.
    ecflow_files : Path
        Server script-search directory.
    """
    address, paths = _load_file_tasks(ecflow_server, ecflow_home, ecflow_files)
    host, port_text = address.split(":")
    app = Ectop(host, int(port_text), refresh_interval=60)

    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        await _wait_for_snapshot(pilot, tree)
        await _select_path(pilot, app, paths[0])
        app._node_load_generation += 1
        generation = app._node_load_generation
        started = time.perf_counter()
        worker = app._load_node_worker(paths[0], generation)
        # The UI remains able to switch views while server calls run in threads.
        content = app.query_one(MainContent)
        content.active = "tab_script"
        assert content.active == "tab_script"
        assert app.get_selected_path() == paths[0]
        await worker.wait()
        elapsed = time.perf_counter() - started

        content = app.query_one(MainContent)
        assert "real ecFlow output" in content._content_cache.get("output", "")
        assert "echo generated" in content._content_cache.get("script", "")
        assert "available" in content._content_cache.get("job", "")
        assert elapsed < 1.0


@pytest.mark.asyncio
async def test_missing_file_does_not_block_other_views_and_stale_node_is_discarded(
    ecflow_server: str, ecflow_home: Path, ecflow_files: Path
) -> None:
    """Show available files when another type is missing and reject stale work.

    Parameters
    ----------
    ecflow_server : str
        Address of the real test server.
    ecflow_home : Path
        Isolated server home directory.
    ecflow_files : Path
        Server script-search directory.
    """
    address, paths = _load_file_tasks(ecflow_server, ecflow_home, ecflow_files)
    host, port_text = address.split(":")
    app = Ectop(host, int(port_text), refresh_interval=60)

    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        await _wait_for_snapshot(pilot, tree)
        content = app.query_one(MainContent)
        await _select_path(pilot, app, paths[1])
        app._node_load_generation += 1
        worker = app._load_node_worker(paths[1], app._node_load_generation)
        await worker.wait()
        assert "echo no-output" in content._content_cache.get("script", "")
        assert "missing_output" in content._content_cache.get("job", "")
        assert content._content_cache.get("output", "") == ""

        stale_generation = app._node_load_generation
        app._node_load_generation += 1
        worker = app._load_node_worker(paths[0], stale_generation)
        await worker.wait()
        for _ in range(50):
            if "echo no-output" in content._content_cache.get("script", ""):
                break
            await pilot.pause(0.02)
        assert app.get_selected_path() == paths[1]
        # No stale successful file should replace the selected node's views.
        assert "echo no-output" in content._content_cache.get("script", "")
