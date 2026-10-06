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

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

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


@dataclass
class NodeDTO:
    """
    Data Transfer Object for ecFlow Node state, decoupling UI from C++ API.

    Attributes:
        name: The name of the node.
        path: The absolute path of the node.
        state: The current state of the node.
        is_container: Whether the node is a Suite or Family.
        has_children: Whether the node has children.
    """

    name: str
    path: str
    state: str
    is_container: bool
    has_children: bool


@dataclass(frozen=True, slots=True)
class DefinitionNode:
    """A plain immutable definition-tree node.

    Parameters
    ----------
    name : str
        Node name as returned by ecFlow.
    path : str
        Absolute ecFlow node path.
    state : str
        String form of the node state.
    parent_path : str | None
        Absolute path of the parent, if present.
    child_paths : tuple[str, ...]
        Absolute paths of the direct children.
    node_kind : str
        One of ``suite``, ``family``, or ``task``.
    """

    name: str
    path: str
    state: str
    parent_path: str | None
    child_paths: tuple[str, ...]
    node_kind: str

    @property
    def is_container(self) -> bool:
        """Return whether the node may contain children.

        Returns
        -------
        bool
            Whether this node is a suite or family.
        """
        return self.node_kind in {"suite", "family"}

    @property
    def has_children(self) -> bool:
        """Return whether this node has direct children.

        Returns
        -------
        bool
            Whether ``child_paths`` is non-empty.
        """
        return bool(self.child_paths)


@dataclass(frozen=True, slots=True)
class DefinitionSnapshot:
    """Immutable indexed view of one ecFlow definitions generation.

    Parameters
    ----------
    generation : int
        Monotonic identifier for the synchronized definitions.
    nodes : tuple[DefinitionNode, ...]
        All nodes in hierarchy order.
    paths : tuple[str, ...]
        Absolute paths in the same order as ``nodes``.
    paths_lower : tuple[str, ...]
        Case-folded paths for search.
    by_path : Mapping[str, DefinitionNode]
        Read-only index of nodes by absolute path.
    visible_by_state : Mapping[str, frozenset[str]]
        Paths matching each state, including their ancestors.
    focus_visible_paths : frozenset[str]
        Non-complete nodes and ancestors required to reach them.
    """

    generation: int
    nodes: tuple[DefinitionNode, ...]
    paths: tuple[str, ...]
    paths_lower: tuple[str, ...]
    by_path: Mapping[str, DefinitionNode]
    visible_by_state: Mapping[str, frozenset[str]]
    focus_visible_paths: frozenset[str]

    @classmethod
    def from_defs(cls, defs: Defs | None, generation: int) -> DefinitionSnapshot:
        """Project ecFlow definitions into immutable plain values.

        Parameters
        ----------
        defs : ecflow.Defs | None
            Definitions returned by the ecFlow client.
        generation : int
            Generation to associate with the resulting snapshot.

        Returns
        -------
        DefinitionSnapshot
            Indexed nodes and status visibility for the definitions.
        """
        records: list[DefinitionNode] = []
        if defs:
            suites = list(defs.suites)
            stack: list[tuple[ecflow.Node, str | None]] = [(suite, None) for suite in reversed(suites)]
            while stack:
                node, parent_path = stack.pop()
                is_suite = isinstance(node, ecflow.Suite)
                is_family = isinstance(node, ecflow.Family)
                children = tuple(node.nodes) if is_suite or is_family else ()
                path = node.get_abs_node_path()
                node_kind = "suite" if is_suite else "family" if is_family else "task"
                records.append(
                    DefinitionNode(
                        name=node.name(),
                        path=path,
                        state=str(node.get_state()),
                        parent_path=parent_path,
                        child_paths=tuple(child.get_abs_node_path() for child in children),
                        node_kind=node_kind,
                    )
                )
                stack.extend((child, path) for child in reversed(children))

        paths = tuple(record.path for record in records)
        by_path = {record.path: record for record in records}
        states = {record.state for record in records}
        visible: dict[str, set[str]] = {state: set() for state in states}
        focus_visible: set[str] = set()
        for record in reversed(records):
            if record.state in visible:
                visible[record.state].add(record.path)
            if record.state != "complete" or any(child in focus_visible for child in record.child_paths):
                focus_visible.add(record.path)
            if record.parent_path:
                for _state, visible_paths in visible.items():
                    if record.path in visible_paths:
                        visible_paths.add(record.parent_path)

        return cls(
            generation=generation,
            nodes=tuple(records),
            paths=paths,
            paths_lower=tuple(path.casefold() for path in paths),
            by_path=MappingProxyType(by_path),
            visible_by_state=MappingProxyType({state: frozenset(paths) for state, paths in visible.items()}),
            focus_visible_paths=frozenset(focus_visible),
        )


class SuiteTree(Tree[str]):
    """
    A tree widget to display ecFlow suites and nodes.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.

    Attributes:
        current_filter: The current status filter applied to the tree.
        defs: The ecFlow definitions to display.
    """

    current_filter: reactive[str | None] = reactive(None, init=False)
    """The current status filter applied to the tree."""

    focus_mode: reactive[bool] = reactive(False, init=False)
    """Whether Focus Mode is active (hides complete nodes)."""

    defs: reactive[Defs | None] = reactive(None, init=False)
    """The ecFlow definitions to display."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the SuiteTree.

        Args:
            *args: Positional arguments for the Tree widget.
            **kwargs: Keyword arguments for the Tree widget.
        """
        super().__init__(*args, **kwargs)
        self.filters: list[str | None] = TREE_FILTERS
        self.host: str = ""
        self.port: int = 0
        self._all_paths_cache: list[str] | None = None
        self._visibility_cache: dict[str, set[str]] = {}
        self._search_paths_lower: list[str] = []
        self._last_selected_path: str | None = None
        self.snapshot: DefinitionSnapshot | None = None
        self._definition_generation = 0
        self._search_generation = 0
        self._pending_search: tuple[int, str] | None = None
        self._loaded_paths: set[str] = set()
        self._updating_tree = False

    def update_tree(self, client_host: str, client_port: int, defs: Defs | None) -> None:
        """
        Update the tree data.

        Args:
            client_host: The hostname of the ecFlow server.
            client_port: The port of the ecFlow server.
            defs: The ecFlow definitions to display.

        Notes:
            This method triggers the reactive watchers.
        """
        self.host = client_host
        self.port = client_port
        self._definition_generation += 1
        self._search_generation += 1
        self._pending_search = None
        self.snapshot = None
        self._updating_tree = True
        try:
            self.defs = defs
        finally:
            self._updating_tree = False
        self._rebuild_tree()

    def watch_defs(self, new_defs: Defs | None) -> None:
        """
        Watch for changes in definitions and rebuild the tree.

        Args:
            new_defs: The new ecFlow definitions.

        Returns:
            None
        """
        if not self._updating_tree:
            self._definition_generation += 1
            self._search_generation += 1
            self._pending_search = None
            self.snapshot = None
            self._rebuild_tree()

    def watch_current_filter(self, new_filter: str | None) -> None:
        """
        Watch for changes in the current filter and rebuild the tree.

        Args:
            new_filter: The new filter value.

        Returns:
            None
        """
        self._rebuild_tree()

    def watch_focus_mode(self, focus_mode: bool) -> None:
        """
        Watch for changes in focus mode and rebuild the tree.

        Args:
            focus_mode: The new focus mode value.

        Returns:
            None
        """
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        """
        Rebuild the tree from ecFlow definitions using lazy loading.

        Returns:
            None

        Notes:
            This method captures the current selection path to restore it
            after the background population worker finishes.
        """
        # Capture current selection to restore it after rebuild
        try:
            cursor_node = getattr(self, "cursor_node", None)
            if cursor_node and cursor_node.data:
                self._last_selected_path = str(cursor_node.data)
            elif cursor_node == self.root:
                self._last_selected_path = "/"
        except (AttributeError, RuntimeError):
            # Fail gracefully if cursor_node is inaccessible during clear/rebuild
            self._last_selected_path = None

        self.clear()
        self.root.expand()
        self._loaded_paths.clear()
        if not self.defs:
            self.snapshot = None
            self.root.label = "Server Empty"
            self._all_paths_cache = None
            self._visibility_cache = {}
            self._search_paths_lower = []
            return

        filter_str = f" [Filter: {self.current_filter}]" if self.current_filter else ""
        focus_str = " [Focus]" if self.focus_mode else ""
        self.root.label = f"{ICON_SERVER} {self.host}:{self.port}{filter_str}{focus_str}"

        if self.snapshot and self.snapshot.generation == self._definition_generation:
            self._populate_snapshot_roots()
        else:
            self._build_caches_and_populate()

    def _build_caches_and_populate(self) -> None:
        """Build a snapshot off-thread while attached to a running app.

        Returns
        -------
        None
            Snapshot creation is scheduled or completed for a detached tree.
        """
        defs = self.defs
        generation = self._definition_generation
        if defs is None:
            return
        try:
            app_is_running = self.is_attached and self.app.is_running
        except (AttributeError, RuntimeError):
            app_is_running = False
        if app_is_running:
            self._build_snapshot_worker(defs, generation)
        else:
            self._install_snapshot(DefinitionSnapshot.from_defs(defs, generation))

    @work(group="tree-build", exclusive=True, thread=True)
    def _build_snapshot_worker(self, defs: Defs, generation: int) -> None:
        """Build plain node data and deliver it to the UI thread.

        Parameters
        ----------
        defs : ecflow.Defs
            Definitions captured by the UI thread.
        generation : int
            Generation assigned to these definitions.

        Returns
        -------
        None
            A current snapshot is published to the tree.
        """
        try:
            snapshot = DefinitionSnapshot.from_defs(defs, generation)
        except RuntimeError as error:
            self._safe_call(self.app.notify, f"Failed to index ecFlow definitions: {error}", severity="error")
            return
        self._safe_call(self._install_snapshot, snapshot)

    def _install_snapshot(self, snapshot: DefinitionSnapshot) -> None:
        """Install the current snapshot and render visible suite roots.

        Parameters
        ----------
        snapshot : DefinitionSnapshot
            Immutable view built from synchronized definitions.

        Returns
        -------
        None
            Current caches and suite roots are updated on the UI thread.
        """
        if snapshot.generation != self._definition_generation:
            return
        self.snapshot = snapshot
        self._all_paths_cache = list(snapshot.paths)
        self._search_paths_lower = list(snapshot.paths_lower)
        self._visibility_cache = {state: set(paths) for state, paths in snapshot.visible_by_state.items()}
        self._populate_snapshot_roots()
        if self._pending_search and self._pending_search[0] == self._search_generation:
            generation, query = self._pending_search
            self._pending_search = None
            self._start_search(query, generation, snapshot)

    def _visible_paths(self, snapshot: DefinitionSnapshot) -> frozenset[str]:
        """Return paths visible for the current filter and focus settings.

        Parameters
        ----------
        snapshot : DefinitionSnapshot
            Snapshot used to calculate visibility.

        Returns
        -------
        frozenset[str]
            Paths visible in the current tree view.
        """
        if self.current_filter is None:
            visible = frozenset(snapshot.paths)
        else:
            visible = snapshot.visible_by_state.get(self.current_filter, frozenset())
        if self.focus_mode:
            return visible & snapshot.focus_visible_paths
        return visible

    def _populate_snapshot_roots(self) -> None:
        """Render visible suite roots from the current snapshot.

        Returns
        -------
        None
            Suite nodes are added on the UI thread.
        """
        snapshot = self.snapshot
        if snapshot is None:
            return
        visible = self._visible_paths(snapshot)
        self._loaded_paths = {"/"}
        for record in snapshot.nodes:
            if record.parent_path is None and record.path in visible:
                self._add_node_to_ui(self.root, self._record_to_dto(record))
        if self._last_selected_path:
            path = self._last_selected_path
            self._last_selected_path = None
            if path in visible:
                self._select_path_from_snapshot(path)

    def _record_to_dto(self, record: DefinitionNode) -> NodeDTO:
        """Convert an immutable node record to tree-rendering data.

        Parameters
        ----------
        record : DefinitionNode
            Definition record to render.

        Returns
        -------
        NodeDTO
            Display values for one tree node.
        """
        return NodeDTO(
            name=record.name,
            path=record.path,
            state=record.state,
            is_container=record.is_container,
            has_children=record.has_children,
        )

    def _populate_root(self) -> None:
        """Render suite roots from the installed snapshot.

        Returns
        -------
        None
            Visible suite nodes are added on the UI thread.
        """
        self._populate_snapshot_roots()

    def _add_nodes_batch(self, parent_ui_node: TreeNode[str], node_dtos: list[NodeDTO]) -> None:
        """
        Batch add nodes to the UI to reduce main thread pressure.

        Args:
            parent_ui_node: The parent UI node.
            node_dtos: List of NodeDTO objects to add.

        Returns:
            None
        """
        for dto in node_dtos:
            self._add_node_to_ui(parent_ui_node, dto)

    def _to_dto(self, node: ecflow.Node) -> NodeDTO:
        """
        Convert an ecflow.Node to a NodeDTO.

        Args:
            node: The ecFlow node to convert.

        Returns:
            The corresponding NodeDTO.
        """
        has_children = False
        is_container = isinstance(node, ecflow.Suite | ecflow.Family)
        if is_container:
            try:
                # Optimized check: check if nodes iterator is non-empty
                # Note: ecFlow nodes iterator might not support bool() or direct any()
                # in all environments, so we use a standard iterator check.
                for _ in node.nodes:
                    has_children = True
                    break
            except (StopIteration, RuntimeError):
                pass

        return NodeDTO(
            name=node.name(),
            path=node.get_abs_node_path(),
            state=str(node.get_state()),
            is_container=is_container,
            has_children=has_children,
        )

    def _should_show_node(self, node: Node | DefinitionNode) -> bool:
        """Check whether a node belongs in the current snapshot view.

        Parameters
        ----------
        node : ecflow.Node | DefinitionNode
            Node whose path should be checked.

        Returns
        -------
        bool
            Whether the node is in the indexed visible-path set.
        """
        snapshot = self.snapshot
        if snapshot is not None:
            path = node.path if isinstance(node, DefinitionNode) else node.get_abs_node_path()
            return path in self._visible_paths(snapshot)

        if isinstance(node, DefinitionNode):
            return False
        if self.focus_mode and str(node.get_state()) == "complete":
            return False
        if self.current_filter is None:
            return True
        return str(node.get_state()) == self.current_filter

    def action_cycle_filter(self) -> None:
        """
        Cycle through available status filters and refresh the tree.

        Returns:
            None
        """
        current_idx = self.filters.index(self.current_filter)
        next_idx = (current_idx + 1) % len(self.filters)
        self.current_filter = self.filters[next_idx]

        self.app.notify(f"Filter: {self.current_filter or 'All'}")

    def action_toggle_focus(self) -> None:
        """
        Toggle Focus Mode and refresh the tree.

        Returns:
            None
        """
        self.focus_mode = not self.focus_mode
        state = "ON" if self.focus_mode else "OFF"
        self.app.notify(f"Focus Mode: {state}")

    def _add_node_to_ui(self, parent_ui_node: TreeNode[str], dto: NodeDTO) -> TreeNode[str]:
        """
        Add a single ecflow node to the UI tree using a DTO.

        Args:
            parent_ui_node: The parent node in the Textual tree.
            dto: The NodeDTO to add.

        Returns:
            The newly created UI node.
        """
        icon = STATE_MAP.get(dto.state, ICON_UNKNOWN_STATE)
        type_icon = ICON_FAMILY if dto.is_container else ICON_TASK

        label = Text(f"{icon} {type_icon} {dto.name} ")
        label.append(f"[{dto.state}]", style="bold italic")

        new_ui_node = parent_ui_node.add(
            label,
            data=dto.path,
            expand=False,
        )

        # If it's a container and has children, add a placeholder for lazy loading
        if dto.is_container and dto.has_children:
            new_ui_node.add(LOADING_PLACEHOLDER, allow_expand=False)

        return new_ui_node

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[str]) -> None:
        """
        Handle node expansion to load children on demand.

        Args:
            event: The expansion event.

        Returns:
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

        Returns:
            None

        Notes:
            Uses `_load_children_worker` for async loading.
        """
        if self.snapshot is None:
            return
        self._populate_snapshot_children(ui_node)

    def _populate_snapshot_children(self, ui_node: TreeNode[str], reveal_path: str | None = None) -> None:
        """Materialize direct children from plain snapshot records.

        Parameters
        ----------
        ui_node : TreeNode[str]
            Parent widget node to populate.
        reveal_path : str | None, optional
            Search target whose otherwise filtered ancestors should be included.

        Returns
        -------
        None
            Direct child widgets are created on the UI thread.
        """
        snapshot = self.snapshot
        if snapshot is None:
            return
        parent_path = ui_node.data or "/"
        if parent_path in self._loaded_paths:
            return

        if ui_node.data:
            parent = snapshot.by_path.get(ui_node.data)
            if parent is None:
                return
            child_paths = parent.child_paths
        else:
            child_paths = tuple(record.path for record in snapshot.nodes if record.parent_path is None)

        visible = self._visible_paths(snapshot)
        for child in list(ui_node.children):
            child.remove()
        child_records = []
        for child_path in child_paths:
            record = snapshot.by_path[child_path]
            leads_to_target = reveal_path is not None and (
                reveal_path == child_path or reveal_path.startswith(child_path.rstrip("/") + "/")
            )
            if child_path in visible or leads_to_target:
                child_records.append(self._record_to_dto(record))
        for start in range(0, len(child_records), 50):
            self._add_nodes_batch(ui_node, child_records[start : start + 50])
        self._loaded_paths.add(parent_path)

    def invalidate_search(self) -> int:
        """Invalidate pending search results and return the new generation.

        Returns
        -------
        int
            Generation that supersedes all outstanding searches.
        """
        self._search_generation += 1
        self._pending_search = None
        return self._search_generation

    def find_and_select(self, query: str) -> int:
        """Search the current immutable snapshot for a node path.

        Parameters
        ----------
        query : str
            Search text to match against absolute node paths.

        Returns
        -------
        int
            Generation assigned to this search request.
        """
        generation = self.invalidate_search()
        normalized_query = query.strip()
        if not normalized_query:
            return generation
        snapshot = self.snapshot
        if snapshot is None:
            self._pending_search = (generation, normalized_query)
            return generation
        self._start_search(normalized_query, generation, snapshot)
        return generation

    def _start_search(self, query: str, generation: int, snapshot: DefinitionSnapshot) -> None:
        """Start search work using only the query and immutable snapshot.

        Parameters
        ----------
        query : str
            Query to match.
        generation : int
            Current request generation.
        snapshot : DefinitionSnapshot
            Immutable source for path matching.

        Returns
        -------
        None
            Work is scheduled or applied synchronously for a detached widget.
        """
        cursor_node = self.cursor_node
        current_path = cursor_node.data if cursor_node else None
        try:
            app_is_running = self.is_attached and self.app.is_running
        except (AttributeError, RuntimeError):
            app_is_running = False
        if app_is_running:
            self._search_snapshot_worker(query, generation, snapshot, current_path)
        else:
            result_path = self._find_path(snapshot, query, current_path)
            self._apply_search_result(generation, snapshot.generation, result_path, query)

    @work(group="node-search", exclusive=True, thread=True)
    def _search_snapshot_worker(
        self,
        query: str,
        generation: int,
        snapshot: DefinitionSnapshot,
        current_path: str | None,
    ) -> None:
        """Find a path in immutable worker input and publish the plain result.

        Parameters
        ----------
        query : str
            Search text.
        generation : int
            Search request generation.
        snapshot : DefinitionSnapshot
            Immutable node index captured by the UI thread.
        current_path : str | None
            Selection captured by the UI thread for next-match ordering.

        Returns
        -------
        None
            A path or no-match result is sent to the UI thread.
        """
        result_path = self._find_path(snapshot, query, current_path)
        self._safe_call(self._apply_search_result, generation, snapshot.generation, result_path, query)

    @staticmethod
    def _find_path(snapshot: DefinitionSnapshot, query: str, current_path: str | None) -> str | None:
        """Find the next matching path, wrapping around from the selection.

        Parameters
        ----------
        snapshot : DefinitionSnapshot
            Immutable ordered path index.
        query : str
            Text to match case-insensitively.
        current_path : str | None
            Currently selected path, if any.

        Returns
        -------
        str | None
            Next matching absolute path, or ``None`` when there is no match.
        """
        if not snapshot.paths:
            return None
        query_lower = query.casefold()
        start_index = snapshot.paths.index(current_path) + 1 if current_path in snapshot.paths else 0
        for offset in range(len(snapshot.paths)):
            index = (start_index + offset) % len(snapshot.paths)
            if query_lower in snapshot.paths_lower[index]:
                return snapshot.paths[index]
        return None

    def _apply_search_result(
        self,
        generation: int,
        definition_generation: int,
        result_path: str | None,
        query: str,
    ) -> None:
        """Apply a result only while both query and definitions are current.

        Parameters
        ----------
        generation : int
            Search request generation returned by the worker.
        definition_generation : int
            Snapshot generation used for matching.
        result_path : str | None
            Matching absolute path, if any.
        query : str
            Original query used for the result message.

        Returns
        -------
        None
            Current results select a node or report no match.
        """
        snapshot = self.snapshot
        if generation != self._search_generation or snapshot is None:
            return
        if definition_generation != snapshot.generation:
            return
        if result_path is None:
            self.app.notify(f"No match found for '{query}'", severity="warning")
            return
        self._select_path_from_snapshot(result_path)

    def _find_and_select_logic(self, query: str) -> None:
        """Run a synchronous search for direct UI-thread callers.

        Parameters
        ----------
        query : str
            Search text.

        Returns
        -------
        None
            A matching path is selected if the snapshot contains one.
        """
        if self.snapshot is None:
            return
        cursor_node = self.cursor_node
        current_path = cursor_node.data if cursor_node else None
        result_path = self._find_path(self.snapshot, query, current_path)
        self._apply_search_result(self._search_generation, self.snapshot.generation, result_path, query)

    def _select_path_from_snapshot(self, path: str) -> None:
        """Materialize a path from snapshot records and select it on the UI thread.

        Parameters
        ----------
        path : str
            Absolute ecFlow path to reveal and select.

        Returns
        -------
        None
            The target node is selected when it belongs to the active snapshot.
        """
        snapshot = self.snapshot
        if snapshot is None or path not in snapshot.by_path:
            return
        current_ui_node = self.root
        current_path = ""
        for part in path.strip("/").split("/"):
            current_path += "/" + part
            if current_path not in self._loaded_paths:
                self._populate_snapshot_children(current_ui_node, reveal_path=path)
            current_ui_node = next(
                (child for child in current_ui_node.children if child.data == current_path),
                None,
            )
            if current_ui_node is None:
                return
            current_ui_node.expand()
        self.refresh(layout=True)
        self.call_after_refresh(self._select_after_layout, current_ui_node)

    def _select_after_layout(self, node: TreeNode[str]) -> None:
        """Wait until the target has a rendered tree line before selection.

        Parameters
        ----------
        node : TreeNode[str]
            Materialized target node.

        Returns
        -------
        None
            The node is selected after layout assigns its visible line.
        """
        if node._line < 0:
            self.refresh(layout=True)
            self.call_after_refresh(self._select_after_layout, node)
            return
        self._select_and_reveal(node)

    def _safe_call(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Deliver a UI callback on the Textual thread and drop it after shutdown.

        Parameters
        ----------
        callback : Callable[..., Any]
            The UI callback to deliver.
        *args : Any
            Positional callback arguments.
        **kwargs : Any
            Keyword callback arguments.

        Returns
        -------
        Any
            The callback result or ``None`` when delivery is unavailable.
        """
        try:
            return safe_call_app(self.app, callback, *args, **kwargs)
        except (AttributeError, RuntimeError):
            return None

    def select_by_path(self, path: str) -> None:
        """Select a node path from the active snapshot.

        Parameters
        ----------
        path : str
            Absolute ecFlow path to reveal and select.

        Returns
        -------
        None
            The matching node is selected on the UI thread.
        """
        self._select_by_path_logic(path)

    def _select_by_path_logic(self, path: str) -> None:
        """Select a node path using the UI-owned tree and snapshot.

        Parameters
        ----------
        path : str
            Absolute ecFlow path to reveal and select.

        Returns
        -------
        None
            The matching node is selected when it exists in the snapshot.
        """
        if path == "/":
            self.select_node(self.root)
        else:
            self._select_path_from_snapshot(path)

    def _select_and_reveal(self, node: TreeNode[str]) -> None:
        """
        Select a node and expand all its parents.

        Args:
            node: The node to select and reveal.

        Returns:
            None
        """
        self.select_node(node)
        parent = node.parent
        while parent:
            parent.expand()
            parent = parent.parent
        self.scroll_to_node(node)
