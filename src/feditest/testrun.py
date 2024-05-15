"""
Classes that represent a running TestPlan and its its parts.
"""

import getpass
import platform
import time
from abc import ABC
from datetime import UTC, datetime, timezone
import traceback
from typing import Any, Type, cast

import feditest.testruntranscript
import feditest.tests
from feditest.protocols import Node, NodeDriver
from feditest.reporting import error, fatal, info, trace, warning
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSession, TestPlanTestSpec
import feditest.testruncontroller
from feditest.testruntranscript import TestRunTranscript, TestRunSessionTranscript, TestRunTestTranscript, TestRunTestStepTranscript, TestRunResultTranscript


class TestRunConstellation:
    """
    The instance of a TestPlanConstellation associated with a particular test run.
    """
    def __init__(self, plan_constellation: TestPlanConstellation ):
        self._plan_constellation = plan_constellation
        self._run_constellation : dict[str, Node] = {}


    def setup(self) -> None:
        """
        Set up the constellation of nodes needed for some tests.
        """
        if self._plan_constellation.name:
            trace('Setting up constellation:', self._plan_constellation.name)
        else:
            trace('Setting up constellation')

        wait_time = 0
        for plan_role in self._plan_constellation.roles:
            if plan_role.nodedriver is None:
                raise ValueError('Unexpected null nodedriver')
            node_driver_class : Type[Any] = feditest.all_node_drivers[plan_role.nodedriver]

            trace('Setting up role', plan_role.name, f'(node driver: {plan_role.nodedriver})')

            node_driver : NodeDriver = node_driver_class(plan_role.name)
            parameters = plan_role.parameters if plan_role.parameters else {}
            node : Node = node_driver.provision_node(plan_role.name, parameters)
            if node:
                self._run_constellation[plan_role.name] = node
            else:
                raise Exception(f'NodeDriver {node_driver} returned null Node from provision_node()')

            if 'start-delay' in parameters:
                wait_time = max(wait_time, int(parameters['start-delay']))

        if wait_time:
            info(f'Sleeping for { wait_time } sec to give the Nodes some time to get ready.')
            time.sleep(wait_time) # Apparently some applications take some time
                                  # after deployment before they are ready to communicate.


    def teardown(self) -> None:
        if self._plan_constellation.name:
            trace('Tearing down constellation:', self._plan_constellation.name)
        else:
            trace('Tearing down constellation')

        for plan_role in reversed(self._plan_constellation.roles):
            plan_role.name = plan_role.name

            if plan_role.name in self._run_constellation: # setup may never have succeeded
                try:
                    trace('Tearing down role', plan_role.name)
                    node = self._run_constellation[plan_role.name]
                    node.node_driver.unprovision_node(node)
                    del self._run_constellation[plan_role.name]

                except Exception as e:
                    warning(f'Problem unprovisioning node {node}', e)


    def get_node(self, role_name: str) -> Node | None:
        return self._run_constellation.get(role_name)


class HasStartEndResults(ABC):
    def __init__(self) -> None:
        self.started : datetime | None = None
        self.ended : datetime | None = None
        self.exception : BaseException | None = None # If the item ended with a exception, here it is. None if no exception


class TestRunTest(HasStartEndResults):
    def __init__(self, run_session: 'TestRunSession', plan_test_index: int):
        super().__init__()
        self.run_session = run_session
        self.plan_test_index = plan_test_index


    @property
    def plan_testspec(self) -> TestPlanTestSpec:
        return self.run_session.plan_session.tests[self.plan_test_index]


    def outcome(self) -> BaseException | None:
        """
        Returns the exception that stopped the test, or None if all passed.
        """
        ...


class TestRunFunction(TestRunTest):
    def __init__(self, run_session: 'TestRunSession', test_from_test_function: feditest.TestFromTestFunction, plan_test_index: int):
        super().__init__(run_session, plan_test_index)
        self.test_from_test_function = test_from_test_function


    def __str__(self):
        return str(self.test_from_test_function)


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        self.started = datetime.now(UTC)
        info(f'Started TestRunFunction { self }')

        args = {}
        for local_role_name in self.test_from_test_function.needed_local_role_names():
            constellation_role_name = local_role_name
            if self.plan_testspec.rolemapping and local_role_name in self.plan_testspec.rolemapping:
                constellation_role_name = self.plan_testspec.rolemapping[local_role_name]
            args[local_role_name] = self.run_session.run_constellation.get_node(constellation_role_name) # type: ignore[union-attr]

        try:
            self.test_from_test_function.test_function(**args)

        except BaseException as e: # This should not happen
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended TestRunFunction { self } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended TestRunFunction { self }')


class TestRunStepInClass(HasStartEndResults):
    def __init__(self, run_test: 'TestRunClass', test_step: feditest.TestStepInTestClass, plan_step_index: int):
        super().__init__()
        self.run_test = run_test
        self.test_step = test_step
        self.plan_step_index = plan_step_index


    def __str__(self):
        return str(self.test_step)


    def run(self, test_instance: object, controller: feditest.testruncontroller.TestRunController) -> None:
        self.started = datetime.now(UTC)
        info(f'Started TestRunStepInClass { self }')

        try:
            self.test_step.test_step_function(test_instance) # what an object-oriented language this is

        except BaseException as e:
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended TestRunStepInClass { self } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended TestRunStepInClass { self }')


class TestRunClass(TestRunTest):
    def __init__(self, run_session: 'TestRunSession', test_from_test_class: feditest.TestFromTestClass, plan_test_index: int):
        super().__init__(run_session, plan_test_index)
        self.run_steps : list[TestRunStepInClass] = []
        self.test_from_test_class = test_from_test_class


    def __str__(self):
        return str(self.test_from_test_class)


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        self.started = datetime.now(UTC)
        info(f'Started TestRunClass { self }')

        args = {}
        for local_role_name in self.plan_testspec.needed_role_names():
            constellation_role_name = local_role_name
            if self.plan_testspec.rolemapping and local_role_name in self.plan_testspec.rolemapping:
                constellation_role_name = self.plan_testspec.rolemapping[local_role_name]
            args[local_role_name] = self.run_session.run_constellation.get_node(constellation_role_name) # type: ignore[union-attr]

        try:
            test_instance = self.test_from_test_class.clazz(**args)

            plan_step_index = controller.determine_next_test_step_index()
            while plan_step_index>=0 and plan_step_index<len(self.test_from_test_class.steps):
                plan_step : feditest.tests.TestStepInTestClass = self.test_from_test_class.steps[plan_step_index]
                run_step = TestRunStepInClass(self, plan_step, plan_step_index)
                self.run_steps.append(run_step)

                run_step.run(test_instance, controller)

                plan_step_index = controller.determine_next_session_index(plan_step_index)

        except feditest.testruncontroller.AbortTestException as e: # User input
            self.exception = e
            # we are done here
        except feditest.testruncontroller.AbortTestRunSessionException as e: # User input
            self.exception = e
            raise
        except feditest.testruncontroller.AbortTestRunException as e: # User input
            self.exception = e
            raise
        except BaseException as e: # This should not happen
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended TestRunClass { self } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended TestRunClass { self }')


class TestRunSession(HasStartEndResults):
    def __init__(self, the_run: 'TestRun', plan_session_index: int):
        super().__init__()
        self.the_run = the_run
        self.plan_session_index = plan_session_index
        self.run_tests : list[TestRunTest] = []
        self.run_constellation : TestRunConstellation | None = None


    @property
    def plan_session(self) -> TestPlanSession:
        return self.the_run.plan.sessions[self.plan_session_index]


    def __str__(self):
        return f'{ self.plan_session }'


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        """
        Run a TestSession.

        return: the number of tests run, or a negative number to signal that not all tests were run or completed
        """
        self.started = datetime.now(UTC)
        info(f'Started TestRunSession for TestPlanSession { self }')

        try:
            plan_test_index = controller.determine_next_test_index()
            while plan_test_index>=0 and plan_test_index<len(self.plan_session.tests):
                try:
                    test_spec = self.plan_session.tests[plan_test_index]

                    if test_spec.disabled:
                        info('Skipping Test:', test_spec.disabled)
                    else:
                        test = test_spec.get_test()
                        run_test : TestRunTest | None = None
                        if isinstance(test, feditest.TestFromTestFunction):
                            run_test = TestRunFunction(self, test, plan_test_index)
                        elif isinstance(test, feditest.TestFromTestClass):
                            run_test = TestRunClass(self, test, plan_test_index)
                        else:
                            fatal('What is this?', test)
                            return # does not actually return, but makes lint happy

                        self.run_tests.append(run_test)

                        if not self.run_constellation:
                            # only allocate the constellation if we actually want to run a test
                            self.run_constellation = TestRunConstellation(self.plan_session.constellation)
                            self.run_constellation.setup()

                        run_test.run(controller)

                    plan_test_index = controller.determine_next_test_index(plan_test_index)

                except feditest.testruncontroller.AbortTestException as e:
                    self.exception = e
                    break

        except feditest.testruncontroller.AbortTestRunSessionException as e: # User input
            self.exception = e
            # we are done here
        except feditest.testruncontroller.AbortTestRunException as e: # User input
            self.exception = e
            raise
        except BaseException as e: # This should not happen
            self.exception = e
        finally:
            if self.run_constellation:
                self.run_constellation.teardown()
                if self.run_constellation._run_constellation:
                    fatal( 'Still have nodes in the constellation', self.run_constellation._run_constellation )
            else:
                info(f'Skipping TestRunSession { self }: no tests')

            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended TestRunSession { self } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended TestRunSession { self }')


class TestRun(HasStartEndResults):
    """
    Encapsulates the state of a test run while feditest is executing a TestPlan
    """
    def __init__(self, plan: TestPlan):
        super().__init__()
        self.plan = plan
        self.id : str = 'feditest-run-' + datetime.now(timezone.utc).strftime( "%Y-%m-%dT%H:%M:%S.%fZ")
        self.platform : str = platform.platform()
        self.username : str = getpass.getuser()
        self.hostname : str = platform.node()
        self.run_sessions : list[TestRunSession] = []


    def __str__(self):
        if self.plan.name:
            return f'{ self.id } ({ self.plan.name })'
        return self.id


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        """
        Run a TestPlan.

        return: the number of sessions run, or a negative number to signal that not all sessions were run or completed
        """
        self.started = datetime.now(UTC)
        info(f'Started TestRun { self }')

        try:
            plan_session_index = controller.determine_next_session_index()
            while plan_session_index >=0 and plan_session_index<len(self.plan.sessions):
                run_session = TestRunSession(self, plan_session_index)
                self.run_sessions.append(run_session) # always append, even if we run the session plan session again

                run_session.run(controller)

                plan_session_index = controller.determine_next_session_index(plan_session_index)

            return

        except feditest.testruncontroller.AbortTestRunException as e: # User input
            self.exception = e
            # we are done here
        except BaseException as e: # This should not happen
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended TestRun { self } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended TestRun { self }')


    def transcribe(self) -> TestRunTranscript:
        trans_sessions = []
        for run_session in self.run_sessions:
            trans_tests : list[TestRunTestTranscript] = []
            for run_test in run_session.run_tests:
                if isinstance(run_test, TestRunClass):
                    trans_steps = []
                    for run_step in run_test.run_steps:
                        trans_steps.append(TestRunTestStepTranscript(
                                run_step.plan_step_index,
                                cast(datetime, run_step.started),
                                cast(datetime, run_step.ended),
                                TestRunResultTranscript.create_if_present(run_step.exception)))
                else:
                    trans_steps = None
                trans_tests.append(TestRunTestTranscript(
                        run_test.plan_test_index,
                        cast(datetime, run_test.started),
                        cast(datetime, run_test.ended),
                        TestRunResultTranscript.create_if_present(run_test.exception),
                        trans_steps))
            trans_sessions.append(TestRunSessionTranscript(
                    run_session.plan_session_index,
                    cast(datetime, run_session.started),
                    cast(datetime, run_session.ended),
                    trans_tests,
                    TestRunResultTranscript.create_if_present(run_session.exception)))

        ret = TestRunTranscript(
                self.plan,
                self.id,
                cast(datetime, self.started),
                cast(datetime, self.ended),
                self.platform,
                self.username,
                self.hostname,
                trans_sessions,
                TestRunResultTranscript.create_if_present(self.exception))
        return ret
