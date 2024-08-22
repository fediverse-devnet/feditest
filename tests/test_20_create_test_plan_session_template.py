# SPDX-FileCopyrightText: 2023-2024 Johannes Ernst
# SPDX-FileCopyrightText: 2023-2024 Steve Bate
#
# SPDX-License-Identifier: MIT

"""
Test the equivalent of `feditest create-session-template`
"""
from typing import Any

import pytest

import feditest
from feditest import test
from feditest.protocols import Node
from feditest.testplan import TestPlanConstellation, TestPlanConstellationNode, TestPlanSession, TestPlanTestSpec


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


def _session_template(session_name: str | None) -> TestPlanSession:
    test_plan_specs : list[TestPlanTestSpec]= []
    constellation_role_names : dict[str,Any] = {}
    for name in sorted(feditest.all_tests.keys()):
        test = feditest.all_tests.get(name)
        if test is None: # make linter happy
            continue

        test_plan_spec = TestPlanTestSpec(name)
        test_plan_specs.append(test_plan_spec)

        for role_name in test.needed_local_role_names():
            constellation_role_names[role_name] = 1
            if not test_plan_spec.rolemapping:
                test_plan_spec.rolemapping = {}
            test_plan_spec.rolemapping[role_name] = role_name

    constellation_roles: dict[str,TestPlanConstellationNode | None] = {}
    for constellation_role_name in constellation_role_names:
        constellation_roles[constellation_role_name] = None

    session = TestPlanSession(TestPlanConstellation(constellation_roles), test_plan_specs, session_name)
    return session


@pytest.fixture()
def unnamed() -> TestPlanSession:
    return _session_template(None)


@pytest.fixture()
def named() -> TestPlanSession:
    return _session_template(SESSION_TEMPLATE_NAME)


def test_session_template_unnamed(unnamed: TestPlanSession) -> None:
    assert unnamed.name is None
    assert str(unnamed) == 'Unnamed'
    assert len(unnamed.tests) == 3
    assert unnamed.constellation
    assert unnamed.constellation.name is None
    assert str(unnamed.constellation) == 'Unnamed'
    assert unnamed.constellation.is_template()
    assert len(unnamed.constellation.roles) == 3
    assert 'role_a' in unnamed.constellation.roles
    assert 'role_b' in unnamed.constellation.roles
    assert 'role_c' in unnamed.constellation.roles
    assert unnamed.constellation.roles['role_a'] is None
    assert unnamed.constellation.roles['role_b'] is None
    assert unnamed.constellation.roles['role_c'] is None


def test_session_template_named(named: TestPlanSession) -> None:
    assert named.name == SESSION_TEMPLATE_NAME
    assert str(named) == SESSION_TEMPLATE_NAME
    assert len(named.tests) == 3
    assert named.constellation
    assert named.constellation.name is None
    assert str(named.constellation) == 'Unnamed'
    assert named.constellation.is_template()
    assert len(named.constellation.roles) == 3
    assert 'role_a' in named.constellation.roles
    assert 'role_b' in named.constellation.roles
    assert 'role_c' in named.constellation.roles
    assert named.constellation.roles['role_a'] is None
    assert named.constellation.roles['role_b'] is None
    assert named.constellation.roles['role_c'] is None
