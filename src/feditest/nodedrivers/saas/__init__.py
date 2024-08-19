"""
A NodeDriver that supports all protocols but doesn't automate anything and assumes the
Node under test exists as a website that we don't have/can provision/unprovision.
"""

from typing import Any

from feditest.protocols import NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.testplan import TestPlanConstellationNode
from feditest.utils import appname_validate, hostname_validate


class SaasFediverseNodeDriver(NodeDriver):
    """
    A NodeDriver that supports all protocols but doesn't automate anything and assumes the
    Node under test exists as a website that we don't have/can provision/unprovision.
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, test_plan_node, parameters)

        hostname = parameters.get('hostname')
        if not hostname:
            hostname = self.prompt_user(f'Enter the hostname for "{ rolename }": ', parse_validate=hostname_validate)
            parameters= dict(parameters)
            parameters['hostname'] = hostname

        app = parameters.get('app')
        if not app:
            parameters['app'] = self.prompt_user('Enter the name of the app you just provisioned'
                                                 + f' at hostname { parameters["hostname"] }: ',
                                                 parse_validate=appname_validate)


    # Python 3.12 @override
    def _provision_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]) -> FediverseNode:
        return FediverseNode(rolename, parameters, self)
