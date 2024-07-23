"""
"""

from typing import Any

from feditest.nodedrivers.mastodon import MastodonNode
from feditest.ubos import UbosNodeDriver


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
        return MastodonNode(rolename, parameters, self)


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
