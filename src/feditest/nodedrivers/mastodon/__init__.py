"""
"""

from dataclasses import dataclass, field
import importlib
import os
import re
import sys
import time
from typing import Any, Callable, cast
from urllib.parse import urlparse

from feditest import AssertionFailure, InteropLevel, SpecLevel
from feditest.nodedrivers.manual import AbstractManualWebServerNodeDriver
from feditest.protocols import NodeDriver, TimeoutException
from feditest.protocols.activitypub import ActivityPubNode, AnyObject
from feditest.protocols.fediverse import FediverseNode
from feditest.reporting import trace
from feditest.utils import email_validate


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
        from mastodon_api import Mastodon
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


@dataclass
class UserRecord:
    """
    Collects what we know of a user at a NodeWithMastodonAPI
    """

    userid: str
    email: str
    passwd: str

    _mastodon_user_client: Mastodon | None = field(default=None, init=False, repr=False)

    def mastodon_user_client(self, mastodon_app_client: Mastodon):
        if not self._mastodon_user_client:
            self._mastodon_user_client = mastodon_app_client.copy()
            self._mastodon_user_client.log_in(self.email, self.passwd)
        return self._mastodon_user_client


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

        self._mastodon_app_client = None
        # This instance of Mastodon from Mastodon.py creates the OAuth app. We use it as a template
        # to clone user-specific instances of Mastodon. It is allocated when it is needed, because
        # if we were to allocate here, our custom certificate authority isn't here yet and the
        # operation will fail with a certificate error

        self._local_users_by_role: dict[str|None, UserRecord] = {} # always add new UserRecords to both
        self._local_users_by_userid: dict[str, UserRecord] = {} # always add new UserRecords to both
        self._non_existing_userids_by_role: dict[str|None, str] = {}
        self._status_dict_by_uri: dict[str, dict[str,Any]] = {} # Maps URIs of created status objects to the corresponding Mastodon.py "status dicts"
            # We keep this around so we can look up id attributes by URI and we can map the FediverseNode API URI parameters
            # to Mastodon's internal status ids


# From FediverseNode
    # Python 3.12 @override
    def make_create_note(self, actor_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        trace('make_create_note:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)

        if deliver_to:
            for to in deliver_to:
                results = mastodon_client.search(q=to, result_type="accounts")
                if to_account := next(
                    (a for a in results.get("accounts", []) if a.uri == to), None
                ):
                    to_url = urlparse(to_account.uri)
                    to_handle = f"@{to_account.acct}@{to_url.netloc}"
                    content += f" {to_handle}"
        response = mastodon_client.status_post(content)
        self._status_dict_by_uri[response.uri] = response
        trace(f'make_create_note returns with { response }')
        return response.uri


    # Python 3.12 @override
    def wait_for_object_in_inbox(self, actor_uri: str, object_uri: str) -> str:
        trace('wait_for_object_in_inbox:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)

        response = self._poll_until_result( # may throw
            lambda: next(
                (
                    s
                    for s in mastodon_client.timeline("local")
                    if s.uri == object_uri
                ),
                None,
            ),
            int(self.parameter('inbox_wait_retry_count') or '5'),
            int(self.parameter('inbox_wait_retry_interval') or '1'),
            f'Expected object { object_uri } has not arrived in inbox of actor { actor_uri }')
        trace(f'wait_for_object_in_inbox returns with { response }')
        return response


    # Python 3.12 @override
    def make_announce_object(self, actor_uri, note_uri: str) -> str:
        trace('make_announce_object:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)
        # FIXME: the URI could be remote, right?
        if note := self._status_dict_by_uri.get(note_uri):
            reblog = mastodon_client.status_reblog(note['id'])
            self._status_dict_by_uri[reblog.uri] = reblog
            trace(f'make_announce_object returns with { reblog }')
            return reblog.uri
        raise ValueError(f'Note URI not found: { note_uri }')


    # Python 3.12 @override
    def make_reply(self, actor_uri, note_uri: str, reply_content: str) -> str:
        trace('make_reply:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)
        # FIXME: the URI could be remote, right?
        if note := self._status_dict_by_uri.get(note_uri):
            reply = mastodon_client.status_reply(
                to_status=note, status=reply_content
            )
            self._status_dict_by_uri[reply.uri] = reply
            trace(f'make_reply returns with { reply }')
            return reply.uri
        raise ValueError(f'Note URI not found: { note_uri }')


    # Python 3.12 @override
    def make_a_follow_b(self, a_uri_here: str, b_uri_there: str, node_there: ActivityPubNode) -> None:
        trace('make_a_follow_b:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(a_uri_here)

        results = mastodon_client.search(q=b_uri_there, result_type="accounts")
        if b_account := next(
            (b for b in results.get("accounts", []) if b.uri == b_uri_there), None
        ):
            relationship = mastodon_client.account_follow(b_account)
            if not relationship["following"]:
                def f(): # I thought I could make this a lambda but python and I don't get a long
                    relationship = mastodon_client.account_relationships(b_account)
                    if relationship["following"]:
                        return relationship["following"]
                    return None

                self._poll_until_result( # may throw
                    f,
                    int(self.parameter('follow_wait_retry_count') or '5'),
                    int(self.parameter('follow_wait_retry_interval') or '1'),
                    f'Expected follow relationship was not established between { a_uri_here } and { b_uri_there }')
                trace('make_a_follow_b returns')
        raise ValueError(f'Actor URI not found: { b_uri_there }')


# From ActivityPubNode
    # Python 3.12 @override
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        trace(f'obtain_actor_document_uri for role {rolename}')
        user = self._local_users_by_role.get(rolename)
        if not user:
            user = self._provision_new_user()
            self._local_users_by_role[rolename] = user
        return self._userid_to_actor_uri(user.userid)


    # Python 3.12 @override
    def assert_member_of_collection_at(
        self,
        candidate_member_uri: str,
        collection_uri: str,
        spec_level: SpecLevel | None = None,
        interop_level: InteropLevel | None= None
    ):
        collection = AnyObject(collection_uri).as_collection()
        if not collection.contains_item_with_id(candidate_member_uri):
            raise AssertionFailure(
                spec_level or SpecLevel.UNSPECIFIED,
                interop_level or InteropLevel.UNKNOWN,
                f"{candidate_member_uri} not in {collection_uri}")


    # Python 3.12 @override
    def assert_not_member_of_collection_at(
        self,
        candidate_member_uri: str,
        collection_uri: str,
        spec_level: SpecLevel | None = None,
        interop_level: InteropLevel | None= None
    ):
        collection = AnyObject(collection_uri).as_collection()
        if collection.contains_item_with_id(candidate_member_uri):
            raise AssertionFailure(
                spec_level or SpecLevel.UNSPECIFIED,
                interop_level or InteropLevel.UNKNOWN,
                f"{candidate_member_uri} must not be in {collection_uri}")


# From WebFingerServer
    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        trace(f'obtain_account_identifier for role {rolename}')
        user = self._local_users_by_role.get(rolename)
        if not user:
            user = self._provision_new_user()
            self._local_users_by_role[rolename] = user
        return f'acct:{ user.userid }@{ self.parameter( "hostname" )}'


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        trace(f'obtain_non_existing_account_identifier for role {rolename}')
        if existing_user_id := self._non_existing_userids_by_role.get(rolename):
            return existing_user_id
        userid = self._create_non_existing_user()
        self._non_existing_userids_by_role[rolename] = userid
        return userid


    # Not implemented
    # def obtain_account_identifier_requiring_percent_encoding(self, nickname: str | None = None) -> str:
    # def override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# From WebServer

    # Not implemented:
    # def transaction(self, code: Callable[[],None]) -> WebServerLog:
    # def override_http_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# Internal implementation helpers

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


    def _provision_new_user(self) -> UserRecord:
        """
        Make sure a new user exists. This should be overridden in subclasses if at all possible.
        """
        userid = self.prompt_user('Create a new user account on the app'
                                + f' in role { self._rolename } at hostname { self._parameters["hostname"] }'
                                + ' and enter its user handle: ',
                               parse_validate=lambda x: x if len(x) else None )
        useremail = self.prompt_user('... and its e-mail: ', parse_validate=email_validate)
        userpass = self.prompt_user('... and its password:', parse_validate=lambda x: len(x) > 3)
        return UserRecord(cast(str, userid), cast(str, useremail), cast(str, userpass))


    def _create_non_existing_user(self):
        """
        Create a new user handle that could exist on this Node, but does not.
        """
        return f'does-not-exist-{ os.urandom(4).hex() }' # This is strictly speaking not always true, but will do I think


    def _get_mastodon_client_by_actor_uri(self, actor_uri: str):
        """
        Convenience method to get the instance of the Mastodon client object for a given actor URI.
        """
        if self._mastodon_app_client is None:
            app_base_url = f'https://{ self.parameter("hostname") }/'
            trace( f'Creating Mastodon.py app base with url { app_base_url } ')
            self._mastodon_app_client = Mastodon.create_app('feditest', api_base_url=app_base_url)

        trace(f'Mastodon.py app is { self._mastodon_app_client }')
        userid = self._actor_uri_to_userid(actor_uri)
        if not userid:
            raise ValueError(f'Cannot find actor { actor_uri }')
        user = self._local_users_by_userid.get(userid)
        if not user:
            raise ValueError(f'Cannot find user { userid }')
        mastodon_client = user.mastodon_user_client(self._mastodon_app_client)
        return mastodon_client


    def _poll_until_result(self,
        condition: Callable[[], Any | None],
        retry_count: int,
        retry_interval: int,
        msg: str | None = None
    ) -> Any:
        for _ in range(retry_count):
            response = condition()
            if response:
                return response
            time.sleep(retry_interval)
        if not msg:
            msg = 'Expected object has not arrived in time'
        raise TimeoutException(msg, retry_count * retry_interval)


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
