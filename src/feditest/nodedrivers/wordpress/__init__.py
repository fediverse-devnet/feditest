"""
"""

import time
from typing import cast

from feditest.nodedrivers import (
    Account,
    AccountManager,
    DefaultAccountManager,
    NodeConfiguration,
    NodeDriver,
    NonExistingAccount,
    APP_PAR,
    APP_VERSION_PAR,
    HOSTNAME_PAR
)
from feditest.nodedrivers.mastodon import (
    AccountOnNodeWithMastodonAPI,
    AuthenticatedMastodonApiClient,
    NodeWithMastodonAPI,
    NodeWithMastodonApiConfiguration
)
from feditest.protocols.fediverse import (
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD,
    FediverseNode,
    FediverseNonExistingAccount
)
from feditest.reporting import trace
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField, TestPlanNodeParameter
from feditest.utils import boolean_parse_validate, hostname_validate, prompt_user_parse_validate


VERIFY_API_TLS_CERTIFICATE_PAR = TestPlanNodeParameter(
    'verify_api_tls_certificate',
    """If set to false, accessing the Mastodon API will be performed without checking TLS certificates.""",
    validate=boolean_parse_validate
)

def _oauth_token_validate(candidate: str) -> str | None:
    """
    Validate a WordPress "Enable Mastodon Apps" app client API token. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if len(candidate)>10 else None


OAUTH_TOKEN_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'oauth_token',
        """OAuth token of a user so the "Enable Mastodon apps" API can be invoked.""",
        _oauth_token_validate
)


class WordPressAccount(AccountOnNodeWithMastodonAPI):
    """
    Compare with MastodonOAuthTokenAccount.
    """
    def __init__(self, role: str | None, userid: str, oauth_token: str | None, internal_userid: int = -1):
        """
        internal_userid: the number needed to identify the account for oauth token provisioning. There may be better ways
                         of doing this
        The oauth_token may be None. In which case we dynamically obtain one.
        """
        super().__init__(role, userid)
        self._oauth_token = oauth_token
        self._internal_userid = internal_userid
        self._mastodon_client: AuthenticatedMastodonApiClient | None = None # Allocated as needed


    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], context_msg: str = ''):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        userid = USERID_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        role = ROLE_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, context_msg)
        oauth_token = OAUTH_TOKEN_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        return WordPressAccount(role, userid, oauth_token)


    @property
    def mastodon_client(self) -> AuthenticatedMastodonApiClient:
        if self._mastodon_client is None:
            node = cast(NodeWithMastodonAPI, self._node)
            oauth_app = node._obtain_mastodon_oauth_app()
            oauth_token = self.oauth_token(oauth_app.client_id)
            trace(f'Logging into WordPress at "{ oauth_app.api_base_url }" with userid "{ self.userid }" with OAuth token "{ oauth_token }".')
            self._mastodon_client = AuthenticatedMastodonApiClient(oauth_app, self, oauth_token)
        return self._mastodon_client


    # Python 3.12 @override
    @property
    def internal_userid(self) -> int:
        if self._internal_userid >= 0:
            return self._internal_userid
        return self.account_dict['id']


    def oauth_token(self, oauth_client_id: str) -> str:
        """
        Helper to dynamically provision an OAuth token if we don't have one yet.
        """
        if not self._oauth_token:
            real_node = cast(WordPressPlusPluginsNode, self._node)
            self._oauth_token = real_node._provision_oauth_token_for(self, oauth_client_id)
        return self._oauth_token


class WordPressPlusPluginsNode(NodeWithMastodonAPI):
    """
    A Node running WordPress with the ActivityPub plugin.
    """
    def _provision_oauth_token_for(self, account: WordPressAccount, oauth_client_id: str) -> str:
        ret = prompt_user_parse_validate(f'Enter the OAuth token for the Mastodon API for user "{ account.userid  }"'
                                       + f' on constellation role "{ self.rolename }", OAuth client id "{ oauth_client_id }" (user field "{ OAUTH_TOKEN_ACCOUNT_FIELD }"): ',
                                       parse_validate=_oauth_token_validate)
        return ret


    # Python 3.12 @override
    def _run_poor_mans_cron(self) -> None:
        # Seems we need two HTTP GETs
        url = f'https://{ self.hostname }/wp-cron.php?doing_wp_cron'
        session = self._obtain_requests_session()

        # There must be a better way. But this seems to do it. 15 might be enough. 10 might not.
        for _ in range(20):
            time.sleep(1)
            trace('Triggering wp-cron at { url }')
            session.get(url)


class WordPressPlusPluginsSaasNodeDriver(NodeDriver):
    """
    Create a WordPress+plugins Node that already runs as Saas
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return [ APP_PAR, APP_VERSION_PAR, HOSTNAME_PAR, VERIFY_API_TLS_CERTIFICATE_PAR ]


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
        app = test_plan_node.parameter_or_raise(APP_PAR, { APP_PAR.name:  'WordPress+plugins' }) # Let user give a more descriptive name if they want to
        app_version = test_plan_node.parameter(APP_VERSION_PAR)
        hostname = test_plan_node.parameter_or_raise(HOSTNAME_PAR)
        verify_tls_certificate = test_plan_node.parameter_or_raise(VERIFY_API_TLS_CERTIFICATE_PAR, { VERIFY_API_TLS_CERTIFICATE_PAR.name: 'true' })

        if not hostname:
            hostname = prompt_user_parse_validate(f'Enter the hostname for the WordPress+plugins Node of constellation role "{ rolename }"'
                                                + f' (node parameter "{ HOSTNAME_PAR }"): ',
                                                parse_validate=hostname_validate)

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

        return (
            NodeWithMastodonApiConfiguration(
                node_driver=self,
                app=cast(str, app),
                app_version=cast(str, app_version),
                hostname=hostname,
                verify_tls_certificate=verify_tls_certificate
            ),
            DefaultAccountManager(accounts, non_existing_accounts)
        )


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> FediverseNode:
        return WordPressPlusPluginsNode(rolename, config, cast(AccountManager, account_manager))
