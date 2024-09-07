"""
Fallback implementation for FediverseNode
"""

from typing import Final, cast

from feditest.protocols import (
    AbstractAccountManager,
    Account,
    AccountManager,
    InvalidAccountSpecificationException,
    InvalidNonExistingAccountSpecificationException,
    NodeConfiguration,
    NodeDriver,
    NonExistingAccount,
    OutOfAccountsException
)
from feditest.protocols.activitypub import ActivityPubNode
from feditest.protocols.fediverse import FediverseNode
from feditest.testplan import TestPlanConstellationNode, TestPlanError
from feditest.utils import appname_validate, hostname_validate, http_https_acct_uri_validate, https_uri_validate

ROLE_KEY: Final[str] = 'role'
URI_KEY: Final[str] = 'uri'
ACTOR_URI_KEY: Final[str] = 'actor_uri'

"""
Pre-existing accounts in TestPlans are specified as follows:
* URI_KEY: URI that either is a WebFinger resource (e.g. acct:joe@example.com or https://example.com/ ) or an Actor URI
* ROLE_KEY: optional account role
* ACTOR_URI_KEY: optional https URI that points to the Actor. This is calculated by WebFinger lookup if not provided

Known non-existing accounts are specified as follows:
* URI_KEY: URI that neither is a WebFinger resource nor an Actor URI
* ROLE_KEY: optional non-existing account role
"""

class FallbackFediverseAccount(Account):
    def __init__(self, uri: str, actor_uri: str | None, role: str | None):
        self._uri = uri
        self._actor_uri = actor_uri
        self._role = role


    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], node_driver: NodeDriver):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        if URI_KEY not in account_info_in_testplan or not account_info_in_testplan[URI_KEY]:
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Missing field value for: { URI_KEY }.')
        uri = account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')

        actor_uri = account_info_in_testplan.get(ACTOR_URI_KEY)
        if actor_uri:
            if not https_uri_validate(actor_uri):
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { ACTOR_URI_KEY } must be https URI, is: "{ actor_uri }".')
        # We cannot perform a WebFinger query here: the Node may not exist yet

        role = account_info_in_testplan.get(ROLE_KEY) # may or may not be there

        return FallbackFediverseAccount(uri, actor_uri, role)


    @property
    def uri(self):
        return self._uri


    @property
    def actor_uri(self):
        if not self._actor_uri:
            raise Exception('Perhaps perform WebFinger query here? But its unclear we can: feditest may not run on a host that has access to the same DNS info as the Nodes in the constellation')
        #     webfinger_response : WebFingerQueryResponse = self.perform_webfinger_query(uri)
        #     if not webfinger_response.jrd:
        #         raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Cannot determine actor URI from { uri }: WebFinger query failed')
        #     webfinger_response.jrd.validate() # may throw

        #     links = webfinger_response.jrd.links()
        #     if links:
        #         for link in links:
        #             if 'self' == link.get('rel') and 'application/activity+json' == link.get('type'):
        #                 actor_uri = link.get('href')

        #     if not actor_uri:
        #         raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Cannot determine actor URI from { uri }: WebFinger query has no rel=self and type=application/activity+json entry')
        #     if not https_uri_validate(actor_uri):
        #         raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'URI determined from WebFinger query of { uri } is not a valid Actor HTTP URI: "{ actor_uri }".')
        return self._actor_uri


    @property
    def role(self):
        return self._role


class FallbackFediverseNonExistingAccount(NonExistingAccount):
    def __init__(self, uri: str, actor_uri: str | None, role: str | None):
        self._uri = uri
        self._actor_uri = actor_uri
        self._role = role


    @staticmethod
    def create_from_non_existing_account_info_in_testplan(non_existing_account_info_in_testplan: dict[str, str | None], node_driver: NodeDriver):
        """
        Parses the information provided in an "non_existing_account" dict of TestPlanConstellationNode
        """
        if URI_KEY not in non_existing_account_info_in_testplan or not non_existing_account_info_in_testplan[URI_KEY]:
            raise InvalidNonExistingAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Missing field value for: { URI_KEY }.')
        uri = non_existing_account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')

        actor_uri = non_existing_account_info_in_testplan.get(ACTOR_URI_KEY)
        if actor_uri:
            if not https_uri_validate(actor_uri):
                raise InvalidAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Field { ACTOR_URI_KEY } must be https URI, is: "{ actor_uri }".')
        # We cannot perform a WebFinger query: account does not exist

        role = non_existing_account_info_in_testplan.get(ROLE_KEY) # may or may not be there

        return FallbackFediverseNonExistingAccount(uri, actor_uri, role)


    @property
    def uri(self):
        return self._uri


    @property
    def actor_uri(self):
        if self._actor_uri:
            return self._actor_uri
        raise Exception(f'No value for { ACTOR_URI_KEY } in non-existing account with role { self.role }.')


    @property
    def role(self):
        return self._role


class FallbackFediverseNode(FediverseNode):
    # Python 3.12 @override
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        if not self.account_manager:
            raise OutOfAccountsException('No AccountManager set')
        account = cast(FallbackFediverseAccount, self.account_manager.obtain_account_by_role(rolename))
        return account.actor_uri


    # Python 3.12 @override
    def make_create_note(self, actor_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        if deliver_to :
            return cast(str, self.prompt_user(
                    f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" create a Note'
                    + ' to be delivered to ' + ", ".join(deliver_to)
                    + ' and enter its URI when created.'
                    + f' Note content:"""\n{ content }\n"""' ))
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" create a Note'
                + ' and enter its URI when created.'
                + f' Note content:"""\n{ content }\n"""' ))


    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        if not self.account_manager:
            raise OutOfAccountsException('No AccountManager set')
        account = cast(FallbackFediverseAccount, self.account_manager.obtain_account_by_role(rolename))
        return account.uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        if not self.account_manager:
            raise OutOfAccountsException('No AccountManager set')
        non_account = cast(FallbackFediverseNonExistingAccount, self.account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.uri


    # Python 3.12 @override
    def make_announce_object(self, actor_uri, note_uri: str) -> str:
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" boost "{ note_uri }"'
                + ' and enter the boost activity\' local URI:'))


    # Python 3.12 @override
    def make_reply(self, actor_uri, note_uri: str, reply_content: str) -> str:
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" reply to object with "{ note_uri }"'
                + ' and enter its URI when created.'
                + f' Reply content:"""\n{ reply_content }\n"""' ))


    # Python 3.12 @override
    def make_a_follow_b(self, a_uri_here: str, b_uri_there: str, node_there: ActivityPubNode) -> None:
        self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ a_uri_here }" follow actor "{ b_uri_there }" and hit return once the relationship is fully established.' )


    # Python 3.12 @override
    def wait_for_object_in_inbox(self, actor_uri: str, object_uri: str) -> str:
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until in actor "{ actor_uri }"\'s inbox,'
                + f' the object with URI "{ object_uri }" has appeared and enter its local URI:'))


class InteractiveFallbackFediverseAccountManager(AbstractAccountManager):
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
        uri = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' provision an account for account role "{ role }" and enter its URI here (with https: or acct: scheme) (node account field "{ URI_KEY }"): ',
                parse_validate=http_https_acct_uri_validate))
        actor_uri = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' for the account with account role "{ role }", enter its Actor URI here (with https: scheme) (node account field "{ ACTOR_URI_KEY }"): ',
                parse_validate=https_uri_validate))

        return FallbackFediverseAccount(uri, actor_uri, role)


    def _provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        uri = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' provide the URI of a non-existing account for account role "{ role }" (with https: or acct: scheme) (node non_existing_account field "{ URI_KEY }"): ',
                parse_validate=http_https_acct_uri_validate))
        actor_uri = cast(str, self._node_driver.prompt_user(
                self._context_msg
                + f' provide the Actor URI of a non-existing account with account role "{ role }" (with https: scheme) (node non_existing_account field "{ ACTOR_URI_KEY }"): ',
                parse_validate=https_uri_validate))

        return FallbackFediverseNonExistingAccount(uri, actor_uri, role)


class AbstractFallbackFediverseNodeDriver(NodeDriver):
    """
    Abstract superclass of NodeDrivers that support all web server-side protocols but don't
    automate anything.
    """
    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        app = test_plan_node.parameter('app')
        app_version = test_plan_node.parameter('app_version')
        hostname = test_plan_node.parameter('hostname')

        if not hostname:
            hostname = self.prompt_user(f'Enter the hostname for the Node of constellation role "{ rolename }" (node parameter "hostname"): ',
                                        parse_validate=hostname_validate)
        if not app:
            app = self.prompt_user(f'Enter the name of the app at constellation role "{ rolename }" and hostname "{ hostname }" (node parameter "app"): ',
                                   parse_validate=appname_validate)

        accounts : list[Account] = []
        if test_plan_node.accounts:
            for account_info in test_plan_node.accounts:
                accounts.append(FallbackFediverseAccount.create_from_account_info_in_testplan(account_info, self))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for non_existing_account_info in test_plan_node.non_existing_accounts:
                non_existing_accounts.append(FallbackFediverseNonExistingAccount.create_from_non_existing_account_info_in_testplan(non_existing_account_info, self))

        return (
            NodeConfiguration(
                self,
                cast(str, app),
                cast(str, app_version),
                hostname
            ),
            InteractiveFallbackFediverseAccountManager(
                accounts,
                non_existing_accounts,
                f'On FediverseNode "{ hostname }" with constellation role "{ rolename }", running app "{ app }":',
                self
            )
        )
