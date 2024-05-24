"""
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import Node
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class WordPressPlusActivityPubPluginUbosNode(FediverseNode):
    """
    A Node running WordPress with the ActivityPub plugin, instantiated with UBOS.
    """
    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        return f"https://{self.hostname}/author/{ self.parameter('adminid') }/"


    @property
    def app_name(self):
        return "WordPress + ActivityPub plugin"


@nodedriver
class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate WordPress with the ActivityPub plugin via UBOr.
    """
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str,Any]) -> WordPressPlusActivityPubPluginUbosNode:
        pars = dict(parameters)
        pars['app'] = 'WordPress + ActivityPub plugin'
        return WordPressPlusActivityPubPluginUbosNode(rolename, pars, self)


    def _unprovision_node(self, node: Node) -> None:
        self._exec_shell(f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }")
