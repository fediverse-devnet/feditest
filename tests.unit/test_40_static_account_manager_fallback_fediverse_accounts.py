"""
Test the StaticAccountManager with the FediverseAccounts and FediverseNonExistingAccounts defined
in the fallback Fediverse implementation.
"""

from typing import cast

import pytest

import feditest
from feditest.nodedrivers.fallback.fediverse import FallbackFediverseAccount, FallbackFediverseNonExistingAccount
from feditest.protocols import StaticAccountManager

HOSTNAME = 'localhost'

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

    initial_accounts : list[FallbackFediverseAccount] = [
        FallbackFediverseAccount(None, f'acct:user-0-unallocated@{ HOSTNAME }', f'https://{ HOSTNAME }/actor-0-unallocated'),
        FallbackFediverseAccount('role1', f'acct:user-1-role1@{ HOSTNAME }', f'https://{ HOSTNAME }/actor-1-role1'),
        FallbackFediverseAccount(None, f'acct:user-2-unallocated@{ HOSTNAME }', f'https://{ HOSTNAME }/actor-2-unallocated'),
        FallbackFediverseAccount('role3', f'acct:user-3-role3@{ HOSTNAME }', f'https://{ HOSTNAME }/actor-3-role3'),
    ]

    initial_non_existing_accounts : list[FallbackFediverseNonExistingAccount] = [
        FallbackFediverseNonExistingAccount(None, f'acct:nonuser-0-unallocated@{ HOSTNAME }', f'https://{ HOSTNAME }/nonactor-0-unallocated'),
        FallbackFediverseNonExistingAccount('role1', f'acct:nonuser-1-role1@{ HOSTNAME }', f'https://{ HOSTNAME }/nonactor-1-role1'),
        FallbackFediverseNonExistingAccount(None, f'acct:nonuser-2-unallocated@{ HOSTNAME }', f'https://{ HOSTNAME }/nonactor-2-unallocated'),
        FallbackFediverseNonExistingAccount('role3', f'acct:nonuser-3-role3@{ HOSTNAME }', f'https://{ HOSTNAME }/nonactor-3-role3'),
    ]

    ret = StaticAccountManager(initial_accounts, initial_non_existing_accounts)
    return ret


def test_initial_accounts(account_manager: StaticAccountManager) -> None:
   """
   Test that AccountManager has sorted the provided Accounts into the right buckets.
   """
   acc1 = cast(FallbackFediverseAccount | None, account_manager.get_account_by_role('role1'))
   assert acc1
   assert acc1.role == 'role1'
   assert acc1.actor_uri == f'https://{ HOSTNAME }/actor-1-role1'

   acc3 = cast(FallbackFediverseAccount | None, account_manager.get_account_by_role('role3'))
   assert acc3
   assert acc3.role == 'role3'
   assert acc3.actor_uri == f'https://{ HOSTNAME }/actor-3-role3'


def test_initial_non_existing_accounts(account_manager: StaticAccountManager) -> None:
   """
   Test that AccountManager has sorted the provided NonExistingAccounts into the right buckets.
   """
   acc1 = cast(FallbackFediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role1'))
   assert acc1
   assert acc1.role == 'role1'
   assert acc1.actor_uri == f'https://{ HOSTNAME }/nonactor-1-role1'

   acc3 = cast(FallbackFediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role3'))
   assert acc3
   assert acc3.role == 'role3'
   assert acc3.actor_uri == f'https://{ HOSTNAME }/nonactor-3-role3'


def test_allocates_accounts_correctly(account_manager: StaticAccountManager) -> None:
   """
   Test that the right accounts are returned given the assigned and non-assigned roles.
   """
   # Do things a little out of order
   acc2 = cast(FallbackFediverseAccount | None, account_manager.get_account_by_role('role2'))
   assert acc2 is None

   acc0 = cast(FallbackFediverseAccount | None, account_manager.get_account_by_role('role0'))
   assert acc0 is None

   acc0 = cast(FallbackFediverseAccount | None, account_manager.obtain_account_by_role('role0'))
   assert acc0
   assert acc0.role is None
   assert acc0.actor_uri == f'https://{ HOSTNAME }/actor-0-unallocated'

   acc2 = cast(FallbackFediverseAccount | None, account_manager.get_account_by_role('role2'))
   assert acc2 is None

   acc2 = cast(FallbackFediverseAccount | None, account_manager.obtain_account_by_role('role2'))
   assert acc2
   assert acc2.role is None
   assert acc2.actor_uri == f'https://{ HOSTNAME }/actor-2-unallocated'


def test_allocates_non_existing_accountscorrectly(account_manager: StaticAccountManager) -> None:
   """
   Test that the right non-existing accounts are returned given the assigned and non-assigned roles.
   """
   # Do things a little out of order
   acc2 = cast(FallbackFediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role2'))
   assert acc2 is None

   acc0 = cast(FallbackFediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role0'))
   assert acc0 is None

   acc0 = cast(FallbackFediverseNonExistingAccount | None, account_manager.obtain_non_existing_account_by_role('role0'))
   assert acc0
   assert acc0.role is None
   assert acc0.actor_uri == f'https://{ HOSTNAME }/nonactor-0-unallocated'

   acc2 = cast(FallbackFediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('role2'))
   assert acc2 is None

   acc2 = cast(FallbackFediverseNonExistingAccount | None, account_manager.obtain_non_existing_account_by_role('role2'))
   assert acc2
   assert acc2.role is None
   assert acc2.actor_uri == f'https://{ HOSTNAME }/nonactor-2-unallocated'

