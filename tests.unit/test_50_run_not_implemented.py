"""
Run a test that throws a NotImplemented error.
"""

import pytest

import feditest
from feditest.nodedrivers import AccountManager, Node, NodeConfiguration, NodeDriver, NotImplementedByNodeError
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSessionTemplate, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest import test


class DummyNode(Node):
    def missing_method(self):
        pass


class DummyNodeDriver(NodeDriver):
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> Node:
        return DummyNode(rolename, config, account_manager)


    def missing_method(self):
        pass


@pytest.fixture(scope="module", autouse=True)
def init_node_drivers():
    """
    Cleanly define the NodeDrivers.
    """
    feditest.all_node_drivers = {}
    feditest.load_default_node_drivers()


@pytest.fixture(scope="module", autouse=True)
def init_tests():
    """
    Cleanly define some tests.
    """
    feditest.all_tests = {}
    feditest._registered_as_test = {}
    feditest._registered_as_test_step = {}
    feditest._loading_tests = True

    ##
    ## FediTest tests start here
    ##

    @test
    def not_implemented_by_node_error() -> None:
        """
        A Node does not implement a method.
        """
        driver = DummyNodeDriver()
        node = driver.provision_node('testrole', NodeConfiguration(driver, 'dummy'))

        raise NotImplementedByNodeError(node, DummyNode.missing_method)

    ##
    ## FediTest tests end here
    ## (Don't forget the next two lines)
    ##

    feditest._loading_tests = False
    feditest._load_tests_pass2()


@pytest.fixture(autouse=True)
def test_plan_fixture() -> TestPlan:
    """
    The test plan tests all known tests.
    """

    constellation = TestPlanConstellation({}, 'No nodes needed')
    tests = [ TestPlanTestSpec(name) for name in sorted(feditest.all_tests.keys()) if feditest.all_tests.get(name) is not None ]
    session = TestPlanSessionTemplate(tests, "Test tests that throw NotImplemented errors")
    ret = TestPlan(session, [ constellation ])
    return ret


def test_run_testplan(test_plan_fixture: TestPlan):
    test_plan_fixture.check_can_be_executed()

    test_run = TestRun(test_plan_fixture)
    controller = AutomaticTestRunController(test_run)
    test_run.run(controller)

    transcript = test_run.transcribe()
    summary = transcript.build_summary()

    assert summary.n_total == 1
    assert summary.n_failed == 0
    assert summary.n_skipped == 1 # NotImplemented exceptions cause skips
    assert summary.n_errored == 0
    assert summary.n_passed == 0

    assert len(transcript.sessions) == 1
    assert len(transcript.sessions[0].run_tests) == 1
    assert transcript.sessions[0].run_tests[0].result.type == 'NotImplementedByNodeError'