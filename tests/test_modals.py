from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from ectop.widgets.modals.variables import VariableTweaker
from ectop.widgets.modals.why import WhyInspector


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.mark.asyncio
async def test_variable_tweaker_workers(mock_client):
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        mock_app.return_value = AsyncMock()
        tweaker = VariableTweaker("/node", mock_client)
        tweaker.query_one = MagicMock()

        with patch.object(tweaker, "refresh_vars", new_callable=AsyncMock):
            await tweaker._delete_variable_logic("VAR1")
            mock_client.alter.assert_called_with("/node", "delete_variable", "VAR1")

            await tweaker._submit_variable_logic("NEWVAR=NEWVAL")
            mock_client.alter.assert_called_with("/node", "add_variable", "NEWVAR", "NEWVAL")


@pytest.mark.asyncio
async def test_why_inspector_worker(mock_client):
    with patch.object(WhyInspector, "app", new_callable=PropertyMock) as mock_app:
        mock_app.return_value = AsyncMock()
        inspector = WhyInspector("/node", mock_client)
        tree = MagicMock()
        with patch.object(inspector, "_gather_dependency_data"), patch.object(inspector, "_update_tree_ui"):
            await inspector._refresh_deps_logic(tree)
            mock_client.sync_local.assert_called_once()
