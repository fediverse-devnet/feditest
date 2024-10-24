"""
Test that Accounts and NonExistingAccounts are parsed correctly when given in a TestPlan that
specifies a MastodonUbosNodeDriver
"""

from typing import cast

import pytest

import feditest
from feditest.nodedrivers.mastodon import (
    MastodonAccount,
    MastodonOAuthTokenAccount,
    MastodonUserPasswordAccount,
    EMAIL_ACCOUNT_FIELD,
    PASSWORD_ACCOUNT_FIELD,
    OAUTH_TOKEN_ACCOUNT_FIELD,
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD
)
from feditest.nodedrivers.mastodon.ubos import MastodonUbosNodeDriver
from feditest.protocols.fediverse import FediverseNonExistingAccount
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSessionTemplate


HOSTNAME = 'localhost'
NODE1_ROLE = 'node1-role'


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
def the_test_plan() -> TestPlan:
    node_driver = MastodonUbosNodeDriver()
    parameters = None
    plan_accounts = [
        {
            ROLE_ACCOUNT_FIELD.name : 'role1',
            USERID_ACCOUNT_FIELD.name : 'foo',
            EMAIL_ACCOUNT_FIELD.name : 'foo@bar.com',
            PASSWORD_ACCOUNT_FIELD.name : 'verysecret'
        },
        {
            ROLE_ACCOUNT_FIELD.name : 'role2',
            USERID_ACCOUNT_FIELD.name : 'bar',
            OAUTH_TOKEN_ACCOUNT_FIELD.name : 'tokentokentoken'
        }
    ]
    plan_non_existing_accounts = [
        {
            ROLE_NON_EXISTING_ACCOUNT_FIELD.name : 'nonrole1',
            USERID_NON_EXISTING_ACCOUNT_FIELD.name : 'nouser'
        }
    ]
    node1 = TestPlanConstellationNode(node_driver, parameters, plan_accounts, plan_non_existing_accounts)
    constellation = TestPlanConstellation( { NODE1_ROLE : node1 })
    session = TestPlanSessionTemplate([])
    ret = TestPlan( session, [ constellation ] )
    return ret


def test_parse(the_test_plan: TestPlan) -> None:
    """
    Tests parsing the TestPlan
    """
    node1 = the_test_plan.constellations[0].roles[NODE1_ROLE]
    node_driver = node1.nodedriver

    node_config, account_manager = node_driver.create_configuration_account_manager(NODE1_ROLE, node1)

    acc1 = cast(MastodonAccount | None, account_manager.get_account_by_role('role1'))
    assert acc1
    assert acc1.role == 'role1'
    assert acc1.userid == 'foo'
    assert isinstance(acc1, MastodonUserPasswordAccount)
    assert acc1._email == 'foo@bar.com'
    assert acc1._password == 'verysecret'

    acc2 = cast(MastodonAccount | None, account_manager.get_account_by_role('role2'))
    assert acc2
    assert acc2.role == 'role2'
    assert acc2.userid == 'bar'
    assert isinstance(acc2, MastodonOAuthTokenAccount)
    assert acc2._oauth_token == 'tokentokentoken'

    non_acc1 = cast(FediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('nonrole1'))
    assert non_acc1
    assert non_acc1.role == 'nonrole1'
    assert non_acc1.userid == 'nouser'

