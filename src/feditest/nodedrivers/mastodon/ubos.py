
from typing import Any

from feditest import nodedriver
from feditest.nodedrivers.mastodon.mixin import MastodonApiMixin
from feditest.protocols import Node, NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class MastodonUbosNode(MastodonApiMixin, FediverseNode):
    """
    A Node running Mastodon, instantiated with UBOS.
    """

    def __init__(self, rolename: str, parameters: dict[str, Any], node_driver: NodeDriver):
        # TODO Automatic actor provisioning
        # Use parameters to determine which actors to provision 
        # with UBOS with which information
        # Copy and modify the parameters for usage by the MastodonApiMixin
        # Must invoke base class constructors explicitly since Python will
        # normally only call the first __init__ it finds in the MRO.
        # super().__init__(rolename, parameters, node_driver)
        MastodonApiMixin.__init__(self, rolename, parameters, node_driver)
        FediverseNode.__init__(self, rolename, parameters, node_driver)

    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        return f"https://{self.hostname}/users/{self.parameter('adminid') }"

    @property
    def app_name(self):
        return "Mastodon"


@nodedriver
class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """

    def _instantiate_ubos_node(
        self, rolename: str, parameters: dict[str, Any]
    ) -> MastodonUbosNode:
        return MastodonUbosNode(rolename, parameters, self)

    def _unprovision_node(self, node: Node) -> None:
        self._exec_shell(
            f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }"
        )  # pylint: disable=protected-access
