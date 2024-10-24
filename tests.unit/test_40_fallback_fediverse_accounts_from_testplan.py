"""
Test that Accounts and NonExistingAccounts are parsed correctly when given in a TestPlan that
specifies a FallbackFediverseNode
"""

from typing import cast

import pytest

import feditest
from feditest.nodedrivers.saas import FediverseSaasNodeDriver
from feditest.protocols.fediverse import (
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD,
    FediverseAccount,
    FediverseNonExistingAccount
)
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
def test_plan_fixture() -> TestPlan:
    node_driver = FediverseSaasNodeDriver()
    parameters = {
        'hostname' : 'example.com', # Avoid interactive question
        'app' : 'test-dummy' # Avoid interactive question
    }
    plan_accounts = [
        {
            ROLE_ACCOUNT_FIELD.name : 'role1',
            USERID_ACCOUNT_FIELD.name : 'foo'
        }
    ]
    plan_non_existing_accounts = [
        {
            ROLE_NON_EXISTING_ACCOUNT_FIELD.name : 'nonrole1',
            USERID_NON_EXISTING_ACCOUNT_FIELD.name : 'nonfoo'
        }
    ]
    node1 = TestPlanConstellationNode(node_driver, parameters, plan_accounts, plan_non_existing_accounts)
    constellation = TestPlanConstellation( { NODE1_ROLE : node1 })
    session_template = TestPlanSessionTemplate([])
    ret = TestPlan( session_template, [ constellation ] )
    return ret


def test_parse(test_plan_fixture: TestPlan) -> None:
    """
    Tests parsing the TestPlan
    """
    node1 = test_plan_fixture.constellations[0].roles[NODE1_ROLE]
    node_driver = node1.nodedriver

    node_config, account_manager = node_driver.create_configuration_account_manager(NODE1_ROLE, node1)
    node_driver.provision_node('test', node_config, account_manager)

    acc1 = cast(FediverseAccount | None, account_manager.get_account_by_role('role1'))

    assert acc1
    assert acc1.role == 'role1'
    assert acc1.actor_acct_uri == 'acct:foo@example.com'

    non_acc1 = cast(FediverseNonExistingAccount | None, account_manager.get_non_existing_account_by_role('nonrole1'))
    assert non_acc1
    assert non_acc1.role == 'nonrole1'
    assert non_acc1.actor_acct_uri == 'acct:nonfoo@example.com'

