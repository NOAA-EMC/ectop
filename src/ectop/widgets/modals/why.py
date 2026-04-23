# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Modal screen for inspecting 'why' a node is not running.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode

from ectop.constants import (
    EXPR_AND_LABEL,
    EXPR_OR_LABEL,
    ICON_MET,
    ICON_NOT_MET,
    ICON_REASON,
    ICON_UNKNOWN,
)

if TYPE_CHECKING:
    from ecflow import Defs, Node

    from ectop.client import EcflowClient


@dataclass
class DepData:
    """Data structure representing a dependency.

    Attributes:
        label (str): The display label.
        path (str | None): Node path.
        is_met (bool): Whether dependency is met.
        icon (str | None): Icon override.
        children (list[DepData]): Sub-dependencies.
    """

    label: str
    path: str | None = None
    is_met: bool = True
    icon: str | None = None
    children: list[DepData] = field(default_factory=list)


class WhyInspector(ModalScreen[None]):
    """
    A modal screen for inspecting node dependencies and status.
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("w", "close", "Close"),
        Binding("enter", "jump_to_node", "Jump to Node"),
    ]

    def __init__(self, node_path: str, client: EcflowClient) -> None:
        """Initialize the WhyInspector.

        Args:
            node_path (str): Path to inspect.
            client (EcflowClient): Client instance.
        """
        super().__init__()
        self.node_path: str = node_path
        self.client: EcflowClient = client

    def compose(self) -> ComposeResult:
        """Compose UI components.

        Returns:
            ComposeResult: The UI tree.
        """
        with Vertical(id="why_container"):
            yield Static(f"Why {self.node_path}?", id="why_title")
            yield Tree("Dependencies", id="dep_tree")
            yield Static("Press ENTER to jump, ESC or 'w' to close", id="why_footer")

    def on_mount(self) -> None:
        """Handle mount event."""
        self.refresh_why()

    def action_close(self) -> None:
        """Close modal."""
        self.app.pop_screen()

    def action_jump_to_node(self) -> None:
        """Jump to selected node."""
        tree = self.query_one("#dep_tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            path = tree.cursor_node.data
            try:
                from ectop.app import Ectop

                if isinstance(self.app, Ectop):
                    self.app.pop_screen()
                    self.app.call_later(self.app.query_one("#suite_tree").select_by_path, path)
            except Exception as e:
                self.app.notify(f"Failed to jump: {e}", severity="error")

    @work()
    async def refresh_why(self) -> None:
        """Worker to refresh dependency data."""
        try:
            await self.client.sync_local()
            defs = await self.client.get_defs()
            if not defs:
                self._update_ui(DepData("Server Empty"))
                return

            node = defs.find_abs_node(self.node_path)
            if not node:
                self._update_ui(DepData("Node not found"))
                return

            dep_data = self._gather_dependency_data(node, defs)
            self._update_ui(dep_data)

        except RuntimeError as e:
            self._update_ui(DepData(f"Error: {e}"))
        except Exception as e:
            self._update_ui(DepData(f"Unexpected Error: {e}"))

    def _update_ui(self, data: DepData) -> None:
        """Update the tree UI on main thread.

        Args:
            data (DepData): Data to display.
        """
        tree = self.query_one("#dep_tree", Tree)
        tree.clear()
        tree.root.label = data.label
        for child in data.children:
            self._add_to_tree(tree.root, child)
        tree.root.expand_all()

    def _gather_dependency_data(self, node: Node, defs: Defs) -> DepData:
        """Gather dependency data from node.

        Args:
            node (Node): ecFlow node.
            defs (Defs): Global defs.

        Returns:
            DepData: Dependency tree root.
        """
        root = DepData("Dependencies")
        try:
            why_str = node.get_why()
            if why_str:
                root.children.append(DepData(f"Reason: {why_str}", icon=ICON_REASON))
        except (AttributeError, RuntimeError):
            pass

        try:
            trigger = node.get_trigger()
            if trigger:
                t_root = DepData("Triggers")
                self._parse_expression_data(t_root, trigger.get_expression(), defs)
                root.children.append(t_root)
        except (AttributeError, RuntimeError) as e:
            root.children.append(DepData(f"Trigger Error: {e}", is_met=False))

        return root

    def _parse_expression_data(self, parent: DepData, expr_str: str, defs: Defs) -> bool:
        """Parse expression and build tree.

        Args:
            parent (DepData): Parent data node.
            expr_str (str): Expression string.
            defs (Defs): Global definitions.

        Returns:
            bool: Whether expression is met.
        """
        try:
            expr_str = expr_str.strip()
            if not expr_str:
                return True

            # Handle parentheses
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

            if expr_str.startswith("!"):
                not_node = DepData("NOT (Must be false)")
                is_met = not self._parse_expression_data(not_node, expr_str[1:].strip(), defs)
                not_node.is_met = is_met
                parent.children.append(not_node)
                return is_met

            for op, label in [(" or ", EXPR_OR_LABEL), (" and ", EXPR_AND_LABEL)]:
                depth = 0
                for i in range(len(expr_str)):
                    if expr_str[i] == "(":
                        depth += 1
                    elif expr_str[i] == ")":
                        depth -= 1
                    elif depth == 0 and expr_str[i : i + len(op)] == op:
                        op_node = DepData(label)
                        met_l = self._parse_expression_data(op_node, expr_str[:i].strip(), defs)
                        met_r = self._parse_expression_data(op_node, expr_str[i + len(op) :].strip(), defs)
                        is_met = (met_l or met_r) if op == " or " else (met_l and met_r)
                        op_node.is_met = is_met
                        parent.children.append(op_node)
                        return is_met

            match = re.search(r"(!?\s*)(/[a-zA-Z0-9_\-\./]+)(\s*(==|!=|<=|>=|<|>)\s*(\w+))?", expr_str)
            if match:
                neg, path, _, op, val = match.groups()
                target = defs.find_abs_node(path)
                if target:
                    s = str(target.get_state())
                    met = (s == (val or "complete")) if (not op or op == "==") else (s != val)
                    if neg and "!" in neg:
                        met = not met
                    parent.children.append(DepData(f"{neg or ''}{path} [{s}]", path=path, is_met=met))
                    return met
                parent.children.append(DepData(f"{path} (Not found)", is_met=False, icon=ICON_UNKNOWN))
                return False
            parent.children.append(DepData(expr_str))
            return True
        except Exception as e:
            parent.children.append(DepData(f"Error: {e}", is_met=False))
            return False

    def _add_to_tree(self, ui_node: TreeNode[str], data: DepData) -> None:
        """Recursively add data to UI tree.

        Args:
            ui_node (TreeNode): Parent UI node.
            data (DepData): Data node.
        """
        icon = data.icon or (ICON_MET if data.is_met else ICON_NOT_MET)
        label = Text(f"{icon} {data.label}")
        new_node = ui_node.add(label, data=data.path, expand=True)
        for child in data.children:
            self._add_to_tree(new_node, child)
