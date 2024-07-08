
from typing import Any

from feditest import nodedriver
from feditest.nodedrivers.mastodon.mixin import MastodonApiMixin
from feditest.protocols import Node, NodeDriver
from feditest.protocols.activitypub import ActivityPubNode


class MastodonManualNode(MastodonApiMixin, ActivityPubNode):
    ...
    
@nodedriver
class MastodonManualNodeDriver(NodeDriver):
    """
    Expects a manually-provisioned Mastodon node.
    """

    def _provision_node(self, rolename: str, parameters: dict[str, Any]) -> Node:
        return MastodonManualNode(rolename, parameters, self)

    def _unprovision_node(self, node: Node) -> None: ...
