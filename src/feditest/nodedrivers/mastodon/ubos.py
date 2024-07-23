"""
"""

from typing import Any

from feditest.nodedrivers.mastodon import MastodonNode
from feditest.ubos import UbosNodeDriver


class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str, Any]) -> MastodonNode:
        parameters['app'] = 'Mastodon'
        parameters['start-delay'] = 10
        return MastodonNode(rolename, parameters, self)


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
