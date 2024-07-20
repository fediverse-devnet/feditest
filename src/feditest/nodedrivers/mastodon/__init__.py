"""
"""
from typing import Any

from feditest import nodedriver
from feditest.nodedrivers import AbstractManualWebServerNodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.ubos import UbosNodeDriver


class NodeWithMastodonAPI(FediverseNode):
    """
    Any Node that supports the Mastodon API
    """
    pass


class MastodonNode(NodeWithMastodonAPI):
    """
    An actual Mastodon Node.
    """
    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        return f"https://{self.hostname}/users/{self.parameter('adminid') }"



@nodedriver
class MastodonManualNodeDriver(AbstractManualWebServerNodeDriver):
    """
    Create a manually provisioned Mastodon Node
    """
    def _provision_node(self, rolename: str, parameters: dict[str, Any]) -> MastodonNode:
        parameters['app'] = 'Mastodon'
        self._fill_in_parameters(rolename, parameters)
        return MastodonNode(rolename, parameters, self)
