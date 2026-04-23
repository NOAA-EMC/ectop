# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Modal screen for viewing and editing ecFlow variables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Static

from ectop.constants import (
    INHERITED_VAR_PREFIX,
    VAR_TYPE_GENERATED,
    VAR_TYPE_INHERITED,
    VAR_TYPE_USER,
)

if TYPE_CHECKING:
    from ectop.client import EcflowClient


class VariableTweaker(ModalScreen[None]):
    """
    A modal screen for managing ecFlow node variables.
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("v", "close", "Close"),
        Binding("a", "add_variable", "Add Variable"),
        Binding("d", "delete_variable", "Delete Variable"),
    ]

    def __init__(self, node_path: str, client: EcflowClient) -> None:
        """
        Initialize the VariableTweaker.

        Parameters
        ----------
        node_path : str
            Absolute node path.
        client : EcflowClient
            Client instance.
        """
        super().__init__()
        self.node_path: str = node_path
        self.client: EcflowClient = client
        self.selected_var_name: str | None = None

    def compose(self) -> ComposeResult:
        """
        Compose UI.

        Returns
        -------
        ComposeResult
            UI components.
        """
        with Vertical(id="var_container"):
            yield Static(f"Variables for {self.node_path}", id="var_title")
            yield DataTable(id="var_table")
            yield Input(placeholder="Enter new value...", id="var_input")
            with Horizontal(id="var_actions"):
                yield Button("Close", variant="primary", id="close_btn")

    def on_mount(self) -> None:
        """
        Handle mount event.
        """
        table = self.query_one("#var_table", DataTable)
        table.add_columns("Name", "Value", "Type")
        table.cursor_type = "row"
        self.refresh_vars()
        self.query_one("#var_input").add_class("hidden")

    def action_close(self) -> None:
        """
        Close modal.
        """
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press.

        Parameters
        ----------
        event : Button.Pressed
            Button press event.
        """
        if event.button.id == "close_btn":
            self.app.pop_screen()

    @work()
    async def refresh_vars(self) -> None:
        """
        Worker to refresh variables from server.
        """
        try:
            await self.client.sync_local()
            defs = await self.client.get_defs()
            if not defs:
                return
            node = defs.find_abs_node(self.node_path)

            if not node:
                self.app.notify("Node not found", severity="error")
                return

            rows: list[tuple[str, str, str, str]] = []
            seen_vars: set[str] = set()

            for var in node.variables:
                rows.append((var.name(), var.value(), VAR_TYPE_USER, var.name()))
                seen_vars.add(var.name())

            for var in node.get_generated_variables():
                rows.append((var.name(), var.value(), VAR_TYPE_GENERATED, var.name()))
                seen_vars.add(var.name())

            parent = node.get_parent()
            while parent:
                for var in parent.variables:
                    if var.name() not in seen_vars:
                        rows.append(
                            (
                                var.name(),
                                var.value(),
                                f"{VAR_TYPE_INHERITED} ({parent.name()})",
                                f"{INHERITED_VAR_PREFIX}{var.name()}",
                            )
                        )
                        seen_vars.add(var.name())
                parent = parent.get_parent()

            self._update_table(rows)

        except RuntimeError as e:
            self.app.notify(f"Error fetching variables: {e}", severity="error")
        except Exception as e:
            self.app.notify(f"Unexpected Error: {e}", severity="error")

    def _update_table(self, rows: list[tuple[str, str, str, str]]) -> None:
        """
        Update table UI.

        Parameters
        ----------
        rows : list
            Rows to add.
        """
        table = self.query_one("#var_table", DataTable)
        table.clear()
        for row in rows:
            table.add_row(row[0], row[1], row[2], key=row[3])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Handle row selection.

        Parameters
        ----------
        event : DataTable.RowSelected
            Selection event.
        """
        row_key = event.row_key.value
        if row_key and row_key.startswith(INHERITED_VAR_PREFIX):
            self.app.notify("Cannot edit inherited variables.", severity="warning")
            return

        self.selected_var_name = row_key
        input_field = self.query_one("#var_input", Input)
        input_field.remove_class("hidden")
        input_field.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle input submission.

        Parameters
        ----------
        event : Input.Submitted
            Submission event.
        """
        if event.input.id == "var_input":
            self._submit_variable_worker(event.value)

    @work()
    async def _submit_variable_worker(self, value: str) -> None:
        """
        Worker to submit variable change.

        Parameters
        ----------
        value : str
            New value.
        """
        try:
            if self.selected_var_name:
                await self.client.alter(self.node_path, "add_variable", self.selected_var_name, value)
                self.app.notify(f"Updated {self.selected_var_name}")
            else:
                if "=" in value:
                    name, val = value.split("=", 1)
                    await self.client.alter(self.node_path, "add_variable", name.strip(), val.strip())
                    self.app.notify(f"Added {name.strip()}")
                else:
                    self.app.notify("Use name=value format", severity="warning")
                    return

            self._reset_input()
            self.refresh_vars()
        except RuntimeError as e:
            self.app.notify(f"Error: {e}", severity="error")
        except Exception as e:
            self.app.notify(f"Unexpected Error: {e}", severity="error")

    def _reset_input(self) -> None:
        """
        Reset input UI.
        """
        input_field = self.query_one("#var_input", Input)
        input_field.add_class("hidden")
        input_field.value = ""
        self.query_one("#var_table").focus()

    def action_add_variable(self) -> None:
        """
        Start adding a variable.
        """
        input_field = self.query_one("#var_input", Input)
        input_field.placeholder = "Enter name=value to add"
        input_field.remove_class("hidden")
        input_field.focus()
        self.selected_var_name = None

    def action_delete_variable(self) -> None:
        """
        Delete selected variable.
        """
        table = self.query_one("#var_table", DataTable)
        row_index = table.cursor_row
        if row_index is not None:
            row_keys = list(table.rows.keys())
            row_key = row_keys[row_index].value
            if row_key:
                self._delete_variable_worker(row_key)

    @work()
    async def _delete_variable_worker(self, row_key: str) -> None:
        """
        Worker to delete variable.

        Parameters
        ----------
        row_key : str
            Variable name.
        """
        if row_key.startswith(INHERITED_VAR_PREFIX):
            self.app.notify("Cannot delete inherited variables", severity="error")
            return

        try:
            await self.client.alter(self.node_path, "delete_variable", row_key)
            self.app.notify(f"Deleted {row_key}")
            self.refresh_vars()
        except RuntimeError as e:
            self.app.notify(f"Error: {e}", severity="error")
