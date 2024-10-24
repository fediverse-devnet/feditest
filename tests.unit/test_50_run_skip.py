"""
Run a test that wants to be skipped.
"""

import pytest

import feditest
from feditest.nodedrivers import SkipTestException
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSessionTemplate, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest import test


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
    def skip() -> None:
        """
        Always skips itself.
        """
        raise SkipTestException('We skipped this.')

    ##
    ## FediTest tests end here
    ## (Don't forget the next two lines)
    ##

    feditest._loading_tests = False
    feditest._load_tests_pass2()


@pytest.fixture(autouse=True)
def the_test_plan() -> TestPlan:
    """
    The test plan tests all known tests.
    """

    constellation = TestPlanConstellation({}, 'No nodes needed')
    tests = [ TestPlanTestSpec(name) for name in sorted(feditest.all_tests.keys()) if feditest.all_tests.get(name) is not None ]
    session = TestPlanSessionTemplate(tests, "Test a test that wants to be skipped")
    ret = TestPlan(session, [ constellation ])
    return ret


def test_run_testplan(the_test_plan: TestPlan):
    the_test_plan.check_can_be_executed()

    test_run = TestRun(the_test_plan)
    controller = AutomaticTestRunController(test_run)
    test_run.run(controller)

    transcript = test_run.transcribe()
    summary = transcript.build_summary()

    assert summary.n_total == 1
    assert summary.n_failed == 0
    assert summary.n_skipped == 1
    assert summary.n_errored == 0
    assert summary.n_passed == 0

    assert len(transcript.sessions) == 1
    assert len(transcript.sessions[0].run_tests) == 1
    assert transcript.sessions[0].run_tests[0].result.type == 'SkipTestException'