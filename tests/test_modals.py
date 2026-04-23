# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for modal widgets in Ectop.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from textual.widgets import DataTable

from ectop.app import Ectop
from ectop.widgets.modals.variables import VariableTweaker
from ectop.widgets.modals.why import WhyInspector


@pytest.mark.asyncio
async def test_why_inspector() -> None:
    """
    Test the WhyInspector modal.
    """
    mock_client = AsyncMock()
    mock_defs = MagicMock()
    mock_node = MagicMock()
    mock_node.get_abs_node_path.return_value = "/s/t"
    mock_node.name.return_value = "t"
    mock_node.get_state.return_value = "aborted"
    mock_node.get_trigger.return_value = None
    mock_node.get_complete.return_value = None
    mock_node.get_why.return_value = ""
    mock_defs.find_abs_node.return_value = mock_node
    mock_client.get_defs.return_value = mock_defs

    app = Ectop()
    async with app.run_test() as pilot:
        modal = WhyInspector("/s/t", mock_client)
        app.push_screen(modal)
        await pilot.pause()

        worker = modal.refresh_why()
        await worker.wait()
        await pilot.pause()

        assert modal.query_one("#dep_tree").root.label.plain == "Dependencies"


@pytest.mark.asyncio
async def test_variable_tweaker() -> None:
    """
    Test the VariableTweaker modal.
    """
    mock_client = AsyncMock()
    mock_defs = MagicMock()
    mock_node = MagicMock()
    mock_node.variables = []
    mock_node.get_generated_variables.return_value = []
    mock_node.get_parent.return_value = None
    mock_defs.find_abs_node.return_value = mock_node
    mock_client.get_defs.return_value = mock_defs

    app = Ectop()
    async with app.run_test() as pilot:
        modal = VariableTweaker("/s/t", mock_client)
        app.push_screen(modal)
        await pilot.pause()

        worker = modal.refresh_vars()
        await worker.wait()
        await pilot.pause()

        table = modal.query_one(DataTable)
        assert table.row_count == 0
