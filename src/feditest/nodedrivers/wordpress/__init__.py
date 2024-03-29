"""
"""

from feditest import nodedriver
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class WordPressPlusActivityPubPluginUbosNode(FediverseNode):
    def __init__(self, site_id: str, rolename: str, hostname: str, admin_id: str, node_driver: 'WordPressPlusActivityPubPluginUbosNodeDriver') -> None:
        super(FediverseNode, self).__init__(rolename, hostname, node_driver)

        self._site_id = site_id
        self._admin_id = admin_id


    def obtain_account_identifier(self, nickname: str = None) -> str:
        """
        We simply return the admin account that we know exists.
        """
        return f"acct:{self._admin_id}@{self._hostname}"


    def obtain_non_existing_account_identifier(self, nickname: str = None ) ->str:
        return f"acct:undefined@{self._hostname}"


    def obtain_actor_document_uri(self, actor_rolename: str = None) -> str:
        return f"https://{self._hostname}/author/{self._admin_id}/"


@nodedriver
class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    def _instantiate_node(self, site_id: str, rolename: str, hostname: str, admin_id: str) -> None:
        return WordPressPlusActivityPubPluginUbosNode(site_id, rolename, hostname, admin_id, self)
