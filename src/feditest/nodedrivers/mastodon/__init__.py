"""
"""

import importlib
import re
import sys
from typing import Any, cast

from feditest.nodedrivers.manual import AbstractManualWebServerNodeDriver
from feditest.protocols import NodeDriver
from feditest.protocols.fediverse import FediverseNode

# We use the Mastodon.py module primarily because of its built-in support for rate limiting.
# Also it seems to have implemented some workarounds for inconsistent implementations by
# different apps, which we don't want to reinvent.
#
# Importing it isn't so easy:
# This kludge is needed because the node driver loader
# will always try to load the current mastodon subpackage (relative)
# instead of absolute package
if "mastodon" in sys.modules:
    m = sys.modules.pop("mastodon")
    try:
        mastodon_api = importlib.import_module("mastodon")
        Mastodon = mastodon_api.Mastodon # type: ignore
    finally:
        sys.modules["mastodon"] = m
else:
    from mastodon import Mastodon # type: ignore


def _token_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon client API token. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    return candidate if len(candidate)>10 else None


class NodeWithMastodonAPI(FediverseNode):
    """
    Any Node that supports the Mastodon API. This will be subtyped into things like
    * MastodonNode
    * WordPressPlusAccessoriesNode
    ... so they can add whatever is specific to their implementation.

    This implementation assumes that there is a single client API access token
    (which lets us act as a single user) and there are no tests that require
    us to have multiple accounts that we can act as, on the same node.
    """
    def __init__(
        self, rolename: str, parameters: dict[str, Any], node_driver: NodeDriver
    ):
        super().__init__(rolename, parameters, node_driver)
        access_token = parameters.get("access_token")
        self.api = Mastodon(
            api_base_url=f'https://{ self.parameter("hostname") }',
            access_token=access_token
        )
        self._local_userids_by_role: dict[str|None, str] = {
            None : cast(str,parameters.get('adminid'))
        }
        # Maps actor role names to provisioned userids.
        # None key for the user without rolename.
        # Note: We use the site admin user as the default user, which may or may not
        # be a good idea.


    # Override
    def obtain_actor_document_uri(self, actor_rolename: str | None = None) -> str:
        userid = self._local_userids_by_role[actor_rolename]
        if not userid:
            userid = self._provision_new_user()
            self._local_userids_by_role[actor_rolename] = userid
        return self._userid_to_actor_uri(userid)


    def _userid_to_actor_uri(self, userid: str) -> str:
        """
        The algorithm by which this application maps userids to ActivityPub actor URIs.
        Apparently this is different between Mastodon and other implementations, such as WordPress,
        so this might be overridden

        see also: _actor_uri_to_userid()
        """
        return f'https://{ self.parameter("hostname") }/users/{ userid }'


    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        """
        The algorithm by which this application maps userids to ActivityPub actor URIs in reverse.
        Apparently this is different between Mastodon and other implementations, such as WordPress,
        so this might be overridden

        see also: _userid_to_actor_uri()
        """
        if m:= re.match('^https://([^/]+)/users/(.+)$', actor_uri):
            if m.group(1) == self.parameter('hostname'):
                return m.group(2)

        raise ValueError( f'Cannot find actor at this node: { actor_uri }' )


    def _provision_new_user(self):
        """
        Make sure a new user exists. This should be overridden in subclasses if at all possible.
        """
        ret = self.prompt_user('Create a new user account on the app'
                                + f' in role { self._rolename } at hostname { self._parameters["hostname"] }'
                                + ' and enter its user handle: ',
                               parse_validate=lambda x: x if len(x) else None )
        return ret


#    # Override
#    def obtain_followers_collection_uri(self, actor_uri: str) -> str:
#        userid = self._actor_uri_to_userid(actor_uri)



class MastodonNode(NodeWithMastodonAPI):
    """
    An actual Mastodon Node.
    """
    pass


class MastodonManualNodeDriver(AbstractManualWebServerNodeDriver):
    """
    Create a manually provisioned Mastodon Node
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, parameters)
        access_token = parameters.get('access_token')
        if not access_token:
            parameters['access_token'] = self.prompt_user('Enter the client API access token for the app'
                                                 + f' in role { rolename } at hostname { parameters["hostname"] }: ',
                                                 parse_validate=_token_validate)
        parameters['app'] = 'Mastodon'


    # Python 3.12 @override
    def _provision_node(self, rolename: str, parameters: dict[str, Any]) -> MastodonNode:
        return MastodonNode(rolename, parameters, self)
