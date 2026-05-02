# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Modal screen for viewing and editing ecFlow variables.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Static

from ectop.client import EcflowClient
from ectop.constants import (
    INHERITED_VAR_PREFIX,
    VAR_TYPE_GENERATED,
    VAR_TYPE_INHERITED,
    VAR_TYPE_USER,
)
from ectop.utils import safe_call_app


class VariableTweaker(ModalScreen[None]):
    """
    A modal screen for managing ecFlow node variables.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.
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

        Args:
            node_path: The absolute path to the ecFlow node.
            client: The ecFlow client instance.
        """
        super().__init__()
        self.node_path: str = node_path
        self.client: EcflowClient = client
        self.selected_var_name: str | None = None

    def compose(self) -> ComposeResult:
        """
        Compose the modal UI.

        Returns:
            The UI components for the modal.
        """
        with Vertical(id="var_container"):
            yield Static(f"Variables for {self.node_path}", id="var_title")
            yield DataTable(id="var_table")
            yield Input(placeholder="Enter new value...", id="var_input")
            with Horizontal(id="var_actions"):
                yield Button("Close", variant="primary", id="close_btn")

    def on_mount(self) -> None:
        """
        Handle the mount event to initialize the table.
        """
        table = self.query_one("#var_table", DataTable)
        table.add_columns("Name", "Value", "Type")
        table.cursor_type = "row"
        self.refresh_vars()
        self.query_one("#var_input").add_class("hidden")

    def action_close(self) -> None:
        """
        Close the modal.
        """
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events.

        Args:
            event: The button press event.
        """
        if event.button.id == "close_btn":
            self.app.pop_screen()

    @work(thread=True)
    def refresh_vars(self) -> None:
        """
        Fetch variables from the server and refresh the table in a background worker.

        Notes:
            This is a background thread worker.
        """
        self._refresh_vars_logic()

    def _refresh_vars_logic(self) -> None:
        """
        The actual logic for fetching variables and updating the UI.

        Raises:
            RuntimeError: If server synchronization fails.

        Notes:
            This method is called from a background worker.
        """
        try:
            self.client.sync_local_sync()
            defs = self.client.get_defs_sync()
            if not defs:
                return
            node = defs.find_abs_node(self.node_path)

            if not node:
                safe_call_app(self.app, self.app.notify, "Node not found", severity="error")
                return

            rows: list[tuple[str, str, str, str]] = []
            seen_vars: set[str] = set()

            # User variables
            for var in node.variables:
                rows.append((var.name(), var.value(), VAR_TYPE_USER, var.name()))
                seen_vars.add(var.name())

            # Generated variables
            for var in node.get_generated_variables():
                rows.append((var.name(), var.value(), VAR_TYPE_GENERATED, var.name()))
                seen_vars.add(var.name())

            # Inherited variables (climb up the tree)
            parent = node.get_parent()
            while parent:
                for var in parent.variables:
                    # Only add if not already present (overridden)
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

            safe_call_app(self.app, self._update_table, rows)

        except RuntimeError as e:
            safe_call_app(self.app, self.app.notify, f"Error fetching variables: {e}", severity="error")
        except Exception as e:
            safe_call_app(self.app, self.app.notify, f"Unexpected Error: {e}", severity="error")

    def _update_table(self, rows: list[tuple[str, str, str, str]]) -> None:
        """
        Update the DataTable with new rows.

        Args:
            rows: The rows to add to the table.
        """
        table = self.query_one("#var_table", DataTable)
        table.clear()
        for row in rows:
            table.add_row(row[0], row[1], row[2], key=row[3])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Handle row selection to start editing a variable.

        Args:
            event: The row selection event.
        """
        row_key = event.row_key.value
        if row_key and row_key.startswith(INHERITED_VAR_PREFIX):
            self.app.notify("Cannot edit inherited variables directly. Add it to this node to override.", severity="warning")
            return

        self.selected_var_name = row_key
        input_field = self.query_one("#var_input", Input)
        input_field.remove_class("hidden")
        input_field.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle variable submission (add or update).

        Args:
            event: The input submission event.
        """
        if event.input.id == "var_input":
            self._submit_variable_worker(event.value)

    @work(thread=True)
    def _submit_variable_worker(self, value: str) -> None:
        """
        Worker to submit a new or updated variable in a background thread.

        Args:
            value: The new value or 'name=value' string.

        Notes:
            This is a background thread worker.
        """
        self._submit_variable_logic(value)

    def _submit_variable_logic(self, value: str) -> None:
        """
        The actual logic for submitting a variable update or addition.

        Args:
            value: The new value or 'name=value' string.

        Raises:
            RuntimeError: If the server alteration fails.

        Notes:
            This method is called from a background worker.
        """
        try:
            if self.selected_var_name:
                # Editing existing
                self.client.alter_sync(self.node_path, "add", "variable", self.selected_var_name, value)
                safe_call_app(self.app, self.app.notify, f"Updated {self.selected_var_name}")
            else:
                # Adding new (expecting name=value)
                if "=" in value:
                    name, val = value.split("=", 1)
                    self.client.alter_sync(self.node_path, "add", "variable", name.strip(), val.strip())
                    safe_call_app(self.app, self.app.notify, f"Added {name.strip()}")
                else:
                    safe_call_app(self.app, self.app.notify, "Use name=value format to add", severity="warning")
                    return

            safe_call_app(self.app, self._reset_input)
            self.refresh_vars()
        except RuntimeError as e:
            safe_call_app(self.app, self.app.notify, f"Error: {e}", severity="error")
        except Exception as e:
            safe_call_app(self.app, self.app.notify, f"Unexpected Error: {e}", severity="error")

    def _reset_input(self) -> None:
        """
        Reset the input field state.
        """
        input_field = self.query_one("#var_input", Input)
        input_field.add_class("hidden")
        input_field.value = ""
        input_field.placeholder = "Enter new value..."
        self.query_one("#var_table").focus()

    def action_add_variable(self) -> None:
        """
        Show the input field to add a new variable.
        """
        input_field = self.query_one("#var_input", Input)
        input_field.placeholder = "Enter name=value to add"
        input_field.remove_class("hidden")
        input_field.focus()
        self.selected_var_name = None

    def action_delete_variable(self) -> None:
        """
        Delete the selected variable from the server.
        """
        table = self.query_one("#var_table", DataTable)
        row_index = table.cursor_row
        if row_index is not None:
            # Get row key from the index
            row_keys = list(table.rows.keys())
            row_key = row_keys[row_index].value
            if row_key:
                self._delete_variable_worker(row_key)

    @work(thread=True)
    def _delete_variable_worker(self, row_key: str) -> None:
        """
        Worker to delete a variable from the server in a background thread.

        Args:
            row_key: The name (or key) of the variable to delete.

        Notes:
            This is a background thread worker.
        """
        self._delete_variable_logic(row_key)

    def _delete_variable_logic(self, row_key: str) -> None:
        """
        The actual logic for deleting a variable.

        Args:
            row_key: The name (or key) of the variable to delete.

        Raises:
            RuntimeError: If the server alteration fails.

        Notes:
            This method is called from a background worker.
        """
        if row_key.startswith(INHERITED_VAR_PREFIX):
            safe_call_app(self.app, self.app.notify, "Cannot delete inherited variables", severity="error")
            return

        try:
            self.client.alter_sync(self.node_path, "delete", "variable", row_key)
            safe_call_app(self.app, self.app.notify, f"Deleted {row_key}")
            self.refresh_vars()
        except RuntimeError as e:
            safe_call_app(self.app, self.app.notify, f"Error: {e}", severity="error")
        except Exception as e:
            safe_call_app(self.app, self.app.notify, f"Unexpected Error: {e}", severity="error")
