"""
"""

from feditest.nodedrivers import AccountManager, NodeConfiguration
from feditest.nodedrivers.fallback.fediverse import AbstractFallbackFediverseNodeDriver, FallbackFediverseNode


class FediverseSaasNodeDriver(AbstractFallbackFediverseNodeDriver):
    """
    A NodeDriver that supports all protocols but doesn't automate anything and assumes the
    Node under test exists as a website that we don't have/can provision/unprovision.
    """
    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> FallbackFediverseNode:
        return FallbackFediverseNode(rolename, config, account_manager)


    # No need to override _unprovision_node()

