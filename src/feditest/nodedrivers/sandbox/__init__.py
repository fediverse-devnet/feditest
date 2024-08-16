"""
"""

# pylint: disable=invalid-name

from typing import Any, List

from feditest.protocols import NodeDriver
from feditest.protocols.sandbox import SandboxLogEvent, SandboxMultClient, SandboxMultServer
from feditest.testplan import TestPlanConstellationNode
from feditest.utils import FEDITEST_VERSION


class SandboxMultClient_ImplementationA(SandboxMultClient):
    """
    A client implementation in the Sandbox protocol that can be tested. It's trivially simple.
    """
    def cause_mult(self, server: SandboxMultServer, a: float, b: float) -> float:
        c = server.mult(a, b)
        return c


    @property
    def app_version(self):
        return FEDITEST_VERSION


class SandboxMultClientDriver_ImplementationA(NodeDriver):
    """
    Driver for the client implementation, so the client can be provisioned and unprovisioned for
    test sessions.
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, parameters)
        parameters['app'] = 'SandboxMultClient_ImplementationA'


    # Python 3.12 @override
    def _provision_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]) -> SandboxMultClient_ImplementationA:
        return SandboxMultClient_ImplementationA(rolename, test_plan_node, parameters, self)


class SandboxMultServer_Implementation1(SandboxMultServer):
    """
    First server implementation in the Sandbox protocol with some test instrumentation.
    This server implementation simply calculates a*b.
    """
    def __init__(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any], node_driver: 'SandboxMultServerDriver_Implementation1'):
        super().__init__(rolename, test_plan_node, parameters, node_driver)
        self._log : List[SandboxLogEvent] | None = None


    @property
    def app_version(self):
        return FEDITEST_VERSION


    def mult(self, a: float, b: float) -> float:
        # Here's the key 'mult' functionality:
        c = a*b
        if self._log is not None:
            self._log.append(SandboxLogEvent(a, b, c))
        return c


    def start_logging(self):
        self._log = []


    def get_and_clear_log(self):
        ret = self._log
        self._log = None
        return ret


class SandboxMultServerDriver_Implementation1(NodeDriver):
    """
    Driver for the first server implementation, so this server implementation can be provisioned and unprovisioned for
    test sessions.
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, parameters)
        parameters['app'] = 'SandboxMultServer_Implementation1'


    # Python 3.12 @override
    def _provision_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any] ) -> SandboxMultServer_Implementation1:
        return SandboxMultServer_Implementation1(rolename, test_plan_node, parameters, self)


class SandboxMultServer_Implementation2Faulty(SandboxMultServer):
    """
    Second server implementation in the Sandbox protocol with some test instrumentation.
    This server calculates a*b through a for loop using integers rather than floats
    """
    def __init__(self, rolename: str, test_plan_node: TestPlanConstellationNode,  parameters: dict[str,Any], node_driver: 'SandboxMultServerDriver_Implementation2Faulty'):
        super().__init__(rolename, test_plan_node, parameters, node_driver)
        self._log : List[SandboxLogEvent] | None = None


    @property
    def app_version(self):
        return FEDITEST_VERSION


    def mult(self, a: float, b: float) -> float:
        c = 0.0
        # Here's the key 'mult' functionality, but it only works for positive a's that are integers!
        a_int = int(a)
        for _ in range(0, a_int) :
            c += b
        if self._log is not None:
            self._log.append(SandboxLogEvent(a, b, c))
        return c


    def start_logging(self):
        self._log = []


    def get_and_clear_log(self):
        ret = self._log
        self._log = None
        return ret


class SandboxMultServerDriver_Implementation2Faulty(NodeDriver):
    """
    Driver for the second server implementation, so this server implementation can be provisioned and unprovisioned for
    test sessions.
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, parameters)
        parameters['app'] = 'SandboxMultServer_Implementation2Faulty'


    # Python 3.12 @override
    def _provision_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]) -> SandboxMultServer_Implementation2Faulty:
        return SandboxMultServer_Implementation2Faulty(rolename, test_plan_node, parameters, self)
