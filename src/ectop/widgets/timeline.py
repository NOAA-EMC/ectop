# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Timeline widget for visualizing task runtimes.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

from ectop.constants import STATE_MAP

if TYPE_CHECKING:
    import ecflow


class TimelineTab(Static):
    """
    A widget to display a horizontal timeline of task runtimes.
    """

    def update_timeline(self, node: ecflow.Node) -> None:
        """
        Update the timeline for the given node and its siblings/children.

        Args:
            node: The currently selected ecFlow node.
        """
        # If it's a task, show its siblings. If it's a family/suite, show its children.
        is_container = hasattr(node, "nodes")
        parent = node.get_parent()

        if not is_container and parent:
            nodes_to_show = list(parent.nodes)
            title = f"Timeline for {parent.get_abs_node_path()}"
        else:
            nodes_to_show = list(node.nodes) if is_container else [node]
            title = f"Timeline for {node.get_abs_node_path()}"

        if not nodes_to_show:
            self.update(Text("No tasks to display in timeline.", style="italic"))
            return

        # Collect state change times and states
        data = []
        for n in nodes_to_show:
            try:
                # We only have the LAST state change time from ecFlow Node API
                # For a real Gantt chart, we'd need history or more sophisticated tracking.
                # Here we'll visualize the last state change time relative to others.
                time_str = n.get_state_change_time("iso")
                if time_str == "not-a-date-time":
                    continue

                dt = datetime.fromisoformat(time_str)
                data.append({"name": n.name(), "state": str(n.get_state()), "time": dt, "path": n.get_abs_node_path()})
            except (ValueError, AttributeError):
                continue

        if not data:
            self.update(Text("No timing data available for these nodes.", style="italic"))
            return

        # Sort by time
        data.sort(key=lambda x: x["time"])

        min_time = data[0]["time"]
        max_time = data[-1]["time"]
        total_duration = (max_time - min_time).total_seconds()

        width = self.size.width - 20 if self.size.width > 40 else 60

        output = Text()
        output.append(f"📊 {title}\n\n", style="bold underline")

        for item in data:
            offset = 0
            if total_duration > 0:
                offset = int(((item["time"] - min_time).total_seconds() / total_duration) * (width - 1))

            state_icon = STATE_MAP.get(item["state"], "⚪")
            line = Text()
            line.append(f"{item['name'][:15]:<15} ")
            line.append(" " * offset)
            line.append("▆", style="bold")  # Representing the point of state change
            line.append(f" {state_icon} {item['state']} ({item['time'].strftime('%H:%M:%S')})")
            output.append(line)
            output.append("\n")

        self.update(output)
