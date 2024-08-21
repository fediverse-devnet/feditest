"""
Fallback implementation for FediverseNode
"""

from typing import Any, Final, cast

from feditest.account import Account, DefaultAccountManager, InvalidAccountSpecificationException, InvalidNonExistingAccountSpecificationException, NonExistingAccount
from feditest.nodedrivers.fallback.webfinger import FallbackWebFingerServer
from feditest.protocols import NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.protocols.webfinger import WebFingerQueryResponse
from feditest.testplan import TestPlanConstellationNode
from feditest.utils import http_https_acct_uri_validate, https_uri_validate

ROLE_KEY: Final[str] = 'role'
URI_KEY: Final[str] = 'uri'
ACTOR_URI_KEY: Final[str] = 'actor_uri'

"""
Pre-existing oaccounts in TestPlans are specified as follows:
* URI_KEY: URI that either is a WebFinger resource (e.g. acct:joe@example.com or https://example.com/ ) or an Actor URI
* ROLE_KEY: optional account role
* ACTOR_URI_KEY: optional https URI that points to the Actor. This is calculated by WebFinger lookup if not provided

Known non-existing accounts are specified as follows:
* URI_KEY: URI that neither is a WebFinger resource nor an Actor URI
* ROLE_KEY: optional account role
"""

class FallbackFediverseAccount(Account):
    def __init__(self, account_info_in_testplan: dict[str,str], node_driver: NodeDriver):
        if URI_KEY not in account_info_in_testplan:
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Missing field: { URI_KEY }.')
        uri = account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')

        actor_uri = account_info_in_testplan.get(ACTOR_URI_KEY)
        if actor_uri:
            if not https_uri_validate(actor_uri):
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { ACTOR_URI_KEY } must be https URI, is: "{ actor_uri }".')
        else:
            # Determine from WebFinger
            webfinger_response : WebFingerQueryResponse = self.perform_webfinger_query(uri)
            if not webfinger_response.jrd:
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Cannot determine actor URI from { uri }: WebFinger query failed')
            webfinger_response.jrd.validate() # may throw

            links = webfinger_response.jrd.links()
            if links:
                for link in links:
                    if 'self' == link.get('rel') and 'application/activity+json' == link.get('type'):
                        actor_uri = link.get('href')

            if not actor_uri:
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Cannot determine actor URI from { uri }: WebFinger query has no rel=self and type=application/activity+json entry')
            if not https_uri_validate(actor_uri):
                raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'URI determined from WebFinger query of { uri } is not a valid Actor HTTP URI: "{ actor_uri }".')

        self.uri = uri
        self.actor_uri = actor_uri
        self.role = account_info_in_testplan.get(ROLE_KEY) # may or may not be there


class FallbackFediverseNonExistingAccount(NonExistingAccount):
    def __init__(self, non_existing_account_info_in_testplan: dict[str,str], node_driver: NodeDriver):
        if URI_KEY not in non_existing_account_info_in_testplan:
            raise InvalidNonExistingAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Missing field: { URI_KEY }.'))
        uri = non_existing_account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')
        self.uri = uri
        self.role = non_existing_account_info_in_testplan.get(ROLE_KEY) # may or may not be there


class FallbackFediverseNode(FediverseNode, FallbackWebFingerServer):
    @staticmethod
    def create(
        rolename: str,
        parameters: dict[str,Any],
        node_driver: NodeDriver,
        test_plan_node: TestPlanConstellationNode
    ):
        accounts : list[Account] = []
        if test_plan_node.accounts:
            for account_info in test_plan_node.accounts:
                accounts.append(FallbackFediverseAccount(account_info, node_driver))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for non_existing_account_info in test_plan_node.non_existing_accounts:
                non_existing_accounts.append(FallbackFediverseNonExistingAccount(non_existing_account_info, node_driver))

        account_manager = DefaultAccountManager(accounts, non_existing_accounts)
        return FallbackWebFingerServer(rolename, parameters, node_driver, account_manager)


    # Python 3.12 @override
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        account: FallbackFediverseAccount = self._account_manager.obtain_account_by_role(rolename)
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
        account: FallbackFediverseAccount = self._account_manager.obtain_account_by_role(rolename)
        return account.uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        non_account: FallbackFediverseNonExistingAccount = self._account_manager.obtain_non_existing_account_by_role(rolename)
        return non_account.uri


    # Python 3.12 @override
    def wait_for_object_in_inbox(self, actor_uri: str, object_uri: str) -> str:
        return cast(str, self.prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until in actor "{ actor_uri }"\'s inbox,'
                + f' the object with URI "{ object_uri }" has appeared and enter its local URI:'))


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
    def make_a_follow_b(self, a_uri_here: str, b_uri_there: str, node_there: 'ActivityPubNode') -> None:
        self.prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ a_uri_here }" follow actor "{ b_uri_there }" and hit return once the relationship is fully established.' )

