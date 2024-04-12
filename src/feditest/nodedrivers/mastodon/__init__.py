"""
"""
from typing import Any

from feditest import nodedriver
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver
from feditest.utils import account_id_validate


class MastodonUbosNode(FediverseNode):
    """
    A Node running Mastodon, instantiated with UBOS.
    """
    def __init__(self, site_id: str, rolename: str, parameters: dict[str,Any] | None, node_driver: 'MastodonUbosNodeDriver'):
        super(FediverseNode, self).__init__(rolename, parameters, node_driver)


    def obtain_actor_document_uri(self, actor_rolename: str = None) -> str:
        account_tuple = account_id_validate(self.obtain_account_identifier())

        return f"https://{ self.hostname() }/users/{ account_tuple[0] }/"


@nodedriver
class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
    def _instantiate_node(self, site_id: str, rolename: str, parameters: dict[str,Any] | None ) -> MastodonUbosNode:
        if 'siteid' not in parameters:
            raise Exception('UbosNodeDriver parameters must include "siteid"')
        return MastodonUbosNode(site_id, rolename, parameters, self)


    def _unprovision_node(self, node: MastodonUbosNode) -> None:
        self._exec_shell(f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }")
