"""
Fallback implementation for FediverseNode
"""

from typing import cast

from feditest.nodedrivers import (
    Account,
    AccountManager,
    DefaultAccountManager,
    NodeConfiguration,
    NodeDriver,
    NonExistingAccount,
    OutOfAccountsException,
    TimeoutException,
    APP_PAR,
    APP_VERSION_PAR,
    HOSTNAME_PAR
)
from feditest.protocols.fediverse import FediverseNode
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField
from feditest.utils import appname_validate, boolean_parse_validate, hostname_validate, http_https_acct_uri_validate, https_uri_validate, prompt_user


ROLE_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'role',
        """A symbolic name for the Account as used by tests (optional).""",
        lambda x: len(x)
)
URI_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'uri',
        """The acct: or https: URI that identifies the Account (required).""",
        http_https_acct_uri_validate
)
ACTOR_URI_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'actor_uri',
        """The https: Actor URI for this Account (required for ActivityPub tests).""",
        https_uri_validate
)
ROLE_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'role',
        """A symbolic name for the non-existing Account as used by tests (optional).""",
        lambda x: len(x)
)
URI_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'uri',
        """The acct: or https: URI that identifies the non-existing Account (required).""",
        http_https_acct_uri_validate
)
ACTOR_URI_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'actor_uri',
        """The https: Actor URI for this non-existing Account (required for ActivityPub tests).""",
        https_uri_validate
)


class FallbackFediverseAccount(Account):
    def __init__(self, role: str | None, uri: str, actor_uri: str | None):
        super().__init__(role)
        self._uri = uri
        self._actor_uri = actor_uri


    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], context_msg: str = ''):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        uri = URI_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        actor_uri = ACTOR_URI_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        role = ROLE_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, context_msg)

        # If actor_uri was not given, we cannot perform a WebFinger query here: the Node may not exist yet

        return FallbackFediverseAccount(role, uri, actor_uri)


    @property
    def uri(self):
        return self._uri


    @property
    def actor_uri(self):
        if self._actor_uri:
            return self._actor_uri
        raise Exception(f'No value for { ACTOR_URI_ACCOUNT_FIELD.name } in account with role { self.role }.')

        # Perhaps perform WebFinger query here? But its unclear we can: feditest may not run on a host that has access to the same DNS info as the Nodes in the constellation')
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


class FallbackFediverseNonExistingAccount(NonExistingAccount):
    def __init__(self, role: str | None, uri: str, actor_uri: str | None):
        super().__init__(role)
        self._uri = uri
        self._actor_uri = actor_uri


    @staticmethod
    def create_from_non_existing_account_info_in_testplan(non_existing_account_info_in_testplan: dict[str, str | None], context_msg: str = ''):
        """
        Parses the information provided in an "non_existing_account" dict of TestPlanConstellationNode
        """
        uri = URI_NON_EXISTING_ACCOUNT_FIELD.get_validate_from_or_raise(non_existing_account_info_in_testplan, context_msg)
        actor_uri = ACTOR_URI_NON_EXISTING_ACCOUNT_FIELD.get_validate_from(non_existing_account_info_in_testplan, context_msg)
        role = ROLE_NON_EXISTING_ACCOUNT_FIELD.get_validate_from(non_existing_account_info_in_testplan, context_msg)

        # We cannot perform a WebFinger query: account does not exist

        return FallbackFediverseNonExistingAccount(role, uri, actor_uri)


    @property
    def uri(self):
        return self._uri


    @property
    def actor_uri(self):
        if self._actor_uri:
            return self._actor_uri
        raise Exception(f'No value for { ACTOR_URI_NON_EXISTING_ACCOUNT_FIELD.name } in non-existing account with role { self.role }.')


class FallbackFediverseNode(FediverseNode):
    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        context_msg = f'Node { self }:'
        uri = cast(str, prompt_user(
                context_msg
                + f' provision an account for account role "{ role }" and enter its URI here (with https: or acct: scheme) (node account field "{ URI_ACCOUNT_FIELD.name }"): ',
                parse_validate=http_https_acct_uri_validate))
        actor_uri = cast(str, prompt_user(
                context_msg
                + f' for the account with account role "{ role }", enter its Actor URI here (with https: scheme) (node account field "{ ACTOR_URI_ACCOUNT_FIELD.name }"): ',
                parse_validate=https_uri_validate))

        return FallbackFediverseAccount(uri, actor_uri, role)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        context_msg = f'Node { self }:'
        uri = cast(str, prompt_user(
                context_msg
                + f' provide the URI of a non-existing account for account role "{ role }" (with https: or acct: scheme) (node non_existing_account field "{ URI_NON_EXISTING_ACCOUNT_FIELD.name }"): ',
                parse_validate=http_https_acct_uri_validate))
        actor_uri = cast(str, prompt_user(
                context_msg
                + f' provide the Actor URI of a non-existing account with account role "{ role }" (with https: scheme) (node non_existing_account field "{ ACTOR_URI_NON_EXISTING_ACCOUNT_FIELD.name }"): ',
                parse_validate=https_uri_validate))

        return FallbackFediverseNonExistingAccount(uri, actor_uri, role)


    # Python 3.12 @override
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        if not self.account_manager:
            raise OutOfAccountsException('No AccountManager set')
        account = cast(FallbackFediverseAccount, self.account_manager.obtain_account_by_role(rolename))
        return account.actor_uri


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
    def make_create_note(self, actor_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        if deliver_to :
            return cast(str, prompt_user(
                    f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" create a Note'
                    + ' to be delivered to ' + ", ".join(deliver_to)
                    + ' and enter its URI when created.'
                    + f' Note content:"""\n{ content }\n"""' ))
        return cast(str, prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" create a Note'
                + ' and enter its URI when created.'
                + f' Note content:"""\n{ content }\n"""' ))



    # Python 3.12 @override
    def make_announce_object(self, actor_uri, to_be_announced_object_uri: str) -> str:
        return cast(str, prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" boost "{ to_be_announced_object_uri }"'
                + ' and enter the Announce object\'s local URI:',
                parse_validate=https_uri_validate))


    # Python 3.12 @override
    def make_reply_note(self, actor_uri, to_be_replied_to_object_uri: str, reply_content: str) -> str:
        return cast(str, prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" reply to object with "{ to_be_replied_to_object_uri }"'
                + ' and enter the Announce object\'s URI when created.'
                + f' Reply content:"""\n{ reply_content }\n"""' ))


    # Python 3.12 @override
    def make_follow(self, actor_uri: str, to_follow_actor_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_uri }" follow actor "{ to_follow_actor_uri }"'
                + ' and hit return when done.')


    # We leave the NotImplementedByNodeError raised by the superclass for all other follow-related actions
    # until we have a better idea :-)

    # Python 3.12 @override
    def wait_until_actor_is_following_actor(self, actor_uri: str, to_be_followed_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until actor "{ actor_uri }" is following actor "{ to_be_followed_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_uri } not following actor { to_be_followed_uri}.', max_wait)


    # Python 3.12 @override
    def wait_until_actor_is_followed_by_actor(self, actor_uri: str, to_be_following_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until actor "{ actor_uri }" is followed by actor "{ to_be_following_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_uri } not followed by actor { to_be_following_uri}.', max_wait)


    # Python 3.12 @override
    def wait_until_actor_is_unfollowing_actor(self, actor_uri: str, to_be_unfollowed_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until actor "{ actor_uri }" is not following any more actor "{ to_be_unfollowed_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_uri } still following actor { to_be_unfollowed_uri}.', max_wait)


    # Python 3.12 @override
    def wait_until_actor_is_unfollowed_by_actor(self, actor_uri: str, to_be_unfollowing_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until in actor "{ actor_uri }" is not followed any more by actor "{ to_be_unfollowing_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_uri } is still followed by actor { to_be_unfollowing_uri}.', max_wait)


class AbstractFallbackFediverseNodeDriver(NodeDriver):
    """
    Abstract superclass of NodeDrivers that support all web server-side protocols but don't
    automate anything.
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_account_fields() -> list[TestPlanNodeAccountField]:
        return [ ROLE_ACCOUNT_FIELD, URI_ACCOUNT_FIELD, ACTOR_URI_ACCOUNT_FIELD ]


    # Python 3.12 @override
    @staticmethod
    def test_plan_node_non_existing_account_fields() -> list[TestPlanNodeNonExistingAccountField]:
        return [ ROLE_NON_EXISTING_ACCOUNT_FIELD, URI_NON_EXISTING_ACCOUNT_FIELD, ACTOR_URI_NON_EXISTING_ACCOUNT_FIELD ]


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        app = test_plan_node.parameter(APP_PAR)
        app_version = test_plan_node.parameter(APP_VERSION_PAR)
        hostname = test_plan_node.parameter(HOSTNAME_PAR)

        if not hostname:
            hostname = prompt_user(f'Enter the hostname for the Node of constellation role "{ rolename }" (node parameter "hostname"): ',
                                        parse_validate=hostname_validate)
        if not app:
            app = prompt_user(f'Enter the name of the app at constellation role "{ rolename }" and hostname "{ hostname }" (node parameter "app"): ',
                                   parse_validate=appname_validate)

        accounts : list[Account] = []
        if test_plan_node.accounts:
            for index, account_info in enumerate(test_plan_node.accounts):
                accounts.append(FallbackFediverseAccount.create_from_account_info_in_testplan(
                        account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Account { index }: '))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for index, non_existing_account_info in enumerate(test_plan_node.non_existing_accounts):
                non_existing_accounts.append(FallbackFediverseNonExistingAccount.create_from_non_existing_account_info_in_testplan(
                        non_existing_account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Non-existing account { index }: '))

        return (
            NodeConfiguration(
                self,
                cast(str, app),
                cast(str, app_version),
                hostname
            ),
            DefaultAccountManager(accounts, non_existing_accounts)
        )
