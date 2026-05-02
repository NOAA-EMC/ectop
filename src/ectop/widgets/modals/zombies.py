# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Zombie Management Dashboard for ectop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Static

if TYPE_CHECKING:
    import ecflow

    from ectop.client import EcflowClient


class ZombieDashboard(ModalScreen):
    """
    A dashboard to view and resolve ecFlow Zombies.
    """

    BINDINGS = [
        Binding("escape,q", "dismiss", "Close"),
        Binding("r", "refresh", "Refresh"),
        Binding("f", "fob", "Fob"),
        Binding("F", "fail", "Fail"),
        Binding("a", "adopt", "Adopt"),
    ]

    def __init__(self, client: EcflowClient, **kwargs: Any) -> None:
        """
        Initialize the ZombieDashboard.

        Args:
            client: The EcflowClient instance.
        """
        super().__init__(**kwargs)
        self.ecflow_client = client
        self._zombies: list[ecflow.Zombie] = []

    def compose(self) -> ComposeResult:
        """
        Compose the UI.
        """
        yield Container(
            Static("🧟 Zombie Management Dashboard", id="zombie_title"),
            DataTable(id="zombie_table"),
            Horizontal(
                Button("Refresh (r)", variant="primary", id="btn_refresh"),
                Button("Fob (f)", variant="warning", id="btn_fob"),
                Button("Fail (F)", variant="error", id="btn_fail"),
                Button("Adopt (a)", variant="success", id="btn_adopt"),
                classes="modal_actions",
            ),
            id="zombie_container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """
        Handle mount event.
        """
        table = self.query_one(DataTable)
        table.add_columns("Path", "Status", "User", "Host", "RID", "Try", "Created")
        table.cursor_type = "row"
        self.action_refresh()

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        """
        Refresh the zombie list.
        """
        self.app.notify("Refreshing zombies...")
        try:
            self._zombies = await self.ecflow_client.zombie_get()
            self._update_table()
        except RuntimeError as e:
            self.app.notify(f"Failed to fetch zombies: {e}", severity="error")

    def _update_table(self) -> None:
        """
        Update the DataTable with fetched zombies.
        """
        table = self.query_one(DataTable)
        table.clear()
        for i, z in enumerate(self._zombies):
            table.add_row(
                z.path(),
                z.calls(),  # Using calls() as a proxy for status/type if needed, or z.type()
                z.user(),
                z.host(),
                z.rid(),
                str(z.try_no()),
                z.allowed(),  # creation_time might be available in stats or allowed()
                key=str(i),
            )

    def get_selected_zombie(self) -> ecflow.Zombie | None:
        """
        Get the currently selected zombie object.
        """
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            if row_key and row_key.value:
                return self._zombies[int(row_key.value)]
        return None

    @work
    async def action_fob(self) -> None:
        """
        Fob the selected zombie.
        """
        z = self.get_selected_zombie()
        if z:
            try:
                await self.ecflow_client.zombie_fob(z)
                self.app.notify(f"Fobbed: {z.path()}")
                self.action_refresh()
            except RuntimeError as e:
                self.app.notify(f"Fob failed: {e}", severity="error")

    @work
    async def action_fail(self) -> None:
        """
        Fail the selected zombie.
        """
        z = self.get_selected_zombie()
        if z:
            try:
                await self.ecflow_client.zombie_fail(z)
                self.app.notify(f"Failed: {z.path()}")
                self.action_refresh()
            except RuntimeError as e:
                self.app.notify(f"Fail failed: {e}", severity="error")

    @work
    async def action_adopt(self) -> None:
        """
        Adopt the selected zombie.
        """
        z = self.get_selected_zombie()
        if z:
            try:
                await self.ecflow_client.zombie_adopt(z)
                self.app.notify(f"Adopted: {z.path()}")
                self.action_refresh()
            except RuntimeError as e:
                self.app.notify(f"Adopt failed: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses.
        """
        if event.button.id == "btn_refresh":
            self.action_refresh()
        elif event.button.id == "btn_fob":
            self.action_fob()
        elif event.button.id == "btn_fail":
            self.action_fail()
        elif event.button.id == "btn_adopt":
            self.action_adopt()
