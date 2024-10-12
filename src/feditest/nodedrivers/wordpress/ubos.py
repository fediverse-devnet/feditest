"""
"""

import os
from typing import cast

from feditest.nodedrivers import (
    Account,
    AccountManager,
    DefaultAccountManager,
    NonExistingAccount,
    Node,
    NodeConfiguration
)
from feditest.nodedrivers.mastodon.ubos import MastodonUbosNodeConfiguration
from feditest.nodedrivers.ubos import UbosNodeConfiguration, UbosNodeDriver
from feditest.nodedrivers.wordpress import (
    OAUTH_TOKEN_ACCOUNT_FIELD,
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD,
    WordPressAccount,
    WordPressPlusPluginsNode
)
from feditest.protocols.fediverse import FediverseNonExistingAccount
from feditest.reporting import trace
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField



class WordPressUbosAccountManager(DefaultAccountManager):
    """
    Knows how to provision new accounts in WordPress
    """
    # Python 3.12 @override
    def set_node(self, node: Node) -> None:
        """
        We override this so we can insert the admin account in the list of accounts, now that the Node has been instantiated.
        """
        super().set_node(node)

        if not self._accounts_allocated_to_role and not self._accounts_not_allocated_to_role:
            config = cast(UbosNodeConfiguration, node.config)
            admin_account = WordPressAccount(None, config.admin_userid, None, 1) # We know this is account with internal identifier 1
            admin_account.set_node(node)
            self._accounts_not_allocated_to_role.append(admin_account)


class WordPressPlusPluginsUbosNode(WordPressPlusPluginsNode):
    """
    A WordPress+plugins Node running on UBOS. This means we know how to interact with it exactly.
    """
    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        trace('Provisioning new user')
        raise NotImplementedError('FIXME')


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        raise NotImplementedError('FIXME')


    def add_cert_to_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(WordPressPlusPluginsUbosNodeDriver, self.node_driver)

        node_driver.add_cert_to_trust_store_via(root_cert, config.rshcmd)


    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(WordPressPlusPluginsUbosNodeDriver, self.node_driver)

        node_driver.remove_cert_from_trust_store_via(root_cert, config.rshcmd)


    # Python 3.12 @override
    def _provision_oauth_token_for(self, account: WordPressAccount, oauth_client_id: str) -> str :
        # Code from here: https://wordpress.org/support/topic/programmatically-obtaining-oauth-token-for-testing/
        # $desired_token = '123';
        # $user_id = 1;
        # $oauth = new Enable_Mastodon_Apps\Mastodon_OAuth();
        # $oauth->get_token_storage()->setAccessToken( $desired_token, $app->get_client_id(), $user_id, time() + HOUR_IN_SECONDS, $app->get_scopes() );

        trace(f'Provisioning OAuth token on {self} for user with name="{ account.userid }".')
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(WordPressPlusPluginsUbosNodeDriver, self.node_driver)

        token = os.urandom(16).hex()
        php_script = f"""
<?php
$_SERVER['HTTP_HOST'] = '{ self.hostname }';

include 'wp-load.php';

$oauth = new Enable_Mastodon_Apps\\Mastodon_OAuth();
$oauth->get_token_storage()->setAccessToken( "{ token }", "{ oauth_client_id }", { account.internal_userid }, time() + HOUR_IN_SECONDS, 'read write follow push' );
"""
        dir = f'/ubos/http/sites/{ config.siteid }'
        cmd = f'cd { dir } && sudo sudo -u http php' # from user ubosdev -> root -> http

        trace( f'PHP script is "{ php_script }"')
        result = node_driver._exec_shell(cmd, config.rshcmd, stdin_content=php_script, capture_output=True)
        if result.returncode:
            raise Exception(self, f'Failed to create OAuth token for user with id="{ account.userid }", cmd="{ cmd }", stdout="{ result.stdout}", stderr="{ result.stderr }"')
        return token


class WordPressPlusPluginsUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_account_fields() -> list[TestPlanNodeAccountField]:
        return [ USERID_ACCOUNT_FIELD, OAUTH_TOKEN_ACCOUNT_FIELD, ROLE_ACCOUNT_FIELD ]


    # Python 3.12 @override
    @staticmethod
    def test_plan_node_non_existing_account_fields() -> list[TestPlanNodeNonExistingAccountField]:
        return [ USERID_NON_EXISTING_ACCOUNT_FIELD, ROLE_NON_EXISTING_ACCOUNT_FIELD ]


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        accounts : list[Account] = []
        if test_plan_node.accounts:
            for index, account_info in enumerate(test_plan_node.accounts):
                accounts.append(WordPressAccount.create_from_account_info_in_testplan(
                        account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Account { index }: '))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for index, non_existing_account_info in enumerate(test_plan_node.non_existing_accounts):
                non_existing_accounts.append(FediverseNonExistingAccount.create_from_non_existing_account_info_in_testplan(
                        non_existing_account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Non-existing account { index }: '))

        # Once has the Node has been instantiated (we can't do that here yet): if the user did not specify at least one Account, we add the admin account

        return (
            MastodonUbosNodeConfiguration.create_from_node_in_testplan(
                test_plan_node,
                self,
                appconfigjson = {
                    "appid" : "wordpress",
                    "accessoryids" : [
                        "wordpress-plugin-activitypub",
                        "wordpress-plugin-enable-mastodon-apps",
                        "wordpress-plugin-friends",
                        "wordpress-plugin-webfinger"
                    ],
                    "context" : "",
                    "customizationpoints" : {
                        "wordpress" : {
                            "disablessrfprotection" : {
                                "value" : True
                            }
                        }
                    }
                },
                defaults = {
                    'app' : 'WordPress+plugins'
                }),
            WordPressUbosAccountManager(accounts, non_existing_accounts)
        )

    # Python 3.12 @override
    def _instantiate_ubos_node(self, rolename: str, config: UbosNodeConfiguration, account_manager: AccountManager) -> Node:
        return WordPressPlusPluginsUbosNode(rolename, config, account_manager)
