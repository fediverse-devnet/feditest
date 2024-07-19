"""
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class WordPressPlusActivityPubPluginNode(FediverseNode):
    """
    A Node running WordPress with the ActivityPub plugin, instantiated with UBOS.
    """
    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        return f"https://{self.hostname}/author/{ self.parameter('adminid') }/"

@nodedriver
class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate WordPress with the ActivityPub plugin via UBOS.
    """
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str,Any]) -> WordPressPlusActivityPubPluginNode:
        parameters['app'] = 'WordPress + ActivityPub plugin'
        return WordPressPlusActivityPubPluginNode(rolename, parameters, self)
