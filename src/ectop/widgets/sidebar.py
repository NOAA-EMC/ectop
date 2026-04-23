# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Sidebar widget for the ecFlow suite tree.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

import ecflow
from rich.text import Text
from textual import work
from textual.reactive import reactive
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from ectop.constants import (
    ICON_FAMILY,
    ICON_SERVER,
    ICON_TASK,
    ICON_UNKNOWN_STATE,
    LOADING_PLACEHOLDER,
    STATE_MAP,
    TREE_FILTERS,
)
from ectop.utils import safe_call_app

if TYPE_CHECKING:
    from ecflow import Defs, Node


class SuiteTree(Tree[str]):
    """
    A tree widget to display ecFlow suites and nodes.
    """

    current_filter: reactive[str | None] = reactive(None, init=False)
    defs: reactive[Defs | None] = reactive(None, init=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the SuiteTree.

        Parameters
        ----------
        *args : Any
            Positional arguments for Tree.
        **kwargs : Any
            Keyword arguments for Tree.
        """
        super().__init__(*args, **kwargs)
        self.filters: list[str | None] = TREE_FILTERS
        self.host: str = ""
        self.port: int = 0
        self._all_paths_cache: list[str] | None = None

    def update_tree(self, client_host: str, client_port: int, defs: Defs | None) -> None:
        """
        Update the tree with new definitions.

        Parameters
        ----------
        client_host : str
            ecFlow host.
        client_port : int
            ecFlow port.
        defs : Defs | None
            Node definitions.
        """
        self.host = client_host
        self.port = client_port
        self.defs = defs

    def watch_defs(self, new_defs: Defs | None) -> None:
        """
        Watch for changes in the definitions.

        Parameters
        ----------
        new_defs : Defs | None
            New definitions.
        """
        self._rebuild_tree()

    def watch_current_filter(self, new_filter: str | None) -> None:
        """
        Watch for changes in the current filter.

        Parameters
        ----------
        new_filter : str | None
            New filter.
        """
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        """
        Rebuild the tree structure.
        """
        self._all_paths_cache = None
        self.clear()
        if not self.defs:
            self.root.label = "Server Empty"
            return
        filter_str = f" [Filter: {self.current_filter}]" if self.current_filter else ""
        self.root.label = f"{ICON_SERVER} {self.host}:{self.port}{filter_str}"
        self._populate_tree_worker()
        self._build_all_paths_cache_worker()

    @work()
    async def _populate_tree_worker(self) -> None:
        """
        Populate the tree nodes in a background worker.
        """
        if not self.defs:
            return
        for suite in cast("list[ecflow.Suite]", self.defs.suites):
            if self._should_show_node(suite):
                self._safe_call(self._add_node_to_ui, self.root, suite)

    def _should_show_node(self, node: Node) -> bool:
        """
        Check if a node should be visible based on the current filter.

        Parameters
        ----------
        node : Node
            The node to check.

        Returns
        -------
        bool
            True if visible.
        """
        if not self.current_filter:
            return True
        state = str(node.get_state())
        if state == self.current_filter:
            return True
        if hasattr(node, "nodes"):
            return any(self._should_show_node(child) for child in node.nodes)
        return False

    @work()
    async def _build_all_paths_cache_worker(self) -> None:
        """
        Build a cache of all node paths for searching.
        """
        if not self.defs:
            return
        paths: list[str] = []
        for suite in self.defs.suites:
            for node in suite.get_all_nodes():
                paths.append(node.get_abs_node_path())
        self._all_paths_cache = paths

    def action_cycle_filter(self) -> None:
        """
        Cycle through the available status filters.
        """
        current_idx = self.filters.index(self.current_filter)
        next_idx = (current_idx + 1) % len(self.filters)
        self.current_filter = self.filters[next_idx]
        self.app.notify(f"Filter: {self.current_filter or 'All'}")

    def _add_node_to_ui(self, parent_ui_node: TreeNode[str], ecflow_node: ecflow.Node) -> TreeNode[str]:
        """
        Add an ecFlow node to the UI tree.

        Parameters
        ----------
        parent_ui_node : TreeNode
            Parent UI node.
        ecflow_node : ecflow.Node
            The ecFlow node.

        Returns
        -------
        TreeNode
            The created UI node.
        """
        state = str(ecflow_node.get_state())
        icon = STATE_MAP.get(state, ICON_UNKNOWN_STATE)
        is_container = isinstance(ecflow_node, (ecflow.Family, ecflow.Suite))
        type_icon = ICON_FAMILY if is_container else ICON_TASK
        label = Text(f"{icon} {type_icon} {ecflow_node.name()} ")
        label.append(f"[{state}]", style="bold italic")
        new_ui_node = parent_ui_node.add(label, data=ecflow_node.get_abs_node_path(), expand=False)
        if is_container and hasattr(ecflow_node, "nodes"):
            has_children = False
            try:
                next(iter(ecflow_node.nodes))
                has_children = True
            except (StopIteration, RuntimeError):
                pass
            if has_children:
                new_ui_node.add(LOADING_PLACEHOLDER, allow_expand=False)
        return new_ui_node

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[str]) -> None:
        """
        Handle tree node expansion to load children lazily.

        Parameters
        ----------
        event : Tree.NodeExpanded
            The expansion event.
        """
        self._load_children(event.node)

    def _load_children(self, ui_node: TreeNode[str], sync: bool = False) -> None:
        """
        Load children for a tree node.

        Parameters
        ----------
        ui_node : TreeNode
            UI node to load children for.
        sync : bool
            Whether to load synchronously.
        """
        if not ui_node.data or not self.defs:
            return
        if len(ui_node.children) == 1 and str(ui_node.children[0].label) == LOADING_PLACEHOLDER:
            placeholder = ui_node.children[0]
            self._safe_call(placeholder.remove)
            if sync:
                ecflow_node = self.defs.find_abs_node(ui_node.data)
                if ecflow_node and hasattr(ecflow_node, "nodes"):
                    for child in ecflow_node.nodes:
                        self._safe_call(self._add_node_to_ui, ui_node, child)
            else:
                self._load_children_worker(ui_node, ui_node.data)

    @work()
    async def _load_children_worker(self, ui_node: TreeNode[str], node_path: str) -> None:
        """
        Load children in a background worker.

        Parameters
        ----------
        ui_node : TreeNode
            UI node.
        node_path : str
            Absolute node path.
        """
        if not self.defs:
            return
        ecflow_node = self.defs.find_abs_node(node_path)
        if ecflow_node and hasattr(ecflow_node, "nodes"):
            for child in cast("list[ecflow.Node]", ecflow_node.nodes):
                if self._should_show_node(child):
                    self.app.call_from_thread(self._add_node_to_ui, ui_node, child)

    @work(exclusive=True)
    async def find_and_select(self, query: str) -> None:
        """
        Find a node by query and select it.

        Parameters
        ----------
        query : str
            The search query.
        """
        self._find_and_select_logic(query)

    def _find_and_select_logic(self, query: str) -> None:
        """
        Internal logic for finding and selecting a node.

        Parameters
        ----------
        query : str
            The search query.
        """
        if not self.defs:
            return
        query = query.lower()
        if not hasattr(self, "_all_paths_cache") or self._all_paths_cache is None:
            paths: list[str] = []
            for suite in self.defs.suites:
                for node in suite.get_all_nodes():
                    paths.append(node.get_abs_node_path())
            self._all_paths_cache = paths
        all_paths = self._all_paths_cache
        cursor_node = getattr(self, "cursor_node", None)
        current_path = cursor_node.data if cursor_node else None
        start_index = 0
        if current_path and current_path in all_paths:
            try:
                start_index = all_paths.index(current_path) + 1
            except ValueError:
                start_index = 0
        found_path = None
        for i in range(len(all_paths)):
            path = all_paths[(start_index + i) % len(all_paths)]
            if query in path.lower():
                found_path = path
                break
        if found_path:
            self._select_by_path_logic(found_path)
        else:
            self._safe_call(self.app.notify, f"No match found for '{query}'", severity="warning")

    def _safe_call(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Safely call a function, ensuring it runs on the main thread if needed.

        Parameters
        ----------
        callback : Callable
            Function to call.
        *args : Any
            Positional arguments.
        **kwargs : Any
            Keyword arguments.

        Returns
        -------
        Any
            Callback result.
        """
        try:
            return safe_call_app(self.app, callback, *args, **kwargs)
        except (AttributeError, RuntimeError, Exception):
            return callback(*args, **kwargs)

    @work()
    async def select_by_path(self, path: str) -> None:
        """
        Select a node by its absolute path.

        Parameters
        ----------
        path : str
            Absolute node path.
        """
        self._select_by_path_logic(path)

    def _select_by_path_logic(self, path: str) -> None:
        """
        Internal logic for selecting a node by path.

        Parameters
        ----------
        path : str
            Absolute node path.
        """
        if path == "/":
            self.app.call_from_thread(self.select_node, self.root)
            return
        parts = path.strip("/").split("/")
        current_ui_node = self.root
        current_path = ""
        for part in parts:
            current_path += "/" + part
            self._load_children(current_ui_node, sync=True)
            self._safe_call(current_ui_node.expand)
            found = False
            for child in current_ui_node.children:
                if child.data == current_path:
                    current_ui_node = child
                    found = True
                    break
            if not found:
                return
        self._safe_call(self._select_and_reveal, current_ui_node)

    def _select_and_reveal(self, node: TreeNode[str]) -> None:
        """
        Select a node and ensure its ancestors are expanded.

        Parameters
        ----------
        node : TreeNode
            The UI node.
        """
        self.select_node(node)
        parent = node.parent
        while parent:
            parent.expand()
            parent = parent.parent
        self.scroll_to_node(node)
