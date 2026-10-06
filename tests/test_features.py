# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the documentation immediately.
# #############################################################################
"""Feature tests for plain-data search matching."""

from __future__ import annotations

import ecflow

from ectop.widgets.sidebar import DefinitionSnapshot, SuiteTree


def test_search_logic_uses_real_definition_snapshot() -> None:
    """Match paths case-insensitively using actual ecFlow definitions.

    Returns
    -------
    None
        The test asserts next-match and missing-match behavior.
    """
    defs = ecflow.Defs()
    suite = defs.add_suite("suite")
    suite.add_task("task1")
    suite.add_task("post_proc")
    snapshot = DefinitionSnapshot.from_defs(defs, generation=1)

    assert SuiteTree._find_path(snapshot, "task", None) == "/suite/task1"
    assert SuiteTree._find_path(snapshot, "POST", None) == "/suite/post_proc"
    assert SuiteTree._find_path(snapshot, "missing", None) is None
