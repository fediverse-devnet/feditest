"""
A NodeDriver that supports all protocols but doesn't automate anything.
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import Node, NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.utils import appname_validate, hostname_validate


class ManualFediverseNode(FediverseNode):
    @property
    def app_name(self):
        return self._parameters.get('app')


@nodedriver
class ManualFediverseNodeDriver(NodeDriver):
    """
    A NodeDriver that supports all protocols but doesn't automate anything.
    """
    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> ManualFediverseNode:
        hostname = parameters.get('hostname')
        if hostname:
            self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                             + f' with hostname "{ hostname }" and hit return when done.')
        else:
            hostname = self.prompt_user(f'Manually provision a Node for constellation role "{ rolename }"'
                                        + ' and enter the hostname when done: ',
                                        parse_validate=hostname_validate)
        parameters = dict(parameters)
        parameters['hostname'] = hostname

        app = parameters.get('app')
        if not app:
            parameters['app'] = self.prompt_user('Enter the name of the app you just provisioned'
                                                 + f' at hostname { parameters["hostname"] }: ',
                                                 parse_validate=appname_validate)

        return ManualFediverseNode(rolename, parameters, self)


    def _unprovision_node(self, node: Node) -> None:
        self.prompt_user(f'Manually unprovision the Node for constellation role { node.rolename() } and hit return when done.')
