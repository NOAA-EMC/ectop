# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Main content area for displaying ecFlow node information.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from typing import Any

from rich.syntax import Syntax
from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Input, RichLog, Static, TabbedContent, TabPane

from ectop.constants import DEFAULT_SHELL, SYNTAX_THEME
from ectop.utils import safe_call_app


class MainContent(Vertical):
    """
    A container to display Output logs, Scripts, and Job files in tabs.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.

    Attributes
    ----------
    is_live : bool
        Whether live log updates are enabled.
    last_log_size : int
        The size of the log content at the last update.
    """

    is_live: reactive[bool] = reactive(False, init=False)
    """Whether live log updates are enabled."""

    log_content: reactive[str] = reactive("", init=False)
    """The content of the output log."""

    script_content: reactive[str] = reactive("", init=False)
    """The content of the script."""

    job_content: reactive[str] = reactive("", init=False)
    """The content of the job file."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the MainContent widget.

        Parameters
        ----------
        *args : Any
            Positional arguments for Vertical.
        **kwargs : Any
            Keyword arguments for Vertical.
        """
        super().__init__(*args, **kwargs)
        self.last_log_size: int = 0
        self._content_cache: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        """
        Compose the tabs for Output, Script, and Job.

        Returns
        -------
        ComposeResult
            The UI components for the tabs.
        """
        yield Input(placeholder="Search in content...", id="content_search", classes="hidden")
        with TabbedContent(id="content_tabs"):
            with TabPane("Output", id="tab_output"):
                yield RichLog(markup=True, highlight=True, id="log_output")
            with TabPane("Script (.ecf)", id="tab_script"):
                with VerticalScroll():
                    yield Static("", id="view_script", classes="code_view")
            with TabPane("Job (Processed)", id="tab_job"):
                with VerticalScroll():
                    yield Static("", id="view_job", classes="code_view")

    @property
    def active(self) -> str | None:
        """
        Get the active tab ID.

        Returns
        -------
        str | None
            The ID of the active tab.
        """
        return self.query_one("#content_tabs", TabbedContent).active

    @active.setter
    def active(self, value: str) -> None:
        """
        Set the active tab ID.

        Parameters
        ----------
        value : str
            The ID of the tab to activate.
        """
        self.query_one("#content_tabs", TabbedContent).active = value

    def watch_log_content(self, content: str) -> None:
        """
        Watch for changes in log content and update the widget.

        Parameters
        ----------
        content : str
            The new log content.
        """
        if content == self._content_cache.get("output"):
            return

        self.update_log(content, append=False)

    def watch_script_content(self, content: str) -> None:
        """
        Watch for changes in script content and update the widget.

        Parameters
        ----------
        content : str
            The new script content.
        """
        if content == self._content_cache.get("script"):
            return

        self._content_cache["script"] = content
        widget = self.query_one("#view_script", Static)
        syntax = Syntax(content, DEFAULT_SHELL, theme=SYNTAX_THEME, line_numbers=True)
        widget.update(syntax)

    def watch_job_content(self, content: str) -> None:
        """
        Watch for changes in job content and update the widget.

        Parameters
        ----------
        content : str
            The new job content.
        """
        if content == self._content_cache.get("job"):
            return

        self._content_cache["job"] = content
        widget = self.query_one("#view_job", Static)
        syntax = Syntax(content, DEFAULT_SHELL, theme=SYNTAX_THEME, line_numbers=True)
        widget.update(syntax)

    def update_log(self, content: str, append: bool = False) -> None:
        """
        Update the Output log tab.

        Parameters
        ----------
        content : str
            The content to display or append.
        append : bool, optional
            Whether to attempt appending to existing content, by default False.
        """
        widget = self.query_one("#log_output", RichLog)

        # Check if we can actually append
        actual_append = append and content.startswith(self._content_cache.get("output", ""))

        if not actual_append:
            widget.clear()
            self.last_log_size = 0
            self._content_cache["output"] = content
            widget.write(content)
            self.last_log_size = len(content)
        else:
            new_content = content[self.last_log_size :]
            if new_content:
                widget.write(new_content)
                self._content_cache["output"] = content
                self.last_log_size = len(content)

    def update_script(self, content: str) -> None:
        """
        Update the Script tab.

        Parameters
        ----------
        content : str
            The script content.
        """
        self.script_content = content

    def update_job(self, content: str) -> None:
        """
        Update the Job tab.

        Parameters
        ----------
        content : str
            The job content.
        """
        self.job_content = content

    def action_search(self) -> None:
        """
        Toggle the content search input.

        Returns
        -------
        None
        """
        search_input = self.query_one("#content_search", Input)
        if "hidden" in search_input.classes:
            search_input.remove_class("hidden")
            search_input.focus()
        else:
            search_input.add_class("hidden")
            # Refocus the active tab's content
            active_tab = self.active
            if active_tab == "tab_output":
                self.query_one("#log_output").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle content search submission.

        Parameters
        ----------
        event : Input.Submitted
            The input submission event.

        Returns
        -------
        None
        """
        if event.input.id == "content_search":
            query = event.value
            if not query:
                return

            active_tab = self.active
            cache_key = "output"
            label = "Output"
            if active_tab == "tab_script":
                cache_key = "script"
                label = "Script"
            elif active_tab == "tab_job":
                cache_key = "job"
                label = "Job"

            content = self._content_cache.get(cache_key, "")
            self._run_search_worker(query, content, label)

    @work(thread=True)
    def _run_search_worker(self, query: str, content: str, label: str) -> None:
        """
        Run the search in a background worker.

        Parameters
        ----------
        query : str
            The search query.
        content : str
            The content to search.
        label : str
            The label of the content being searched.
        """
        matches = content.lower().count(query.lower())
        if matches > 0:
            safe_call_app(self.app, self.app.notify, f"Found {matches} matches for '{query}' in {label}", severity="information")
        else:
            safe_call_app(self.app, self.app.notify, f"No matches found for '{query}' in {label}", severity="warning")

    def show_error(self, widget_id: str, message: str) -> None:
        """
        Display an error message in a specific widget and clear cache.

        Parameters
        ----------
        widget_id : str
            The ID of the widget where the error should be shown.
        message : str
            The error message to display.
        """
        cache_key = None
        if widget_id == "#log_output":
            cache_key = "output"
        elif widget_id == "#view_script":
            cache_key = "script"
        elif widget_id == "#view_job":
            cache_key = "job"

        if cache_key:
            self._content_cache[cache_key] = ""

        widget = self.query_one(widget_id)
        if isinstance(widget, RichLog):
            widget.write(f"[italic red]{message}[/]")
        elif isinstance(widget, Static):
            widget.update(f"[italic red]{message}[/]")
