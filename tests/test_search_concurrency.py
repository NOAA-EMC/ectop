# If you modify features, API, or usage, you MUST update the documentation immediately.
"""Concurrency regressions for latest-wins node search."""

from __future__ import annotations

import ecflow
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input

from ectop.app import Ectop
from ectop.widgets.sidebar import SuiteTree


class SearchTreeApp(App[None]):
    """Host a real SuiteTree and its Textual worker manager."""

    def compose(self) -> ComposeResult:
        """Compose the tree used by search tests.

        Returns
        -------
        ComposeResult
            The suite tree widget.
        """
        yield SuiteTree("ecFlow", id="suite_tree")


@pytest.mark.asyncio
async def test_search_reaches_match_in_collapsed_branch() -> None:
    """Find and select a node whose family has not been expanded.

    Returns
    -------
    None
        The test asserts search selection and collapsed-branch materialization.
    """
    defs = ecflow.Defs()
    suite = defs.add_suite("search_suite")
    family = suite.add_family("collapsed_family")
    family.add_task("unique_target")

    app = SearchTreeApp()
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        tree.update_tree("localhost", 3141, defs)
        for _ in range(40):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.05)

        assert tree.snapshot is not None
        assert all(node.data != "/search_suite/collapsed_family" for node in tree.root.children[0].children)

        tree.find_and_select("unique_target")
        for _ in range(40):
            if tree.cursor_node and tree.cursor_node.data == "/search_suite/collapsed_family/unique_target":
                break
            await pilot.pause(0.05)

        assert tree.cursor_node is not None
        assert tree.cursor_node.data == "/search_suite/collapsed_family/unique_target"


@pytest.mark.asyncio
async def test_latest_query_and_clear_discard_stale_results() -> None:
    """Apply only the current query and ignore completions invalidated by clear.

    Returns
    -------
    None
        The test asserts that stale generations cannot change selection.
    """
    defs = ecflow.Defs()
    suite = defs.add_suite("generation_suite")
    suite.add_task("older_match")
    suite.add_task("latest_match")

    app = SearchTreeApp()
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        tree.update_tree("localhost", 3141, defs)
        for _ in range(40):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.05)
        assert tree.snapshot is not None

        tree.find_and_select("older_match")
        older_generation = tree._search_generation
        tree.find_and_select("latest_match")
        latest_generation = tree._search_generation
        assert latest_generation > older_generation

        tree._apply_search_result(
            older_generation,
            tree.snapshot.generation,
            "/generation_suite/older_match",
            "older_match",
        )
        assert tree.cursor_node is None or tree.cursor_node.data != "/generation_suite/older_match"

        tree._apply_search_result(
            latest_generation,
            tree.snapshot.generation,
            "/generation_suite/latest_match",
            "latest_match",
        )
        await pilot.pause()
        assert tree.cursor_node is not None
        assert tree.cursor_node.data == "/generation_suite/latest_match"

        stale_generation = tree._search_generation
        tree.invalidate_search()
        current_path = tree.cursor_node.data
        tree._apply_search_result(
            stale_generation,
            tree.snapshot.generation,
            "/generation_suite/older_match",
            "older_match",
        )
        await pilot.pause()
        assert tree.cursor_node.data == current_path


@pytest.mark.asyncio
async def test_app_debounces_queries_and_clear_invalidates_pending_search() -> None:
    """Debounce changed input and discard a query cleared before dispatch.

    Returns
    -------
    None
        The test asserts latest-query selection and clear invalidation.
    """
    defs = ecflow.Defs()
    suite = defs.add_suite("debounce_suite")
    suite.add_task("older_match")
    suite.add_task("latest_match")

    app = Ectop()
    app._initial_connect = lambda: None
    async with app.run_test() as pilot:
        tree = app.query_one(SuiteTree)
        tree.update_tree("localhost", 3141, defs)
        for _ in range(40):
            if tree.snapshot is not None:
                break
            await pilot.pause(0.05)
        assert tree.snapshot is not None

        search = app.query_one("#search_box", Input)
        search.value = "older_match"
        await pilot.pause(0.04)
        search.value = "latest_match"
        for _ in range(40):
            if tree.cursor_node and tree.cursor_node.data == "/debounce_suite/latest_match":
                break
            await pilot.pause(0.05)
        assert tree.cursor_node is not None
        assert tree.cursor_node.data == "/debounce_suite/latest_match"

        search.value = "older_match"
        await pilot.pause(0.04)
        search.value = ""
        await pilot.pause(0.25)
        assert tree.cursor_node.data == "/debounce_suite/latest_match"
