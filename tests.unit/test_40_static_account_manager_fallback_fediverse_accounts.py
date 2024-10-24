"""
Test the StaticAccountManager with the FediverseAccounts and FediverseNonExistingAccounts defined
in the fallback Fediverse implementation.
"""

from typing import cast

import pytest

import feditest
from feditest.nodedrivers import StaticAccountManager
from feditest.protocols.fediverse import (
    FediverseAccount,
    FediverseNonExistingAccount
)

@pytest.fixture(scope="module", autouse=True)
def init():
    """ Clean init """
    feditest.all_tests = {}
    feditest._registered_as_test = {}
    feditest._registered_as_test_step = {}
    feditest._loading_tests = True

    feditest._loading_tests = False
    feditest._load_tests_pass2()


@pytest.fixture(autouse=True)
def account_manager() -> StaticAccountManager:

    initial_accounts : list[FediverseAccount] = [
        FediverseAccount(None, 'user-0-unallocated'),
        FediverseAccount('role1', 'user-1-role1'),
        FediverseAccount(None, 'user-2-unallocated'),
        FediverseAccount('role3', 'user-3-role3'),
    ]
    initial_non_existing_accounts : list[FediverseNonExistingAccount] = [
        FediverseNonExistingAccount(None, 'nonuser-0-unallocated'),
        FediverseNonExistingAccount('role1', 'nonuser-1-role1'),
        FediverseNonExistingAccount(None, 'nonuser-2-unallocated'),
        FediverseNonExistingAccount('role3', 'nonuser-3-role3'),
    ]
    ret = StaticAccountManager(initial_accounts, initial_non_existing_accounts)
    return ret


def test_initial_accounts(account_manager: StaticAccountManager) -> None:
   """
   Test that AccountManager has sorted the provided Accounts into the right buckets.
   """
   acc1 = cast(FediverseAccount | None, account_manager.get_account_by_role('role1'))
   assert acc1
   assert acc1.role == 'role1'
   assert acc1.userid == 'user-1-role1'

   acc3 = cast(FediverseAccount | None, account_manager.get_account_by_role('role3'))
   assert acc3
   assert acc3.role == 'role3'
   assert acc3.userid == 'user-3-role3'


def test_initial_non_existing_accounts(account_manager: StaticAccountManager) -> None:
   """
   Test that AccountManager has sorted the provided NonExistingAccounts into the right buckets.
   """
   acc1 = cast(FediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role1'))
   assert acc1
   assert acc1.role == 'role1'
   assert acc1.userid == 'nonuser-1-role1'

   acc3 = cast(FediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role3'))
   assert acc3
   assert acc3.role == 'role3'
   assert acc3.userid == 'nonuser-3-role3'


def test_allocates_accounts_correctly(account_manager: StaticAccountManager) -> None:
   """
   Test that the right accounts are returned given the assigned and non-assigned roles.
   """
   # Do things a little out of order
   acc2 = cast(FediverseAccount | None, account_manager.get_account_by_role('role2'))
   assert acc2 is None

   acc0 = cast(FediverseAccount | None, account_manager.get_account_by_role('role0'))
   assert acc0 is None

   acc0 = cast(FediverseAccount | None, account_manager.obtain_account_by_role('role0'))
   assert acc0
   assert acc0.role is None
   assert acc0.userid == 'user-0-unallocated'

   acc2 = cast(FediverseAccount | None, account_manager.get_account_by_role('role2'))
   assert acc2 is None

   acc2 = cast(FediverseAccount | None, account_manager.obtain_account_by_role('role2'))
   assert acc2
   assert acc2.role is None
   assert acc2.userid == 'user-2-unallocated'


def test_allocates_non_existing_accountscorrectly(account_manager: StaticAccountManager) -> None:
   """
   Test that the right non-existing accounts are returned given the assigned and non-assigned roles.
   """
   # Do things a little out of order
   acc2 = cast(FediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role2'))
   assert acc2 is None

   acc0 = cast(FediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role0'))
   assert acc0 is None

   acc0 = cast(FediverseNonExistingAccount | None, account_manager.obtain_non_existing_account_by_role('role0'))
   assert acc0
   assert acc0.role is None
   assert acc0.userid == 'nonuser-0-unallocated'

   acc2 = cast(FediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role2'))
   assert acc2 is None

   acc2 = cast(FediverseNonExistingAccount | None, account_manager.obtain_non_existing_account_by_role('role2'))
   assert acc2
   assert acc2.role is None
   assert acc2.userid == 'nonuser-2-unallocated'
