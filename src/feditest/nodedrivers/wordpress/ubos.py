"""
"""

from typing import Any, cast

from feditest import registry
from feditest.nodedrivers.mastodon import (
    MastodonAccount,
    MastodonNonExistingAccount,
    EMAIL_ACCOUNT_FIELD,
    OAUTH_TOKEN_ACCOUNT_FIELD,
    PASSWORD_ACCOUNT_FIELD,
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD
)
from feditest.nodedrivers.mastodon.ubos import MastodonUbosAccountManager, MastodonUbosNodeConfiguration
from feditest.nodedrivers.wordpress import WordPressPlusActivityPubPluginNode
from feditest.protocols import (
    Account,
    NonExistingAccount,
    AccountManager,
    Node,
    NodeConfiguration
)
from feditest.reporting import error, trace
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField
from feditest.ubos import UbosNodeConfiguration, UbosNodeDriver


class WordPressPlusActivityPubPluginUbosNode(WordPressPlusActivityPubPluginNode):
    """
    A WordPress + ActivityPubPlugin Node running on UBOS. This means we know how to interact with it exactly.
    """
    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        trace('Provisioning new user')
        raise NotImplementedError('FIXME')


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        raise NotImplementedError('FIXME')


    def add_cert_to_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(WordPressPlusActivityPubPluginUbosNodeDriver, self.node_driver)

        node_driver.add_cert_to_trust_store_via(root_cert, config.rshcmd)


    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(WordPressPlusActivityPubPluginUbosNodeDriver, self.node_driver)

        node_driver.remove_cert_from_trust_store_via(root_cert, config.rshcmd)


class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
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
        accounts : list[Account] = []
        if test_plan_node.accounts:
            for account_info in test_plan_node.accounts:
                accounts.append(MastodonAccount.create_from_account_info_in_testplan(account_info, self))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for non_existing_account_info in test_plan_node.non_existing_accounts:
                non_existing_accounts.append(MastodonNonExistingAccount.create_from_non_existing_account_info_in_testplan(non_existing_account_info, self))

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
                        "wordpress-plugin-webfinger"
                    ],
                    "context" : ""
                },
                defaults = {
                    'app' : 'WordPress + ActivityPub plugin'
                }),
            MastodonUbosAccountManager(accounts, non_existing_accounts)
        )

    # Python 3.12 @override
    def _instantiate_ubos_node(self, rolename: str, config: UbosNodeConfiguration, account_manager: AccountManager) -> Node:
        return WordPressPlusActivityPubPluginUbosNode(rolename, config, account_manager)
