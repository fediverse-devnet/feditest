"""
Test the equivalent of `feditest create-session-template`
"""

import pytest

import feditest
from feditest import test
from feditest.nodedrivers import Node
from feditest.testplan import TestPlanSessionTemplate, TestPlanTestSpec


@pytest.fixture(scope="module", autouse=True)
def init():
    """ Keep these isolated to this module """
    feditest.all_tests = {}
    feditest._registered_as_test = {}
    feditest._registered_as_test_step = {}
    feditest._loading_tests = True

    @test
    def test1(role_a: Node) -> None:
        return

    @test
    def test2(role_a: Node, role_c: Node) -> None:
        return

    @test
    def test3(role_b: Node) -> None:
        return

    feditest._loading_tests = False
    feditest._load_tests_pass2()


SESSION_TEMPLATE_NAME = 'My Session'


def _session_template(session_name: str | None) -> TestPlanSessionTemplate:
    test_plan_specs : list[TestPlanTestSpec]= []
    for name in sorted(feditest.all_tests.keys()):
        test = feditest.all_tests.get(name)
        if test is None: # make linter happy
            continue
        test_plan_spec = TestPlanTestSpec(name)
        test_plan_specs.append(test_plan_spec)

    session = TestPlanSessionTemplate(test_plan_specs, session_name)
    return session


@pytest.fixture()
def unnamed() -> TestPlanSessionTemplate:
    return _session_template(None)


@pytest.fixture()
def named() -> TestPlanSessionTemplate:
    return _session_template(SESSION_TEMPLATE_NAME)


def test_session_template_unnamed(unnamed: TestPlanSessionTemplate) -> None:
    assert unnamed.name is None
    assert str(unnamed) == 'Unnamed'
    assert len(unnamed.tests) == 3


def test_session_template_named(named: TestPlanSessionTemplate) -> None:
    assert named.name == SESSION_TEMPLATE_NAME
    assert str(named) == SESSION_TEMPLATE_NAME
    assert len(named.tests) == 3
