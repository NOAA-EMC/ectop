# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from ectop.widgets.modals.variables import VariableTweaker
from ectop.widgets.modals.why import WhyInspector


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.mark.asyncio
async def test_variable_tweaker_workers(mock_client):
    """Test variable tweaker logic for deleting and adding variables."""
    with patch.object(VariableTweaker, "app", new_callable=PropertyMock) as mock_app:
        mock_app.return_value = MagicMock()
        tweaker = VariableTweaker("/node", mock_client)
        tweaker.query_one = MagicMock()

        with patch.object(tweaker, "refresh_vars", new_callable=MagicMock):
            await tweaker._delete_variable_logic("VAR1")
            mock_client.alter.assert_called_with("/node", "delete", "variable", "VAR1")

            await tweaker._submit_variable_logic("NEWVAR=NEWVAL")
            mock_client.alter.assert_called_with("/node", "add", "variable", "NEWVAR", "NEWVAL")


@pytest.mark.asyncio
async def test_why_inspector_worker(mock_client):
    """Test why inspector logic for refreshing dependencies."""
    with patch.object(WhyInspector, "app", new_callable=PropertyMock) as mock_app:
        mock_app.return_value = MagicMock()
        inspector = WhyInspector("/node", mock_client)
        tree = MagicMock()
        with patch.object(inspector, "_gather_dependency_data"), patch.object(inspector, "_update_tree_ui"):
            await inspector._refresh_deps_logic(tree)
            mock_client.sync_local.assert_called_once()
