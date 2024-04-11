"""
A NodeDriver implemnentation that supports all protocols but doesn't automate anything.
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import Node, NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.utils import hostname_validate


class ManualFediverseNode(FediverseNode):
    def __init__(self, rolename: str, hostname: str, node_driver: 'ManualFediverseNodeDriver') -> None:
        super(ManualFediverseNode, self).__init__(rolename, hostname, node_driver)


@nodedriver
class ManualFediverseNodeDriver(NodeDriver):
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> ManualFediverseNode:
        if hostname:
            self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                             + f' with hostname "{ hostname }" and hit return when done.')
        else:
            hostname = self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                                        + ' and enter the hostname when done: ',
                                        hostname_validate)
            
        return ManualFediverseNode(rolename, hostname, self)

    def _unprovision_node(self, node: Node) -> None:
        self.prompt_user(f'Manually unprovision the Node for constellation role { node.rolename() } and hit return when done.')
