"""
Test that NodeDriver errors are reported in the test reports
"""

from typing import Any

import feditest
import pytest
from feditest import nodedriver
from feditest.protocols import AccountManager, Node, NodeConfiguration, NodeDriver
from feditest.testplan import (
    TestPlan,
    TestPlanConstellation,
    TestPlanConstellationNode,
    TestPlanSession,
    TestPlanTestSpec,
)
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest.testruntranscript import (
    JsonTestRunTranscriptSerializer,
    SummaryTestRunTranscriptSerializer,
    TapTestRunTranscriptSerializer,
)


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
    plan = TestPlan( [
        TestPlanSession(
            TestPlanConstellation( {
                'node' : TestPlanConstellationNode(
                    nodedriver = 'test_40_report_node_driver_errors.init.<locals>.Faulty_NodeDriver',
                    parameters = { 'app' : 'Dummy for test_faulty_node_driver_reporting'}
                )
            }),
            [
                TestPlanTestSpec('test_40_report_node_driver_errors::init.<locals>.dummy')
            ]
        )
    ])
    run = TestRun(plan)
    controller = AutomaticTestRunController(run)

    run.run(controller)

    transcript : feditest.testruntranscript.TestRunTranscript = run.transcribe()
    # transcript.save('transcript.json')

    summary_serializer = SummaryTestRunTranscriptSerializer(transcript)
    summary : str = summary_serializer.write_to_string()
    # print(summary)
    assert 'errors=1' in summary

    tap_serializer = TapTestRunTranscriptSerializer(transcript)
    tap : str = tap_serializer.write_to_string()
    # print(tap)
    assert 'errors: 1' in tap

    json_serializer = JsonTestRunTranscriptSerializer(transcript)
    j : str = json_serializer.write_to_string()
    # print(j)
    assert f'"type": "{NodeDriverTestException.__name__}"' in j
