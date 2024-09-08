"""
"""

import re
import secrets
import string
import subprocess
from typing import cast

from feditest.nodedrivers.mastodon import MastodonNode, MastodonAccount, MastodonUserPasswordAccount, MastodonNonExistingAccount
from feditest.protocols import Account, NonExistingAccount, AccountManager, DefaultAccountManager, Node, NodeConfiguration
from feditest.reporting import error, trace
from feditest.testplan import TestPlanConstellationNode
from feditest.ubos import UbosNodeConfiguration, UbosNodeDriver


class UbosMastodonAccountManager(DefaultAccountManager):
    """
    Knows how to provision new accounts in Mastodon
    """
    # Python 3.12 @override
    def set_node(self, node: Node) -> None:
        """
        We override this so we can insert the admin account in the list of accounts, now that the Node has been instantiated.
        """
        super().set_node(node)

        if not self._accounts_allocated_to_role and not self._accounts_not_allocated_to_role:
            config = cast(UbosNodeConfiguration, node.config)
            admin_account = MastodonUserPasswordAccount(None, config.admin_userid, config.admin_credential, config.admin_email)
            admin_account.set_node(node)
            self._accounts_not_allocated_to_role.append(admin_account)


class MastodonUbosNode(MastodonNode):
    """
    A Mastodon Node running on UBOS. This means we know how to interact with it exactly.
    """
    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        trace('Provisioning new user')
        userid = self._generate_candidate_userid()
        useremail = f'{ userid }@localhost' # Mastodon checks that the host exists, so we pick localhost

        result = self._invoke_tootctl(f'accounts create { userid } --email { useremail }')

        if result.returncode:
            error(f'Provisioniong new user { userid } on Mastodon Node { self._rolename } failed.')
            return None

        m = re.search( r'password:\s+([a-z0-9]+)', result.stdout )
        if not m:
            error('Failed to parse tootctl accounts create output:' + result.stdout)
            return None

        passwd = m.group(1)
        return MastodonUserPasswordAccount(role, userid, passwd, useremail)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        # We just make it up
        userid = self._generate_candidate_userid()

        return MastodonNonExistingAccount(role, userid)


    def add_cert_to_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(MastodonUbosNodeDriver, self.node_driver)

        node_driver.add_cert_to_trust_store(root_cert, config.rshcmd)


    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(MastodonUbosNodeDriver, self.node_driver)

        node_driver.remove_cert_from_trust_store(root_cert, config.rshcmd)


    def _generate_candidate_userid(self) -> str:
        """
        Given what we know about Mastodon's userids, generate a random one that might work.
        """
        chars = string.ascii_letters + string.digits
        userid = ''.join(secrets.choice(chars) for i in range(8))
        return userid


    def _invoke_tootctl(self, args: str) -> subprocess.CompletedProcess:
        config = cast(UbosNodeConfiguration, self.config)

        cmd = f'cd /ubos/lib/mastodon/{ config.appconfigid }/mastodon'
        cmd += ' && sudo RAILS_ENV=production bin/tootctl ' # This needs to be run as root, because .env.production is not world-readable
        cmd += args

        node_driver = cast(MastodonUbosNodeDriver, self.node_driver)
        ret = node_driver._exec_shell(cmd, config.rshcmd, capture_output=True)
        return ret


class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
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
            UbosNodeConfiguration.create_from_node_in_testplan(
                test_plan_node,
                self,
                appconfigjson = {
                    "appid" : "mastodon",
                    "context" : "",
                    "customizationpoints" : {
                        "mastodon" : {
                            "singleusermode" : {
                                "value" : False
                            }
                        }
                    }
                },
                defaults = {
                    'app' : 'Mastodon'
                }),
            UbosMastodonAccountManager(accounts, non_existing_accounts)
        )

    # Python 3.12 @override
    def _instantiate_ubos_node(self, rolename: str, config: UbosNodeConfiguration, account_manager: AccountManager) -> Node:
        return MastodonUbosNode(rolename, config, account_manager)
