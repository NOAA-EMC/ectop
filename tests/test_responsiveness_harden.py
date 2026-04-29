# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import pytest

from ectop.app import Ectop
from ectop.widgets.modals.variables import VariableTweaker
from ectop.widgets.modals.why import WhyInspector


@pytest.mark.asyncio
async def test_why_inspector_responsiveness(ecflow_server):
    """
    Verify that WhyInspector remains responsive and non-blocking.
    """
    host, port = ecflow_server.split(":")
    app = Ectop(host=host, port=int(port))

    async with app.run_test() as pilot:
        # Give some time for initial connect
        await pilot.pause(0.5)

        # Manually push the screen to test it
        why_screen = WhyInspector("/nonexistent", app.ecflow_client)
        await app.push_screen(why_screen)
        await pilot.pause(0.2)

        # Verify the screen is active
        assert isinstance(app.screen, WhyInspector)

        # Try a keypress to see if event loop is alive
        # Escape should close it
        await pilot.press("escape")
        await pilot.pause(0.1)

        # Should be back to main screen
        assert not isinstance(app.screen, WhyInspector)


@pytest.mark.asyncio
async def test_variable_tweaker_responsiveness(ecflow_server):
    """
    Verify that VariableTweaker remains responsive and non-blocking.
    """
    host, port = ecflow_server.split(":")
    app = Ectop(host=host, port=int(port))

    async with app.run_test() as pilot:
        await pilot.pause(0.5)

        var_screen = VariableTweaker("/nonexistent", app.ecflow_client)
        await app.push_screen(var_screen)
        await pilot.pause(0.2)

        assert isinstance(app.screen, VariableTweaker)

        await pilot.press("escape")
        await pilot.pause(0.1)

        assert not isinstance(app.screen, VariableTweaker)
