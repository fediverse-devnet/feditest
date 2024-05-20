"""
"""

from typing import Any

from feditest import nodedriver
from feditest.protocols import Node
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class MastodonUbosNode(FediverseNode):
    """
    A Node running Mastodon, instantiated with UBOS.
    """
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
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str,Any]) -> MastodonUbosNode:
        return MastodonUbosNode(rolename, parameters, self)


    def _unprovision_node(self, node: Node) -> None:
        self._exec_shell(f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }") # pylint: disable=protected-access
