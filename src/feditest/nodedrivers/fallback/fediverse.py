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
from feditest.utils import (
    acct_uri_list_validate,
    acct_uri_validate,
    appname_validate,
    boolean_parse_validate,
    hostname_validate,
    https_uri_list_validate,
    https_uri_validate,
    prompt_user,
    prompt_user_parse_validate
)


class FallbackFediverseNode(FediverseNode):
    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        userid = prompt_user_parse_validate(
                f'Node { self }:'
                + f' for the account with account role "{ role }", enter its userid (the user part of the acct: URI) (node account field "{ USERID_ACCOUNT_FIELD.name }"): ',
                parse_validate=userid_validate)
        return FediverseAccount(role, userid)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        userid = prompt_user_parse_validate(
                f'Node { self }:'
                + f' provide the userid of a non-existing account with account role "{ role }" (the user part of the with acct: URI) (node non_existing_account field "{ USERID_NON_EXISTING_ACCOUNT_FIELD.name }"): ',
                parse_validate=userid_validate)
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
    def make_follow(self, actor_acct_uri: str, to_follow_actor_acct_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" follow actor "{ to_follow_actor_acct_uri }"'
                + ' and hit return when done.')


    def make_unfollow(self, actor_acct_uri: str, following_actor_acct_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" unfollow actor "{ following_actor_acct_uri }"'
                + ' and hit return when done.')


    # Python 3.12 @override
    def actor_is_following_actor(self, actor_acct_uri: str, leader_actor_acct_uri: str) -> bool:
        answer = prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", is actor "{ actor_acct_uri }" following actor "{ leader_actor_acct_uri }"?'
                + ' Enter "true" or "false".',
                parse_validate=boolean_parse_validate)
        return answer


    # Python 3.12 @override
    def actor_is_followed_by_actor(self, actor_acct_uri: str, follower_actor_acct_uri: str) -> bool:
        answer = prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", is actor "{ actor_acct_uri }" being followed by actor "{ follower_actor_acct_uri }"?'
                + ' Enter "true" or "false".',
                parse_validate=boolean_parse_validate)
        return answer

    # All other follow-related methods: We leave the NotImplementedByNodeError raised by the superclass until we have a better idea :-)

    # Python 3.12 @override
    def make_create_note(self, actor_acct_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        if deliver_to :
            return prompt_user_parse_validate(
                    f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" create a Note'
                    + ' to be delivered to ' + ", ".join(deliver_to)
                    + ' and enter its URI when created.'
                    + f' Note content:"""\n{ content }\n"""',
                parse_validate=https_uri_validate)
        return prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" create a Note'
                + ' and enter its URI when created.'
                + f' Note content:"""\n{ content }\n"""',
                parse_validate=https_uri_validate)


    # Python 3.12 @override
    def update_note(self, actor_acct_uri: str, note_uri: str, new_content: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" update the note at "{ note_uri }"'
                + ' with new content:"""\n{ new_content }\n"""'
                + ' and hit return when done.')


    # Python 3.12 @override
    def delete_object(self, actor_acct_uri: str, object_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" delete the object at "{ object_uri }"'
                + ' and hit return when done.')


    # Python 3.12 @override
    def make_reply_note(self, actor_acct_uri, to_be_replied_to_object_uri: str, reply_content: str) -> str:
        return prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" reply to object with "{ to_be_replied_to_object_uri }"'
                + ' and enter the reply note\'s URI when created.'
                + f' Reply content:"""\n{ reply_content }\n"""',
                parse_validate=https_uri_validate)


    # Python 3.12 @override
    def like_object(self, actor_acct_uri: str, object_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" like the object at "{ object_uri }"'
                + ' and hit return when done.')


    # Python 3.12 @override
    def unlike_object(self, actor_acct_uri: str, object_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" unlike the object at "{ object_uri }"'
                + ' and hit return when done.')


    # Python 3.12 @override
    def announce_object(self, actor_acct_uri: str, object_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" announce/reblog/boost the object at "{ object_uri }"'
                + ' and hit return when done.')


    # Python 3.12 @override
    def unannounce_object(self, actor_acct_uri: str, object_uri: str) -> None:
        prompt_user(
                f'On FediverseNode "{ self.hostname }", make actor "{ actor_acct_uri }" unannounce/undo reblog/undo boost the object at "{ object_uri }"'
                + ' and hit return when done.')


    # Python 3.12 @override
    def actor_has_received_object(self, actor_acct_uri: str, object_uri: str) -> str | None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", has actor "{ actor_acct_uri }" received the object "{ object_uri }"?'
                + ' Enter the content of the object, or leave empty if it didn\'t happen.')
        return answer if answer else None


    # Python 3.12 @override
    def note_content(self, actor_acct_uri: str, note_uri: str) -> str | None:
        answer = prompt_user(
                f'On FediverseNode "{ self.hostname }", have actor "{ actor_acct_uri }" access note "{ note_uri }" and enter its content.')
        return answer if answer else None


    # Python 3.12 @override
    def object_author(self, actor_acct_uri: str, object_uri: str) -> str | None:
        answer = prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", have actor "{ actor_acct_uri }" access object "{ object_uri }" and enter the acct URI of the object\'s author.',
                parse_validate=acct_uri_validate)
        return answer


    # Python 3.12 @override
    def direct_replies_to_object(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        answer = prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", have actor "{ actor_acct_uri }" access object "{ object_uri }"'
                + ' and enter the https URIs of all objects that directly reply to it (space-separated list).',
                parse_validate=https_uri_list_validate)
        return answer.split()


    # Python 3.12 @override
    def object_likers(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        answer = prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", have actor "{ actor_acct_uri }" access object "{ object_uri }"'
                + ' and enter the acct URIs of all accounts that like it (space-separated list).',
                parse_validate=acct_uri_list_validate)
        return answer.split()


    # Python 3.12 @override
    def object_announcers(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        answer = prompt_user_parse_validate(
                f'On FediverseNode "{ self.hostname }", have actor "{ actor_acct_uri }" access object "{ object_uri }"'
                + ' and enter the acct URIs of all accounts that have announced/reblogged/boosted it (space-separated list).',
                parse_validate=acct_uri_list_validate)
        return answer.split()


# From WebFingerServer

    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(FediverseAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        non_account = cast(FediverseNonExistingAccount, account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.actor_acct_uri

    # Not implemented:
    # def obtain_account_identifier_requiring_percent_encoding(self, rolename: str | None = None) -> str:
    # def override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):


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
            hostname = prompt_user_parse_validate(
                    f'Enter the hostname for the Node of constellation role "{ rolename }" (node parameter "hostname"): ',
                    parse_validate=hostname_validate)
        if not app:
            app = prompt_user_parse_validate(
                    f'Enter the name of the app at constellation role "{ rolename }" and hostname "{ hostname }" (node parameter "app"): ',
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
