"""
"""

from typing import Final, cast

from feditest.accountmanager import Account, AccountManager, DefaultAccountManager, InvalidAccountSpecificationException, InvalidNonExistingAccountSpecificationException, NonExistingAccount
from feditest.protocols import NodeConfiguration, NodeDriver
from feditest.protocols.webfinger import WebFingerServer
from feditest.utils import http_https_acct_uri_validate

ROLE_KEY: Final[str] = 'role'
URI_KEY: Final[str] = 'uri'

"""
Pre-existing or known non-existing accounts in TestPlans are specified as follows:
* URI_KEY: WebFinger resource, e.g. acct:joe@example.com or https://example.com/
* ROLE_KEY: optional account role
"""

class FallbackWebFingerAccount(Account):
    def __init__(self, account_info_in_testplan: dict[str,str], node_driver: NodeDriver):
        if URI_KEY not in account_info_in_testplan:
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Missing field: { URI_KEY }.')
        uri = account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')
        self.uri = uri
        self.role = account_info_in_testplan.get(ROLE_KEY) # may or may not be there


class FallbackWebFingerNonExistingAccount(NonExistingAccount):
    def __init__(self, non_existing_account_info_in_testplan: dict[str,str], node_driver: NodeDriver):
        if URI_KEY not in non_existing_account_info_in_testplan:
            raise InvalidNonExistingAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Missing field: { URI_KEY }.')
        uri = non_existing_account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')
        self.uri = uri
        self.role = non_existing_account_info_in_testplan.get(ROLE_KEY) # may or may not be there


class FallbackWebFingerServer(WebFingerServer):
    def __init__(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None = None):
        super().__init__(rolename, config)
        self._account_manager = account_manager if account_manager else DefaultAccountManager(config)


    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        account = cast(FallbackWebFingerAccount, self._account_manager.obtain_account_by_role(rolename))
        return account.uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        non_account = cast(FallbackWebFingerNonExistingAccount, self._account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.uri

