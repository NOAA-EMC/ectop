# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for Timeline visualization using real ecFlow objects.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, PropertyMock, patch

import ecflow
from rich.text import Text

from ectop.widgets.timeline import TimelineData, TimelineEvent, TimelineTab, gather_timeline_data


def test_gather_timeline_data():
    """
    Test that gather_timeline_data correctly extracts data from a real ecFlow hierarchy.
    """
    defs = ecflow.Defs()
    suite = defs.add_suite("s1")
    fam = suite.add_family("f1")
    t1 = fam.add_task("t1")
    fam.add_task("t2")

    # ecFlow doesn't allow setting state change time directly easily in Python without a server
    # but we can verify it handles the 'not-a-date-time' case or mock the specific node method if needed.
    # However, for 'Anti-Mocking', we prefer using the real objects.

    data = gather_timeline_data(t1)
    assert data.title == "Timeline for /s1/f1"
    # Initially they might have 'not-a-date-time' if not run
    assert len(data.events) == 0


def test_timeline_render():
    """
    Test that TimelineTab.update_timeline correctly renders pre-processed data.
    """
    timeline = TimelineTab()
    mock_size = MagicMock()
    mock_size.width = 100

    with patch.object(TimelineTab, "size", return_value=mock_size, new_callable=PropertyMock):
        events = [
            TimelineEvent(name="task1", state="complete", time=datetime(2023, 10, 27, 10, 0, 0), path="/s1/f1/task1"),
            TimelineEvent(name="task2", state="active", time=datetime(2023, 10, 27, 10, 5, 0), path="/s1/f1/task2"),
        ]
        data = TimelineData(title="Timeline for /s1/f1", events=events)

        timeline.update = MagicMock()
        timeline.update_timeline(data)

        timeline.update.assert_called_once()
        rendered_text = timeline.update.call_args[0][0]
        assert isinstance(rendered_text, Text)
        text_content = str(rendered_text)
        assert "task1" in text_content
        assert "task2" in text_content
        assert "complete" in text_content
        assert "active" in text_content
        assert "10:00:00" in text_content
        assert "10:05:00" in text_content


def test_timeline_empty():
    """
    Test that TimelineTab handles empty data gracefully.
    """
    timeline = TimelineTab()
    timeline.update = MagicMock()

    timeline.update_timeline(None)
    rendered_text = timeline.update.call_args[0][0]
    assert "No tasks" in str(rendered_text)

    timeline.update.reset_mock()
    timeline.update_timeline(TimelineData(title="Empty", events=[]))
    rendered_text = timeline.update.call_args[0][0]
    assert "No tasks" in str(rendered_text)
