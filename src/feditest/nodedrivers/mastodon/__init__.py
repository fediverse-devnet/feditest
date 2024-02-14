"""
"""

from feditest import nodedriver
from feditest.ubos import UbosDriver, UbosNode

@nodedriver
class MastodonUbosDriver(UbosDriver):
    def _instantiate_node(self, site_id: str, rolename: str) -> None:
        return UbosNode(site_id, rolename, self)
