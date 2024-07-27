"""
A NodeDriver that supports all protocols but doesn't automate anything and assumes the
Node under test exists as a website that we don't have/can provision/unprovision.
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.utils import appname_validate, hostname_validate


@nodedriver
class SaasFediverseNodeDriver(NodeDriver):
    """
    A NodeDriver that supports all protocols but doesn't automate anything and assumes the
    Node under test exists as a website that we don't have/can provision/unprovision.
    """
    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> FediverseNode:
        if not parameters.get("server-prefix"):
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
        return  FediverseNode(rolename, parameters, self)
