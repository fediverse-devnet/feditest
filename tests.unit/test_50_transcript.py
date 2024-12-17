#
# Test the transcript has all the expected values
#

import pytest

import feditest
from feditest import nodedriver, test
from feditest.utils import FEDITEST_VERSION
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSessionTemplate, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest.testruntranscript import TestRunResultTranscript

from dummy import DummyNodeDriver

APP_NAMES = [
    'APP_0',
    'APP_1',
    'APP_2',
    'APP_3'
]
driver_names = []

@pytest.fixture(scope="module", autouse=True)
def init_node_drivers():
    global driver_names

    """ Keep these isolated to this module """
    feditest.all_node_drivers = {}
    feditest._loading_node_drivers = True

    @nodedriver
    class NodeDriver1(DummyNodeDriver):
        pass

    @nodedriver
    class NodeDriver2(DummyNodeDriver):
        pass

    feditest._loading_node_drivers = False

    driver_names = list(feditest.all_node_drivers.keys())


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
    def passes() -> None:
        """
        This test always passes.
        """
        return

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
    constellations = [
        TestPlanConstellation(
            {
                'node1a': TestPlanConstellationNode(
                    driver_names[0],
                    {
                        'app' : APP_NAMES[0]
                    }
                ),
                'node2a': TestPlanConstellationNode(
                    driver_names[1],
                    {
                        'app' : APP_NAMES[1]
                    }
                )
            },
            'constellation-1'),
        TestPlanConstellation(
            {
                'node1b': TestPlanConstellationNode(
                    driver_names[0],
                    {
                        'app' : APP_NAMES[2]
                    }
                ),
                'node2b': TestPlanConstellationNode(
                    driver_names[1],
                    {
                        'app' : APP_NAMES[3]
                    }
                )
            },
            'constellation-2')
    ]
    tests = [ TestPlanTestSpec(name) for name in sorted(feditest.all_tests.keys()) if feditest.all_tests.get(name) is not None ]
    session = TestPlanSessionTemplate(tests, "Test a test that passes")
    ret = TestPlan(session, constellations)
    ret.properties_validate()
    # ret.print()
    return ret


@pytest.fixture
def transcript(test_plan_fixture: TestPlan) -> TestRunResultTranscript:
    test_plan_fixture.check_can_be_executed()

    test_run = TestRun(test_plan_fixture)
    controller = AutomaticTestRunController(test_run)
    test_run.run(controller)

    ret = test_run.transcribe()
    return ret


def test_transcript(transcript: TestRunResultTranscript):
    assert transcript.plan
    assert transcript.id
    assert transcript.started
    assert transcript.ended

    assert len(transcript.sessions) == 2
    assert len(transcript.test_meta) == 1
    assert transcript.result is None
    assert transcript.type == 'feditest-testrun-transcript'
    assert transcript.feditest_version == FEDITEST_VERSION

    for i in range(0, 1):
        assert transcript.sessions[i].started
        assert transcript.sessions[i].ended
        assert len(transcript.sessions[i].run_tests) == 1
        assert transcript.sessions[i].run_tests[0].started
        assert transcript.sessions[i].run_tests[0].ended
        assert transcript.sessions[i].run_tests[0].result is None

