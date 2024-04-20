"""
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import Node, NodeSpecificationInsufficientError
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class WordPressPlusActivityPubPluginUbosNode(FediverseNode):
    """
    A Node running WordPress with the ActivityPub plugin, instantiated with UBOS.
    """
    def __init__(self, rolename: str, parameters: dict[str,Any], node_driver: 'WordPressPlusActivityPubPluginUbosNodeDriver'):
        super(FediverseNode, self).__init__(rolename, parameters, node_driver)


    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        return f"https://{self.hostname}/author/{ self.parameter('adminid') }/"


@nodedriver
class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate WordPress with the ActivityPub plugin via UBOr.
    """
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str,Any]) -> WordPressPlusActivityPubPluginUbosNode:
        if 'siteid' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'no siteid given')
        if 'adminid' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'no adminid given')

        return WordPressPlusActivityPubPluginUbosNode(rolename, parameters, self)


    def _unprovision_node(self, node: Node) -> None:
        self._exec_shell(f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }")
