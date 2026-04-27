# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Sidebar widget for the ecFlow suite tree.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
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

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.
    """

    current_filter: reactive[str | None] = reactive(None, init=False)
    """The current status filter applied to the tree."""

    defs: reactive[Defs | None] = reactive(None, init=False)
    """The ecFlow definitions to display."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the SuiteTree.

        Parameters
        ----------
        *args : Any
            Positional arguments for the Tree widget.
        **kwargs : Any
            Keyword arguments for the Tree widget.

        Returns
        -------
        None
        """
        super().__init__(*args, **kwargs)
        self.filters: list[str | None] = TREE_FILTERS
        self.host: str = ""
        self.port: int = 0
        self._all_paths_cache: list[str] | None = None
        self._visibility_cache: dict[str, set[str]] = {}
        self._search_paths_lower: list[str] = []

    def update_tree(self, client_host: str, client_port: int, defs: Defs | None) -> None:
        """
        Update the tree data.

        Parameters
        ----------
        client_host : str
            The hostname of the ecFlow server.
        client_port : int
            The port of the ecFlow server.
        defs : ecflow.Defs | None
            The ecFlow definitions to display.

        Returns
        -------
        None

        Notes
        -----
        This method triggers the reactive watchers.
        """
        self.host = client_host
        self.port = client_port
        self.defs = defs

    def watch_defs(self, new_defs: Defs | None) -> None:
        """
        Watch for changes in definitions and rebuild the tree.

        Parameters
        ----------
        new_defs : ecflow.Defs | None
            The new ecFlow definitions.
        """
        self._rebuild_tree()

    def watch_current_filter(self, new_filter: str | None) -> None:
        """
        Watch for changes in the current filter and rebuild the tree.

        Parameters
        ----------
        new_filter : str | None
            The new filter value.
        """
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        """
        Rebuild the tree from ecFlow definitions using lazy loading.
        """
        self.clear()
        if not self.defs:
            self.root.label = "Server Empty"
            self._all_paths_cache = None
            self._visibility_cache = {}
            self._search_paths_lower = []
            return

        filter_str = f" [Filter: {self.current_filter}]" if self.current_filter else ""
        self.root.label = f"{ICON_SERVER} {self.host}:{self.port}{filter_str}"

        # Combine cache building and population triggering
        self._build_caches_and_populate()

    @work(exclusive=True, thread=True)
    def _build_caches_and_populate(self) -> None:
        """
        Build search and visibility caches in background and then populate root.
        """
        if not self.defs:
            return

        all_paths: list[str] = []
        # Pre-calculate visibility for all filters to avoid re-calculation on filter cycle
        visibility: dict[str, set[str]] = {f: set() for f in self.filters if f is not None}

        # Optimized single-pass traversal using get_all_nodes()
        # and post-order visibility propagation.
        try:
            # get_all_nodes() returns all nodes in the definitions
            # If it's a mock, it might not have get_all_nodes or it might return a list
            all_nodes_raw = self.defs.get_all_nodes()
            all_nodes = list(all_nodes_raw)

            # For visibility propagation, we need to go from leaves to root.
            # get_all_nodes() usually returns in pre-order.
            # We reverse it for a post-order effect.
            for node in reversed(all_nodes):
                path = node.get_abs_node_path()
                all_paths.append(path)

                state = str(node.get_state())
                if state in visibility:
                    visibility[state].add(path)

                # If this node matches a filter, its parent should also be visible for that filter.
                # Since we are going in reverse (leaves to root), parents will be processed after children.
                parent = node.get_parent()
                if parent:
                    parent_path = parent.get_abs_node_path()
                    # Propagation: if any child is visible for a filter, parent is visible too.
                    # We check all filters.
                    for f in visibility:
                        if path in visibility[f]:
                            visibility[f].add(parent_path)

            # all_paths was collected in reverse, fix it
            all_paths.reverse()

        except Exception:
            # Fallback to per-suite traversal if get_all_nodes() fails or behavior is unexpected
            all_paths = []
            for suite in self.defs.suites:
                suite_path = suite.get_abs_node_path()
                all_paths.append(suite_path)

                # Check suite state for visibility
                suite_state = str(suite.get_state())
                if suite_state in visibility:
                    visibility[suite_state].add(suite_path)

                suite_nodes = list(suite.get_all_nodes())
                for node in suite_nodes:
                    path = node.get_abs_node_path()
                    all_paths.append(path)
                    state = str(node.get_state())
                    if state in visibility:
                        curr: ecflow.Node | None = node
                        while curr:
                            curr_path = curr.get_abs_node_path()
                            if curr_path in visibility[state]:
                                break
                            visibility[state].add(curr_path)
                            curr = curr.get_parent()

        self._all_paths_cache = all_paths
        self._search_paths_lower = [p.lower() for p in all_paths]
        self._visibility_cache = visibility

        # Now that caches are ready, populate the tree root on main thread
        self._safe_call(self._populate_root)

    def _populate_root(self) -> None:
        """
        Populate the tree root with suites.
        """
        self._populate_tree_worker()

    @work(exclusive=True, thread=True)
    def _populate_tree_worker(self) -> None:
        """
        Worker to populate the tree root with suites in a background thread.

        Notes:
            This is a background worker that performs recursive filtering.
        """
        if not self.defs:
            return
        suites = [s for s in cast("list[ecflow.Suite]", self.defs.suites) if self._should_show_node(s)]
        batch_size = 50
        for i in range(0, len(suites), batch_size):
            batch = suites[i : i + batch_size]
            self._safe_call(self._add_nodes_batch, self.root, batch)

    def _add_nodes_batch(self, parent_ui_node: TreeNode[str], ecflow_nodes: list[ecflow.Node]) -> None:
        """
        Batch add nodes to the UI to reduce main thread pressure.

        Args:
            parent_ui_node: The parent UI node.
            ecflow_nodes: List of ecFlow nodes to add.
        """
        for ecflow_node in ecflow_nodes:
            self._add_node_to_ui(parent_ui_node, ecflow_node)

    def _should_show_node(self, node: Node) -> bool:
        """
        Determine if a node should be shown based on the current filter.

        Parameters
        ----------
        node : ecflow.Node
            The ecFlow node to check.

        Returns
        -------
        bool
            True if the node or any of its descendants match the filter.
        """
        if not self.current_filter:
            return True

        visible_paths = self._visibility_cache.get(self.current_filter)
        if not visible_paths:
            # Cache not ready or filter unknown, fallback to slow check
            state = str(node.get_state())
            if state == self.current_filter:
                return True
            if hasattr(node, "nodes") and node.nodes:
                return any(self._should_show_node(child) for child in node.nodes)
            return False

        return node.get_abs_node_path() in visible_paths

    def action_cycle_filter(self) -> None:
        """
        Cycle through available status filters and refresh the tree.

        Returns
        -------
        None
        """
        current_idx = self.filters.index(self.current_filter)
        next_idx = (current_idx + 1) % len(self.filters)
        self.current_filter = self.filters[next_idx]

        self.app.notify(f"Filter: {self.current_filter or 'All'}")

    def _add_node_to_ui(self, parent_ui_node: TreeNode[str], ecflow_node: ecflow.Node) -> TreeNode[str]:
        """
        Add a single ecflow node to the UI tree.

        Parameters
        ----------
        parent_ui_node : TreeNode[str]
            The parent node in the Textual tree.
        ecflow_node : ecflow.Node
            The ecFlow node to add.

        Returns
        -------
        TreeNode[str]
            The newly created UI node.
        """
        state = str(ecflow_node.get_state())
        icon = STATE_MAP.get(state, ICON_UNKNOWN_STATE)

        is_container = isinstance(ecflow_node, ecflow.Family | ecflow.Suite)
        type_icon = ICON_FAMILY if is_container else ICON_TASK

        label = Text(f"{icon} {type_icon} {ecflow_node.name()} ")
        label.append(f"[{state}]", style="bold italic")

        new_ui_node = parent_ui_node.add(
            label,
            data=ecflow_node.get_abs_node_path(),
            expand=False,
        )

        # If it's a container and has children, add a placeholder for lazy loading
        if is_container and hasattr(ecflow_node, "nodes"):
            # Use a more efficient check for presence of children than len(list(...))
            has_children = False
            try:
                # Check if there is at least one child
                next(iter(ecflow_node.nodes))
                has_children = True
            except (StopIteration, RuntimeError):
                pass

            if has_children:
                new_ui_node.add(LOADING_PLACEHOLDER, allow_expand=False)

        return new_ui_node

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[str]) -> None:
        """
        Handle node expansion to load children on demand.

        Parameters
        ----------
        event : Tree.NodeExpanded[str]
            The expansion event.

        Returns
        -------
        None
        """
        node = event.node
        self._load_children(node)

    def _load_children(self, ui_node: TreeNode[str], sync: bool = False) -> None:
        """
        Load children for a UI node if they haven't been loaded yet.

        Args:
            ui_node: The UI node to load children for.
            sync: Whether to load children synchronously. Defaults to False.

        Notes:
            Uses `_load_children_worker` for async loading.
        """
        if not ui_node.data or not self.defs:
            return

        # Check if we have the placeholder
        if len(ui_node.children) == 1 and str(ui_node.children[0].label) == LOADING_PLACEHOLDER:
            # UI modification must be scheduled on the main thread
            placeholder = ui_node.children[0]
            self._safe_call(placeholder.remove)

            if sync:
                ecflow_node = self.defs.find_abs_node(ui_node.data)
                if ecflow_node and hasattr(ecflow_node, "nodes"):
                    # Use batching even for sync loading to keep implementation consistent
                    nodes = list(ecflow_node.nodes)
                    self._safe_call(self._add_nodes_batch, ui_node, nodes)
            else:
                self._load_children_worker(ui_node, ui_node.data)

    @work(exclusive=True, thread=True)
    def _load_children_worker(self, ui_node: TreeNode[str], node_path: str) -> None:
        """
        Worker to load children nodes in a background thread.

        Args:
            ui_node: The UI node to populate.
            node_path: The absolute path of the ecFlow node.

        Notes:
            UI updates are scheduled back to the main thread using `call_from_thread`.
        """
        if not self.defs:
            return

        ecflow_node = self.defs.find_abs_node(node_path)
        if ecflow_node and hasattr(ecflow_node, "nodes"):
            children = [c for c in cast("list[ecflow.Node]", ecflow_node.nodes) if self._should_show_node(c)]
            batch_size = 50
            for i in range(0, len(children), batch_size):
                batch = children[i : i + batch_size]
                self._safe_call(self._add_nodes_batch, ui_node, batch)

    @work(exclusive=True, thread=True)
    def find_and_select(self, query: str) -> None:
        """
        Find nodes matching query in the ecFlow definitions and select them.

        This handles searching through unloaded parts of the tree in a
        background thread to keep the UI responsive.

        Parameters
        ----------
        query : str
            The search query.

        Returns
        -------
        None

        Notes
        -----
        This is a background worker.
        """
        self._find_and_select_logic(query)

    def _find_and_select_logic(self, query: str) -> None:
        """
        The actual search logic split out for testing.

        Parameters
        ----------
        query : str
            The search query.
        """
        if not self.defs:
            return

        query = query.lower()

        # Build or use cached paths
        if self._all_paths_cache is None:
            # Fallback if cache isn't ready yet
            all_paths: list[str] = []
            for suite in self.defs.suites:
                all_paths.append(suite.get_abs_node_path())
                all_paths.extend(n.get_abs_node_path() for n in suite.get_all_nodes())
            self._all_paths_cache = all_paths
            self._search_paths_lower = [p.lower() for p in self._all_paths_cache]

        all_paths = self._all_paths_cache
        search_paths = self._search_paths_lower

        # Get current cursor state on main thread
        cursor_node = getattr(self, "cursor_node", None)
        current_path = cursor_node.data if cursor_node else None

        start_index = 0
        if current_path and current_path in all_paths:
            try:
                start_index = all_paths.index(current_path) + 1
            except ValueError:
                start_index = 0

        # Search from start_index to end, then wrap around
        found_path = None
        for i in range(len(all_paths)):
            idx = (start_index + i) % len(all_paths)
            if query in search_paths[idx]:
                found_path = all_paths[idx]
                break

        if found_path:
            self._select_by_path_logic(found_path)
        else:
            self._safe_call(self.app.notify, f"No match found for '{query}'", severity="warning")

    def _safe_call(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Safely call a UI-related function from either the main thread or a worker.

        Parameters
        ----------
        callback : Callable[..., Any]
            The function to call.
        *args : Any
            Positional arguments.
        **kwargs : Any
            Keyword arguments.

        Returns
        -------
        Any
            The result of the call if synchronous, or None if scheduled.
        """
        try:
            return safe_call_app(self.app, callback, *args, **kwargs)
        except (AttributeError, RuntimeError, Exception):
            # App might not be fully initialized in some tests
            # Fallback to direct call if app is not available
            return callback(*args, **kwargs)

    @work(thread=True)
    def select_by_path(self, path: str) -> None:
        """
        Select a node by its absolute ecFlow path, expanding parents as needed.

        Parameters
        ----------
        path : str
            The absolute path of the node to select.

        Returns
        -------
        None

        Notes
        -----
        This is a background worker to avoid blocking the UI thread when
        loading many nested nodes synchronously.
        """
        self._select_by_path_logic(path)

    def _select_by_path_logic(self, path: str) -> None:
        """
        The actual logic for selecting a node by path.

        Parameters
        ----------
        path : str
            The absolute path of the node to select.

        Returns
        -------
        None

        Notes
        -----
        This method should be called from a background thread as it performs
        synchronous child loading.
        """
        if path == "/":
            self.app.call_from_thread(self.select_node, self.root)
            return

        parts = path.strip("/").split("/")
        current_ui_node = self.root

        current_path = ""
        for part in parts:
            current_path += "/" + part
            # Load children synchronously within the worker thread
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
        Select a node and expand all its parents.

        Parameters
        ----------
        node : TreeNode[str]
            The node to select and reveal.

        Returns
        -------
        None
        """
        self.select_node(node)
        parent = node.parent
        while parent:
            parent.expand()
            parent = parent.parent
        self.scroll_to_node(node)
