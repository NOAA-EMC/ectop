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

from typing import TYPE_CHECKING, Any

from rich.syntax import Syntax
from rich.text import Text
from textual import work
from textual.binding import Binding

if TYPE_CHECKING:
    from ectop.widgets.timeline import TimelineData
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Input, RichLog, Static, TabbedContent, TabPane

from ectop.constants import DEFAULT_SHELL, SYNTAX_THEME
from ectop.utils import safe_call_app
from ectop.widgets.timeline import TimelineTab


class MainContent(Vertical):
    """
    A container to display Output logs, Scripts, and Job files in tabs.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.

    Attributes:
        is_live: Whether live log updates are enabled.
        last_log_size: The size of the log content at the last update.
        search_query: The current search query.
        search_results: List of (start, end) offsets for search matches.
        current_result_index: The index of the currently active search match.
    """

    BINDINGS = [
        Binding("n", "search_next", "Next Match"),
        Binding("N", "search_prev", "Prev Match"),
    ]

    is_live: reactive[bool] = reactive(False, init=False)
    """Whether live log updates are enabled."""

    log_content: reactive[str] = reactive("", init=False)
    """The content of the output log."""

    script_content: reactive[str] = reactive("", init=False)
    """The content of the script."""

    job_content: reactive[str] = reactive("", init=False)
    """The content of the job file."""

    search_query: reactive[str] = reactive("", init=False)
    """The current search query."""

    search_results: reactive[list[tuple[int, int]]] = reactive([], init=False)
    """List of (start, end) offsets for search matches."""

    current_result_index: reactive[int] = reactive(0, init=False)
    """The index of the currently active search match."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the MainContent widget.

        Args:
            *args: Positional arguments for Vertical.
            **kwargs: Keyword arguments for Vertical.
        """
        super().__init__(*args, **kwargs)
        self.last_log_size: int = 0
        self._content_cache: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        """
        Compose the tabs for Output, Script, and Job.

        Returns:
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
            with TabPane("Timeline", id="tab_timeline"):
                yield TimelineTab(id="view_timeline", classes="code_view")

    @property
    def active(self) -> str | None:
        """
        Get the active tab ID.

        Returns:
            The ID of the active tab.
        """
        return self.query_one("#content_tabs", TabbedContent).active

    @active.setter
    def active(self, value: str) -> None:
        """
        Set the active tab ID.

        Args:
            value: The ID of the tab to activate.
        """
        self.query_one("#content_tabs", TabbedContent).active = value

    def watch_log_content(self, content: str) -> None:
        """
        Watch for changes in log content and update the widget.

        Args:
            content: The new log content.
        """
        if not content or content == self._content_cache.get("output"):
            return

        self.update_log(content)

    def watch_script_content(self, content: str) -> None:
        """
        Watch for changes in script content and update the widget.

        Args:
            content: The new script content.
        """
        if content == self._content_cache.get("script") and not self.search_query:
            return

        self._content_cache["script"] = content
        widget = self.query_one("#view_script", Static)
        if self.search_query and self.active == "tab_script":
            widget.update(self._get_highlighted_content(content))
        else:
            syntax = Syntax(content, DEFAULT_SHELL, theme=SYNTAX_THEME, line_numbers=True)
            widget.update(syntax)

    def watch_job_content(self, content: str) -> None:
        """
        Watch for changes in job content and update the widget.

        Args:
            content: The new job content.
        """
        if content == self._content_cache.get("job") and not self.search_query:
            return

        self._content_cache["job"] = content
        widget = self.query_one("#view_job", Static)
        if self.search_query and self.active == "tab_job":
            widget.update(self._get_highlighted_content(content))
        else:
            syntax = Syntax(content, DEFAULT_SHELL, theme=SYNTAX_THEME, line_numbers=True)
            widget.update(syntax)

    def update_log(self, content: str, delta: str | None = None) -> None:
        """
        Update the Output log tab.

        Args:
            content: The full log content.
            delta: Optional new content to append. If provided, expensive
                full-content comparisons and clears are avoided.
        """
        widget = self.query_one("#log_output", RichLog)

        if self.search_query:
            # When searching, we don't use delta because we need to highlight the full text
            widget.clear()
            self._content_cache["output"] = content
            widget.write(self._get_highlighted_content(content))
            self.last_log_size = len(content)
            return

        if delta is not None:
            if delta:
                widget.write(delta)
                self._content_cache["output"] = content
                self.last_log_size = len(content)
            return

        # Optimization: Return early if content is identical
        if content == self._content_cache.get("output"):
            return

        widget.clear()
        self._content_cache["output"] = content
        widget.write(content)
        self.last_log_size = len(content)

    def update_script(self, content: str) -> None:
        """
        Update the Script tab.

        Args:
            content: The script content.
        """
        self.script_content = content

    def update_job(self, content: str) -> None:
        """
        Update the Job tab.

        Args:
            content: The job content.
        """
        self.job_content = content

    def update_timeline(self, data: TimelineData | None) -> None:
        """
        Update the Timeline tab.

        Args:
            data: The pre-processed timeline data.
        """
        self.query_one("#view_timeline", TimelineTab).update_timeline(data)

    def _get_highlighted_content(self, content: str) -> Text:
        """
        Apply search highlights to the content.

        Args:
            content: The raw content to highlight.

        Returns:
            A Rich Text object with highlights applied.
        """
        text = Text(content)
        if not self.search_query or not self.search_results:
            return text

        for i, (start, end) in enumerate(self.search_results):
            # Use orange for the current match, yellow for others
            style = "bold black on orange3" if i == self.current_result_index else "bold black on yellow"
            text.stylize(style, start, end)

        return text

    def action_search_next(self) -> None:
        """
        Navigate to the next search match.
        """
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
        self._refresh_active_content()
        self._scroll_to_current_match()

    def action_search_prev(self) -> None:
        """
        Navigate to the previous search match.
        """
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index - 1) % len(self.search_results)
        self._refresh_active_content()
        self._scroll_to_current_match()

    def _refresh_active_content(self) -> None:
        """
        Refresh the currently active tab's content to update highlights.
        """
        active_tab = self.active
        if active_tab == "tab_output":
            self.update_log(self._content_cache.get("output", ""))
        elif active_tab == "tab_script":
            self.watch_script_content(self._content_cache.get("script", ""))
        elif active_tab == "tab_job":
            self.watch_job_content(self._content_cache.get("job", ""))

    def _scroll_to_current_match(self) -> None:
        """
        Scroll the active view to the current search match.
        """
        if not self.search_results:
            return

        start, _ = self.search_results[self.current_result_index]
        active_tab = self.active
        content = ""
        scroll_container = None

        if active_tab == "tab_output":
            content = self._content_cache.get("output", "")
            scroll_container = self.query_one("#log_output", RichLog)
        elif active_tab == "tab_script":
            content = self._content_cache.get("script", "")
            scroll_container = self.query_one("#tab_script VerticalScroll", VerticalScroll)
        elif active_tab == "tab_job":
            content = self._content_cache.get("job", "")
            scroll_container = self.query_one("#tab_job VerticalScroll", VerticalScroll)

        if scroll_container and content:
            line_no = content.count("\n", 0, start)
            scroll_container.scroll_to(y=line_no, animate=False)

    def action_search(self) -> None:
        """
        Toggle the content search input.
        """
        search_input = self.query_one("#content_search", Input)
        if "hidden" in search_input.classes:
            search_input.remove_class("hidden")
            search_input.focus()
        else:
            search_input.add_class("hidden")
            self.search_query = ""
            self.search_results = []
            self.current_result_index = 0
            self._refresh_active_content()
            # Refocus the active tab's content
            active_tab = self.active
            if active_tab == "tab_output":
                self.query_one("#log_output").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle content search submission.

        Args:
            event: The input submission event.
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

        Args:
            query: The search query.
            content: The content to search.
            label: The label of the content being searched.

        Returns:
            None

        Notes:
            This is a threaded background worker.
        """
        import re

        # Find all match offsets (start, end) case-insensitively
        try:
            matches = [(m.start(), m.end()) for m in re.finditer(re.escape(query), content, re.IGNORECASE)]
        except Exception:
            matches = []

        def _update_ui() -> None:
            self.search_query = query
            self.search_results = matches
            self.current_result_index = 0
            if matches:
                self.app.notify(f"Found {len(matches)} matches for '{query}' in {label}", severity="information")
                # Trigger a refresh of the current tab content with highlights
                active_tab = self.active
                if active_tab == "tab_output":
                    self.update_log(content)
                elif active_tab == "tab_script":
                    self.watch_script_content(content)
                elif active_tab == "tab_job":
                    self.watch_job_content(content)
            else:
                self.app.notify(f"No matches found for '{query}' in {label}", severity="warning")

        safe_call_app(self.app, _update_ui)

    def show_error(self, widget_id: str, message: str) -> None:
        """
        Display an error message in a specific widget and clear cache.

        Args:
            widget_id: The ID of the widget where the error should be shown.
            message: The error message to display.
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
