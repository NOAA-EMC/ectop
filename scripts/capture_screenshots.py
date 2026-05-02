# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import asyncio
import os
import sys
from unittest.mock import MagicMock

# Mock ecflow before importing anything else
mock_ecflow = MagicMock()


class MockNode:
    def __init__(self, name, parent=None):
        self._name = name
        self._parent = parent
        self.nodes = []
        self.variables = []
        self.inlimits = []

    def name(self):
        return self._name

    def get_abs_node_path(self):
        if self._parent:
            return self._parent.get_abs_node_path().rstrip("/") + "/" + self._name
        return "/" + self._name

    def get_parent(self):
        return self._parent

    def get_state(self):
        return "active"

    def get_generated_variables(self):
        return []

    def get_trigger(self):
        return None

    def get_complete(self):
        return None

    def get_why(self):
        return "Testing"

    def get_all_nodes(self):
        res = []
        for n in self.nodes:
            res.append(n)
            res.extend(n.get_all_nodes())
        return res


class MockSuite(MockNode):
    pass


class MockFamily(MockNode):
    pass


class MockTask(MockNode):
    pass


mock_ecflow.Suite = MockSuite
mock_ecflow.Family = MockFamily
mock_ecflow.Task = MockTask
mock_ecflow.State.active = "active"
mock_ecflow.State.complete = "complete"

sys.modules["ecflow"] = mock_ecflow

# We need to set PYTHONPATH to find src BEFORE importing ectop
sys.path.insert(0, os.path.abspath("src"))

# Mock the client
from ectop.app import Ectop  # noqa: E402


async def capture_screenshots():
    # Setup mock client
    mock_client = MagicMock()
    mock_defs = MagicMock()

    suite = MockSuite("ectop_demo")
    family = MockFamily("operational", suite)
    task1 = MockTask("process_1", family)
    task2 = MockTask("process_2", family)
    family.nodes = [task1, task2]
    suite.nodes = [family]

    mock_defs.suites = [suite]
    mock_defs.get_all_nodes.return_value = suite.get_all_nodes() + [suite]
    mock_defs.find_abs_node.side_effect = lambda p: task1 if "process_1" in p else (family if "operational" in p else suite)

    mock_client.get_defs_sync.return_value = mock_defs

    # Initialize app
    app = Ectop()
    app.client = mock_client

    # Capture main view
    async with app.run_test(size=(120, 40)) as pilot:
        # Load the mock defs into the tree
        from ectop.widgets.sidebar import SuiteTree

        tree = app.query_one(SuiteTree)
        tree.update_tree("localhost", 3141, mock_defs)

        await pilot.pause(1.0)
        # Expand the tree to show something
        await pilot.press("enter")  # Expand suite
        await pilot.pause(0.5)
        await pilot.press("down", "enter")  # Expand family
        await pilot.pause(0.5)

        try:
            svg = app.export_screenshot()
            with open("docs/assets/main_view.svg", "w") as f:
                f.write(svg)
            print("Captured main_view.svg")
        except Exception as e:
            print(f"Failed main_view: {e}")

        # Open Why Inspector
        try:
            from ectop.widgets.modals.why import WhyInspector

            screen = WhyInspector("/ectop_demo/operational/process_1", mock_client)
            app.push_screen(screen)
            await pilot.pause(1.0)
            svg = app.export_screenshot()
            with open("docs/assets/why_inspector.svg", "w") as f:
                f.write(svg)
            print("Captured why_inspector.svg")
            app.pop_screen()
        except Exception as e:
            print(f"Failed why_inspector: {e}")

        # Open Variable Tweaker
        try:
            from ectop.widgets.modals.variables import VariableTweaker

            screen = VariableTweaker("/ectop_demo/operational/process_1", mock_client)
            app.push_screen(screen)
            await pilot.pause(1.0)
            svg = app.export_screenshot()
            with open("docs/assets/variable_tweaker.svg", "w") as f:
                f.write(svg)
            print("Captured variable_tweaker.svg")
            app.pop_screen()
        except Exception as e:
            print(f"Failed variable_tweaker: {e}")


if __name__ == "__main__":
    os.makedirs("docs/assets", exist_ok=True)
    try:
        asyncio.run(capture_screenshots())
    except Exception as e:
        print(f"Error: {e}")
