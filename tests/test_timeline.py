# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for Timeline visualization.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import ecflow
from rich.text import Text

from ectop.widgets.timeline import TimelineTab


def test_timeline_update():
    """
    Test that update_timeline correctly processes nodes and renders text.
    """
    timeline = TimelineTab()
    mock_size = MagicMock()
    mock_size.width = 100
    with patch.object(TimelineTab, "size", return_value=mock_size, new_callable=PropertyMock):
        # Mock ecflow nodes
        task1 = MagicMock(spec=ecflow.Node)
        task1.name.return_value = "task1"
        task1.get_state.return_value = ecflow.State.complete
        task1.get_state_change_time.return_value = "2023-10-27T10:00:00"
        task1.get_abs_node_path.return_value = "/s1/f1/task1"

        task2 = MagicMock(spec=ecflow.Node)
        task2.name.return_value = "task2"
        task2.get_state.return_value = ecflow.State.active
        task2.get_state_change_time.return_value = "2023-10-27T10:05:00"
        task2.get_abs_node_path.return_value = "/s1/f1/task2"

        parent = MagicMock(spec=ecflow.Node)
        parent.nodes = [task1, task2]
        parent.get_abs_node_path.return_value = "/s1/f1"

        task1.get_parent.return_value = parent
        task2.get_parent.return_value = parent

        timeline.update = MagicMock()

        # Update timeline for task1
        timeline.update_timeline(task1)

        timeline.update.assert_called_once()
    rendered_text = timeline.update.call_args[0][0]
    assert isinstance(rendered_text, Text)
    text_content = str(rendered_text)
    assert "task1" in text_content
    assert "task2" in text_content
    assert "complete" in text_content
    assert "active" in text_content
