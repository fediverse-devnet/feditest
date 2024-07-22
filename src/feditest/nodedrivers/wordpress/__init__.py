"""
"""

import re
from typing import Any

from feditest import nodedriver
from feditest.nodedrivers import AbstractManualWebServerNodeDriver
from feditest.nodedrivers.mastodon import NodeWithMastodonAPI


def _token_validate(candidate: str) -> str | None:
    """
    Validate a WordPress client API token. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    return candidate if len(candidate)>10 else None


class WordPressPlusActivityPubPluginNode(NodeWithMastodonAPI):
    """
    A Node running WordPress with the ActivityPub plugin, instantiated with UBOS.
    """
    # implementation override -- WordPress has a different scheme than Mastodon
    def _userid_to_actor_uri(self, userid: str) -> str:
        return f'https://{ self.parameter("hostname") }/author/{ userid }'


    # implementation override -- WordPress has a different scheme than Mastodon
    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        if m:= re.match('^https://([^/]+)/author/(.+)$', actor_uri):
            if m.group(1) == self.parameter('hostname'):
                return m.group(2)

        raise ValueError( f'Cannot find actor at this node: { actor_uri }' )


@nodedriver
class WordPressPlusActivityPubPluginManualNodeDriver(AbstractManualWebServerNodeDriver):
    """
    Create a manually provisioned WordPress + ActivityPubPlugin Node
    """
    def _provision_node(self, rolename: str, parameters: dict[str, Any]) -> WordPressPlusActivityPubPluginNode:
        parameters['app'] = 'WordPress + ActivityPub plugin'

        return WordPressPlusActivityPubPluginNode(rolename, parameters, self)


    # Override
    def _fill_in_parameters(self, rolename: str, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, parameters)

        access_token = parameters.get('access_token')
        if not access_token:
            parameters['access_token'] = self.prompt_user('Enter the client API access token for the app'
                                                 + f' in role { rolename } at hostname { parameters["hostname"] }: ',
                                                 parse_validate=_token_validate)
