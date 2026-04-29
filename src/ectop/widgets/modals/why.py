# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Modal screen for inspecting why an ecFlow node is not running.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING

import ecflow
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Tree
from textual.widgets.tree import TreeNode

from ectop.client import EcflowClient
from ectop.constants import (
    EXPR_AND_LABEL,
    EXPR_OR_LABEL,
    ICON_CRON,
    ICON_DATE,
    ICON_MET,
    ICON_NOT_MET,
    ICON_NOTE,
    ICON_REASON,
    ICON_TIME,
    ICON_UNKNOWN,
)
from ectop.utils import safe_call_app

# Pre-compile the regex for expression parsing to improve performance
EXPR_RE = re.compile(r"(!?\s*)(/[a-zA-Z0-9_\-\./]+)(\s*(==|!=|<=|>=|<|>)\s*(\w+))?")

if TYPE_CHECKING:
    from ecflow import Defs, Node


@dataclass
class DepData:
    """
    Intermediate data structure for dependency information.

    Attributes
    ----------
    label : str
        The text to display for this dependency.
    path : str | None
        The ecFlow path if this represents a node, otherwise None.
    is_met : bool
        Whether this dependency is currently satisfied.
    children : list[DepData]
        Nested dependencies.
    icon : str | None
        Optional icon override.
    """

    label: str
    path: str | None = None
    is_met: bool = True
    children: list[DepData] = field(default_factory=list)
    icon: str | None = None


class WhyInspector(ModalScreen[None]):
    """
    A modal screen to inspect dependencies and triggers of an ecFlow node.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("w", "close", "Close"),
    ]

    def __init__(self, node_path: str, client: EcflowClient) -> None:
        """
        Initialize the WhyInspector.

        Parameters
        ----------
        node_path : str
            The absolute path to the ecFlow node.
        client : EcflowClient
            The ecFlow client instance.

        Returns
        -------
        None
        """
        super().__init__()
        self.node_path: str = node_path
        self.client: EcflowClient = client
        self._state_map = {
            "unknown": ecflow.State.unknown,
            "complete": ecflow.State.complete,
            "queued": ecflow.State.queued,
            "aborted": ecflow.State.aborted,
            "submitted": ecflow.State.submitted,
            "active": ecflow.State.active,
        }

    def compose(self) -> ComposeResult:
        """
        Compose the modal UI.

        Returns
        -------
        ComposeResult
            The UI components for the modal.
        """
        with Vertical(id="why_container"):
            yield Static(f"Why is {self.node_path} not running?", id="why_title")
            yield Tree("Dependencies", id="dep_tree")
            with Horizontal(id="why_actions"):
                yield Button("Close", variant="primary", id="close_btn")

    def on_mount(self) -> None:
        """
        Handle the mount event to initialize the dependency tree.

        Returns
        -------
        None
        """
        self.refresh_deps()

    def action_close(self) -> None:
        """
        Close the modal.

        Returns
        -------
        None
        """
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events.

        Parameters
        ----------
        event : Button.Pressed
            The button press event.

        Returns
        -------
        None
        """
        if event.button.id == "close_btn":
            self.app.pop_screen()

    def on_tree_node_selected(self, event: Tree.NodeSelected[str]) -> None:
        """
        Jump to the selected dependency node in the main tree.

        Parameters
        ----------
        event : Tree.NodeSelected[str]
            The tree node selection event.

        Returns
        -------
        None
        """
        node_path = event.node.data
        if node_path:
            from ectop.widgets.sidebar import SuiteTree

            try:
                tree = self.app.query_one("#suite_tree", SuiteTree)
                tree.select_by_path(node_path)
                self.app.notify(f"Jumped to {node_path}")
                self.app.pop_screen()
            except Exception as e:
                self.app.notify(f"Failed to jump: {e}", severity="error")

    def refresh_deps(self) -> None:
        """
        Fetch dependencies from the server and rebuild the tree.

        Returns
        -------
        None
        """
        self._refresh_deps_worker()

    @work(thread=True)
    def _refresh_deps_worker(self) -> None:
        """
        Worker to fetch dependencies from the server and rebuild the tree.

        Returns
        -------
        None

        Notes
        -----
        This is a background thread worker.
        """
        self._refresh_deps_logic()

    def _refresh_deps_logic(self) -> None:
        """
        The actual logic for fetching dependencies and updating the UI tree.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If server synchronization fails.
        """
        tree = self.query_one("#dep_tree", Tree)
        try:
            self.client.sync_local_sync()
            defs = self.client.get_defs_sync()
            if not defs:
                safe_call_app(self.app, self._update_tree_ui, tree, DepData("Server Empty"))
                return

            node = defs.find_abs_node(self.node_path)
            if not node:
                safe_call_app(self.app, self._update_tree_ui, tree, DepData("Node not found"))
                return

            # Gather data (this is currently CPU-bound parsing)
            dep_data = self._gather_dependency_data(node, defs)

            # Update UI
            safe_call_app(self.app, self._update_tree_ui, tree, dep_data)

        except RuntimeError as e:
            safe_call_app(self.app, self._update_tree_ui, tree, DepData(f"Error: {e}"))
        except Exception as e:
            safe_call_app(self.app, self._update_tree_ui, tree, DepData(f"Unexpected Error: {e}"))

    def _gather_dependency_data(self, node: Node, defs: Defs) -> DepData:
        """
        Gather dependency data from an ecFlow node.

        Parameters
        ----------
        node : Node
            The ecFlow node to inspect.
        defs : Defs
            The ecFlow definitions for node lookups.

        Returns
        -------
        DepData
            The root dependency data object.
        """
        root = DepData("Dependencies")

        # Reason
        try:
            why_str = node.get_why()
            if why_str:
                root.children.append(DepData(f"Reason: {why_str}", icon=ICON_REASON))
        except (AttributeError, RuntimeError):
            pass

        # Triggers
        try:
            trigger = node.get_trigger()
            if trigger:
                trigger_root = DepData("Triggers")
                self._parse_expression_data(trigger_root, trigger.get_expression(), defs)
                root.children.append(trigger_root)
        except (AttributeError, RuntimeError) as e:
            root.children.append(DepData(f"Trigger Error: {e}", icon=ICON_NOT_MET, is_met=False))

        # Complete
        try:
            complete = node.get_complete()
            if complete:
                complete_root = DepData("Complete Expression")
                self._parse_expression_data(complete_root, complete.get_expression(), defs)
                root.children.append(complete_root)
        except (AttributeError, RuntimeError) as e:
            root.children.append(DepData(f"Complete Expr Error: {e}", icon=ICON_NOT_MET, is_met=False))

        # Limits
        try:
            inlimits = list(node.inlimits)
            if inlimits:
                limit_root = DepData("Limits")
                for il in inlimits:
                    # InLimit.value() does not exist in ecFlow Python API, but name() and path_to_node() do.
                    # Or we just use str(il) which often gives 'inlimit name path'
                    path = il.path_to_node() or "Self"
                    limit_root.children.append(DepData(f"Limit: {il.name()} (Path: {path})", icon="🔒"))
                root.children.append(limit_root)
        except (AttributeError, RuntimeError):
            pass

        # Times, Dates, Crons
        try:
            time_root = DepData("Time Dependencies")
            has_time = False

            # We try to use the most common methods/attributes.
            # Real ecFlow has .times, .dates, .crons attributes.
            # Some older/mock versions use get_times(), etc.

            times = []
            for attr in ["times", "get_times"]:
                try:
                    val = getattr(node, attr)
                    times = list(val() if callable(val) else val)
                    if times:
                        break
                except (AttributeError, RuntimeError, TypeError):
                    continue
            for t in times:
                time_root.children.append(DepData(f"Time: {t}", icon=ICON_TIME))
                has_time = True

            dates = []
            for attr in ["dates", "get_dates"]:
                try:
                    val = getattr(node, attr)
                    dates = list(val() if callable(val) else val)
                    if dates:
                        break
                except (AttributeError, RuntimeError, TypeError):
                    continue
            for d in dates:
                time_root.children.append(DepData(f"Date: {d}", icon=ICON_DATE))
                has_time = True

            crons = []
            for attr in ["crons", "get_crons"]:
                try:
                    val = getattr(node, attr)
                    crons = list(val() if callable(val) else val)
                    if crons:
                        break
                except (AttributeError, RuntimeError, TypeError):
                    continue
            for c in crons:
                time_root.children.append(DepData(f"Cron: {c}", icon=ICON_CRON))
                has_time = True

            if has_time:
                root.children.append(time_root)
        except (AttributeError, RuntimeError):
            pass

        return root

    def _parse_expression_data(self, parent: DepData, expr_str: str, defs: Defs) -> bool:
        """
        Parse an ecFlow expression and populate DepData objects.

        Parameters
        ----------
        parent : DepData
            The parent DepData object.
        expr_str : str
            The expression string to parse.
        defs : Defs
            The ecFlow definitions for node lookups.

        Returns
        -------
        bool
            True if the expression is currently met.
        """
        try:
            tree = _get_expr_tree(expr_str)
            return self._evaluate_expr_tree(parent, tree, defs)
        except Exception as e:
            parent.children.append(DepData(f"Parse Error: {expr_str} ({e})", is_met=False, icon=ICON_NOT_MET))
            return False

    def _evaluate_expr_tree(self, parent: DepData, tree: dict, defs: Defs) -> bool:
        """
        Evaluate a parsed expression tree against ecFlow definitions.

        Parameters
        ----------
        parent : DepData
            The parent DepData object.
        tree : dict
            The parsed expression tree.
        defs : Defs
            The ecFlow definitions for node lookups.

        Returns
        -------
        bool
            True if the expression is currently met.
        """
        expr_type = tree["type"]

        if expr_type == "empty":
            return True

        if expr_type == "not":
            not_node = DepData("NOT (Must be false)")
            inner_met = self._evaluate_expr_tree(not_node, tree["child"], defs)
            is_met = not inner_met
            not_node.is_met = is_met
            parent.children.append(not_node)
            return is_met

        if expr_type in ("and", "or"):
            label = EXPR_AND_LABEL if expr_type == "and" else EXPR_OR_LABEL
            op_node = DepData(label)
            is_met_left = self._evaluate_expr_tree(op_node, tree["left"], defs)
            is_met_right = self._evaluate_expr_tree(op_node, tree["right"], defs)
            is_met = (is_met_left and is_met_right) if expr_type == "and" else (is_met_left or is_met_right)
            op_node.is_met = is_met
            parent.children.append(op_node)
            return is_met

        if expr_type == "leaf":
            negation = tree["negation"]
            path = tree["path"]
            op = tree["op"]
            expected_state_str = tree["expected"]
            target_node = defs.find_abs_node(path)

            if target_node is not None:
                actual_state = target_node.get_state()

                # For tests where get_state might return a string mock
                if isinstance(actual_state, str):
                    expected_state = expected_state_str
                else:
                    expected_state = self._state_map.get(expected_state_str, ecflow.State.complete)

                is_met = False
                if op == "==":
                    is_met = actual_state == expected_state
                elif op == "!=":
                    is_met = actual_state != expected_state
                elif op == "<":
                    is_met = actual_state < expected_state
                elif op == ">":
                    is_met = actual_state > expected_state
                elif op == "<=":
                    is_met = actual_state <= expected_state
                elif op == ">=":
                    is_met = actual_state >= expected_state

                if negation == "!":
                    is_met = not is_met

                neg_str = "! " if negation == "!" else ""
                label = f"{neg_str}{path} {op} {str(actual_state)} (Expected: {expected_state_str})"
                if str(actual_state) == "aborted":
                    label = f"[b red]{label} (STOPPED HERE)[/]"

                parent.children.append(DepData(label, path=path, is_met=is_met))
                return is_met
            else:
                parent.children.append(DepData(f"{path} (Not found)", is_met=False, icon=ICON_UNKNOWN))
                return False

        if expr_type == "literal":
            parent.children.append(DepData(tree["value"], icon=ICON_NOTE))
            return True

        return True

    def _update_tree_ui(self, tree: Tree, data: DepData) -> None:
        """
        Update the tree UI from DepData.

        Parameters
        ----------
        tree : Tree
            The tree widget.
        data : DepData
            The root dependency data.

        Returns
        -------
        None
        """
        tree.clear()
        tree.root.label = data.label
        for child in data.children:
            self._add_to_tree(tree.root, child)
        tree.root.expand_all()

    def _add_to_tree(self, parent_node: TreeNode[str], data: DepData) -> None:
        """
        Recursively add DepData to the Textual Tree.

        Parameters
        ----------
        parent_node : TreeNode[str]
            The parent TreeNode.
        data : DepData
            The DepData to add.

        Returns
        -------
        None
        """
        icon = data.icon or (ICON_MET if data.is_met else ICON_NOT_MET)
        label = f"{icon} {data.label}"
        new_node = parent_node.add(label, data=data.path, expand=True)
        for child in data.children:
            self._add_to_tree(new_node, child)


@lru_cache(maxsize=128)
def _get_expr_tree(expr_str: str) -> dict:
    """
    Parse an ecFlow expression string into a tree structure. Cached for performance.

    Parameters
    ----------
    expr_str : str
        The expression string to parse.

    Returns
    -------
    dict
        A dictionary representing the expression tree.
    """
    expr_str = expr_str.strip()
    if not expr_str:
        return {"type": "empty"}

    # Remove outer parentheses
    while expr_str.startswith("(") and expr_str.endswith(")"):
        depth = 0
        is_pair = True
        for i, char in enumerate(expr_str):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if depth == 0 and i < len(expr_str) - 1:
                is_pair = False
                break
        if is_pair:
            expr_str = expr_str[1:-1].strip()
        else:
            break

    # NOT operator
    if expr_str.startswith("!"):
        return {"type": "not", "child": _get_expr_tree(expr_str[1:].strip())}

    # AND/OR operators
    for op in (" or ", " and "):
        depth = 0
        for i in range(len(expr_str)):
            if expr_str[i] == "(":
                depth += 1
            elif expr_str[i] == ")":
                depth -= 1
            elif depth == 0 and expr_str[i : i + len(op)] == op:
                return {
                    "type": op.strip(),
                    "left": _get_expr_tree(expr_str[:i].strip()),
                    "right": _get_expr_tree(expr_str[i + len(op) :].strip()),
                }

    # Leaf node
    match = EXPR_RE.search(expr_str)
    if match:
        return {
            "type": "leaf",
            "negation": match.group(1).strip(),
            "path": match.group(2),
            "op": match.group(4) or "==",
            "expected": match.group(5) or "complete",
        }

    return {"type": "literal", "value": expr_str}
