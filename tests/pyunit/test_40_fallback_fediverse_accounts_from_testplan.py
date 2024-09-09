"""
Test that Accounts and NonExistingAccounts are parsed correctly when given in a TestPlan that
specifies a FallbackFediverseNode
"""

from typing import cast

import pytest

import feditest
from feditest.nodedrivers.fallback.fediverse import (
    FallbackFediverseAccount,
    FallbackFediverseNonExistingAccount,
    ACTOR_URI_ACCOUNT_FIELD,
    ACTOR_URI_NON_EXISTING_ACCOUNT_FIELD,
    ROLE_ACCOUNT_FIELD,
    URI_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    URI_NON_EXISTING_ACCOUNT_FIELD,
)
from feditest.nodedrivers.saas import FediverseSaasNodeDriver
from feditest.protocols import StaticAccountManager
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSession


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
    node_driver = FediverseSaasNodeDriver()
    parameters = {
        'hostname' : 'localhost', # Avoid interactive question
        'app' : 'test-dummy' # Avoid interactive question
    }
    plan_accounts = [
        {
            ROLE_ACCOUNT_FIELD.name : 'role1',
            URI_ACCOUNT_FIELD.name : 'acct:foo@bar.com',
            ACTOR_URI_ACCOUNT_FIELD.name : 'https://bar.com/user/foo'
        }
    ]
    plan_non_existing_accounts = [
        {
            ROLE_NON_EXISTING_ACCOUNT_FIELD.name : 'nonrole1',
            URI_NON_EXISTING_ACCOUNT_FIELD.name : 'acct:foo@nowhere.com',
            ACTOR_URI_NON_EXISTING_ACCOUNT_FIELD.name : 'https://nowhere.com/user/foo'
        }
    ]
    node1 = TestPlanConstellationNode(node_driver, parameters, plan_accounts, plan_non_existing_accounts)
    constellation = TestPlanConstellation( { NODE1_ROLE : node1 })
    session = TestPlanSession(constellation, [])
    ret = TestPlan( [ session ] )
    return ret


def test_parse(the_test_plan: TestPlan) -> None:
    """
    Tests parsing the TestPlan
    """
    node1 = the_test_plan.sessions[0].constellation.roles[NODE1_ROLE]
    node_driver = node1.nodedriver

    node_config, account_manager = node_driver.create_configuration_account_manager(NODE1_ROLE, node1)

    acc1 = cast(FallbackFediverseAccount | None, account_manager.get_account_by_role('role1'))

    assert acc1
    assert acc1.role == 'role1'
    assert acc1.uri == 'acct:foo@bar.com'

    non_acc1 = cast(FallbackFediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('nonrole1'))
    assert non_acc1
    assert non_acc1.role == 'nonrole1'
    assert non_acc1.uri == 'acct:foo@nowhere.com'

