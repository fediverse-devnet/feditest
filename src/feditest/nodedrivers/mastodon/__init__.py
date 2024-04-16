"""
"""

from feditest import nodedriver
from feditest.protocols import NodeSpecificationInsufficientError
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class MastodonUbosNode(FediverseNode):
    """
    A Node running Mastodon, instantiated with UBOS.
    """
<<<<<<< Updated upstream
    def __init__(self, site_id: str, rolename: str, hostname: str, admin_id: str, node_driver: 'MastodonUbosNodeDriver') -> None:
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
=======
    def __init__(self, rolename: str, parameters: dict[str,Any] | None, node_driver: 'MastodonUbosNodeDriver') -> None:
        super(FediverseNode, self).__init__(rolename, parameters, node_driver)
>>>>>>> Stashed changes


    def obtain_actor_document_uri(self, actor_rolename: str = None) -> str:
        return f"https://{self._hostname}/users/{self._admin_id}"


@nodedriver
class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
<<<<<<< Updated upstream
    def _instantiate_node(self, site_id: str, rolename: str, hostname: str, admin_id: str) -> None:
        return MastodonUbosNode(site_id, rolename, hostname, admin_id, self)
=======
    def _instantiate_node(self, site_id: str, rolename: str, parameters: dict[str,Any] | None ) -> MastodonUbosNode:
        if 'siteid' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'no siteid given')
        return MastodonUbosNode(site_id, rolename, parameters, self)
>>>>>>> Stashed changes


    def _unprovision_node(self, node: MastodonUbosNode) -> None:
        self._exec_shell(f"sudo ubos-admin undeploy --siteid {node._site_id}") # pylint: disable=protected-access
