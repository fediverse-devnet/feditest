"""
"""

from abc import abstractmethod
import certifi
from dataclasses import dataclass
import importlib
import requests
import sys
import time
from typing import Any, Callable, cast

from feditest.nodedrivers import (
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
from feditest.protocols.fediverse import (
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD,
    FediverseAccount,
    FediverseNode,
    FediverseNonExistingAccount,
    userid_validate
)
from feditest.reporting import is_trace_active, trace
from feditest.testplan import InvalidAccountSpecificationException, TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField, TestPlanNodeParameter
from feditest.utils import boolean_parse_validate, email_validate, find_first_in_array, hostname_validate, prompt_user, ParsedUri, ParsedAcctUri


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
        from mastodon_api import AttribAccessDict, Mastodon # type: ignore
    finally:
        sys.modules["mastodon"] = m
else:
    from mastodon import AttribAccessDict, Mastodon # type: ignore


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


def _password_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon password. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if len(candidate)>4 else None


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
        trace(f'Created Mastodon app with client_id="{ client_id }", client_secret="{ client_secret }".')
        return MastodonOAuthApp(client_id, client_secret, api_base_url, session)


class AccountOnNodeWithMastodonAPI(FediverseAccount): # this is intended to be abstract
    def __init__(self, role: str | None, userid: str, internal_userid: int | None = None):
        """
        userid: the string representing the user, e.g. "joe"
        internal_userid: the id of the user object in the API, e.g. 1
        """
        super().__init__(role, userid)
        self._internal_userid = internal_userid


    @property
    def internal_userid(self) -> int:
        if not self._internal_userid:
            mastodon_client = self.mastodon_user_client
            actor = mastodon_client.account_verify_credentials()
            self._internal_userid = cast(int, actor.id)
        return self._internal_userid


    @property
    @abstractmethod
    def mastodon_user_client(self) -> Mastodon:
        ...


class MastodonAccount(AccountOnNodeWithMastodonAPI): # this is intended to be abstract
    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], context_msg: str = ''):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        userid = USERID_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        role = ROLE_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, context_msg)
        oauth_token = OAUTH_TOKEN_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, context_msg)

        if oauth_token:
            if EMAIL_ACCOUNT_FIELD.name in account_info_in_testplan:
                raise InvalidAccountSpecificationException(
                    account_info_in_testplan,
                    f'Specify { OAUTH_TOKEN_ACCOUNT_FIELD.name } or { EMAIL_ACCOUNT_FIELD.name }, not both.')
            if PASSWORD_ACCOUNT_FIELD.name in account_info_in_testplan:
                raise InvalidAccountSpecificationException(
                    account_info_in_testplan,
                    f'Specify { OAUTH_TOKEN_ACCOUNT_FIELD.name } or { PASSWORD_ACCOUNT_FIELD.name }, not both.')
            return MastodonOAuthTokenAccount(role, userid, oauth_token)

        email = EMAIL_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        password = PASSWORD_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        return MastodonUserPasswordAccount(role, userid, password, email)


class MastodonUserPasswordAccount(MastodonAccount):
    def __init__(self, role: str | None, username: str, password: str, email: str):
        super().__init__(role, username)
        self._password = password
        self._email = email
        self._mastodon_user_client: Mastodon | None = None # Allocated as needed


    # Python 3.12 @override
    @property
    def mastodon_user_client(self) -> Mastodon:
        if self._mastodon_user_client is None:
            node = cast(NodeWithMastodonAPI, self._node)
            oauth_app = node._obtain_mastodon_oauth_app()
            trace(f'Logging into Mastodon at "{ oauth_app.api_base_url }" as "{ self._email }" with password.')
            client = Mastodon(
                client_id = oauth_app.client_id,
                client_secret = oauth_app.client_secret,
                api_base_url = oauth_app.api_base_url,
                session = oauth_app.session,
                debug_requests = is_trace_active()
            )
            client.log_in(username = self._email, password = self._password) # returns the token

            self._mastodon_user_client = client

        return self._mastodon_user_client


class MastodonOAuthTokenAccount(MastodonAccount):
    """
    Compare with WordPressAccount.
    """
    def __init__(self, role: str | None, userid: str, oauth_token: str):
        super().__init__(role, userid)
        self._oauth_token = oauth_token
        self._mastodon_user_client: Mastodon | None = None # Allocated as needed


    # Python 3.12 @override
    @property
    def mastodon_user_client(self) -> Mastodon:
        if self._mastodon_user_client is None:
            node = cast(NodeWithMastodonAPI, self._node)
            oauth_app = node._obtain_mastodon_oauth_app()
            trace(f'Logging into Mastodon at "{ oauth_app.api_base_url }" with userid "{ self.userid }" with OAuth token.')
            client = Mastodon(
                client_id = oauth_app.client_id,
                client_secret=oauth_app.client_secret,
                access_token=self._oauth_token,
                api_base_url=oauth_app.api_base_url,
                session=oauth_app.session,
                debug_requests = is_trace_active()
            )
            self._mastodon_user_client = client
        return self._mastodon_user_client


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


# From FediverseNode

    # Python 3.12 @override
    def obtain_actor_acct_uri(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri


    # Python 3.12 @override
    def make_create_note(self, actor_acct_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        trace('make_create_note:')
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)

        if deliver_to: # The only way we can address specific accounts in Mastodon
            for to in deliver_to:
                if to_account := self._find_account_dict_by_other_actor_acct_uri(mastodon_client, to):
                    to_handle = f"@{to_account.acct}"
                    content += f" {to_handle}"
                else:
                    raise ValueError(f'Cannot find account for Actor on { self }: "{ to }"')
        response = mastodon_client.status_post(content)
        trace(f'make_create_note returns with { response }')
        self._run_poor_mans_cron()
        return response.uri


    # Python 3.12 @override
    def make_announce_object(self, actor_acct_uri, to_be_announced_object_uri: str) -> str:
        trace('make_announce_object:')
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)

        if local_note := self._find_note_dict_by_uri(mastodon_client, to_be_announced_object_uri):
            reblog = mastodon_client.status_reblog(local_note)
            trace(f'make_announce_object returns with { reblog }')
            self._run_poor_mans_cron()
            return reblog.uri
        raise ValueError(f'Cannot find Note on { self } : "{ to_be_announced_object_uri }"')


    # Python 3.12 @override
    def make_reply_note(self, actor_acct_uri, to_be_replied_to_object_uri: str, reply_content: str) -> str:
        trace('make_reply_note:')
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        if local_note := self._find_note_dict_by_uri(mastodon_client, to_be_replied_to_object_uri):
            reply = mastodon_client.status_reply(to_status=local_note, status=reply_content)
            trace(f'make_reply returns with { reply }')
            self._run_poor_mans_cron()
            return reply.uri

        raise ValueError(f'Cannot find Note on { self }: "{ to_be_replied_to_object_uri }"')


    # Python 3.12 @override
    def make_follow(self, actor_acct_uri: str, to_follow_actor_acct_uri: str) -> None:
        trace('make_follow:')
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)

        if to_follow_account := self._find_account_dict_by_other_actor_acct_uri(mastodon_client, to_follow_actor_acct_uri):
            relationship = mastodon_client.account_follow(to_follow_account) # noqa: F841
            return
        raise ValueError(f'Cannot find account for Actor on { self }: "{ to_follow_actor_acct_uri }"')


    # Python 3.12 @override
    def set_auto_accept_follow(self, actor_acct_uri: str, auto_accept_follow: bool = True) -> None:
        if auto_accept_follow:
            return # Default for Mastodon

        raise NotImplementedByNodeError(self, NodeWithMastodonAPI.set_auto_accept_follow) # Can't find an API call for this


    # Python 3.12 @override
    def make_follow_accept(self, actor_acct_uri: str, follower_actor_acct_uri: str) -> None:
        super().make_follow_accept(actor_acct_uri, follower_actor_acct_uri) # FIXME


    # Python 3.12 @override
    def make_follow_reject(self, actor_acct_uri: str, follower_actor_acct_uri: str) -> None:
        super().make_follow_reject(actor_acct_uri, follower_actor_acct_uri) # FIXME


    # Python 3.12 @override
    def make_follow_undo(self, actor_acct_uri: str, following_actor_acct_uri: str) -> None:
        trace('make_follow_undo:')
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)

        if following_account := self._find_account_dict_by_other_actor_acct_uri(mastodon_client, following_actor_acct_uri):
            relationship = mastodon_client.account_unfollow(following_account) # noqa: F841
            self._run_poor_mans_cron()
            return
        raise ValueError(f'Account not found with Actor URI: { following_actor_acct_uri }')


    # Python 3.12 @override
    def wait_until_actor_has_received_note(self, actor_acct_uri: str, object_uri: str, max_wait: float = 5.) -> str:
        trace('wait_until_actor_has_received_note:')
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)

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
            f'Expected object { object_uri } has not arrived in inbox of actor { actor_acct_uri }'
        )
        trace(f'wait_for_object_in_inbox returns with { response }')
        return response.content


    # Python 3.12 @override
    def wait_until_actor_is_following_actor(self, actor_acct_uri: str, to_be_followed_uri: str, max_wait: float = 5.) -> None:
        trace(f'wait_until_actor_is_following_actor: actor_acct_uri = { actor_acct_uri }, to_be_followed_uri = { to_be_followed_uri }')
        account = self._get_account_by_actor_acct_uri(actor_acct_uri)
        if account is None:
            raise ValueError(f'Cannot find Account on { self }: "{ actor_acct_uri }"')
        mastodon_client = account.mastodon_user_client

        if to_be_followed_account := self._find_account_dict_by_other_actor_acct_uri(mastodon_client, to_be_followed_uri):
            self._poll_until_result( # may throw
                lambda: self._is_following(account, to_be_followed_account),
                int(max_wait),
                1.0,
                f'Actor { actor_acct_uri } is not following { to_be_followed_uri }')
            return
        raise ValueError(f'Cannot find account on { self }: "{ to_be_followed_uri }"')


    # Python 3.12 @override
    def wait_until_actor_is_followed_by_actor(self, actor_acct_uri: str, to_be_following_uri: str, max_wait: float = 5.) -> None:
        trace(f'wait_until_actor_is_followed_by_actor: actor_acct_uri = { actor_acct_uri }, to_be_followed_uri = { to_be_following_uri }')
        account = self._get_account_by_actor_acct_uri(actor_acct_uri)
        if account is None:
            raise ValueError(f'Cannot find Account on { self }: "{ actor_acct_uri }"')
        mastodon_client = account.mastodon_user_client

        if to_be_following_account := self._find_account_dict_by_other_actor_acct_uri(mastodon_client, to_be_following_uri):
            self._poll_until_result( # may throw
                lambda: self._is_followed_by(account, to_be_following_account),
                int(max_wait),
                1.0,
                f'Actor { actor_acct_uri } is not followed by { to_be_following_uri }')
            return
        raise ValueError(f'Cannot find account on { self }: "{ to_be_following_uri }"')


    # Python 3.12 @override
    def wait_until_actor_is_unfollowing_actor(self, actor_acct_uri: str, to_be_unfollowed_uri: str, max_wait: float = 5.) -> None:
        trace(f'wait_until_actor_is_unfollowing_actor: actor_acct_uri = { actor_acct_uri }, to_be_unfollowed_uri = { to_be_unfollowed_uri }')
        account = self._get_account_by_actor_acct_uri(actor_acct_uri)
        if account is None:
            raise ValueError(f'Cannot find Account on { self }: "{ actor_acct_uri }"')
        mastodon_client = account.mastodon_user_client

        if to_be_unfollowed_account := self._find_account_dict_by_other_actor_acct_uri(mastodon_client, to_be_unfollowed_uri):
            self._poll_until_result( # may throw
                lambda: not self._is_following(account, to_be_unfollowed_account),
                int(max_wait),
                1.0,
                f'Actor { actor_acct_uri } is still following { to_be_unfollowed_uri }')
            return
        raise ValueError(f'Account not found with Actor URI: { to_be_unfollowed_uri }')


    # Python 3.12 @override
    def wait_until_actor_is_unfollowed_by_actor(self, actor_acct_uri: str, to_be_unfollowing_uri: str, max_wait: float = 5.) -> None:
        trace(f'wait_until_actor_is_unfollowed_by_actor: actor_acct_uri = { actor_acct_uri }, to_be_unfollowing_uri = { to_be_unfollowing_uri }')
        account = self._get_account_by_actor_acct_uri(actor_acct_uri)
        if account is None:
            raise ValueError(f'Cannot find Account on { self }: "{ actor_acct_uri }"')
        mastodon_client = account.mastodon_user_client

        if to_be_unfollowing_account := self._find_account_dict_by_other_actor_acct_uri(mastodon_client, to_be_unfollowing_uri):
            self._poll_until_result( # may throw
                lambda: not self._is_followed_by(account, to_be_unfollowing_account),
                int(max_wait),
                1.0,
                f'Actor { actor_acct_uri } is still followed by { to_be_unfollowing_uri }')
            return
        raise ValueError(f'Account not found with Actor URI: { to_be_unfollowing_uri }')


# From ActivityPubNode

    # Python 3.12 @override
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri

    # Not implemented:
    # def obtain_followers_collection_uri(self, actor_acct_uri: str) -> str:
    # def obtain_following_collection_uri(self, actor_acct_uri: str) -> str:

    # Python 3.12 @override

    # Work in progress

    # def assert_member_of_collection_at(
    #     self,
    #     candidate_member_uri: str,
    #     collection_uri: str,
    #     spec_level: SpecLevel | None = None,
    #     interop_level: InteropLevel | None= None
    # ):
    #     collection = AnyObject(collection_uri).as_collection()
    #     if not collection.contains_item_with_id(candidate_member_uri):
    #         raise AssertionFailure(
    #             spec_level or SpecLevel.UNSPECIFIED,
    #             interop_level or InteropLevel.UNKNOWN,
    #             f"Node { self }: {candidate_member_uri} not in {collection_uri}")


    # # Python 3.12 @override
    # def assert_not_member_of_collection_at(
    #     self,
    #     candidate_member_uri: str,
    #     collection_uri: str,
    #     spec_level: SpecLevel | None = None,
    #     interop_level: InteropLevel | None= None
    # ):
    #     collection = AnyObject(collection_uri).as_collection()
    #     if collection.contains_item_with_id(candidate_member_uri):
    #         raise AssertionFailure(
    #             spec_level or SpecLevel.UNSPECIFIED,
    #             interop_level or InteropLevel.UNKNOWN,
    #             f"Node { self }: {candidate_member_uri} must not be in {collection_uri}")

# From WebFingerServer

    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        non_account = cast(FediverseNonExistingAccount, account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.actor_acct_uri

    # Not implemented:
    # def obtain_account_identifier_requiring_percent_encoding(self, rolename: str | None = None) -> str:
    # def override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# From WebServer

    # Not implemented:
    # def transaction(self, code: Callable[[],None]) -> WebServerLog:
    # def override_http_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# From Node

    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        context_msg = f'Mastodon Node { self }: '
        userid = cast(str, prompt_user(
                context_msg
                + f' provide the userid of an existing account for account role "{ role }" (node account field "{ USERID_ACCOUNT_FIELD.name }"): ',
                parse_validate=userid_validate))
        password = cast(str, prompt_user(
                context_msg
                + f' provide the password for account "{ userid }", account role "{ role }" (node account field "{ PASSWORD_ACCOUNT_FIELD.name }"): ',
                parse_validate=_password_validate))
        email = cast(str, prompt_user(
                context_msg
                + f' provide the email for account "{ userid }", account role "{ role }" (node account field "{ EMAIL_ACCOUNT_FIELD.name }"): ',
                parse_validate=_password_validate))

        return MastodonUserPasswordAccount(role, userid, password, email)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        context_msg = f'Mastodon Node { self }: '
        userid = cast(str, prompt_user(
                context_msg
                + f' provide the userid of a non-existing account for account role "{ role }" (node non_existing_account field "{ USERID_NON_EXISTING_ACCOUNT_FIELD.name }"): ',
                parse_validate=userid_validate))

        return FediverseNonExistingAccount(role, userid)

# Test support

    def delete_all_followers_of(self, actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        actor = mastodon_client.account_verify_credentials()
        for followed in mastodon_client.account_followers(actor.id):
            mastodon_client.account_unfollow(followed.id)
        self._run_poor_mans_cron()


    def delete_all_following_of(self, actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        actor = mastodon_client.account_verify_credentials()
        for following in mastodon_client.account_following(actor.id):
            mastodon_client.account_unfollow(following.id)
        self._run_poor_mans_cron()


    def delete_all_statuses_by(self, actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        actor = mastodon_client.account_verify_credentials()
        for status in mastodon_client.account_statuses(actor.id):
            mastodon_client.status_delete(status)
        self._run_poor_mans_cron()

# Internal implementation helpers

    def _obtain_requests_session(self) -> requests.Session:
        if self._requests_session is None:
            self._requests_session = requests.Session()
            config = cast(NodeWithMastodonApiConfiguration, self.config)
            if config.verify_tls_certificate:
                self._requests_session.verify = certifi.where() # force re-read of cacert file, which the requests library reads upon first import
            else:
                self._requests_session.verify = None
        return self._requests_session


    def _obtain_mastodon_oauth_app(self) -> MastodonOAuthApp:
        session = self._obtain_requests_session()
        if not self._mastodon_oauth_app:
            self._mastodon_oauth_app = MastodonOAuthApp.create(f'https://{ self.hostname}', session)
        return self._mastodon_oauth_app


    def _get_account_by_actor_acct_uri(self, actor_acct_uri: str) -> MastodonAccount | None:
        """
        Convenience method to get the Account that goes with this actor URI
        """
        userid = self._actor_acct_uri_to_userid(actor_acct_uri)
        if not userid:
            raise ValueError(f'Cannot find Actor on { self }: "{ actor_acct_uri }"')

        ret = self._account_manager.get_account_by_match(lambda candidate: isinstance(candidate, AccountOnNodeWithMastodonAPI) and candidate.userid == userid )
        return cast(MastodonAccount | None, ret)


    def _get_mastodon_client_by_actor_acct_uri(self, actor_acct_uri: str) -> Mastodon:
        """
        Convenience method to get the instance of the Mastodon client object for a given actor URI.
        """
        account = self._get_account_by_actor_acct_uri(actor_acct_uri)
        if account is None:
            raise Exception(f'On Node { self }, failed to find account with for "{ actor_acct_uri }".')

        return account.mastodon_user_client


    def _find_account_dict_by_other_actor_acct_uri(self, mastodon_client: Mastodon, other_actor_acct_uri: str) -> AttribAccessDict | None:
        """
        Using the specified Mastodon client, find an account dict for another Actor with
        other_actor_acct_uri, or None.
        """
        # Search for @foo@bar.com, not acct:foo@bar.com or foo@bar.com
        handle_without_at = other_actor_acct_uri.replace('acct:', '')
        handle_with_at = '@' + handle_without_at
        trace(f'On node { self } as { mastodon_client.account }, search for "{ handle_with_at }", result-type=accounts')
        results = mastodon_client.search(q=handle_with_at, result_type="accounts")

        # Mastodon has the foo@bar.com in the 'acct' field
        ret = find_first_in_array(results.get("accounts"), lambda b: b.acct == handle_without_at)
        return ret


    def _find_note_dict_by_uri(self, mastodon_client: Mastodon, uri: str) -> AttribAccessDict | None:
        """
        Using the specified Mastodon client, find a the dict for a status, or None.
        """
        trace(f'On node { self } as { mastodon_client.account }, search for "{ uri }", result-type=statuses')
        results = mastodon_client.search(q=uri, result_type="statuses")
        ret = find_first_in_array(results.get("statuses"), lambda b: b.uri == uri)
        return ret


    def _is_following(self, account: MastodonAccount, candidate_leader: AttribAccessDict) -> bool:
        """
        Determine whether the Actor of the specified Mastodon client is following the candidate_leader.
        """
        mastodon_client = account.mastodon_user_client

        relationships = mastodon_client.account_following(account.internal_userid) # this returns a list
        if relationships:
            relationship = find_first_in_array(relationships, lambda r: r.acct == candidate_leader.acct)
            return relationship is not None
        return False


    def _is_followed_by(self, account: MastodonAccount, candidate_follower: AttribAccessDict) -> bool:
        """
        Determine whether the Actor of the specified Mastodon client has the candidate_follower as follower.
        """
        mastodon_client = account.mastodon_user_client

        relationships = mastodon_client.account_followers(account.internal_userid) # this returns a list
        if relationships:
            relationship = find_first_in_array(relationships, lambda r: r.acct == candidate_follower.acct)
            return relationship is not None
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


    def _actor_acct_uri_to_userid(self, actor_acct_uri: str) -> str:
        """
        The algorithm by which this application maps userids to ActivityPub actor handles in reverse.
        """
        parsed = ParsedUri.parse(actor_acct_uri)
        if isinstance(parsed, ParsedAcctUri):
            return parsed.user
        raise ValueError(f'Not an acct: URI: { actor_acct_uri }')


    def _run_poor_mans_cron(self) -> None:
        """
        This method is invoked after each operation that may need to push an activity to another node.
        By default, this does nothing: Mastodon itself does not need it, it has a separate queuing daemon.
        But WordPress wants to do it on an HTTP request; so we give it the opportunity to override this.
        """
        pass


class MastodonNode(NodeWithMastodonAPI):
    pass


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
            hostname = prompt_user(f'Enter the hostname for the Mastodon Node of constellation role "{ rolename }" (node parameter "hostname"): ',
                                        parse_validate=hostname_validate)

        accounts : list[Account] = []
        if test_plan_node.accounts:
            for index, account_info in enumerate(test_plan_node.accounts):
                accounts.append(MastodonAccount.create_from_account_info_in_testplan(
                        account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Account { index }: '))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for index, non_existing_account_info in enumerate(test_plan_node.non_existing_accounts):
                non_existing_accounts.append(FediverseNonExistingAccount.create_from_non_existing_account_info_in_testplan(
                        non_existing_account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Non-existing account { index }: '))

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
