"""
Test that NodeDriver errors are reported in the test reports
"""

from typing import Any

import pytest

import feditest
from feditest import nodedriver
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSession, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest.testruntranscript import JsonTestRunTranscriptSerializer, SummaryTestRunTranscriptSerializer, TapTestRunTranscriptSerializer
from feditest.protocols import Node, NodeDriver

class TestException(Exception):
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
        def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> Node:
            raise TestException()

    feditest._loading_node_drivers = False


def test_faulty_node_driver_reportiung() -> None:
    plan = TestPlan( [
        TestPlanSession(
            TestPlanConstellation( {
                'node' : TestPlanConstellationNode('test_report_node_driver_errors.init.<locals>.Faulty_NodeDriver')
            }),
            [
                TestPlanTestSpec('test_report_node_driver_errors::init.<locals>.dummy')
            ]
        )
    ])
    run = TestRun(plan)
    controller = AutomaticTestRunController(run)

    try:
        run.run(controller)
    except:
        pass

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
    assert '"type": "TestException"' in j
