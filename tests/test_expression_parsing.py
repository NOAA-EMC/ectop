# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
import ecflow
import pytest

from ectop.client import EcflowClient
from ectop.constants import EXPR_AND_LABEL, EXPR_OR_LABEL
from ectop.widgets.modals.why import DepData, WhyInspector


@pytest.fixture
def inspector():
    return WhyInspector("/test", EcflowClient())


@pytest.fixture
def defs():
    d = ecflow.Defs()
    s = d.add_suite("s1")
    s.add_task("t1")
    s.add_task("t2")
    f = s.add_family("f1")
    f.add_task("t3")
    return d


def test_parse_complex_path(inspector, defs):
    s1 = defs.find_suite("s1")
    s1.add_family("family_1").add_task("task.2")
    expr = "/s1/family_1/task.2 == complete"
    parent = DepData("Root")
    inspector._parse_expression_data(parent, expr, defs)
    assert "/s1/family_1/task.2 == unknown (Expected: complete)" in parent.children[0].label


def test_parse_nested_and_or(inspector, defs):
    expr = "(/s1/t1 == complete and /s1/t2 == complete) or /s1/f1/t3 == complete"
    parent = DepData("Root")
    inspector._parse_expression_data(parent, expr, defs)
    root = parent.children[0]
    assert EXPR_OR_LABEL in root.label
    assert len(root.children) == 2
    assert EXPR_AND_LABEL in root.children[0].label


def test_gather_dependency_data_limits(inspector, defs):
    suite = defs.find_suite("s1")
    suite.add_limit("max_jobs", 10)
    task = suite.find_task("t1")
    task.add_inlimit("max_jobs")
    dep_data = inspector._gather_dependency_data(task, defs)
    limit_node = next((d for d in dep_data.children if "Limits" in d.label), None)
    if limit_node:
        assert any("max_jobs" in c.label for c in limit_node.children)


def test_gather_dependency_data_times(inspector, defs):
    task = defs.find_abs_node("/s1/t1")
    task.add_time("10:00")
    dep_data = inspector._gather_dependency_data(task, defs)
    assert any("Time Dependencies" in d.label for d in dep_data.children)
