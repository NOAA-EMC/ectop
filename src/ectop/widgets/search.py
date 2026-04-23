# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Search box widget for finds nodes in the suite tree.
"""

from __future__ import annotations

from typing import Any

from textual.binding import Binding
from textual.widgets import Input


class SearchBox(Input):
    """
    An input widget for searching nodes in the tree.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel Search"),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the SearchBox.

        Parameters
        ----------
        *args : Any
            Positional arguments for the Input widget.
        **kwargs : Any
            Keyword arguments for the Input widget.
        """
        super().__init__(*args, **kwargs)

    def action_cancel(self) -> None:
        """
        Clear and hide the search box.
        """
        self.value = ""
        self.remove_class("visible")
        self.app.query_one("#suite_tree").focus()
