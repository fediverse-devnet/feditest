"""
Test the equivalent of `feditest create-constellation`
"""

import pytest

from feditest.testplan import TestPlanConstellation, TestPlanConstellationNode

@pytest.fixture(scope="session")
def node1() -> TestPlanConstellationNode:
    return TestPlanConstellationNode( 'node1-driver', { 'foo' : 'Foo', 'bar' : 'Bar'})


@pytest.fixture(scope="session")
def node2() -> TestPlanConstellationNode:
    return TestPlanConstellationNode( 'node2-driver', { 'baz' : 'Baz'})


def test_unnamed(
    node1: TestPlanConstellationNode,
    node2: TestPlanConstellationNode
) -> None:
    """
    TestPlanConstellations don't have automatic names.
    """
    roles = {
        'role1' : node1,
        'role2'  : node2
    }

    constellation = TestPlanConstellation(roles)

    assert len(constellation.roles) == 2
    assert constellation.name is None


def test_named(
    node1: TestPlanConstellationNode,
    node2: TestPlanConstellationNode
) -> None:
    """
    TestPlanConstellations can be named
    """

    NAME = 'My constellation'

    roles = {
        'role1' : node1,
        'role2'  : node2
    }

    constellation = TestPlanConstellation(roles)
    constellation.name = NAME

    assert len(constellation.roles) == 2
    assert constellation.name == NAME

