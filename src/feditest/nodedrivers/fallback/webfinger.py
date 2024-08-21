"""
"""

from typing import Any, Final

from feditest.account import Account, AccountManager, DefaultAccountManager, InvalidAccountSpecificationException, InvalidNonExistingAccountSpecificationException, NonExistingAccount
from feditest.protocols import NodeDriver
from feditest.protocols.webfinger import WebFingerServer
from feditest.testplan import TestPlanConstellationNode
from feditest.utils import http_https_acct_uri_validate

ROLE_KEY: Final[str] = 'role'
URI_KEY: Final[str] = 'uri'

"""
Pre-existing or known non-existing accounts in TestPlans are specified as follows:
* URI_KEY: WebFinger resource, e.g. acct:joe@example.com or https://example.com/
* ROLE_KEY: optional account role
"""

class FallbackWebfingerAccount(Account):
    def __init__(self, account_info_in_testplan: dict[str,str], node_driver: NodeDriver):
        if URI_KEY not in account_info_in_testplan:
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Missing field: { URI_KEY }.')
        uri = account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')
        self.uri = uri
        self.role = account_info_in_testplan.get(ROLE_KEY) # may or may not be there


class FallbackWebfingerNonExistingAccount(NonExistingAccount):
    def __init__(self, non_existing_account_info_in_testplan: dict[str,str], node_driver: NodeDriver):
        if URI_KEY not in non_existing_account_info_in_testplan:
            raise InvalidNonExistingAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Missing field: { URI_KEY }.'))
        uri = non_existing_account_info_in_testplan[URI_KEY]
        if not http_https_acct_uri_validate(uri):
            raise InvalidAccountSpecificationException(non_existing_account_info_in_testplan, node_driver, f'Field { URI_KEY } must be acct, http or https URI, is: "{ uri }".')
        self.uri = uri
        self.role = non_existing_account_info_in_testplan.get(ROLE_KEY) # may or may not be there


class FallbackWebFingerServer(WebFingerServer):
    @staticmethod
    def create(
        rolename: str,
        parameters: dict[str,Any],
        node_driver: NodeDriver,
        test_plan_node: TestPlanConstellationNode
    ):
        accounts : list[Account] = []
        if test_plan_node.accounts:
            for account_info in test_plan_node.accounts:
                accounts.append(FallbackWebfingerAccount(account_info, node_driver))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for non_existing_account_info in test_plan_node.non_existing_accounts:
                non_existing_accounts.append(FallbackWebfingerNonExistingAccount(non_existing_account_info, node_driver))

        account_manager = DefaultAccountManager(accounts, non_existing_accounts)
        return FallbackWebFingerServer(rolename, parameters, node_driver, account_manager)


    def __init__(self,
        rolename: str,
        parameters: dict[str,Any],
        node_driver: NodeDriver,
        account_manager: AccountManager
    ):
        super().__init__(rolename, parameters, node_driver)
        self._account_manager = account_manager


    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        account: FallbackWebfingerAccount = self._account_manager.obtain_account_by_role(rolename)
        return account.uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        non_account: FallbackWebfingerNonExistingAccount = self._account_manager.obtain_non_existing_account_by_role(rolename)
        return non_account.uri


