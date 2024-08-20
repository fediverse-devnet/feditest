"""
"""

import re
from typing import Any

from feditest.nodedrivers.manual import AbstractManualWebServerNodeDriver
from feditest.nodedrivers.mastodon import NodeWithMastodonAPI, existing_users_by_role, non_existing_users_by_role
from feditest.testplan import TestPlanConstellationNode


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
        return f'https://{ self.parameter("hostname") }/author/{ userid }/'


    # implementation override -- WordPress has a different scheme than Mastodon
    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        if m:= re.match('^https://([^/]+)/author/([^/]+)/?$', actor_uri):
            if m.group(1) == self.parameter('hostname'):
                return m.group(2)

        raise ValueError( f'Cannot find actor at this node: { actor_uri }' )


class WordPressPlusActivityPubPluginManualNodeDriver(AbstractManualWebServerNodeDriver):
    """
    Create a manually provisioned WordPress + ActivityPubPlugin Node
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, test_plan_node, parameters)
        access_token = parameters.get('access_token')
        if not access_token:
            parameters['access_token'] = self.prompt_user('Enter the client API access token for the app'
                                                 + f' in role { rolename } at hostname { parameters["hostname"] }: ',
                                                 parse_validate=_token_validate)

        parameters['app'] = 'WordPress + ActivityPub plugin'


    # Python 3.12 @override
    def _provision_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str, Any]) -> WordPressPlusActivityPubPluginNode:
        return WordPressPlusActivityPubPluginNode(
            rolename,
            parameters,
            self,
            existing_users_by_role(test_plan_node, self),
            non_existing_users_by_role(test_plan_node, self))


