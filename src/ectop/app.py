# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Main application class for ectop.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, Input

from ectop.client import EcflowClient
from ectop.constants import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CONTENT_BG,
    COLOR_HEADER_BG,
    COLOR_SIDEBAR_BG,
    COLOR_STATUS_BAR_BG,
    COLOR_TEXT,
    COLOR_TEXT_HIGHLIGHT,
    DEFAULT_EDITOR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL,
    ERROR_CONNECTION_FAILED,
    STATUS_SYNC_ERROR,
)
from ectop.widgets.content import MainContent
from ectop.widgets.modals.variables import VariableTweaker
from ectop.widgets.modals.why import WhyInspector
from ectop.widgets.search import SearchBox
from ectop.widgets.sidebar import SuiteTree
from ectop.widgets.statusbar import StatusBar


class EctopCommands(Provider):
    """Command palette provider for ectop."""

    async def search(self, query: str) -> Hits:
        """Search for commands in the palette.

        Args:
            query (str): The search query.

        Yields:
            Hit: Command hits matching the query.
        """
        matcher = self.matcher(query)
        app = self.app
        assert isinstance(app, Ectop)
        commands = [
            ("Refresh Tree", app.action_refresh, "Refresh the ecFlow suite tree"),
            ("Search Nodes", app.action_search, "Search for a node by name or path"),
            ("Suspend Node", app.action_suspend, "Suspend the currently selected node"),
            ("Resume Node", app.action_resume, "Resume the currently selected node"),
            ("Kill Node", app.action_kill, "Kill the currently selected node"),
            ("Force Complete", app.action_force, "Force complete the currently selected node"),
            ("Cycle Filter", app.action_cycle_filter, "Cycle status filters (All, Aborted, Active...)"),
            ("Requeue", app.action_requeue, "Requeue the currently selected node"),
            ("Copy Path", app.action_copy_path, "Copy the selected node path"),
            ("Why?", app.action_why, "Inspect why a node is not running"),
            ("Variables", app.action_variables, "View/Edit node variables"),
            ("Edit Script", app.action_edit_script, "Edit and rerun node script"),
            ("Restart Server", app.action_restart_server, "Start server scheduling (RUNNING)"),
            ("Halt Server", app.action_halt_server, "Stop server scheduling (HALT)"),
            ("Toggle Live Log", app.action_toggle_live, "Toggle live log updates"),
            ("Quit", app.action_quit, "Quit the application"),
        ]
        for name, action, help_text in commands:
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), action, help=help_text)


class Ectop(App):
    """The main ecFlow TUI application."""

    CSS = f"""
    Screen {{ background: {COLOR_BG}; }}
    StatusBar {{ dock: bottom; height: 1; background: {COLOR_STATUS_BAR_BG}; color: {COLOR_TEXT}; }}
    #sidebar {{ width: 30%; height: 100%; border-right: solid {COLOR_BORDER}; background: {COLOR_SIDEBAR_BG}; }}
    Tree {{ background: {COLOR_SIDEBAR_BG}; color: {COLOR_TEXT}; padding: 1; }}
    #main_content {{ width: 70%; height: 100%; }}
    TabbedContent {{ height: 100%; }}
    RichLog {{ background: {COLOR_CONTENT_BG}; color: {COLOR_TEXT_HIGHLIGHT}; border: none; }}
    .code_view {{ background: {COLOR_CONTENT_BG}; padding: 1; width: 100%; height: auto; }}
    #search_box {{
        dock: top;
        display: none;
        background: {COLOR_CONTENT_BG};
        color: {COLOR_TEXT_HIGHLIGHT};
        border: tall {COLOR_BORDER};
    }}
    #search_box.visible {{ display: block; }}
    #why_container {{ padding: 1 2; background: {COLOR_BG}; border: thick {COLOR_BORDER}; width: 60%; height: 60%; }}
    #why_title {{ text-align: center; background: {COLOR_HEADER_BG}; color: white; margin-bottom: 1; }}
    #confirm_container {{ padding: 1 2; background: {COLOR_BG}; border: thick {COLOR_BORDER}; width: 40%; height: 20%; }}
    #confirm_message {{ text-align: center; margin-bottom: 1; }}
    #confirm_actions {{ align: center middle; }}
    #confirm_actions Button {{ margin: 0 1; }}
    #var_container {{ padding: 1 2; background: {COLOR_BG}; border: thick {COLOR_BORDER}; width: 80%; height: 80%; }}
    #var_title {{ text-align: center; background: {COLOR_HEADER_BG}; color: white; margin-bottom: 1; }}
    #var_input.hidden {{ display: none; }}
    """
    COMMANDS = App.COMMANDS | {EctopCommands}
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "command_palette", "Command Palette"),
        Binding("r", "refresh", "Refresh Tree"),
        Binding("l", "load_node", "Load Logs/Script"),
        Binding("s", "suspend", "Suspend"),
        Binding("u", "resume", "Resume"),
        Binding("k", "kill", "Kill"),
        Binding("f", "force", "Force Complete"),
        Binding("F", "cycle_filter", "Cycle Filter"),
        Binding("R", "requeue", "Requeue"),
        Binding("c", "copy_path", "Copy Path"),
        Binding("S", "restart_server", "Start Server"),
        Binding("H", "halt_server", "Halt Server"),
        Binding("/", "search", "Search"),
        Binding("w", "why", "Why?"),
        Binding("e", "edit_script", "Edit & Rerun"),
        Binding("t", "toggle_live", "Toggle Live Log"),
        Binding("v", "variables", "Variables"),
        Binding("ctrl+f", "search_content", "Search in Content"),
    ]

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        refresh_interval: float = DEFAULT_REFRESH_INTERVAL,
        **kwargs: Any,
    ) -> None:
        """Initialize the Ectop app.

        Args:
            host (str): The ecFlow server hostname.
            port (int): The ecFlow server port.
            refresh_interval (float): Automatic refresh interval in seconds.
            **kwargs (Any): Additional arguments for the Textual App.
        """
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.refresh_interval = refresh_interval
        self.ecflow_client: EcflowClient = EcflowClient(self.host, self.port)

    def compose(self) -> ComposeResult:
        """Compose the app UI.

        Returns:
            ComposeResult: The UI components for the app.
        """
        yield Header(show_clock=True)
        yield SearchBox(placeholder="Search nodes...", id="search_box")
        yield Horizontal(
            Container(SuiteTree("ecFlow Server", id="suite_tree"), id="sidebar"),
            MainContent(id="main_content"),
        )
        yield StatusBar(id="status_bar")
        yield Footer()

    async def on_mount(self) -> None:
        """Handle mount event."""
        self._initial_connect()
        self.set_interval(self.refresh_interval, self._live_log_tick)

    def on_tree_node_selected(self, event: SuiteTree.NodeSelected[str]) -> None:
        """Handle tree node selection.

        Args:
            event (SuiteTree.NodeSelected): The selection event.
        """
        if event.node.data:
            self.action_load_node()

    @work()
    async def _initial_connect(self) -> None:
        """Establish initial connection to ecFlow server."""
        try:
            await self.ecflow_client.ping()
            self.action_refresh()
        except RuntimeError as e:
            self.notify(f"{ERROR_CONNECTION_FAILED}: {e}", severity="error", timeout=10)
            self._update_tree_error(self.query_one("#suite_tree", SuiteTree))
        except Exception as e:
            self.notify(f"Unexpected Error: {e}", severity="error")

    def _update_tree_error(self, tree: SuiteTree) -> None:
        """Update tree root to show error.

        Args:
            tree (SuiteTree): The tree widget to update.
        """
        tree.root.label = f"[red]{ERROR_CONNECTION_FAILED} (Check Host/Port)[/]"

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        """Refresh the ecFlow definition tree."""
        self.notify("Refreshing tree...")
        tree = self.query_one("#suite_tree", SuiteTree)
        status_bar = self.query_one("#status_bar", StatusBar)
        try:
            await self.ecflow_client.sync_local()
            defs = await self.ecflow_client.get_defs()
            status = str(defs.get_server_state()) if defs else "Connected"
            version = "Unknown"
            try:
                version = await self.ecflow_client.server_version()
            except RuntimeError:
                pass
            tree.update_tree(self.ecflow_client.host, self.ecflow_client.port, defs)
            status_bar.update_status(self.ecflow_client.host, self.ecflow_client.port, status=status, version=version)
            self.notify("Tree Refreshed")
        except RuntimeError as e:
            status_bar.update_status(self.ecflow_client.host, self.ecflow_client.port, status=STATUS_SYNC_ERROR)
            self.notify(f"Refresh Error: {e}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected Error: {e}", severity="error")

    @work()
    async def action_restart_server(self) -> None:
        """Restart the ecFlow server scheduling."""
        try:
            await self.ecflow_client.restart_server()
            self.notify("Server Started (RUNNING)")
            self.action_refresh()
        except Exception as e:
            self.notify(f"Restart Error: {e}", severity="error")

    @work()
    async def action_halt_server(self) -> None:
        """Halt the ecFlow server scheduling."""
        try:
            await self.ecflow_client.halt_server()
            self.notify("Server Halted (HALT)")
            self.action_refresh()
        except Exception as e:
            self.notify(f"Halt Error: {e}", severity="error")

    def get_selected_path(self) -> str | None:
        """Get the absolute path of the selected node.

        Returns:
            str | None: The absolute path of the selected node or None.
        """
        try:
            node = self.query_one("#suite_tree", SuiteTree).cursor_node
            return node.data if node else None
        except Exception:
            return None

    def action_load_node(self) -> None:
        """Load logs/scripts for the selected node."""
        path = self.get_selected_path()
        if not path:
            self.notify("No node selected", severity="warning")
            return
        self._load_node_worker(path)

    @work(exclusive=True)
    async def _load_node_worker(self, path: str) -> None:
        """Worker to load node files from server.

        Args:
            path (str): The absolute path of the node to load.
        """
        self.notify(f"Loading files for {path}...")
        content_area = self.query_one("#main_content", MainContent)
        try:
            await self.ecflow_client.sync_local()
        except RuntimeError:
            pass
        try:
            content = await self.ecflow_client.file(path, "jobout")
            content_area.update_log(content)
        except RuntimeError:
            content_area.show_error("#log_output", "File type 'jobout' not found.")
        try:
            content = await self.ecflow_client.file(path, "script")
            content_area.update_script(content)
        except RuntimeError:
            content_area.show_error("#view_script", "File type 'script' not available.")
        try:
            content = await self.ecflow_client.file(path, "job")
            content_area.update_job(content)
        except RuntimeError:
            content_area.show_error("#view_job", "File type 'job' not available.")

    @work()
    async def _run_client_command(self, command_name: str, path: str | None) -> None:
        """Run an arbitrary EcflowClient command.

        Args:
            command_name (str): Name of the method on EcflowClient to call.
            path (str | None): Absolute path to the node.
        """
        if not path:
            return
        try:
            method = getattr(self.ecflow_client, command_name)
            await method(path)
            self.notify(f"{command_name.replace('_', ' ').capitalize()}: {path}")
            self.action_refresh()
        except RuntimeError as e:
            self.notify(f"Command Error: {e}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected Error: {e}", severity="error")

    def action_suspend(self) -> None:
        """Suspend the selected node."""
        self._run_client_command("suspend", self.get_selected_path())

    def action_resume(self) -> None:
        """Resume the selected node."""
        self._run_client_command("resume", self.get_selected_path())

    def action_kill(self) -> None:
        """Kill the selected node."""
        self._run_client_command("kill", self.get_selected_path())

    def action_force(self) -> None:
        """Force complete the selected node."""
        self._run_client_command("force_complete", self.get_selected_path())

    def action_cycle_filter(self) -> None:
        """Cycle status filters."""
        self.query_one("#suite_tree", SuiteTree).action_cycle_filter()

    def action_requeue(self) -> None:
        """Requeue the selected node."""
        self._run_client_command("requeue", self.get_selected_path())

    def action_copy_path(self) -> None:
        """Copy the selected node path to clipboard."""
        path = self.get_selected_path()
        if path:
            if hasattr(self, "copy_to_clipboard"):
                self.copy_to_clipboard(path)
                self.notify(f"Copied to clipboard: {path}")
            else:
                self.notify(f"Node path: {path}")
        else:
            self.notify("No node selected", severity="warning")

    def action_toggle_live(self) -> None:
        """Toggle live log updating."""
        content_area = self.query_one("#main_content", MainContent)
        content_area.is_live = not content_area.is_live
        self.notify(f"Live Log: {'ON' if content_area.is_live else 'OFF'}")
        if content_area.is_live:
            content_area.active = "tab_output"

    def _live_log_tick(self) -> None:
        """Tick for live log updates."""
        content_area = self.query_one("#main_content", MainContent)
        if content_area.is_live and content_area.active == "tab_output":
            path = self.get_selected_path()
            if path:
                self._live_log_worker(path)

    @work(exclusive=True)
    async def _live_log_worker(self, path: str) -> None:
        """Worker to fetch live log content.

        Args:
            path (str): Absolute path to the node.
        """
        try:
            content = await self.ecflow_client.file(path, "jobout")
            self.query_one("#main_content", MainContent).update_log(content, append=True)
        except RuntimeError:
            pass

    def action_why(self) -> None:
        """Open the WhyInspector for the selected node."""
        path = self.get_selected_path()
        if not path:
            self.notify("No node selected", severity="warning")
            return
        self.push_screen(WhyInspector(path, self.ecflow_client))

    def action_variables(self) -> None:
        """Open the VariableTweaker for the selected node."""
        path = self.get_selected_path()
        if not path:
            self.notify("No node selected", severity="warning")
            return
        self.push_screen(VariableTweaker(path, self.ecflow_client))

    def action_search_content(self) -> None:
        """Trigger search in the main content area."""
        self.query_one("#main_content", MainContent).action_search()

    def action_edit_script(self) -> None:
        """Open editor for node script."""
        path = self.get_selected_path()
        if not path:
            self.notify("No node selected", severity="warning")
            return
        self._edit_script_worker(path)

    @work(exclusive=True)
    async def _edit_script_worker(self, path: str) -> None:
        """Worker to handle script editing lifecycle.

        Args:
            path (str): Absolute path to the node to edit.
        """
        try:
            content = await self.ecflow_client.file(path, "script")
            with tempfile.NamedTemporaryFile(suffix=".ecf", delete=False, mode="w") as f:
                f.write(content)
                temp_path = f.name
            await self._run_editor_async(temp_path, path, content)
        except RuntimeError as e:
            self.notify(f"Edit Error: {e}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected Error: {e}", severity="error")

    async def _run_editor_async(self, temp_path: str, path: str, old_content: str) -> None:
        """Asynchronously run the system editor.

        Args:
            temp_path (str): Path to the temporary file.
            path (str): Absolute path to the ecFlow node.
            old_content (str): The original script content.
        """
        editor = os.environ.get("EDITOR", DEFAULT_EDITOR)
        with self.suspend():
            await asyncio.to_thread(subprocess.run, [editor, temp_path], check=False)
        self._finish_edit(temp_path, path, old_content)

    @work()
    async def _finish_edit(self, temp_path: str, path: str, old_content: str) -> None:
        """Handle post-edit operations.

        Args:
            temp_path (str): Path to the temporary file.
            path (str): Absolute path to the ecFlow node.
            old_content (str): The original script content.
        """
        try:
            with open(temp_path) as f:
                new_content = f.read()
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if new_content != old_content:
                await self.ecflow_client.alter(path, "change", "script", new_content)
                self.notify("Script updated on server")
                self._prompt_requeue(path)
            else:
                self.notify("No changes detected")
        except RuntimeError as e:
            self.notify(f"Update Error: {e}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected Error: {e}", severity="error")

    def _prompt_requeue(self, path: str) -> None:
        """Prompt user to requeue after script edit.

        Args:
            path (str): Absolute path to the node.
        """
        from ectop.widgets.modals.confirm import ConfirmModal

        def do_requeue() -> None:
            self._run_client_command("requeue", path)

        self.push_screen(ConfirmModal(f"Re-queue {path} now?", do_requeue))

    def action_search(self) -> None:
        """Show the search box."""
        search_box = self.query_one("#search_box", SearchBox)
        search_box.add_class("visible")
        search_box.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Search).

        Args:
            event (Input.Submitted): The submission event.
        """
        if event.input.id == "search_box":
            query = event.value
            if query:
                self.query_one("#suite_tree", SuiteTree).find_and_select(query)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes (Live Search).

        Args:
            event (Input.Changed): The change event.
        """
        if event.input.id == "search_box":
            query = event.value
            if query:
                self.query_one("#suite_tree", SuiteTree).find_and_select(query)
