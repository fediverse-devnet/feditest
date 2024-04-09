"""
Classes that represent a TestPlan and its parts.
"""

from typing import Any

import msgspec

from feditest import Test, all_node_drivers, all_tests
from feditest.reporting import fatal


class TestPlanConstellationRole(msgspec.Struct):
    name: str
    nodedriver: str
    hostname: str | None = None # If none is given, one is provisioned
    parameters: dict[str,Any] | None = None


class TestPlanConstellation(msgspec.Struct):
    roles : list[TestPlanConstellationRole]
    name: str = None


class TestPlanTestSpec(msgspec.Struct):
    name: str
    disabled: str | None = None # if a string is given, it's a reason message why disabled


class TestPlanSession(msgspec.Struct):
    constellation : TestPlanConstellation
    tests : list[TestPlanTestSpec]
    name: str = None


class TestPlan(msgspec.Struct):
    """
    A TestPlan defines one or more TestPlanSessions. TestPlanSessions can be run sequentially, or
    (in theory; no code yet) in parallel.
    Each TestPlanSession spins up and tears down a constellation of Nodes that participate in the
    test. The constellation has 1 or more roles, which are bound to nodes that communicate with
    each other according to the to-be-tested protocol(s) during the test.
    """
    name: str = None
    sessions : list[TestPlanSession] = []

    @staticmethod
    def load(filename: str) -> 'TestPlan':
        """
        Read a file, and instantiate a TestPlan from what we find.
        """
        with open(filename) as f:
            data = f.read()

        return msgspec.json.decode(data, type=TestPlan)


    def check_can_be_executed(self) -> None:
        """
        Check that we have all the tests and node drivers needed for this plan. If all is well,
        return. If not well, throw an Exception that explains the problem
        """
        for session in self.sessions:
            all_roles = {}
            for role in session.constellation.roles:
                role_name = role.name
                if role_name in all_roles:
                    fatal('Role names must be unique within a constellation:', role_name)
                all_roles[role_name] = True
                node_driver_name : str = role.nodedriver

                if node_driver_name not in all_node_drivers:
                    fatal('Cannot find node driver:', node_driver_name, 'for role:', role.name)

            for test_spec in session.tests:
                test : Test | None = all_tests.get(test_spec.name)
                if test is None:
                    fatal('Cannot find test:', test_spec.name)
                if test.constellation_size != len(session.constellation.roles):
                    fatal('Cannot run test with constellation of size', len(session.constellation.roles), ':', test_spec.name)
