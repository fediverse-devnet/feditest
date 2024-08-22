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
from feditest.nodedrivers.manual import AbstractManualFediverseNodeDriver
from feditest.protocols import Account, AccountManager, NodeDriver, NodeConfiguration, NonExistingAccount, TimeoutException
from feditest.protocols.activitypub import ActivityPubNode, AnyObject
from feditest.protocols.fediverse import FediverseNode
from feditest.reporting import trace
from feditest.testplan import TestPlanConstellationNode, TestPlanError
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
    from mastodon import Mastodon


def _oauth_token_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon client API token. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    return candidate if len(candidate)>10 else None


def _userid_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon user name. Avoids user input errors.
    """
    # FIXME is this right?
    return re.match(r'[a-zA-Z0-9_]', candidate) is not None


def _password_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon password. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    return candidate if len(candidate)>10 else None


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


    @abstractmethod
    @property
    def webfinger_uri(self):
        fixme() # need to get at the root URI


    @abstractmethod
    @property
    def actor_uri(self):
        fixme() # need to get at the root URI


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
            client.log_in(self.email, self.passwd)
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


    @abstractmethod
    @property
    def webfinger_uri(self):
        fixme() # need to get at the root URI


    @abstractmethod
    @property
    def actor_uri(self):
        fixme() # need to get at the root URI


# def existing_users(test_plan_node: TestPlanConstellationNode, node_driver: NodeDriver) -> list[MastodonUserRecord]:
#     """
#     Helper method to determine the initial list of UserRecords from the TestPlanConstellationNode.
#     This can't be a dict because not all accounts will have an assigned role.
#     """
#     if not test_plan_node.accounts:
#         return []

#     ret : list[MastodonUserRecord] = []
#     # FIXME
#     # for plan_account in test_plan_node.accounts:
#     #     if plan_account.role in ret:
#     #         raise NodeSpecificationInvalidError(node_driver, 'accounts', f'Have account with role { plan_account.role } already.')
#     #     if not plan_account.userid:
#     #         raise NodeSpecificationInvalidError(node_driver, 'accounts', 'Must have userid.')
#     #     if plan_account.email:
#     #         if not plan_account.password:
#     #             raise NodeSpecificationInvalidError(node_driver, 'accounts', 'Must have password if email is given.')
#     #         if plan_account.oauth_token:
#     #             raise NodeSpecificationInvalidError(node_driver, 'accounts', 'Must have email or oauth_token, not both.')
#     #         ret[plan_account.role] = MastodonUserRecord(userid=plan_account.userid, passwd=plan_account.password, email=plan_account.email, oauth_token=None)
#     #     else:
#     #         if not plan_account.oauth_token:
#     #             raise NodeSpecificationInvalidError(node_driver, 'accounts', 'Must have email or oauth_token.')
#     #         if plan_account.password:
#     #             raise NodeSpecificationInvalidError(node_driver, 'accounts', 'Must not have password if oauth_token is given.')
#     #         ret[plan_account.role] = MastodonUserRecord(userid=plan_account.userid, passwd=None, email=None, oauth_token=plan_account.oauth_token)
#     return ret


# def non_existing_users(test_plan_node: TestPlanConstellationNode, node_driver: NodeDriver) -> list[MastodonNoUserRecord]:
#     """
#     Helper method to determine the initial table of NoUserRecords from the TestPlanConstellationNode
#     """
#     if not test_plan_node.non_existing_accounts:
#         return []

#     ret : list[MastodonNoUserRecord] = []
#     # FIXME
#     # for plan_non_account in test_plan_node.non_existing_accounts:
#     #     if plan_non_account.role in ret:
#     #         raise NodeSpecificationInvalidError(node_driver, 'non_existing_accounts', f'Have non-existing account with role { plan_non_account.role } already.')
#     #     if not plan_non_account.userid:
#     #         raise NodeSpecificationInvalidError(node_driver, 'non_existing_accounts', 'Must have userid.')
#     #     ret[plan_non_account.role] = MastodonNoUserRecord(userid=plan_non_account.userid)
#     return ret


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
    def __init__(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None = None):
        super().__init__(rolename, config)
        self._account_manager = account_manager

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
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        account = cast(MastodonAccount, self._account_manager.obtain_account_by_role(rolename))
        return account.actor_uri


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


# # From WebFingerServer
    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        account = cast(MastodonAccount, self._account_manager.obtain_account_by_role(rolename))
        return account.webfinger_uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        non_account = cast(MastodonNonExistingAccount, self._account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.webfinger_uri



    # Not implemented
    # def obtain_account_identifier_requiring_percent_encoding(self, nickname: str | None = None) -> str:
    # def override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# # From WebServer

    # Not implemented:
    # def transaction(self, code: Callable[[],None]) -> WebServerLog:
    # def override_http_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# # Internal implementation helpers

#     def _userid_to_actor_uri(self, userid: str) -> str:
#         """
#         The algorithm by which this application maps userids to ActivityPub actor URIs.
#         Apparently this is different between Mastodon and other implementations, such as WordPress,
#         so this might be overridden

#         see also: _actor_uri_to_userid()
#         """
#         return f'https://{ self.parameter("hostname") }/users/{ userid }'


#     def _actor_uri_to_userid(self, actor_uri: str) -> str:
#         """
#         The algorithm by which this application maps userids to ActivityPub actor URIs in reverse.
#         Apparently this is different between Mastodon and other implementations, such as WordPress,
#         so this might be overridden

#         see also: _userid_to_actor_uri()
#         """
#         if m:= re.match('^https://([^/]+)/users/(.+)$', actor_uri):
#             if m.group(1) == self.parameter('hostname'):
#                 return m.group(2)
#         raise ValueError( f'Cannot find actor at this node: { actor_uri }' )


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


#     def _get_user_by_userid(self, userid: str) -> MastodonUserRecord:
#         for user in self._existing_users_by_role.values():
#             if userid is user.userid:
#                 return user
#         return None


class MastodonNode(NodeWithMastodonAPI):
    """
    An actual Mastodon Node.
    """
    @staticmethod
    def check_plan_node(test_plan_node : TestPlanConstellationNode, context_msg: str = '') -> None:
        """
        This encapsulates the requirements the MastodonNode has for TestPlanConstellationNodes.
        It's here as a static so various NodeDrivers can invoke it in their check_plan_node phase.
        """
        if test_plan_node.accounts:
            # Either we have e-mail and password, or oauth_token. Always need userid.
            for account in test_plan_node.accounts:
                if MastodonNode.ACCOUNT_USERID_KEY not in non_account:
                    raise TestPlanError(context_msg + f'Not existing account in TestPlan: no { MastodonNode.ACCOUNT_USERID_KEY }.')
                if not _userid_validate(non_account[MastodonNode.ACCOUNT_USERID_KEY]):
                    raise TestPlanError(context_msg + f'Not existing account in TestPlan: invalid { MastodonNode.ACCOUNT_USERID_KEY }: "{ non_account[MastodonNode.ACCOUNT_USERID_KEY] }".')
                if MastodonNode.ACCOUNT_OAUTH_TOKEN_KEY in account:
                    if MastodonNode.ACCOUNT_EMAIL_KEY in account or MastodonNode.ACCOUNT_PASSWORD_KEY in account:
                        raise TestPlanError(context_msg + f'Account in TestPlan: specify { MastodonNode.ACCOUNT_OAUTH_TOKEN_KEY } or { MastodonNode.ACCOUNT_EMAIL_KEY } and { MastodonNode.ACCOUNT_PASSWORD_KEY }, not both.')
                    if not _oauth_token_validate(non_account[MastodonNode.ACCOUNT_OAUTH_TOKEN_KEY]):
                        raise TestPlanError(context_msg + f'Account in TestPlan: invalid { MastodonNode.ACCOUNT_OAUTH_TOKEN_KEY }: "{ account[MastodonNode.ACCOUNT_OAUTH_TOKEN_KEY] }".')
                else:
                    if MastodonNode.ACCOUNT_EMAIL_KEY not in account or MastodonNode.ACCOUNT_PASSWORD_KEY not in account:
                        raise TestPlanError(context_msg + f'Account in TestPlan: when not providing { MastodonNode.ACCOUNT_OAUTH_TOKEN_KEY }, provide both { MastodonNode.ACCOUNT_EMAIL_KEY } and { MastodonNode.ACCOUNT_PASSWORD_KEY }, not both.')
                    if not email_validate(account[MastodonNode.ACCOUNT_EMAIL_KEY]):
                        raise TestPlanError(context_msg + f'Account in TestPlan: invalid { MastodonNode.ACCOUNT_EMAIL_KEY }, not an e-mail: "{ account[MastodonNode.ACCOUNT_EMAIL_KEY] }".')
                    if not _password_validate(account[MastodonNode.ACCOUNT_PASSWORD_KEY]):
                        raise TestPlanError(context_msg + f'Account in TestPlan: invalid { MastodonNode.ACCOUNT_PASSWORD_KEY }, not a valid password: "{ account[MastodonNode.ACCOUNT_PASSWORD_KEY] }".')

        if test_plan_node.non_existing_accounts:
            # Need userid
            for non_account in test_plan_node.non_existing_accounts:
                if MastodonNode.ACCOUNT_USERID_KEY not in non_account:
                    raise TestPlanError(context_msg + f'Not existing account in TestPlan: no { MastodonNode.ACCOUNT_USERID_KEY }.')
                if not _userid_validate(non_account[MastodonNode.ACCOUNT_USERID_KEY]):
                    raise TestPlanError(context_msg + f'Not existing account in TestPlan: invalid { MastodonNode.ACCOUNT_USERID_KEY }: "{ non_account[MastodonNode.ACCOUNT_USERID_KEY] }".')


    ACCOUNT_USERID_KEY: Final[str] = 'userid'
    ACCOUNT_EMAIL_KEY: Final[str] = 'email'
    ACCOUNT_PASSWORD_KEY: Final[str] = 'password'
    ACCOUNT_OAUTH_TOKEN_KEY: Final[str] = 'oauth_token'


class MastodonManualNodeDriver(AbstractManualFediverseNodeDriver):
    """
    Create a manually provisioned Mastodon Node
    """
    # Python 3.12 @override
    def create_configuration(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> NodeConfiguration:
        return NodeConfiguration(
            self,
            'Mastodon',
            test_plan_node.parameter('app_version'),
            test_plan_node.parameter('hostname')
        )


    def check_plan_node(self,rolename: str, test_plan_node: TestPlanConstellationNode) -> None:
        super().check_plan_node(rolename, test_plan_node)
        MastodonNode.check_plan_node(test_plan_node, 'MastodonManualNodeDriver:')


    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, test_plan_node, parameters)
        parameters['app'] = 'Mastodon'


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration) -> MastodonNode:
        return MastodonNode(rolename, config)
