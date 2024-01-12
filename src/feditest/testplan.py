"""
"""

from typing import Any
import msgspec

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
