"""
"""

from abc import abstractmethod
from dataclasses import dataclass
import importlib
import re
import requests
import sys
import time
from typing import Any, Callable, Final, cast
from urllib.parse import urlparse

from feditest import AssertionFailure, InteropLevel, SpecLevel
from feditest.nodedrivers.fallback.fediverse import AbstractFallbackFediverseNodeDriver
from feditest.protocols import (
    AbstractAccountManager,
    Account,
    AccountManager,
    InvalidAccountSpecificationException,
    InvalidNonExistingAccountSpecificationException,
    Node,
    NodeConfiguration,
    NodeDriver,
    NonExistingAccount,
    OutOfAccountsException,
    TimeoutException
)
from feditest.protocols.activitypub import ActivityPubNode, AnyObject
from feditest.protocols.fediverse import FediverseNode
from feditest.reporting import trace
from feditest.testplan import TestPlanConstellationNode, TestPlanError
from feditest.utils import appname_validate, email_validate, hostname_validate


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
    from mastodon import Mastodon


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

"""
Pre-existing username/password accounts in TestPlans are specified as follows:

* USERID_KEY: Mastodon userid for a user (e.g. "joe")
* EMAIL_KEY: E-mail for a user (needed because logging into Mastodon is by e-mail address)
* PASSWORD_KEY: Password of a user
* ROLE_KEY: optional account role

Pre-existing OAuth token accounts in TestPlans are specified as follows:

* USERID_KEY: Mastodon userid for a user (e.g. "joe")
* OAUTH_TOKEN_KEY: OAuth token of a user, obtained out of band
* ROLE_KEY: optional account role

Known non-existing accounts are specified as follows:
* USERID_KEY: Mastodon userid for a non-existing user (e.g. "joe")
* ROLE_KEY: optional non-existing account role

"""

USERID_KEY: Final[str] = 'userid'
EMAIL_KEY: Final[str] = 'email'
PASSWORD_KEY: Final[str] = 'password'
OAUTH_TOKEN_KEY: Final[str] = 'oauth_token'
ROLE_KEY: Final[str] = 'role'


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
    def create(api_base_url: str, session: requests.Session):
        client_id_secret = Mastodon.create_app('feditest', api_base_url=api_base_url, session=session)
        return MastodonOAuthApp(client_id_secret[0], client_id_secret[1], api_base_url, session)


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
        if USERID_KEY not in account_info_in_testplan or not account_info_in_testplan[USERID_KEY]:
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Missing field value for: { USERID_KEY }.')
        userid = account_info_in_testplan[USERID_KEY]
        if not _userid_validate(userid):
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { USERID_KEY } must be a valid Mastodon userid, is: "{ userid }".')

        role = account_info_in_testplan.get(ROLE_KEY) # may or may not be there

        if OAUTH_TOKEN_KEY in account_info_in_testplan:
            if not account_info_in_testplan[OAUTH_TOKEN_KEY]:
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Either { OAUTH_TOKEN_KEY } is empty.')
            oauth_token = account_info_in_testplan[OAUTH_TOKEN_KEY]
            if not _oauth_token_validate(oauth_token):
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { OAUTH_TOKEN_KEY } must be a valid Mastodon OAuth token, is: "{ oauth_token }".')

            return MastodonOAuthTokenAccount(role, userid, oauth_token)

        else:
            if EMAIL_KEY not in account_info_in_testplan or not account_info_in_testplan[EMAIL_KEY]:
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Either field { EMAIL_KEY } or { OAUTH_TOKEN_KEY } must ben given.')
            email = account_info_in_testplan[EMAIL_KEY]
            if not email_validate(email):
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { EMAIL_KEY } must be a valid e-mail address, is: "{ email }".')

            if PASSWORD_KEY not in account_info_in_testplan or not account_info_in_testplan[PASSWORD_KEY]:
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Missing field value for: { PASSWORD_KEY }.')
            password = account_info_in_testplan[PASSWORD_KEY]
            if not _password_validate(password):
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { PASSWORD_KEY } must be a valid Mastodon password, is: "{ password }".')

            return MastodonUserPasswordAccount(role, userid, email, password)


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
    def __init__(self, role: str | None, userid: str, email: str, password: str):
        super().__init__(role, userid)
        self.email = email
        self.password = password


    # Python 3.12 @override
    def mastodon_user_client(self, oauth_app: MastodonOAuthApp) -> Mastodon:
        if self._mastodon_user_client is None:
            client = Mastodon(
                client_id = oauth_app.client_id,
                client_secret=oauth_app.client_secret,
                api_base_url=oauth_app.api_base_url,
                session=oauth_app.session
            )
            client.log_in(self.email, self.password)
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
        if USERID_KEY not in non_existing_account_info_in_testplan or not non_existing_account_info_in_testplan[USERID_KEY]:
            raise InvalidAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Missing field value for: { USERID_KEY }.')
        userid = non_existing_account_info_in_testplan[USERID_KEY]
        if not _userid_validate(userid):
            raise InvalidAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Field { USERID_KEY } must be a valid Mastodon userid, is: "{ userid }".')

        role = non_existing_account_info_in_testplan.get(ROLE_KEY) # may or may not be there

        return MastodonNonExistingAccount(role, userid)


    @property
    def webfinger_uri(self):
        return f'acct:{ self.userid }@{ self.node.hostname }'


    @property
    def actor_uri(self):
        return f'https://{ self.node.hostname }/users/{ self.userid }'


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
    def __init__(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager):
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
                def f(): # I thought I could make this a lambda but python and I don't get along
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


    # Python 3.12 @override
    def wait_for_object_in_inbox(self, actor_uri: str, object_uri: str, retry_count: int = 5, retry_interval: int = 1) -> str:
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
            retry_count,
            retry_interval,
            f'Expected object { object_uri } has not arrived in inbox of actor { actor_uri }')
        trace(f'wait_for_object_in_inbox returns with { response }')
        return response

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

# Internal implementation helpers

#     def _provision_new_user(self, rolename: str) -> MastodonUserRecord:
#         """
#         Make sure a new user exists. This should be overridden in subclasses if at all possible.
#         """
#         userid = self.prompt_user( f'Create a new user account for user role { rolename } on the app'
#                                  + f' in role { self._rolename } at hostname { self._parameters["hostname"] }'
#                                  + ' and enter its user handle: ',
#                                parse_validate=lambda x: x if len(x) else None )
#         useremail = self.prompt_user('... and its e-mail: ', parse_validate=email_validate)
#         userpass = self.prompt_user('... and its password:', parse_validate=lambda x: len(x) > 3)
#         return MastodonUserRecord(userid=cast(str, userid), email=cast(str, useremail), passwd=cast(str, userpass), oauth_token=None, role=rolename)


#     def _create_non_existing_user(self) -> MastodonNoUserRecord:
#         """
#         Create a new user handle that could exist on this Node, but does not.
#         """
#         return MastodonNoUserRecord(userid=f'does-not-exist-{ os.urandom(5).hex() }')  # This is strictly speaking not always true, but will do I think


    def _get_mastodon_client_by_actor_uri(self, actor_uri: str) -> Mastodon:
        """
        Convenience method to get the instance of the Mastodon client object for a given actor URI.
        """
#         if self._requests_session is None:
#             self._requests_session = requests.Session()
#             self._requests_session.verify = certifi.where() # force re-read of cacert file, which the requests library reads upon first import

#         if self._mastodon_oauth_app is None:
#             api_base_url = f'https://{ self.parameter("hostname") }/'
#             trace( f'Creating Mastodon.py app with API base URL { api_base_url } ')
#             self._mastodon_oauth_app = MastodonOAuthApp.create(api_base_url, self._requests_session)

#         trace('MastodonOAuthApp is', self._mastodon_oauth_app)
#         userid = self._actor_uri_to_userid(actor_uri)
#         if not userid:
#             raise ValueError(f'Cannot find actor { actor_uri }')
#         user = self._get_user_by_userid(userid)
#         if not user:
#             raise ValueError(f'Cannot find user { userid }')
#         mastodon_client = user.mastodon_user_client(self._mastodon_oauth_app)
#         return mastodon_client


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


    @abstractmethod
    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        """
        The algorithm by which this application maps userids to ActivityPub actor URIs in reverse.
        Apparently this is different between Mastodon and other implementations, such as WordPress,
        so this is abstract here and must be overridden.
        """
        ...


#     def _get_user_by_userid(self, userid: str) -> MastodonUserRecord:
#         for user in self._existing_users_by_role.values():
#             if userid is user.userid:
#                 return user
#         return None


class MastodonNode(NodeWithMastodonAPI):
    """
    An actual Mastodon Node.
    """
    # Python 3.12 @override
    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        """
        The algorithm by which this application maps userids to ActivityPub actor URIs in reverse.
        Apparently this is different between Mastodon and other implementations, such as WordPress,
        so this is abstract here and must be overridden.
        """
        if m:= re.match('^https://([^/]+)/users/(.+)$', actor_uri):
            if m.group(1) == self._config.hostname:
                return m.group(2)
        raise ValueError( f'Cannot find actor at this node: { actor_uri }' )


class InteractiveMastodonAccountManager(AbstractAccountManager):
        """
    An AccountManager that asks the user when it runs out of known accounts.
        """
    def __init__(self,
                 initial_accounts: list[Account],
                 initial_non_existing_accounts: list[NonExistingAccount],
                 context_msg: str,
                 node_driver: NodeDriver
    ):
        super().__init__(initial_accounts, initial_non_existing_accounts)

        # we want to prompt the user with some context
        self._context_msg = context_msg
        self._node_driver = node_driver


    # Python 3.12 @override
    def _provision_account_for_role(self, role: str | None = None) -> Account | None:
        userid = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' provide the userid of an existing account for account role "{ role }" (node account field "{ USERID_KEY }"): ',
                parse_validate=_userid_validate))

        password = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' provide the password for account "{ userid }", account role "{ role }" (node account field "{ PASSWORD_KEY }"): ',
                parse_validate=_password_validate))

        email = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' provide the email for account "{ userid }", account role "{ role }" (node account field "{ EMAIL_KEY }"): ',
                parse_validate=_password_validate))

        return MastodonUserPasswordAccount(role, userid, email, password)


    def _provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        userid = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' provide the userid of a non-existing account for account role "{ role }" (node non_existing_account field "{ USERID_KEY }"): ',
                parse_validate=_userid_validate))

        return MastodonNonExistingAccount(role, userid)


class MastodonManualNodeDriver(AbstractManualFediverseNodeDriver):
class MastodonManualNodeDriver(AbstractFallbackFediverseNodeDriver):
    """
    Create a manually provisioned Mastodon Node
    """
    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        app = test_plan_node.parameter('app') or 'Mastodon' # Let user give a more descriptive name if they want to
        app_version = test_plan_node.parameter('app_version')
        hostname = test_plan_node.parameter('hostname')

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
            NodeConfiguration(
            self,
                cast(str, app),
                cast(str, app_version),
                hostname
            ),
            InteractiveMastodonAccountManager(
                accounts,
                non_existing_accounts,
                f'On Mastodon node "{ hostname }" with constellation role "{ rolename }":',
                self
            )
        )


    # Python 3.12 @override


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration) -> MastodonNode:
        return MastodonNode(rolename, config)
