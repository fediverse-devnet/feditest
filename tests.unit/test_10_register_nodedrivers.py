"""
Test that @nodedriver annotations register NodeDrivers correctly.
"""

import pytest

import feditest
from feditest import nodedriver
from feditest.nodedrivers import NodeDriver


@pytest.fixture(scope="module", autouse=True)
def init():
    """ Keep these isolated to this module """
    feditest.all_node_drivers = {}
    feditest._loading_node_drivers = True

    @nodedriver
    class NodeDriver1(NodeDriver):
        pass

    @nodedriver
    class NodeDriver2(NodeDriver):
        pass

    @nodedriver
    class NodeDriver3(NodeDriver):
        pass

    feditest._loading_node_drivers = False


def test_node_drivers_registered() -> None:
    assert len(feditest.all_node_drivers) == 3

    prefix = 'test_10_register_nodedrivers.init.<locals>.'
    assert prefix + 'NodeDriver1' in feditest.all_node_drivers
    assert prefix + 'NodeDriver2' in feditest.all_node_drivers
    assert prefix + 'NodeDriver3' in feditest.all_node_drivers

    # Can't directly refer to NodeDriverX for some reason
    assert feditest.all_node_drivers.get(prefix + 'NodeDriver1').__name__.endswith('NodeDriver1')
    assert feditest.all_node_drivers.get(prefix + 'NodeDriver2').__name__.endswith('NodeDriver2')
    assert feditest.all_node_drivers.get(prefix + 'NodeDriver3').__name__.endswith('NodeDriver3')
