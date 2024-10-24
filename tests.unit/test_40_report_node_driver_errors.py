"""
Test that NodeDriver errors are reported in the test reports
"""

import feditest
import pytest
from feditest import nodedriver
from feditest.nodedrivers import AccountManager, Node, NodeConfiguration, NodeDriver
from feditest.testplan import (
    TestPlan,
    TestPlanConstellation,
    TestPlanConstellationNode,
    TestPlanSessionTemplate,
    TestPlanTestSpec,
)
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest.testruntranscriptserializer.json import JsonTestRunTranscriptSerializer
from feditest.testruntranscriptserializer.summary import SummaryTestRunTranscriptSerializer
from feditest.testruntranscriptserializer.tap import TapTestRunTranscriptSerializer


class NodeDriverTestException(Exception):
    pass


@pytest.fixture(scope="module", autouse=True)
def init():
    global node_driver_name

    """ Keep these isolated to this module """
    feditest.all_tests = {}
    feditest._registered_as_test = {}
    feditest._registered_as_test_step = {}
    feditest._loading_tests = True

    @feditest.test
    def dummy() -> None:
        return

    feditest._loading_tests = False
    feditest._load_tests_pass2()

    """ The NodeDriver we use for testing """
    feditest.all_node_drivers = {}
    feditest._loading_node_drivers = True

    @nodedriver
    class Faulty_NodeDriver(NodeDriver):
        def _provision_node(
            self,
            rolename: str,
            config: NodeConfiguration,
            account_manager: AccountManager | None
        ) -> Node:
            raise NodeDriverTestException()

    feditest._loading_node_drivers = False

    for t in feditest.all_tests:
        print( f'TEST: { t }')


def test_faulty_node_driver_reporting() -> None:
    plan = TestPlan(
        TestPlanSessionTemplate(
            [
                TestPlanTestSpec('test_40_report_node_driver_errors::init.<locals>.dummy')
            ]
        ),
        [
            TestPlanConstellation( {
                'node' : TestPlanConstellationNode(
                    nodedriver = 'test_40_report_node_driver_errors.init.<locals>.Faulty_NodeDriver',
                    parameters = { 'app' : 'Dummy for test_faulty_node_driver_reporting'}
                )
            }),
        ]
    )
    run = TestRun(plan)
    controller = AutomaticTestRunController(run)

    run.run(controller)

    transcript : feditest.testruntranscript.TestRunTranscript = run.transcribe()
    # transcript.save('transcript.json')

    summary = SummaryTestRunTranscriptSerializer().write_to_string(transcript)
    # print(summary)
    assert 'errors=1' in summary

    tap = TapTestRunTranscriptSerializer().write_to_string(transcript)
    # print(tap)
    assert 'errors: 1' in tap

    j = JsonTestRunTranscriptSerializer().write_to_string(transcript)
    # print(j)
    assert f'"type": "{NodeDriverTestException.__name__}"' in j
