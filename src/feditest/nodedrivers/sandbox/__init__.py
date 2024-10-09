"""
"""

from typing import List

from feditest.nodedrivers import AccountManager, NodeConfiguration, NodeDriver, HOSTNAME_PAR
from feditest.protocols.sandbox import SandboxLogEvent, SandboxMultClient, SandboxMultServer
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeParameter
from feditest.utils import FEDITEST_VERSION


class SandboxMultClient_ImplementationA(SandboxMultClient):
    """
    A client implementation in the Sandbox protocol that can be tested. It's trivially simple.
    """
    def cause_mult(self, server: SandboxMultServer, a: float, b: float) -> float:
        c = server.mult(a, b)
        return c


class SandboxMultClientDriver_ImplementationA(NodeDriver):
    """
    Driver for the client implementation, so the client can be provisioned and unprovisioned for
    test sessions.
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return [ HOSTNAME_PAR ]


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        return (
            NodeConfiguration(
                self,
                'SandboxMultClient_ImplementationA',
                FEDITEST_VERSION,
                test_plan_node.parameter(HOSTNAME_PAR)
            ),
            None
        )


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) ->  SandboxMultClient_ImplementationA:
        return SandboxMultClient_ImplementationA(rolename, config, account_manager)


class SandboxMultServer_Implementation1(SandboxMultServer):
    """
    First server implementation in the Sandbox protocol with some test instrumentation.
    This server implementation simply calculates a*b.
    """
    def __init__(self, rolename: str, config: NodeConfiguration):
        super().__init__(rolename, config) # Has no AccountManager
        self._log : List[SandboxLogEvent] | None = None


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
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return [ HOSTNAME_PAR ]


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        return (
            NodeConfiguration(
                self,
                'SandboxMultServer_Implementation1',
                FEDITEST_VERSION,
                test_plan_node.parameter(HOSTNAME_PAR)
            ),
            None
        )


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) ->  SandboxMultServer_Implementation1:
        return SandboxMultServer_Implementation1(rolename, config)


class SandboxMultServer_Implementation2Faulty(SandboxMultServer):
    """
    Second server implementation in the Sandbox protocol with some test instrumentation.
    This server calculates a*b through a for loop using integers rather than floats
    """
    def __init__(self, rolename: str, config: NodeConfiguration):
        super().__init__(rolename, config) # Has no AccountManager
        self._log : List[SandboxLogEvent] | None = None


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
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return [ HOSTNAME_PAR ]


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        return (
            NodeConfiguration(
                self,
                'SandboxMultServer_Implementation2Faulty',
                FEDITEST_VERSION,
                test_plan_node.parameter(HOSTNAME_PAR)
            ),
            None
        )


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) ->  SandboxMultServer_Implementation2Faulty:
        return SandboxMultServer_Implementation2Faulty(rolename, config)
