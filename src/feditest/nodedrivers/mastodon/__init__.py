"""
"""

from abc import abstractmethod
import certifi
from dataclasses import dataclass
import importlib
import re
import requests
import sys
import time
from typing import Any, Callable, cast

from feditest import AssertionFailure, InteropLevel, SpecLevel
from feditest.protocols import (
    Account,
    AccountManager,
    DefaultAccountManager,
    NodeConfiguration,
    NodeDriver,
    NonExistingAccount,
    NotImplementedByNodeError,
    TimeoutException,
    APP_PAR,
    APP_VERSION_PAR,
    HOSTNAME_PAR
)
from feditest.protocols.activitypub import AnyObject
from feditest.protocols.fediverse import FediverseNode
from feditest.reporting import trace
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField, TestPlanNodeParameter
from feditest.utils import boolean_parse_validate, email_validate, find_first_in_array, hostname_validate


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
        from mastodon_api import AttribAccessDict, Mastodon
    finally:
        sys.modules["mastodon"] = m
else:
    from mastodon import AttribAccessDict, Mastodon


VERIFY_API_TLS_CERTIFICATE_PAR = TestPlanNodeParameter(
    'verify_api_tls_certificate',
    """If set to false, accessing the Mastodon API will be performed without checking TLS certificates.""",
    validate=boolean_parse_validate
)


def _oauth_token_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon client API token. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if len(candidate)>10 else None


def _userid_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon user name. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if re.match(r'[a-zA-Z0-9_]', candidate) else None


def _password_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon password. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if len(candidate)>4 else None


USERID_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'userid',
        """Mastodon userid for a user (e.g. "joe") (required).""",
        _userid_validate
)
EMAIL_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'email',
        """E-mail for the user on an Account. Required for accounts specified with a password (not a token) because logging into Mastodon is by e-mail address.""",
        email_validate
)
PASSWORD_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'password',
        """Password for a user. Required for accounts that also have an e-mail address and no token.""",
        _password_validate
)
OAUTH_TOKEN_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'oauth_token',
        """OAuth token of a user, obtained out of band, for users not specified with e-mail address and password.""",
        _oauth_token_validate
)
ROLE_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'role',
        """A symbolic name for the Account as used by tests (optional).""",
        lambda x: len(x)
)

USERID_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'userid',
        """Mastodon userid for a non-existing user (e.g. "joe")  (required).""",
        _userid_validate
)
ROLE_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'role',
        """A symbolic name for the non-existing Account as used by tests (optional).""",
        lambda x: len(x)
)


@dataclass
class MastodonOAuthApp:
    """
    Captures what we know about the Mastodon OAuth "app" we create to interact with our Mastodon instance.
    """
    client_id : str
    client_secret : str
    api_base_url : str
    session : requests.Session # Use this session which has the right CA certs

    @staticmethod
    def create(api_base_url: str, session: requests.Session) -> 'MastodonOAuthApp':
        client_id, client_secret = Mastodon.create_app('feditest', api_base_url=api_base_url, session=session)
        return MastodonOAuthApp(client_id, client_secret, api_base_url, session)


class MastodonAccount(Account): # this is intended to be abstract
    def __init__(self, role: str | None, userid: str):
        super().__init__(role)
        self.userid = userid
        self._mastodon_user_client: Mastodon | None = None


    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], node_driver: NodeDriver):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        userid = USERID_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, f'NodeDriver { node_driver }: ')
        role = ROLE_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, f'NodeDriver { node_driver }: ')

        oauth_token = OAUTH_TOKEN_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, f'NodeDriver { node_driver }: ')
        if oauth_token:
            # FIXME: Raise error if email or password are given
            return MastodonOAuthTokenAccount(role, userid, oauth_token)

        else:
            email = EMAIL_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, f'NodeDriver { node_driver }: ')
            password = PASSWORD_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, f'NodeDriver { node_driver }: ')
            return MastodonUserPasswordAccount(role, userid, password, email)


    @property
    def webfinger_uri(self):
        return f'acct:{ self.userid }@{ self.node.hostname }'


    @property
    def actor_uri(self):
        return f'https://{ self.node.hostname }/users/{ self.userid }'


    @abstractmethod
    def mastodon_user_client(self, oauth_app: MastodonOAuthApp) -> Mastodon:
        ...


class MastodonUserPasswordAccount(MastodonAccount):
    def __init__(self, role: str | None, userid: str, password: str, email: str):
        super().__init__(role, userid)
        self.password = password
        self.email = email


    # Python 3.12 @override
    def mastodon_user_client(self, oauth_app: MastodonOAuthApp) -> Mastodon:
        if self._mastodon_user_client is None:
            trace(f'Logging into Mastodon at { oauth_app.api_base_url } as { self.email }')
            client = Mastodon(
                client_id = oauth_app.client_id,
                client_secret = oauth_app.client_secret,
                api_base_url = oauth_app.api_base_url,
                session = oauth_app.session # , debug_requests = True
            )
            client.log_in(username = self.email, password = self.password) # returns the token

            self._mastodon_user_client = client

        return self._mastodon_user_client


class MastodonOAuthTokenAccount(MastodonAccount):
    def __init__(self, role: str | None, userid: str, oauth_token: str):
        super().__init__(role, userid)
        self.oauth_token = oauth_token


    # Python 3.12 @override
    def mastodon_user_client(self, oauth_app: MastodonOAuthApp) -> Mastodon:
        if self._mastodon_user_client is None:
            client = Mastodon(
                client_id = oauth_app.client_id,
                client_secret=oauth_app.client_secret,
                access_token=self.oauth_token,
                api_base_url=oauth_app.api_base_url,
                session=oauth_app.session
            )
            self._mastodon_user_client = client
        return self._mastodon_user_client


class MastodonNonExistingAccount(NonExistingAccount):
    def __init__(self, role: str | None, userid: str):
        super().__init__(role)
        self.userid = userid


    @staticmethod
    def create_from_non_existing_account_info_in_testplan(non_existing_account_info_in_testplan: dict[str, str | None], node_driver: NodeDriver):
        """
        Parses the information provided in an "non_existing_account" dict of TestPlanConstellationNode
        """
        userid = USERID_NON_EXISTING_ACCOUNT_FIELD.get_validate_from_or_raise(non_existing_account_info_in_testplan, f'NodeDriver { node_driver }: ')
        role = ROLE_ACCOUNT_FIELD.get_validate_from(non_existing_account_info_in_testplan, f'NodeDriver { node_driver }: ')

        return MastodonNonExistingAccount(role, userid)


    @property
    def webfinger_uri(self):
        return f'acct:{ self.userid }@{ self.node.hostname }'


    @property
    def actor_uri(self):
        return f'https://{ self.node.hostname }/users/{ self.userid }'


class NodeWithMastodonApiConfiguration(NodeConfiguration):
    def __init__(self,
        node_driver: 'NodeDriver',
        app: str,
        app_version: str | None = None,
        hostname: str | None = None,
        start_delay: float = 0.0,
        verify_tls_certificate: bool = True
    ):
        super().__init__(node_driver=node_driver, app=app, app_version=app_version, hostname=hostname, start_delay=start_delay)
        self._verify_tls_certificate = verify_tls_certificate


    @property
    def verify_tls_certificate(self) -> bool:
        return self._verify_tls_certificate


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
    def __init__(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager, auto_accept_follow: bool = True):
        super().__init__(rolename, config, account_manager)

        self._mastodon_oauth_app : MastodonOAuthApp | None = None
        # Information we have about the OAuth "app" we we create to interact with a Mastodon instance.
        # Allocated when needed, so our custom certificate authority has been created before this is used.
        self._requests_session : requests.Session | None = None
        # The request.Session with the custom certificate authority set as verifier.
        # Allocated when needed, so our custom certificate authority has been created before this is used.

        self._status_dict_by_uri: dict[str, dict[str,Any]] = {}
        # Maps URIs of created status objects to the corresponding Mastodon.py "status dicts"
        # We keep this around so we can look up id attributes by URI and we can map the FediverseNode API URI parameters
        # to Mastodon's internal status ids

        self._auto_accept_follow = auto_accept_follow # True is default for Mastodon


# From FediverseNode

    # Python 3.12 @override
    def make_create_note(self, actor_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        trace('make_create_note:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)

        if deliver_to: # The only way we can address specific accounts in Mastodon
            for to in deliver_to:
                if to_account := self._get_account_dict_by_other_actor_uri(mastodon_client, to):
                    to_handle = f"@{to_account.acct}"
                    content += f" {to_handle}"
                else:
                    raise ValueError(f'Cannot find account for Actor { to }')
        response = mastodon_client.status_post(content)
        self._status_dict_by_uri[response.uri] = response
        trace(f'make_create_note returns with { response }')
        return response.uri


    # Python 3.12 @override
    def make_announce_object(self, actor_uri, announced_object_uri: str) -> str:
        trace('make_announce_object:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)
        # FIXME: the URI could be remote, right?
        if note := self._status_dict_by_uri.get(announced_object_uri):
            reblog = mastodon_client.status_reblog(note['id'])
            self._status_dict_by_uri[reblog.uri] = reblog
            trace(f'make_announce_object returns with { reblog }')
            return reblog.uri
        raise ValueError(f'Note URI not found: { announced_object_uri }')


    # Python 3.12 @override
    def make_reply_note(self, actor_uri, replied_object_uri: str, reply_content: str) -> str:
        trace('make_reply_note:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)
        # FIXME: the URI could be remote, right?
        if note := self._status_dict_by_uri.get(replied_object_uri):
            reply = mastodon_client.status_reply(
                to_status=note, status=reply_content
            )
            self._status_dict_by_uri[reply.uri] = reply
            trace(f'make_reply returns with { reply }')
            return reply.uri
        raise ValueError(f'Note URI not found: { replied_object_uri }')


    # Python 3.12 @override
    def make_follow(self, actor_uri: str, to_follow_actor_uri: str) -> None:
        trace('make_follow:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)

        if to_follow_account := self._get_account_dict_by_other_actor_uri(mastodon_client, to_follow_actor_uri):
            relationship = mastodon_client.account_follow(to_follow_account) # noqa: F841
            return
        raise ValueError(f'Account not found with Actor URI: { to_follow_actor_uri }')


    # Python 3.12 @override
    def set_auto_accept_follow(self, actor_uri: str, auto_accept_follow: bool = True) -> None:
        if self._auto_accept_follow == auto_accept_follow:
            return
        raise NotImplementedByNodeError(self, NodeWithMastodonAPI.set_auto_accept_follow) # Can't find an API call for this


    # Python 3.12 @override
    def make_follow_accept(self, actor_uri: str, follower_actor_uri: str) -> None:
        super().make_follow_accept(actor_uri, follower_actor_uri) # FIXME


    # Python 3.12 @override
    def make_follow_reject(self, actor_uri: str, follower_actor_uri: str) -> None:
        super().make_follow_reject(actor_uri, follower_actor_uri) # FIXME


    # Python 3.12 @override
    def make_follow_undo(self, actor_uri: str, follower_actor_uri: str) -> None:
        super().make_follow_undo(actor_uri, follower_actor_uri) # FIXME


    # Python 3.12 @override
    def wait_until_actor_has_received_note(self, actor_uri: str, object_uri: str, max_wait: float = 5.) -> str:
        trace('wait_until_actor_has_received_note:')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)

        def find_note():
            """
            Depending on how the Note is addressed and follow status, Mastodon puts it into the Home timeline or only
            into notifications.
            """
            elements = mastodon_client.timeline_home(local=True, remote=True)
            ret = find_first_in_array( elements, lambda s: s.uri == object_uri)
            if not ret:
                elements = mastodon_client.notifications()
                parent_ret = find_first_in_array( elements, lambda s: s.status.uri == object_uri)
                ret = parent_ret.status if parent_ret else None
            return ret

        response = self._poll_until_result( # may throw
            find_note,
            int(max_wait),
            1.0,
            f'Expected object { object_uri } has not arrived in inbox of actor { actor_uri }'
        )
        trace(f'wait_for_object_in_inbox returns with { response }')
        return response.content


    # Python 3.12 @override
    def wait_until_actor_is_following_actor(self, actor_uri: str, to_be_followed_uri: str, max_wait: float = 5.) -> None:
        trace(f'wait_until_actor_is_following_actor: actor_uri = { actor_uri }, to_be_followed_uri = { to_be_followed_uri }')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)

        if to_be_followed_account := self._get_account_dict_by_other_actor_uri(mastodon_client, to_be_followed_uri):
            self._poll_until_result( # may throw
                lambda: self._is_following(mastodon_client, to_be_followed_account),
                int(max_wait),
                1.0,
                f'Actor { actor_uri } is not following { to_be_followed_uri }')
            return
        raise ValueError(f'Account not found with Actor URI: { to_be_followed_uri }')


    # Python 3.12 @override
    def wait_until_actor_is_followed_by_actor(self, actor_uri: str, to_be_following_uri: str, max_wait: float = 5.) -> None:
        trace(f'wait_until_actor_is_followed_by_actor: actor_uri = { actor_uri }, to_be_followed_uri = { to_be_following_uri }')
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)

        if to_be_following_account := self._get_account_dict_by_other_actor_uri(mastodon_client, to_be_following_uri):
            self._poll_until_result( # may throw
                lambda: self._is_followed_by(mastodon_client, to_be_following_account),
                int(max_wait),
                1.0,
                f'Actor { actor_uri } is not followed by { to_be_following_uri }')
            return
        raise ValueError(f'Account not found with Actor URI: { to_be_following_uri }')

# From ActivityPubNode

    # Python 3.12 @override
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_uri

    # Not implemented:
    # def obtain_followers_collection_uri(self, actor_uri: str) -> str:
    # def obtain_following_collection_uri(self, actor_uri: str) -> str:

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
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.webfinger_uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        non_account = cast(MastodonNonExistingAccount, account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.webfinger_uri

    # Not implemented:
    # def obtain_account_identifier_requiring_percent_encoding(self, nickname: str | None = None) -> str:
    # def override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# From WebServer

    # Not implemented:
    # def transaction(self, code: Callable[[],None]) -> WebServerLog:
    # def override_http_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# From Node

    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        context_msg = f'Mastodon Node { self }: '
        userid = cast(str, self.prompt_user(
                context_msg
                + f' provide the userid of an existing account for account role "{ role }" (node account field "{ USERID_ACCOUNT_FIELD.name }"): ',
                parse_validate=_userid_validate))
        password = cast(str, self.prompt_user(
                context_msg
                + f' provide the password for account "{ userid }", account role "{ role }" (node account field "{ PASSWORD_ACCOUNT_FIELD.name }"): ',
                parse_validate=_password_validate))
        email = cast(str, self.prompt_user(
                context_msg
                + f' provide the email for account "{ userid }", account role "{ role }" (node account field "{ EMAIL_ACCOUNT_FIELD.name }"): ',
                parse_validate=_password_validate))

        return MastodonUserPasswordAccount(role, userid, password, email)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        context_msg = f'Mastodon Node { self }: '
        userid = cast(str, self.prompt_user(
                context_msg
                + f' provide the userid of a non-existing account for account role "{ role }" (node non_existing_account field "{ USERID_NON_EXISTING_ACCOUNT_FIELD.name }"): ',
                parse_validate=_userid_validate))

        return MastodonNonExistingAccount(role, userid)

# Test support

    def delete_all_followers_of(self, actor_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)
        actor = mastodon_client.account_verify_credentials()
        for followed in mastodon_client.account_followers(actor.id):
            mastodon_client.account_unfollow(followed.id)


    def delete_all_following_of(self, actor_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)
        actor = mastodon_client.account_verify_credentials()
        for following in mastodon_client.account_following(actor.id):
            mastodon_client.account_unfollow(following.id)


    def delete_all_statuses_by(self, actor_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_uri(actor_uri)
        actor = mastodon_client.account_verify_credentials()
        for status in mastodon_client.account_statuses(actor.id):
            mastodon_client.status_delete(status)

# Internal implementation helpers

    def _get_mastodon_client_by_actor_uri(self, actor_uri: str) -> Mastodon:
        """
        Convenience method to get the instance of the Mastodon client object for a given actor URI.
        """
        config = cast(NodeWithMastodonApiConfiguration, self.config)
        userid = self._actor_uri_to_userid(actor_uri)
        if not userid:
            raise ValueError(f'Cannot find actor { actor_uri }')

        if self._requests_session is None:
            self._requests_session = requests.Session()
            if config.verify_tls_certificate:
                self._requests_session.verify = certifi.where() # force re-read of cacert file, which the requests library reads upon first import
            else:
                self._requests_session.verify = None

        if not self._mastodon_oauth_app:
            self._mastodon_oauth_app = MastodonOAuthApp.create(f'https://{ self.hostname}', self._requests_session)

        account = self._account_manager.get_account_by_match( lambda candidate: isinstance(candidate, MastodonAccount) and candidate.userid == userid )
        if account is None:
            return None

        ret = cast(MastodonAccount, account).mastodon_user_client(self._mastodon_oauth_app)
        return ret


    def _get_account_dict_by_other_actor_uri(self, mastodon_client: Mastodon, other_actor_uri) -> AttribAccessDict | None:
        """
        Using the specified Mastodon client, find an account dict for another Actor on this Node with
        other_actor_uri, or None.
        """
        results = mastodon_client.search(q=other_actor_uri, result_type="accounts")
        ret = find_first_in_array(results.get("accounts"), lambda b: b.uri == other_actor_uri)
        return ret


    def _is_following(self, mastodon_client: Mastodon, candidate_leader: AttribAccessDict) -> bool:
        """
        Determine whether the Actor of the specified Mastodon client is following the candidate_leader.
        """
        relationships = mastodon_client.account_relationships(candidate_leader) # this returns a list
        if relationships:
            relationship = find_first_in_array(relationships, lambda r: r.id == candidate_leader.id)
            return True if relationship and relationship.following else False
        return False


    def _is_followed_by(self, mastodon_client: Mastodon, candidate_follower: AttribAccessDict) -> bool:
        """
        Determine whether the Actor of the specified Mastodon client has the candidate_follower as follower.
        """
        relationships = mastodon_client.account_relationships(candidate_follower) # this returns a list
        if relationships:
            relationship = find_first_in_array(relationships, lambda r: r.id == candidate_follower.id)
            return True if relationship and relationship.followed_by else False
        return False


    def _poll_until_result(self,
        condition: Callable[[], Any | None],
        retry_count: int,
        retry_interval: float,
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


    @abstractmethod
    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        """
        The algorithm by which this application maps userids to ActivityPub actor URIs in reverse.
        Apparently this is different between Mastodon and other implementations, such as WordPress,
        so this is abstract here and must be overridden.
        """
        ...


class MastodonNode(NodeWithMastodonAPI):
    """
    An actual Mastodon Node.
    """
    # Python 3.12 @override
    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        if m:= re.match('^https://([^/]+)/users/(.+)$', actor_uri):
            if m.group(1) == self._config.hostname:
                return m.group(2)
        raise ValueError( f'Cannot find actor at this node: { actor_uri }' )


class MastodonSaasNodeDriver(NodeDriver):
    """
    Create a Mastodon Node that already runs as SaaS
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return [ APP_PAR, APP_VERSION_PAR, HOSTNAME_PAR, VERIFY_API_TLS_CERTIFICATE_PAR ]


    # Python 3.12 @override
    @staticmethod
    def test_plan_node_account_fields() -> list[TestPlanNodeAccountField]:
        return [ USERID_ACCOUNT_FIELD, EMAIL_ACCOUNT_FIELD, PASSWORD_ACCOUNT_FIELD, OAUTH_TOKEN_ACCOUNT_FIELD, ROLE_ACCOUNT_FIELD ]


    # Python 3.12 @override
    @staticmethod
    def test_plan_node_non_existing_account_fields() -> list[TestPlanNodeNonExistingAccountField]:
        return [ USERID_NON_EXISTING_ACCOUNT_FIELD, ROLE_NON_EXISTING_ACCOUNT_FIELD ]


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        app = test_plan_node.parameter_or_raise(APP_PAR, { APP_PAR.name:  'Mastodon' }) # Let user give a more descriptive name if they want to
        app_version = test_plan_node.parameter(APP_VERSION_PAR)
        hostname = test_plan_node.parameter_or_raise(HOSTNAME_PAR)
        verify_tls_certificate = test_plan_node.parameter_or_raise(VERIFY_API_TLS_CERTIFICATE_PAR, { VERIFY_API_TLS_CERTIFICATE_PAR.name: 'true' })

        if not hostname:
            hostname = self.prompt_user(f'Enter the hostname for the Mastodon Node of constellation role "{ rolename }" (node parameter "hostname"): ',
                                        parse_validate=hostname_validate)

        accounts : list[Account] = []
        if test_plan_node.accounts:
            for account_info in test_plan_node.accounts:
                accounts.append(MastodonAccount.create_from_account_info_in_testplan(account_info, self))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for non_existing_account_info in test_plan_node.non_existing_accounts:
                non_existing_accounts.append(MastodonNonExistingAccount.create_from_non_existing_account_info_in_testplan(non_existing_account_info, self))

        return (
            NodeWithMastodonApiConfiguration(
                node_driver=self,
                app=cast(str, app),
                app_version=cast(str, app_version),
                hostname=hostname,
                verify_tls_certificate=verify_tls_certificate
            ),
            DefaultAccountManager(accounts, non_existing_accounts)
        )


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> FediverseNode:
        return MastodonNode(rolename, config, cast(AccountManager, account_manager))
