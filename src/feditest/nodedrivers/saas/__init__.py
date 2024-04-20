"""
A NodeDriver that supports all protocols but doesn't automate anything and assumes the
Node under test exists as a website that we don't have/can provision/unprovision.
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.utils import hostname_validate


class SaasFediverseNode(FediverseNode):
    pass


@nodedriver
class SaasFediverseNodeDriver(NodeDriver):
    """
    A NodeDriver that supports all protocols but doesn't automate anything and assumes the
    Node under test exists as a website that we don't have/can provision/unprovision.
    """
    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> SaasFediverseNode:
        hostname = parameters.get('hostname')
        if not hostname:
            hostname = self.prompt_user(f'Enter the hostname for "{ rolename }": ', None, hostname_validate)
            parameters= dict(parameters)
            parameters['hostname'] = hostname

        return SaasFediverseNode(rolename, parameters, self)
