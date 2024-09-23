"""
"""

import re
from typing import cast

from feditest.nodedrivers.mastodon import (
    AccountOnNodeWithMastodonAPI,
    Mastodon, # Re-import from there to avoid duplicating the package import hackery
    MastodonOAuthApp,
    NodeWithMastodonAPI,
    NodeWithMastodonApiConfiguration
)
from feditest.protocols import (
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
from feditest.protocols.fediverse import FediverseNode
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeAccountField, TestPlanNodeNonExistingAccountField, TestPlanNodeParameter
from feditest.utils import boolean_parse_validate, hostname_validate


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


def _userid_validate(candidate: str) -> str | None:
    """
    Validate a WordPress user name. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if re.match(r'[a-zA-Z0-9_]', candidate) else None


USERID_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'userid',
        """Mastodon userid for a user (e.g. "joe") (required).""",
        _userid_validate
)
OAUTH_TOKEN_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'oauth_token',
        """OAuth token of a user so the "Enable Mastodon apps" API can be invoked.""",
        _oauth_token_validate
)
ROLE_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'role',
        """A symbolic name for the Account as used by tests (optional).""",
        lambda x: len(x)
)

USERID_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'userid',
        """Mastodon userid for a non-existing user (e.g. "joe")  (required).""",
        _userid_validate
)
ROLE_NON_EXISTING_ACCOUNT_FIELD = TestPlanNodeNonExistingAccountField(
        'role',
        """A symbolic name for the non-existing Account as used by tests (optional).""",
        lambda x: len(x)
)


class WordPressAccount(AccountOnNodeWithMastodonAPI):
    """
    Compare with MastodonOAuthTokenAccount.
    """
    def __init__(self, role: str | None, userid: str, oauth_token: str | None):
        """
        The oauth_token may be None. In which case we dynamically obtain one.
        """
        super().__init__(role, userid)
        self.userid = userid
        self.oauth_token = oauth_token


    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], node_driver: NodeDriver):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        userid = USERID_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, f'NodeDriver { node_driver }: ')
        role = ROLE_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, f'NodeDriver { node_driver }: ')

        oauth_token = OAUTH_TOKEN_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, f'NodeDriver { node_driver }: ')
        return WordPressAccount(role, userid, oauth_token)


    @property
    def actor_uri(self):
        return f'https://{ self.node.hostname }/author/{ self.userid }'


    def mastodon_user_client(self, node: NodeWithMastodonAPI) -> Mastodon:
        if self._mastodon_user_client is None:
            oauth_app = cast(MastodonOAuthApp,node._mastodon_oauth_app)
            self._ensure_oauth_token(node, oauth_app.client_id)
            client = Mastodon(
                client_id = oauth_app.client_id,
                client_secret=oauth_app.client_secret,
                access_token=self.oauth_token,
                api_base_url=oauth_app.api_base_url,
                session=oauth_app.session
            )
            self._mastodon_user_client = client
        return self._mastodon_user_client


    def _ensure_oauth_token(self, node: NodeWithMastodonAPI, oauth_client_id: str) -> None:
        """
        Helper to dynamically provision an OAuth token if we don't have one yet.
        """
        if self.oauth_token:
            return
        real_node = cast(WordPressPlusActivityPubPluginNode, node)
        self.oauth_token = real_node._provision_oauth_token_for(self.userid, oauth_client_id)


class WordPressNonExistingAccount(NonExistingAccount):
    def __init__(self, role: str | None, userid: str):
        super().__init__(role)
        self.userid = userid


    @staticmethod
    def create_from_non_existing_account_info_in_testplan(non_existing_account_info_in_testplan: dict[str, str | None], node_driver: NodeDriver):
        """
        Parses the information provided in an "non_existing_account" dict of TestPlanConstellationNode
        """
        userid = USERID_NON_EXISTING_ACCOUNT_FIELD.get_validate_from_or_raise(non_existing_account_info_in_testplan, f'NodeDriver { node_driver }: ')
        role = ROLE_ACCOUNT_FIELD.get_validate_from(non_existing_account_info_in_testplan, f'NodeDriver { node_driver }: ')

        return WordPressNonExistingAccount(role, userid)


    @property
    def webfinger_uri(self):
        return f'acct:{ self.userid }@{ self.node.hostname }'


    @property
    def actor_uri(self):
        return f'https://{ self.node.hostname }/users/{ self.userid }'


class WordPressPlusActivityPubPluginNode(NodeWithMastodonAPI):
    """
    A Node running WordPress with the ActivityPub plugin.
    """
    # Python 3.12 @override -- implement WordPress scheme
    def _actor_uri_to_userid(self, actor_uri: str) -> str:
        if m:= re.match('^https://([^/]+)/author/([^/]+)/?$', actor_uri):
            if m.group(1) == self._config.hostname:
                return m.group(2)
        raise ValueError( f'Cannot find actor at this node: { actor_uri }' )


    def _provision_oauth_token_for(self, userid: str, oauth_client_id: str):
        ret = self.prompt_user(f'Enter the OAuth token for the Mastodon API for user "{ userid }"'
                              + f' on constellation role "{ self.rolename }" (user field "{ OAUTH_TOKEN_ACCOUNT_FIELD }"): ',
                              parse_validate=_oauth_token_validate)
        return ret


class WordPressPlusActivityPubPluginSaasNodeDriver(NodeDriver):
    """
    Create a WordPress + ActivityPubPlugin Node that already runs as Saas
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
        app = test_plan_node.parameter_or_raise(APP_PAR, { APP_PAR.name:  'WordPress + ActivityPub plugin' }) # Let user give a more descriptive name if they want to
        app_version = test_plan_node.parameter(APP_VERSION_PAR)
        hostname = test_plan_node.parameter_or_raise(HOSTNAME_PAR)
        verify_tls_certificate = test_plan_node.parameter_or_raise(VERIFY_API_TLS_CERTIFICATE_PAR, { VERIFY_API_TLS_CERTIFICATE_PAR.name: 'true' })

        if not hostname:
            hostname = self.prompt_user(f'Enter the hostname for the WordPress + ActivityPub plugin Node of constellation role "{ rolename }"'
                                        + f' (node parameter "{ HOSTNAME_PAR }"): ',
                                        parse_validate=hostname_validate)

        accounts : list[Account] = []
        if test_plan_node.accounts:
            for account_info in test_plan_node.accounts:
                accounts.append(WordPressAccount.create_from_account_info_in_testplan(account_info, self))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for non_existing_account_info in test_plan_node.non_existing_accounts:
                non_existing_accounts.append(WordPressNonExistingAccount.create_from_non_existing_account_info_in_testplan(non_existing_account_info, self))

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
        return WordPressPlusActivityPubPluginNode(rolename, config, cast(AccountManager, account_manager))
