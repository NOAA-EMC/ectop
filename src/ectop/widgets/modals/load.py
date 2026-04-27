# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Modal screen for loading ecFlow definition files.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

if TYPE_CHECKING:
    from ectop.app import Ectop


class LoadDefsModal(ModalScreen[None]):
    """
    A modal screen for loading .def files to the ecFlow server.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.
    """

    BINDINGS = [
        Binding("escape", "close", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """
        Compose the modal UI.

        Returns:
            The UI components for the modal.
        """
        with Vertical(id="confirm_container"):
            yield Static("Load Definition File", id="confirm_message")
            yield Input(placeholder="Path to .def file...", id="load_input")
            with Horizontal(id="confirm_actions"):
                yield Button("Load", variant="success", id="load_btn")
                yield Button("Cancel", variant="error", id="cancel_btn")

    def on_mount(self) -> None:
        """
        Focus the input field on mount.
        """
        self.query_one("#load_input", Input).focus()

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
        if event.button.id == "load_btn":
            self._handle_load()
        else:
            self.action_close()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle input submission.

        Args:
            event: The input submission event.
        """
        if event.input.id == "load_input":
            self._handle_load()

    def _handle_load(self) -> None:
        """
        Process the load request.
        """
        path = self.query_one("#load_input", Input).value.strip()
        if not path:
            self.app.notify("Please enter a file path", severity="warning")
            return

        if not os.path.exists(path):
            self.app.notify(f"File not found: {path}", severity="error")
            return

        app = self.app
        assert isinstance(app, Ectop)
        app._load_defs_worker(path)
        self.app.pop_screen()
