"""
A NodeDriver that supports all protocols but doesn't automate anything.
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import Node, NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.utils import hostname_validate


class ManualFediverseNode(FediverseNode):
    pass


@nodedriver
class ManualFediverseNodeDriver(NodeDriver):
    """
    A NodeDriver that supports all protocols but doesn't automate anything.
    """
    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> ManualFediverseNode:
        if 'hostname' in parameters:
            hostname = parameters['hostname']
            self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                             + f' with hostname "{ hostname }" and hit return when done.')
        else:
            hostname = self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                                        + ' and enter the hostname when done: ',
                                        None,
                                        hostname_validate)
            parameters = dict(parameters)
            parameters['hostname'] = hostname

        return ManualFediverseNode(rolename, parameters, self)


    def _unprovision_node(self, node: Node) -> None:
        self.prompt_user(f'Manually unprovision the Node for constellation role { node.rolename() } and hit return when done.')
