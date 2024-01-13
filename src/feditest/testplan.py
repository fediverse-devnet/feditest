"""
"""

from typing import Any
import msgspec

from feditest import all_app_drivers
from feditest.reporting import fatal


class TestPlanConstellationRole(msgspec.Struct):
    appdriver: str
    parameters: dict[str,Any] | None = None

class TestPlanConstellation(msgspec.Struct):
    roles : dict[str,TestPlanConstellationRole]
    name: str = None


class TestPlanTestSpec(msgspec.Struct):
    name: str
    disabled: str | None = None


class TestPlanSession(msgspec.Struct):
    constellation : TestPlanConstellation
    tests : list[TestPlanTestSpec]
    name: str = None


class TestPlan(msgspec.Struct):
    """
    A TestPlan defines one or more TestPlanSessions. TestPlanSessions can be run sequentially, or
    (in theory; no code yet) in parallel.
    Each TestPlanSession spins up and tears down a constellation of Nodes that participate in the
    test. The constellation has 1 or more roles, which are bound to systems-under-test that
    communicate with each other during the test.
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
        Check that we have all the test and app drivers needed for this plan. If all is well,
        return. If not well, throw an Exception that explains the problem
        """
        global all_app_drivers

        for session in self.sessions:
            for role_name in session.constellation.roles:
                role = session.constellation.roles[role_name]
                app_driver_name : str = role.appdriver
                
                if not app_driver_name in all_app_drivers:
                    fatal('Cannot find app driver:', app_driver_name, 'for role:', role_name)
        print( "FIXME: check_can_be_executed")
        return