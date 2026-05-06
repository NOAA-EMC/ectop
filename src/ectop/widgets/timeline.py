# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Timeline widget for visualizing task runtimes.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

from ectop.constants import STATE_MAP

if TYPE_CHECKING:
    import ecflow


@dataclass
class TimelineEvent:
    """
    Data structure for a single timeline event.

    Attributes:
        name: The name of the node.
        state: The current state of the node.
        time: The timestamp of the last state change.
        path: The absolute path of the node.
    """

    name: str
    state: str
    time: datetime
    path: str


@dataclass
class TimelineData:
    """
    Aggregated data for the timeline visualization.

    Attributes:
        title: The title of the timeline.
        events: A list of timeline events.
    """

    title: str
    events: list[TimelineEvent]


def gather_timeline_data(node: ecflow.Node) -> TimelineData:
    """
    Gather timeline data for a node and its related nodes.

    Args:
        node: The ecFlow node to gather data for.

    Returns:
        TimelineData: An object containing the extracted information.

    Raises:
        RuntimeError: If there is an issue accessing ecFlow node attributes.

    Notes:
        This function performs I/O-like operations on ecFlow objects and
        should be called from a background thread to maintain UI responsiveness.
    """
    import ecflow

    # In ecFlow Python API, Task, Family and Suite all have a 'nodes' attribute (iterator).
    # However, for a Task it is always empty.
    is_task = isinstance(node, ecflow.Task)
    parent = node.get_parent()

    if is_task and parent:
        nodes_to_show = list(parent.nodes)
        title = f"Timeline for {parent.get_abs_node_path()}"
    else:
        nodes_to_show = list(node.nodes)
        if not nodes_to_show:
            nodes_to_show = [node]
        title = f"Timeline for {node.get_abs_node_path()}"

    events = []
    for n in nodes_to_show:
        try:
            # We only have the LAST state change time from ecFlow Node API
            time_str = n.get_state_change_time("iso")
            if time_str == "not-a-date-time":
                continue

            dt = datetime.fromisoformat(time_str)
            events.append(
                TimelineEvent(
                    name=n.name(),
                    state=str(n.get_state()),
                    time=dt,
                    path=n.get_abs_node_path(),
                )
            )
        except (ValueError, AttributeError):
            continue

    return TimelineData(title=title, events=events)


class TimelineTab(Static):
    """
    A widget to display a horizontal timeline of task runtimes.

    .. note::
        If you modify features, API, or usage, you MUST update the documentation immediately.
    """

    def update_timeline(self, data: TimelineData | None) -> None:
        """
        Update the timeline visualization with pre-processed data.

        Args:
            data: The pre-processed timeline data, or None if no data is available.

        Returns:
            None
        """
        if not data or not data.events:
            self.update(Text("No tasks to display in timeline.", style="italic"))
            return

        # Sort by time
        sorted_events = sorted(data.events, key=lambda x: x.time)

        min_time = sorted_events[0].time
        max_time = sorted_events[-1].time
        total_duration = (max_time - min_time).total_seconds()

        width = self.size.width - 20 if self.size.width > 40 else 60

        output = Text()
        output.append(f"📊 {data.title}\n\n", style="bold underline")

        for item in sorted_events:
            offset = 0
            if total_duration > 0:
                offset = int(((item.time - min_time).total_seconds() / total_duration) * (width - 1))

            state_icon = STATE_MAP.get(item.state, "⚪")
            line = Text()
            line.append(f"{item.name[:15]:<15} ")
            line.append(" " * offset)
            line.append("▆", style="bold")  # Representing the point of state change
            line.append(f" {state_icon} {item.state} ({item.time.strftime('%H:%M:%S')})")
            output.append(line)
            output.append("\n")

        self.update(output)
