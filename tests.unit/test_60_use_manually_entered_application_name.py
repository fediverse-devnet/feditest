"""
Test that when the user enters an application name at the command-line, it shows up
in the report.
"""

import os
import os.path
import tempfile

import pytest
from bs4 import BeautifulSoup

import feditest
from feditest import test
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSessionTemplate, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController
from feditest.testruntranscript import TestRunResultTranscript
from feditest.testruntranscriptserializer.html import HtmlRunTranscriptSerializer

APP_NAMES = [
    'SENDER_APP_1',
    'RECEIVER_APP_1',
    'SENDER_APP_2',
    'RECEIVER_APP_2'
]

# Use the default NodeDrivers

@pytest.fixture(scope="module", autouse=True)
def init_node_drivers():
    """
    Cleanly define the NodeDrivers.
    """
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


@pytest.fixture(scope="module", autouse=True)
def test_plan_fixture() -> TestPlan:
    """
    The test plan tests all known tests.
    """
    constellations = [
        TestPlanConstellation(
            {
                'sender_node': TestPlanConstellationNode(
                    'FediverseSaasNodeDriver',
                    {
                        'app' : APP_NAMES[0],
                        'hostname' : 'senderA'
                    }),
                'receiver_node': TestPlanConstellationNode(
                    'FediverseSaasNodeDriver',
                    {
                        'app' : APP_NAMES[1],
                        'hostname' : 'senderB'
                    })
            },
            'constellation-1'),
        TestPlanConstellation(
            {
                'sender_node': TestPlanConstellationNode(
                    'FediverseSaasNodeDriver',
                    {
                        'app' : APP_NAMES[2],
                        'hostname' : 'senderA'
                    }),
                'receiver_node': TestPlanConstellationNode(
                    'FediverseSaasNodeDriver',
                    {
                        'app' : APP_NAMES[3],
                        'hostname' : 'senderB'
                    })
            },
            'constellation-2')
    ]
    tests = [ TestPlanTestSpec(name) for name in sorted(feditest.all_tests.keys()) if feditest.all_tests.get(name) is not None ]
    session = TestPlanSessionTemplate(tests, "Test a test that passes")
    ret = TestPlan(session, constellations)
    ret.properties_validate()
    # ret.print()
    return ret


@pytest.fixture(scope="module")
def transcript(test_plan_fixture: TestPlan) -> TestRunResultTranscript:
    test_plan_fixture.check_can_be_executed()

    test_run = TestRun(test_plan_fixture)
    controller = AutomaticTestRunController(test_run)
    test_run.run(controller)

    ret = test_run.transcribe()
    return ret


@pytest.fixture(scope="module")
def html_base_name(transcript: TestRunResultTranscript) -> str:
    def gen(tmpdirname: str) -> str:
        outbase = f'{ tmpdirname }/htmlout'
        HtmlRunTranscriptSerializer().write(transcript, f'{ outbase }.html')
        return outbase

    if False: # Change this to False if you want to see what is being generated
        with tempfile.TemporaryDirectory() as tmpdirname:
            ret = gen(tmpdirname)
            yield ret
            # The yield will cause the TemporaryDirectory to be deleted at the end of the test
        return None

    else:
        dir = f'/tmp/{ os.path.basename(__file__)[:-3] }' # without extension
        os.makedirs(dir, exist_ok=True)
        ret =  gen(dir) # without extension
        yield ret # apparently yielding from one branch, and not the other does not work
        return None


@pytest.fixture(scope="module")
def main_html_soup(html_base_name: str) -> BeautifulSoup:
    content = None
    with open(f'{ html_base_name }.html') as fd:
        content = fd.read()

    ret = BeautifulSoup(content, 'html.parser')
    # print(ret.prettify())
    return ret


@pytest.fixture(scope="module")
def session0_html_soup(html_base_name: str) -> BeautifulSoup:
    content = None
    with open(f'{ html_base_name }.0.html') as fd:
        content = fd.read()

    ret = BeautifulSoup(content, 'html.parser')
    # print(ret.prettify())
    return ret


## Main HTML doc

def test_main_title(main_html_soup: BeautifulSoup):
    title = main_html_soup.head.title.string

    # Don't have an empty string prior to the |
    assert title.split('|')[0].strip()

    # Don't have 'None" in the title
    assert 'None' not in title


def test_main_h1(main_html_soup: BeautifulSoup):
    # Don't have 'None" in the title
    *_, h1 = main_html_soup.body.header.h1.strings
    assert 'None' not in h1


def test_main_app_properties(main_html_soup: BeautifulSoup):
    # Use 'app' properties, not FediverseSaasNodeDriver
    for dl in main_html_soup.body.find_all('dl', class_='roles'):
        for dd in dl.find_all('dd'):
            assert dd.string in APP_NAMES

# Session HTML doc

def test_session0_title(session0_html_soup: BeautifulSoup):
    title = session0_html_soup.head.title.string

    # Don't have an empty string prior to the |
    assert title.split('|')[0].strip()

    # Don't have 'Session 0" in the title
    assert 'Session 0' not in title


def test_session0_h1(session0_html_soup: BeautifulSoup):
    *_, h1 = session0_html_soup.body.header.h1.strings

    # Don't have an empty string prior to the |
    assert h1.split('|')[0].strip()

    # Don't have 'Session 0" in the title
    assert 'Session 0' not in h1
