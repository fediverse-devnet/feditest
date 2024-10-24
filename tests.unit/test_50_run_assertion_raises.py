"""
Run tests that raise various AssertionFailures.
"""

from os.path import basename

import pytest

import feditest
from feditest import SpecLevel, InteropLevel, assert_that, test
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSessionTemplate, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest.testruntranscript import TestRunTestTranscript
from feditest.testruntranscriptserializer.json import JsonTestRunTranscriptSerializer
from feditest.testruntranscriptserializer.html import HtmlRunTranscriptSerializer
from feditest.testruntranscriptserializer.summary import SummaryTestRunTranscriptSerializer
from feditest.testruntranscriptserializer.tap import TapTestRunTranscriptSerializer


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
    def test00_default() -> None:
        assert_that(False, 'This was the default!')


    @test
    def test01_must() -> None:
        assert_that(False, 'This was MUST!', spec_level=SpecLevel.MUST)


    @test
    def test02_should() -> None:
        assert_that(False, 'This was SHOULD!', spec_level=SpecLevel.SHOULD)


    @test
    def test03_implied() -> None:
        assert_that(False, 'This was IMPLIED!', spec_level=SpecLevel.IMPLIED)


    @test
    def test04_problem() -> None:
        assert_that(False, 'This is PROBLEM!', interop_level=InteropLevel.PROBLEM)


    @test
    def test05_degraded() -> None:
        assert_that(False, 'This is DEGRADED!', interop_level=InteropLevel.DEGRADED)


    @test
    def test06_unaffected() -> None:
        assert_that(False, 'This is UNAFFECTED!', interop_level=InteropLevel.UNAFFECTED)


    @test
    def test07_unknown() -> None:
        assert_that(False, 'This is UNKNOWN!', interop_level=InteropLevel.UNKNOWN)


    @test
    def test08_must_problem() -> None:
        assert_that(False, 'This was MUST, PROBLEM!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.PROBLEM)


    @test
    def test09_must_degraded() -> None:
        assert_that(False, 'This was MUST, DEGRADED!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.DEGRADED)


    @test
    def test10_must_unaffected() -> None:
        assert_that(False, 'This was MUST, UNAFFECTED!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.UNAFFECTED)


    @test
    def test11_must_unknown() -> None:
        assert_that(False, 'This was MUST, UNKNOWN!', spec_level=SpecLevel.MUST, interop_level=InteropLevel.UNKNOWN)


    @test
    def test12_should_problem() -> None:
        assert_that(False, 'This was SHOULD, PROBLEM!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.PROBLEM)


    @test
    def test13_should_degraded() -> None:
        assert_that(False, 'This was SHOULD, DEGRADED!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.DEGRADED)


    @test
    def test14_should_unaffected() -> None:
        assert_that(False, 'This was SHOULD, UNAFFECTED!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.UNAFFECTED)


    @test
    def test15_should_unkown() -> None:
        assert_that(False, 'This was SHOULD, UNKNOWN!', spec_level=SpecLevel.SHOULD, interop_level=InteropLevel.UNKNOWN)


    @test
    def test16_implied_problem() -> None:
        assert_that(False, 'This was IMPLIED, PROBLEM!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.PROBLEM)


    @test
    def test17_implied_degraded() -> None:
        assert_that(False, 'This was IMPLIED, DEGRADED!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.DEGRADED)


    @test
    def test18_implied_unaffected() -> None:
        assert_that(False, 'This was IMPLIED, UNAFFECTED!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.UNAFFECTED)


    @test
    def test19_implied_unknown() -> None:
        assert_that(False, 'This was IMPLIED, UNKNOWN!', spec_level=SpecLevel.IMPLIED, interop_level=InteropLevel.UNKNOWN)


    @test
    def test20_unspecified_problem() -> None:
        assert_that(False, 'This was UNSPECIFIED, PROBLEM!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.PROBLEM)


    @test
    def test21_unspecified_degraded() -> None:
        assert_that(False, 'This was UNSPECIFIED, DEGRADED!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.DEGRADED)


    @test
    def test22_unspecified_unaffected() -> None:
        assert_that(False, 'This was UNSPECIFIED, UNAFFECTED!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.UNAFFECTED)


    @test
    def test23_unspecified_unknown() -> None:
        assert_that(False, 'This was UNSPECIFIED, UNKNOWN!', spec_level=SpecLevel.UNSPECIFIED, interop_level=InteropLevel.UNKNOWN)


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
    session = TestPlanSessionTemplate(tests, "Test tests that raise various AssertionFailures")
    ret = TestPlan( session, [ constellation ] )
    return ret


def test_run_testplan(the_test_plan: TestPlan):
    the_test_plan.check_can_be_executed()

    test_run = TestRun(the_test_plan)
    controller = AutomaticTestRunController(test_run)
    test_run.run(controller)

    transcript = test_run.transcribe()
    summary = transcript.build_summary()

    assert summary.n_total == 24
    assert summary.n_failed == 24
    assert summary.n_skipped == 0
    assert summary.n_errored == 0
    assert summary.n_passed == 0

    assert len(transcript.sessions) == 1
    assert len(transcript.sessions[0].run_tests) == 24

    multi_assert( 0, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.UNKNOWN )
    multi_assert( 1, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.UNKNOWN )
    multi_assert( 2, transcript.sessions[0].run_tests, SpecLevel.SHOULD, InteropLevel.UNKNOWN )
    multi_assert( 3, transcript.sessions[0].run_tests, SpecLevel.IMPLIED, InteropLevel.UNKNOWN )

    multi_assert( 4, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.PROBLEM )
    multi_assert( 5, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.DEGRADED )
    multi_assert( 6, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.UNAFFECTED )
    multi_assert( 7, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.UNKNOWN )

    multi_assert( 8, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.PROBLEM )
    multi_assert( 9, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.DEGRADED )
    multi_assert( 10, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.UNAFFECTED )
    multi_assert( 11, transcript.sessions[0].run_tests, SpecLevel.MUST, InteropLevel.UNKNOWN )

    multi_assert( 12, transcript.sessions[0].run_tests, SpecLevel.SHOULD, InteropLevel.PROBLEM )
    multi_assert( 13, transcript.sessions[0].run_tests, SpecLevel.SHOULD, InteropLevel.DEGRADED )
    multi_assert( 14, transcript.sessions[0].run_tests, SpecLevel.SHOULD, InteropLevel.UNAFFECTED )
    multi_assert( 15, transcript.sessions[0].run_tests, SpecLevel.SHOULD, InteropLevel.UNKNOWN )

    multi_assert( 16, transcript.sessions[0].run_tests, SpecLevel.IMPLIED, InteropLevel.PROBLEM )
    multi_assert( 17, transcript.sessions[0].run_tests, SpecLevel.IMPLIED, InteropLevel.DEGRADED )
    multi_assert( 18, transcript.sessions[0].run_tests, SpecLevel.IMPLIED, InteropLevel.UNAFFECTED )
    multi_assert( 19, transcript.sessions[0].run_tests, SpecLevel.IMPLIED, InteropLevel.UNKNOWN )

    multi_assert( 20, transcript.sessions[0].run_tests, SpecLevel.UNSPECIFIED, InteropLevel.PROBLEM )
    multi_assert( 21, transcript.sessions[0].run_tests, SpecLevel.UNSPECIFIED, InteropLevel.DEGRADED )
    multi_assert( 22, transcript.sessions[0].run_tests, SpecLevel.UNSPECIFIED, InteropLevel.UNAFFECTED )
    multi_assert( 23, transcript.sessions[0].run_tests, SpecLevel.UNSPECIFIED, InteropLevel.UNKNOWN )

    if False: # Make linter happy with import
        TapTestRunTranscriptSerializer().write(transcript, f'{ basename(__file__) }.transcript.tap')
        HtmlRunTranscriptSerializer().write( transcript, f'{ basename(__file__) }.transcript.html')
        JsonTestRunTranscriptSerializer().write(transcript, f'{ basename(__file__) }.transcript.json')
        SummaryTestRunTranscriptSerializer().write(transcript, f'{ basename(__file__) }.transcript.summary.txt')


def multi_assert(index: int, t: list[TestRunTestTranscript], spec_level: SpecLevel, interop_level: InteropLevel):
    assert t[index].result.type == 'AssertionFailure'
    assert t[index].result.spec_level == spec_level.name
    assert t[index].result.interop_level == interop_level.name
