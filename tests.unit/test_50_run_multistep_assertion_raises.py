"""
Run a multi-step test that raises various failures in different steps
"""

import pytest

import feditest
from feditest import assert_that, step, test, InteropLevel, SpecLevel
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSessionTemplate, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController


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
    class Example:
        """
        A multi-step test class that raises various failures in different steps.
        """
        def __init__(self):
            pass


        @step
        def step01_default(self) -> None:
            assert_that(False, 'This was the default!')


        @step
        def step02_must(self) -> None:
            assert_that(False, 'This was MUST!', spec_level=SpecLevel.MUST)


        @step
        def step03_should(self) -> None:
            assert_that(False, 'This was SHOULD!', spec_level=SpecLevel.SHOULD)


        @step
        def step04_implied(self) -> None:
            assert_that(False, 'This was IMPLIED!', spec_level=SpecLevel.IMPLIED)


        @step
        def step05_problem(self) -> None:
            assert_that(False, 'This is PROBLEM!', interop_level=InteropLevel.PROBLEM)


        @step
        def step06_degraded(self) -> None:
            assert_that(False, 'This is DEGRADED!', interop_level=InteropLevel.DEGRADED)


        @step
        def step07_unaffected(self) -> None:
            assert_that(False, 'This is UNAFFECTED!', interop_level=InteropLevel.UNAFFECTED)


        @step
        def step08_unknown(self) -> None:
            assert_that(False, 'This is UNKNOWN!', interop_level=InteropLevel.UNKNOWN)


        @step
        def step09_must_problem(self) -> None:
            assert_that(False, 'This was MUST, PROBLEM!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.PROBLEM)


        @step
        def step10_must_degraded(self) -> None:
            assert_that(False, 'This was MUST, DEGRADED!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.DEGRADED)


        @step
        def step11_must_unaffected(self) -> None:
            assert_that(False, 'This was MUST, UNAFFECTED!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.UNAFFECTED)


        @step
        def step12_must_unknown(self) -> None:
            assert_that(False, 'This was MUST, UNKNOWN!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.UNKNOWN)


        @step
        def step13_should_problem(self) -> None:
            assert_that(False, 'This was SHOULD, PROBLEM!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.PROBLEM)


        @step
        def step14_should_degraded(self) -> None:
            assert_that(False, 'This was SHOULD, DEGRADED!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.DEGRADED)


        @step
        def step15_should_unaffected(self) -> None:
            assert_that(False, 'This was SHOULD, UNAFFECTED!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.UNAFFECTED)


        @step
        def step16_should_unkown(self) -> None:
            assert_that(False, 'This was SHOULD, UNKNOWN!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.UNKNOWN)


        @step
        def step17_implied_problem(self) -> None:
            assert_that(False, 'This was IMPLIED, PROBLEM!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.PROBLEM)


        @step
        def step18_implied_degraded(self) -> None:
            assert_that(False, 'This was IMPLIED, DEGRADED!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.DEGRADED)


        @step
        def step19_implied_unaffected(self) -> None:
            assert_that(False, 'This was IMPLIED, UNAFFECTED!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.UNAFFECTED)


        @step
        def step20_implied_unknown(self) -> None:
            assert_that(False, 'This was IMPLIED, UNKNOWN!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.UNKNOWN)


        @step
        def step21_unspecified_problem(self) -> None:
            assert_that(False, 'This was UNSPECIFIED, PROBLEM!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.PROBLEM)


        @step
        def step22_unspecified_degraded(self) -> None:
            assert_that(False, 'This was UNSPECIFIED, DEGRADED!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.DEGRADED)


        @step
        def step23_unspecified_unaffected(self) -> None:
            assert_that(False, 'This was UNSPECIFIED, UNAFFECTED!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.UNAFFECTED)


        @step
        def step24_unspecified_unknown(self) -> None:
            assert_that(False, 'This was UNSPECIFIED, UNKNOWN!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.UNKNOWN)

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
    session = TestPlanSessionTemplate(tests, "Test a test whose steps raises multiple AssertionFailures")
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
    assert summary.n_failed == 1
    assert summary.n_skipped == 0
    assert summary.n_errored == 0
    assert summary.n_passed == 0

    assert len(transcript.sessions) == 1
    assert len(transcript.sessions[0].run_tests) == 1
    assert len(transcript.sessions[0].run_tests[0].run_steps) == 1 # It never getst to the other steps

    assert transcript.sessions[0].run_tests[0].run_steps[0].result.type == 'AssertionFailure'
    assert transcript.sessions[0].run_tests[0].run_steps[0].result.spec_level == SpecLevel.MUST.name
    assert transcript.sessions[0].run_tests[0].run_steps[0].result.interop_level == InteropLevel.UNKNOWN.name
