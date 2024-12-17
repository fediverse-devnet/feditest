#
# Dummy classes for testing
#

from feditest.nodedrivers import AccountManager, Node, NodeConfiguration, NodeDriver


class DummyNode(Node):
    pass


class DummyNodeDriver(NodeDriver):
    # Python 3.12 @Override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> Node:
        return DummyNode(rolename, config, account_manager)

