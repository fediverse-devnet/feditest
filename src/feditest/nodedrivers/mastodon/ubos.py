"""
"""

import re
import secrets
import string
import subprocess
from typing import Any, cast

from feditest.nodedrivers import (
    Account,
    NonExistingAccount,
    AccountManager,
    DefaultAccountManager,
    Node,
    NodeConfiguration,
    APP_PAR,
    APP_VERSION_PAR,
    HOSTNAME_PAR,
)
from feditest.nodedrivers.mastodon import (
    MastodonAccount,
    MastodonNode,
    MastodonUserPasswordAccount,
    NodeWithMastodonApiConfiguration,
    EMAIL_ACCOUNT_FIELD,
    OAUTH_TOKEN_ACCOUNT_FIELD,
    PASSWORD_ACCOUNT_FIELD,
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD
)
from feditest.nodedrivers.ubos import (
    UbosNodeConfiguration,
    UbosNodeDeployConfiguration,
    UbosNodeDriver,
    ADMIN_CREDENTIAL_PAR,
    ADMIN_EMAIL_PAR,
    ADMIN_USERID_PAR,
    ADMIN_USERNAME_PAR,
    APPCONFIGID_PAR,
    BACKUP_APPCONFIGID_PAR,
    BACKUPFILE_PAR,
    RSH_CMD_PAR,
    SITEID_PAR,
    START_DELAY_PAR,
    TLSCERT_PAR,
    TLSKEY_PAR
)
from feditest.protocols.fediverse import FediverseNonExistingAccount
from feditest.registry import registry_singleton
from feditest.reporting import error, trace
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField, TestPlanNodeParameterMalformedError


class MastodonUbosNodeConfiguration(UbosNodeDeployConfiguration, NodeWithMastodonApiConfiguration):
    def __init__(self,
        node_driver: 'MastodonUbosNodeDriver',
        siteid: str,
        appconfigid: str,
        appconfigjson: dict[str,Any],
        admin_userid: str,
        admin_username: str,
        admin_credential: str,
        admin_email: str,
        app: str,
        hostname: str, # Note: switched positions with app_version as it is required here
        app_version: str | None = None,
        tlskey: str | None = None,
        tlscert: str | None = None,
        start_delay: float = 0.0,
        rshcmd: str | None = None,
    ):
        super(UbosNodeDeployConfiguration,self).__init__(
            node_driver = node_driver,
            siteid = siteid,
            appconfigid = appconfigid,
            appconfigjson = appconfigjson,
            admin_userid = admin_userid,
            admin_username = admin_username,
            admin_credential = admin_credential,
            admin_email = admin_email,
            app = app,
            hostname = hostname,
            app_version = app_version,
            tlskey = tlskey,
            tlscert = tlscert,
            start_delay = start_delay,
            rshcmd = rshcmd,
        )
        # We do the initialization ourselves for the Mastodon part, so we avoid the common ancestor
        self._verify_tls_certificate = True


    # Python 3.12 @override
    @staticmethod
    def create_from_node_in_testplan(
        test_plan_node: TestPlanConstellationNode,
        node_driver1: 'UbosNodeDriver',
        appconfigjson: dict[str, Any],
        defaults: dict[str, str | None] | None = None
    ) -> 'UbosNodeConfiguration':
        """
        This is largely copied from the superclass.
        """
        node_driver = cast(MastodonUbosNodeDriver, node_driver1) # Make linter happy
        siteid = test_plan_node.parameter(SITEID_PAR, defaults=defaults) or UbosNodeConfiguration._generate_siteid()
        appconfigid = test_plan_node.parameter(APPCONFIGID_PAR, defaults=defaults) or UbosNodeConfiguration._generate_appconfigid()
        app = test_plan_node.parameter_or_raise(APP_PAR, defaults=defaults)
        hostname = test_plan_node.parameter(HOSTNAME_PAR) or registry_singleton().obtain_new_hostname(app)
        admin_userid = test_plan_node.parameter(ADMIN_USERID_PAR, defaults=defaults) or 'feditestadmin'
        admin_username = test_plan_node.parameter(ADMIN_USERNAME_PAR, defaults=defaults) or 'feditestadmin'
        admin_credential = test_plan_node.parameter(ADMIN_CREDENTIAL_PAR, defaults=defaults) or UbosNodeConfiguration._generate_credential()
        admin_email = test_plan_node.parameter(ADMIN_EMAIL_PAR, defaults=defaults) or f'{ admin_userid }@{ hostname }'
        start_delay_1 = test_plan_node.parameter(START_DELAY_PAR, defaults=defaults)
        if start_delay_1:
            if isinstance(float, start_delay_1):
                start_delay = cast(float, start_delay_1)
            else:
                start_delay = float(start_delay_1)
        else:
            start_delay = 10.0 # 10 sec should be good enough

        if test_plan_node.parameter(BACKUPFILE_PAR):
            raise TestPlanNodeParameterMalformedError(BACKUP_APPCONFIGID_PAR, ' must not be given for MastodonUbosNodeDriver')
        if test_plan_node.parameter(BACKUP_APPCONFIGID_PAR):
            raise TestPlanNodeParameterMalformedError(BACKUP_APPCONFIGID_PAR, ' must not be given for MastodonUbosNodeDriver')

        return MastodonUbosNodeConfiguration(
            node_driver = node_driver,
            siteid = siteid,
            appconfigid = appconfigid,
            appconfigjson = appconfigjson,
            admin_userid = admin_userid,
            admin_username = admin_username,
            admin_credential = admin_credential,
            admin_email = admin_email,
            app = app,
            hostname = hostname,
            app_version = test_plan_node.parameter(APP_VERSION_PAR, defaults=defaults),
            tlskey = test_plan_node.parameter(TLSKEY_PAR, defaults=defaults),
            tlscert = test_plan_node.parameter(TLSCERT_PAR, defaults=defaults),
            start_delay = start_delay,
            rshcmd = test_plan_node.parameter(RSH_CMD_PAR, defaults=defaults)
        )


    @property
    def verify_tls_certificate(self) -> bool:
        return True


class MastodonUbosAccountManager(DefaultAccountManager):
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

        result = self._invoke_tootctl(f'accounts create { userid } --email { useremail } --approve --confirmed --role=Owner')

        if result.returncode:
            error(f'Provisioniong new user { userid } on Mastodon Node { self._rolename } failed.')
            return None

        m = re.search( r'password:\s+([a-z0-9]+)', result.stdout )
        if not m:
            error('Failed to parse tootctl accounts create output:' + result.stdout)
            return None

        passwd = m.group(1)
        trace(f'New Mastodon user in role { role } on { self }: userid: "{ userid }", passwd: "{ passwd }", email: "{ useremail }".')
        return MastodonUserPasswordAccount(role, userid, passwd, useremail)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        # We just make it up
        userid = self._generate_candidate_userid()

        return FediverseNonExistingAccount(role, userid)


    def add_cert_to_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(MastodonUbosNodeDriver, self.node_driver)

        node_driver.add_cert_to_trust_store_via(root_cert, config.rshcmd)


    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self.config)
        node_driver = cast(MastodonUbosNodeDriver, self.node_driver)

        node_driver.remove_cert_from_trust_store_via(root_cert, config.rshcmd)


    def _generate_candidate_userid(self) -> str:
        """
        Given what we know about Mastodon's userids, generate a random one that might work.
        """
        # Do not use uppercase characters. The Mastodon API will not let you log on.
        chars = string.ascii_lowercase + string.digits
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
            for index, account_info in enumerate(test_plan_node.accounts):
                accounts.append(MastodonAccount.create_from_account_info_in_testplan(
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
                    "appid" : "mastodon",
                    "context" : "",
                    "customizationpoints" : {
                        "mastodon" : {
                            "singleusermode" : {
                                "value" : False
                            },
                            "allowed_private_addresses" : {
                                "value" : "192.168.1.1/16" # Allow testing in a Linux container
                            }
                        }
                    }
                },
                defaults = {
                    'app' : 'Mastodon'
                }),
            MastodonUbosAccountManager(accounts, non_existing_accounts)
        )

    # Python 3.12 @override
    def _instantiate_ubos_node(self, rolename: str, config: UbosNodeConfiguration, account_manager: AccountManager) -> Node:
        return MastodonUbosNode(rolename, config, account_manager)
