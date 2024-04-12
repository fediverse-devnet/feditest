"""
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver
from feditest.utils import account_id_validate

class WordPressPlusActivityPubPluginUbosNode(FediverseNode):
    """
    A Node running WordPress with the ActivityPub plugin, instantiated with UBOS.
    """
    def __init__(self, site_id: str, rolename: str, parameters: dict[str,Any] | None, node_driver: 'WordPressPlusActivityPubPluginUbosNodeDriver'):
        super(FediverseNode, self).__init__(rolename, parameters, node_driver)


    def obtain_actor_document_uri(self, actor_rolename: str = None) -> str:
        account_tuple = account_id_validate(self.obtain_account_identifier())

        return f"https://{ self.hostname() }/author/{ account_tuple[0] }/"


@nodedriver
class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate WordPress with the ActivityPub plugin via UBOS.
    """
    def _instantiate_node(self, site_id: str, rolename: str, parameters: dict[str,Any] | None ) -> WordPressPlusActivityPubPluginUbosNode:
        if 'siteid' not in parameters:
            raise Exception('UbosNodeDriver parameters must include "siteid"')

        return WordPressPlusActivityPubPluginUbosNode(site_id, rolename, parameters, self)


    def _unprovision_node(self, node: WordPressPlusActivityPubPluginUbosNode) -> None:
        self._exec_shell(f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }")
