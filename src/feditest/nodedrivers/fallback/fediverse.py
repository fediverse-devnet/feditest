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
from feditest.protocols.fediverse import (
    userid_validate,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD,
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    FediverseAccount,
    FediverseNode,
    FediverseNonExistingAccount
)
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField
from feditest.utils import appname_validate, boolean_parse_validate, hostname_validate, https_uri_validate, prompt_user


class FallbackFediverseNode(FediverseNode):
    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        userid = cast(str, prompt_user(
                f'Node { self }:'
                + f' for the account with account role "{ role }", enter its userid (the user part of the acct: URI) (node account field "{ USERID_ACCOUNT_FIELD.name }"): ',
                parse_validate=userid_validate))
        return FediverseAccount(role, userid)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        userid = cast(str, prompt_user(
                f'Node { self }:'
                + f' provide the userid of a non-existing account with account role "{ role }" (the user part of the with acct: IRO) (node non_existing_account field "{ USERID_NON_EXISTING_ACCOUNT_FIELD.name }"): ',
                parse_validate=https_uri_validate))
        return FediverseNonExistingAccount(role, userid)


    # Python 3.12 @override
    def obtain_actor_acct_uri(self, rolename: str | None = None) -> str:
        if not self.account_manager:
            raise OutOfAccountsException('No AccountManager set')
        account = cast(FediverseAccount, self.account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri


    # Python 3.12 @override
    def obtain_non_existing_actor_acct_uri(self, rolename: str | None = None ) -> str:
        if not self.account_manager:
            raise OutOfAccountsException('No AccountManager set')
        non_account = cast(FediverseNonExistingAccount, self.account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.actor_acct_uri


    # Python 3.12 @override
    def make_create_note(self, actor_acct_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        if deliver_to :
            return cast(str, prompt_user(
                    f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" create a Note'
                    + ' to be delivered to ' + ", ".join(deliver_to)
                    + ' and enter its URI when created.'
                    + f' Note content:"""\n{ content }\n"""' ))
        return cast(str, prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" create a Note'
                + ' and enter its URI when created.'
                + f' Note content:"""\n{ content }\n"""' ))



    # Python 3.12 @override
    def make_announce_object(self, actor_acct_uri, to_be_announced_object_uri: str) -> str:
        return cast(str, prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" boost "{ to_be_announced_object_uri }"'
                + ' and enter the Announce object\'s local URI:',
                parse_validate=https_uri_validate))


    # Python 3.12 @override
    def make_reply_note(self, actor_acct_uri, to_be_replied_to_object_uri: str, reply_content: str) -> str:
        return cast(str, prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" reply to object with "{ to_be_replied_to_object_uri }"'
                + ' and enter the Announce object\'s URI when created.'
                + f' Reply content:"""\n{ reply_content }\n"""' ))


    # Python 3.12 @override
    def make_follow(self, actor_acct_uri: str, to_follow_actor_acct_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" follow actor "{ to_follow_actor_acct_uri }"'
                + ' and hit return when done.')


    # We leave the NotImplementedByNodeError raised by the superclass for all other follow-related actions
    # until we have a better idea :-)

    # Python 3.12 @override
    def wait_until_actor_is_following_actor(self, actor_acct_uri: str, to_be_followed_actor_acct_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until actor "{ actor_acct_uri }" is following actor "{ to_be_followed_actor_acct_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_acct_uri } not following actor { to_be_followed_actor_acct_uri}.', max_wait)


    # Python 3.12 @override
    def wait_until_actor_is_followed_by_actor(self, actor_acct_uri: str, to_be_following_actor_acct_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until actor "{ actor_acct_uri }" is followed by actor "{ to_be_following_actor_acct_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_acct_uri } not followed by actor { to_be_following_actor_acct_uri}.', max_wait)


    # Python 3.12 @override
    def wait_until_actor_is_unfollowing_actor(self, actor_acct_uri: str, to_be_unfollowed_actor_acct_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until actor "{ actor_acct_uri }" is not following any more actor "{ to_be_unfollowed_actor_acct_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_acct_uri } still following actor { to_be_unfollowed_actor_acct_uri}.', max_wait)


    # Python 3.12 @override
    def wait_until_actor_is_unfollowed_by_actor(self, actor_acct_uri: str, to_be_unfollowing_actor_acct_uri: str, max_wait: float = 5.) -> None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", wait until in actor "{ actor_acct_uri }" is not followed any more by actor "{ to_be_unfollowing_actor_acct_uri }"'
                + ' and enter "true"; "false" if it didn\'t happen.',
                parse_validate=boolean_parse_validate)
        if not answer:
            raise TimeoutException(f'Actor { actor_acct_uri } is still followed by actor { to_be_unfollowing_actor_acct_uri}.', max_wait)


class AbstractFallbackFediverseNodeDriver(NodeDriver):
    """
    Abstract superclass of NodeDrivers that support all web server-side protocols but don't
    automate anything.
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_account_fields() -> list[TestPlanNodeAccountField]:
        return [ ROLE_ACCOUNT_FIELD, USERID_ACCOUNT_FIELD ]


    # Python 3.12 @override
    @staticmethod
    def test_plan_node_non_existing_account_fields() -> list[TestPlanNodeNonExistingAccountField]:
        return [ ROLE_NON_EXISTING_ACCOUNT_FIELD, USERID_NON_EXISTING_ACCOUNT_FIELD ]


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
                accounts.append(FediverseAccount.create_from_account_info_in_testplan(
                        account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Account { index }: '))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for index, non_existing_account_info in enumerate(test_plan_node.non_existing_accounts):
                non_existing_accounts.append(FediverseNonExistingAccount.create_from_non_existing_account_info_in_testplan(
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
