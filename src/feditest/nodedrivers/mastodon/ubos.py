"""
"""

from typing import Any, cast

from feditest.nodedrivers.mastodon import MastodonNode
from feditest.reporting import error, trace
from feditest.ubos import UbosNodeDriver


class MastodonUbosNode(MastodonNode):
    """
    A Mastodon Node running on UBOS. This means we know how to interact with it exactly.
    """
    # Python 3.12 @override
    def _provision_new_user(self):
        pass # FIXME


    # Python 3.12 @override
    def add_cert_to_trust_store(self, root_cert: str) -> None:
        # We ask our UbosNodeDriver, so we don't have to have a UbosNode class
        rshcmd = self.parameter('rshcmd')
        real_node_driver = cast(MastodonUbosNodeDriver, self._node_driver)
        real_node_driver.add_cert_to_trust_store(root_cert, rshcmd)


    # Python 3.12 @override
    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        rshcmd = self.parameter('rshcmd')
        real_node_driver = cast(MastodonUbosNodeDriver, self._node_driver)
        real_node_driver.remove_cert_from_trust_store(root_cert, rshcmd)


class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, parameters)
        parameters['app'] = 'Mastodon'
        parameters['start-delay'] = 10


    # Python 3.12 @override
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str, Any]) -> MastodonNode:
        trace('Instantiating MastodonUbosNode')
        return MastodonUbosNode(rolename, parameters, self)


    # Python 3.12 @override
    def _getAppConfigsJson(self, parameters: dict[str,Any]) -> list[dict[str,Any]]:
        return [{
            "appid" : "mastodon",
            "appconfigid" : parameters['appconfigid'],
            "context" : "",
            "customizationpoints" : {
                "mastodon" : {
                    "singleusermode" : {
                        "value" : False
                    }
                }
            }
        }]
