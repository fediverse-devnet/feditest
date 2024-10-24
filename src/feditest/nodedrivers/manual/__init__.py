"""
A NodeDriver that supports all protocols but doesn't automate anything.
"""

from feditest.nodedrivers import AccountManager, Node, NodeConfiguration
from feditest.nodedrivers.fallback.fediverse import AbstractFallbackFediverseNodeDriver, FallbackFediverseNode
from feditest.protocols.fediverse import FediverseNode
from feditest.utils import prompt_user


class FediverseManualNodeDriver(AbstractFallbackFediverseNodeDriver):
    """
    A NodeDriver that supports all web server-side protocols but doesn't automate anything.
    """
    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> FediverseNode:
        prompt_user(
                f'Manually provision the Node for constellation role { rolename }'
                + f' at host { config.hostname } with app { config.app } and hit return when done.')
        return FallbackFediverseNode(rolename, config, account_manager)


    # Python 3.12 @override
    def _unprovision_node(self, node: Node) -> None:
        prompt_user(f'Manually unprovision the Node for constellation role { node.rolename } and hit return when done.')
