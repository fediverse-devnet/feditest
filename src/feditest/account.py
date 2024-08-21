"""
Accounts on a Node.
"""

from abc import ABC, abstractmethod

from feditest.protocols import NodeDriver


class Account(ABC):
    """
    The notion of an existing account on a Node. As different Nodes have different ideas about
    what they know about an Account, this is an entirey abstract base class here.
    """
    def __init__(self, role: str):
        self.role = role


class NonExistingAccount(ABC):
    """
    The notion of a non-existing account on a Node. As different Nodes have different ideas about
    what they know about an Account, this is an entirey abstract base class here.
    """
    def __init__(self, role: str):
        self.role = role


class InvalidAccountSpecificationException(Exception):
    """
    Thrown if an account specification given in a TestPlan does not have sufficient information
    to be used as an Account for a Node instantiated by this NodeDriver.
    """
    def __init__(self, account_info_from_testplan: dict[str, str], node_driver: NodeDriver, msg: str):
        super().__init__(f'Invalid account specification for NodeDriver { node_driver }: { msg }')


class InvalidNonExistingAccountSpecificationException(Exception):
    """
    Thrown if a non-existing account specification given in a TestPlan does not have sufficient information
    to be used as an NonExistingAccount for a Node instantiated by this NodeDriver.
    """
    def __init__(self, non_existing_account_info_from_testplan: dict[str, str], node_driver: NodeDriver, msg: str):
        super().__init__(f'Invalid non-existing account specification for NodeDriver { node_driver }: { msg }')


class OutOfAccountsException(Exception):
    """
    Thrown if another Account was requested, but no additional Account was known or could be
    provisionined.
    """


class OutOfNonExistingAccountsException(Exception):
    """
    Thrown if another NonExistingAccount was requested, but no additional NonExistingAccount
    was known or could be provisionined.
    """


class AccountManager(ABC):
    """
    Manages accounts on a Node. It can be implemented in a variety of ways, including
    being a facade for the Node's API, or returning only Accounts pre-allocated in the
    TestPlan, or dynamically provisioning accounts etc.
    """
    @abstractmethod
    def obtain_account_by_role(self, role: str | None = None) -> Account:
        """
        If this method is invoked with the same role twice, it returns
        the same Account. May raise OutOfAccountsException.
        """
        ...


    @abstractmethod
    def obtain_non_existing_account_by_role(self, role: str | None = None) -> NonExistingAccount:
        """
        If this method is invoked with the same role twice, it returns
        the same NonExistingAccount. May raise OutOfNonExistingAccountsException.
        """
        ...


class DefaultAccountManager(AccountManager):
    """
    An AccountManager implementation that returns the pre-allocated Accounts, and
    has an empty method to dynamically provision new Accounts, which can be implemented
    by subclasses.
    """
    def __init__(self, initial_accounts: list[Account], initial_non_existing_accounts: list[NonExistingAccount]):
        """
        Provide the accounts and non-existing-accounts that are known to exist/not exist
        when the Node is provisioned.

        _accounts_with_role may grow during operation, because:
          * new accounts may be provisioned dynamically
          * accounts initially without role get a role associated with them, so they are removed from
            _accounts_without_role and put here
        """
        self._accounts_allocated_to_role = { account.role : account for account in initial_accounts if account.role }
        self._accounts_not_allocated_to_role = [ account for account in initial_accounts if not account.role ]

        self._non_existing_accounts_allocated_to_role = { non_account.role : non_account for non_account in initial_non_existing_accounts if non_account.role }
        self._non_existing_accounts_not_allocated_to_role = [ non_account for non_account in initial_non_existing_accounts if not non_account.role ]


    # Python 3.12 @override
    def obtain_account_by_role(self, role: str | None = None) -> Account:
        ret = self._accounts_allocated_to_role.get(role)
        if not ret:
            if self._accounts_not_allocated_to_role:
                ret = self._accounts_not_allocated_to_role.pop()
                self._accounts_allocated_to_role[role] = ret
            else:
                ret = self._provision_account_for_role(role)
                if ret:
                    self._accounts_allocated_to_role[role] = ret
        if ret:
            return ret
        raise OutOfAccountsException()


    # Python 3.12 @override
    def obtain_non_existing_account_by_role(self, role: str | None = None) -> NonExistingAccount:
        ret = self._non_existing_accounts_allocated_to_role.get(role)
        if not ret:
            if self._non_existing_accounts_not_allocated_to_role:
                ret = self._non_existing_accounts_not_allocated_to_role.pop()
                self._non_existing_accounts_allocated_to_role[role] = ret
            else:
                ret = self._provision_non_existing_account_for_role(role)
                if ret:
                    self._non_existing_accounts_allocated_to_role[role] = ret
        if ret:
            return ret
        raise OutOfNonExistingAccountsException()


    def _provision_account_for_role(self, role: str | None = None) -> Account | None:
        """
        This no-op method can be overridden by subclasses to dynamically provision a new Account.
        """
        return None


    def _provision_non_existing_account_for_role(self, role: str | None = None) -> Account | None:
        """
        This no-op method can be overridden by subclasses to dynamically provision a new NonExistingAccount.
        """
        return None
