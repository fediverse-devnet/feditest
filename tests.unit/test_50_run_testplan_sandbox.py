"""
Run some sandbox protocol tests.
"""

from typing import List

from hamcrest import equal_to, close_to
import pytest

import feditest
from feditest import assert_that, step, test, SpecLevel
from feditest.protocols.sandbox import SandboxLogEvent, SandboxMultClient, SandboxMultServer
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSessionTemplate, TestPlanTestSpec
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
    These tests are the same as those run in "sandbox-all-clientA-vs-server1.json" from the feditest-tests-sandbox repo.
    """
    feditest.all_tests = {}
    feditest._registered_as_test = {}
    feditest._registered_as_test_step = {}
    feditest._loading_tests = True

    ##
    ## FediTest tests start here
    ##

    @test
    class ExampleTest1:
        """
        Tests the sandbox toy protocol using a FediTest test class.
        """
        def __init__(self,
            client: SandboxMultClient,
            server: SandboxMultServer
        ) -> None:
            self.client = client
            self.server = server

            # We put some test data into the test class instance to demonstrate how it can be passed
            # along several test steps, even if one or more of them fail (with a soft assertion error)

            self.a : float = 2.1
            self.b : int = 7


        @step
        def step1(self):
            self.server.start_logging()

            self.c : float = self.client.cause_mult(self.server, self.a, self.b)

            assert_that(self.c, close_to(15.0, 0.5))

            log: List[SandboxLogEvent] = self.server.get_and_clear_log()

            assert_that(len(log), equal_to(1))
            assert_that(log[0].a, equal_to(self.a))
            assert_that(log[0].b, equal_to(self.b))
            assert_that(log[0].c, equal_to(self.c))


        @step
        def step2(self):

            c_squared = self.client.cause_mult(self.server, self.c, self.c)

            assert_that(c_squared, close_to(self.c * self.c, 0.001), spec_level=SpecLevel.SHOULD)
            assert_that(c_squared, close_to(self.c * self.c, 0.5))


    @test
    def example_test1(
            client: SandboxMultClient,
            server: SandboxMultServer
    ) -> None:
        """
        Tests the sandbox toy protocol using a FediTest test function with hard asserts.
        """
        a : float = 2
        b : int = 7

        server.start_logging()

        c : float = client.cause_mult(server, a, b)

        assert_that(c, equal_to(14.0))

        log: List[SandboxLogEvent] = server.get_and_clear_log()

        assert_that(len(log), equal_to(1))
        assert_that(log[0].a, equal_to(a))
        assert_that(log[0].b, equal_to(b))
        assert_that(log[0].c, equal_to(c))


    @test
    def example_test2(
            client: SandboxMultClient,
            server: SandboxMultServer
    ) -> None:
        """
        Tests the sandbox toy protocol using a FedTest test function with hard asserts.
        """
        a : float = 2.1
        b : int = 7

        c : float = client.cause_mult(server, a, b)

        assert_that(c, close_to(14.7, 0.01), spec_level=SpecLevel.SHOULD)


    @test
    def example_test3(
            client: SandboxMultClient,
            server: SandboxMultServer
    ) -> None:
        """
        Tests the sandbox toy protocol using a FedTest test function.
        """
        a : int = -7
        b : int = 8

        c = client.cause_mult(server, a, b)

        assert_that(c, equal_to(a * b))

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
    roles = {
        'client' : TestPlanConstellationNode('SandboxMultClientDriver_ImplementationA'),
        'server' : TestPlanConstellationNode('SandboxMultServerDriver_Implementation1'),
    }
    constellation = TestPlanConstellation(roles, 'clientA vs server1')
    tests = [ TestPlanTestSpec(name) for name in sorted(feditest.all_tests.keys()) if feditest.all_tests.get(name) is not None ]
    session = TestPlanSessionTemplate(tests, "clientA vs server")
    ret = TestPlan(session, [ constellation ], "All sandbox tests running clientA against server1")
    return ret


def test_run_testplan(test_plan_fixture: TestPlan):
    test_plan_fixture.check_can_be_executed()

    test_run = TestRun(test_plan_fixture)
    controller = AutomaticTestRunController(test_run)
    test_run.run(controller)

    transcript = test_run.transcribe()

    assert transcript.build_summary().n_failed == 0

