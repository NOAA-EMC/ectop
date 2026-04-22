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
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from ecflow import Defs, Node


@dataclass
class DepData:
    """
    Intermediate data structure for dependency information.

    Attributes:
        label: The text to display for this dependency.
        path: The ecFlow path if this represents a node, otherwise None.
        is_met: Whether this dependency is currently satisfied.
        children: Nested dependencies.
        icon: Optional icon override.
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

        Parameters:
            node_path: The absolute path to the ecFlow node.
            client: The ecFlow client instance.
        """
        super().__init__()
        self.node_path: str = node_path
        self.client: EcflowClient = client

    def compose(self) -> ComposeResult:
        """
        Compose the modal UI.

        Returns:
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
        """
        self.refresh_deps()

    def action_close(self) -> None:
        """
        Close the modal.
        """
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events.

        Parameters:
            event: The button press event.
        """
        if event.button.id == "close_btn":
            self.app.pop_screen()

    def on_tree_node_selected(self, event: Tree.NodeSelected[str]) -> None:
        """
        Jump to the selected dependency node in the main tree.

        Parameters:
            event: The tree node selection event.
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
        """
        tree = self.query_one("#dep_tree", Tree)
        self._refresh_deps_worker(tree)

    @work()
    async def _refresh_deps_worker(self, tree: Tree) -> None:
        """
        Worker to fetch dependencies from the server and rebuild the tree.

        Parameters:
            tree: The tree widget to refresh.

        Notes:
            This is a background worker that performs async I/O.
        """
        await self._refresh_deps_logic(tree)

    async def _refresh_deps_logic(self, tree: Tree) -> None:
        """
        The actual logic for fetching dependencies and updating the UI tree.

        Parameters:
            tree: The tree widget to refresh.

        Raises:
            RuntimeError: If server synchronization fails.
        """
        try:
            await self.client.sync_local()
            defs = await self.client.get_defs()
            if not defs:
                self._update_tree_ui(tree, DepData("Server Empty"))
                return

            node = defs.find_abs_node(self.node_path)
            if not node:
                self._update_tree_ui(tree, DepData("Node not found"))
                return

            # Gather data in the worker thread
            dep_data = self._gather_dependency_data(node, defs)

            # Update UI
            self._update_tree_ui(tree, dep_data)

        except RuntimeError as e:
            self._update_tree_ui(tree, DepData(f"Error: {e}"))
        except Exception as e:
            self._update_tree_ui(tree, DepData(f"Unexpected Error: {e}"))

    def _gather_dependency_data(self, node: Node, defs: Defs) -> DepData:
        """
        Gather dependency data from an ecFlow node.

        Parameters
        ----------
        node : ecflow.Node
            The ecFlow node to inspect.
        defs : ecflow.Defs
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
                    limit_root.children.append(DepData(f"Limit: {il.name()} (Path: {il.value()})", icon="🔒"))
                root.children.append(limit_root)
        except (AttributeError, RuntimeError):
            pass

        # Times, Dates, Crons
        try:
            time_root = DepData("Time Dependencies")
            has_time = False
            for t in node.get_times():
                time_root.children.append(DepData(f"Time: {t}", icon=ICON_TIME))
                has_time = True
            for d in node.get_dates():
                time_root.children.append(DepData(f"Date: {d}", icon=ICON_DATE))
                has_time = True
            for c in node.get_crons():
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
        defs : ecflow.Defs
            The ecFlow definitions for node lookups.

        Returns
        -------
        bool
            True if the expression is currently met.
        """
        try:
            expr_str = expr_str.strip()
            if not expr_str:
                return True

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
                not_node = DepData("NOT (Must be false)")
                inner_met = self._parse_expression_data(not_node, expr_str[1:].strip(), defs)
                is_met = not inner_met
                not_node.is_met = is_met
                parent.children.append(not_node)
                return is_met

            # AND/OR operators
            for op, label in [(" or ", EXPR_OR_LABEL), (" and ", EXPR_AND_LABEL)]:
                depth = 0
                for i in range(len(expr_str)):
                    if expr_str[i] == "(":
                        depth += 1
                    elif expr_str[i] == ")":
                        depth -= 1
                    if depth == 0 and expr_str[i : i + len(op)] == op:
                        op_node = DepData(label)
                        left = expr_str[:i].strip()
                        right = expr_str[i + len(op) :].strip()
                        is_met_left = self._parse_expression_data(op_node, left, defs)
                        is_met_right = self._parse_expression_data(op_node, right, defs)
                        is_met = (is_met_left or is_met_right) if op == " or " else (is_met_left and is_met_right)
                        op_node.is_met = is_met
                        parent.children.append(op_node)
                        return is_met

            # Leaf node
            match = re.search(r"(!?\s*)(/[a-zA-Z0-9_\-\./]+)(\s*(==|!=|<=|>=|<|>)\s*(\w+))?", expr_str)
            if match:
                negation = match.group(1).strip()
                path = match.group(2)
                op = match.group(4) or "=="
                expected_state = match.group(5) or "complete"
                target_node = defs.find_abs_node(path)

                if target_node is not None:
                    actual_state = str(target_node.get_state())
                    is_met = False
                    if op == "==":
                        is_met = actual_state == expected_state
                    elif op == "!=":
                        is_met = actual_state != expected_state

                    if negation == "!":
                        is_met = not is_met

                    neg_str = "! " if negation == "!" else ""
                    label = f"{neg_str}{path} {op} {actual_state} (Expected: {expected_state})"
                    if actual_state == "aborted":
                        label = f"[b red]{label} (STOPPED HERE)[/]"

                    parent.children.append(DepData(label, path=path, is_met=is_met))
                    return is_met
                else:
                    parent.children.append(DepData(f"{path} (Not found)", is_met=False, icon=ICON_UNKNOWN))
                    return False
            else:
                parent.children.append(DepData(expr_str, icon=ICON_NOTE))
                return True
        except Exception as e:
            parent.children.append(DepData(f"Parse Error: {expr_str} ({e})", is_met=False, icon=ICON_NOT_MET))
            return False

    def _update_tree_ui(self, tree: Tree, data: DepData) -> None:
        """
        Update the tree UI from DepData.

        Parameters:
            tree: The tree widget.
            data: The root dependency data.
        """
        tree.clear()
        tree.root.label = data.label
        for child in data.children:
            self._add_to_tree(tree.root, child)
        tree.root.expand_all()

    def _add_to_tree(self, parent_node: TreeNode[str], data: DepData) -> None:
        """
        Recursively add DepData to the Textual Tree.

        Parameters:
            parent_node: The parent TreeNode.
            data: The DepData to add.
        """
        icon = data.icon or (ICON_MET if data.is_met else ICON_NOT_MET)
        label = f"{icon} {data.label}"
        new_node = parent_node.add(label, data=data.path, expand=True)
        for child in data.children:
            self._add_to_tree(new_node, child)
