"""
"""

from typing import Any

from feditest import nodedriver
from feditest.nodedrivers.mastodon import MastodonNode
from feditest.ubos import UbosNodeDriver

@nodedriver
class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str, Any]) -> MastodonNode:
        parameters['app'] = 'Mastodon'
        return MastodonNode(rolename, parameters, self)
