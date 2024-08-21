"""
A NodeDriver that supports all protocols but doesn't automate anything.
"""

from typing import Any

from feditest.protocols import Node, NodeDriver
from feditest.protocols.fediverse import FallbackFediverseNode, FediverseNode
from feditest.testplan import TestPlanConstellationNode
from feditest.utils import appname_validate, hostname_validate


class AbstractManualFediverseNodeDriver(NodeDriver):
    """
    Abstract superclass of NodeDrivers that support all web server-side protocols but don't
    automate anything.
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, test_plan_node, parameters)
        hostname = parameters.get('hostname')
        if hostname:
            self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                             + f' with hostname "{ hostname }" and hit return when done.')
        else:
            parameters['hostname'] = self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                                        + ' and enter the hostname when done: ',
                                        parse_validate=hostname_validate)
        app = parameters.get('app')
        if not app:
            parameters['app'] = self.prompt_user('Enter the name of the app you just provisioned'
                                                 + f' at hostname { parameters["hostname"] }: ',
                                                 parse_validate=appname_validate)


    # Python 3.12 @override
    def _provision_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]) -> FediverseNode:
        return FallbackFediverseNode(rolename, parameters, self, test_plan_node)


    def _unprovision_node(self, node: Node) -> None:
        self.prompt_user(f'Manually unprovision the Node for constellation role { node.rolename() } and hit return when done.')


class ManualFediverseNodeDriver(AbstractManualFediverseNodeDriver):
    """
    A NodeDriver that supports all web server-side protocols but doesn't automate anything.
    """
    # Python 3.12 @override
    def check_plan_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, context_msg: str = '') -> None:
        super().check_plan_node(rolename, test_plan_node)
        FallbackFediverseNode.check_plan_node(test_plan_node, context_msg + "ManualFediverseNodeDriver:")
