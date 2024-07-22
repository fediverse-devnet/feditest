"""
"""

from typing import Any

from feditest.protocols import Node, NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.utils import appname_validate, hostname_validate


class AbstractManualWebServerNodeDriver(NodeDriver):
    """
    Abstract superclass of NodeDrivers that support all web server-side protocols but don't
    automate anything.
    This abstract class is needed because @nodedriver subclasses cannot subclass
    another class marked as @nodedriver, apparently.
    This is here in the module hierarchy because if it is in feditest/nodedrivers/manual/__init__.py
    The @nodedriver there gets registered twice under different names
    """
    def _fill_in_parameters(self, rolename: str, parameters: dict[str,Any]):
        parameters = dict(parameters)
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


    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> FediverseNode:
        self._fill_in_parameters(rolename, parameters)
        return FediverseNode(rolename, parameters, self)


    def _unprovision_node(self, node: Node) -> None:
        self.prompt_user(f'Manually unprovision the Node for constellation role { node.rolename() } and hit return when done.')


