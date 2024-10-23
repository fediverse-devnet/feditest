"""
Classes that represent a running TestPlan and its its parts.
"""

import getpass
import platform
import time
import traceback
from abc import ABC
from datetime import UTC, datetime, timezone
from typing import cast

import feditest.testruncontroller
import feditest.testruntranscript
import feditest.tests
from feditest.nodedrivers import AccountManager, Node, NodeConfiguration, NodeDriver
from feditest.registry import registry_singleton
from feditest.reporting import error, fatal, info, trace, warning
from feditest.testplan import (
    TestPlan,
    TestPlanConstellation,
    TestPlanConstellationNode,
    TestPlanSessionTemplate,
    TestPlanTestSpec,
)
from feditest.testruntranscript import (
    TestMetaTranscript,
    TestRunConstellationTranscript,
    TestRunNodeTranscript,
    TestRunResultTranscript,
    TestRunSessionTranscript,
    TestRunTestStepTranscript,
    TestRunTestTranscript,
    TestRunTranscript,
    TestStepMetaTranscript,
)
from feditest.tests import Test, TestFromTestClass

all_node_driver_singletons : dict[str,NodeDriver] = {}
""" Holds all NodeDriver singletons instantiated so far """


def nodedriver_singleton(name: str) -> NodeDriver:
    """
    Smart factory function for nodedrivers.
    """
    ret = all_node_driver_singletons.get(name)
    if ret is None:
        trace('Instantiating nodedriver singleton for', name)
        if name not in feditest.all_node_drivers:
            fatal(f'Cannot find a nodedriver with name: \"{ name }\"')
        node_driver_class = feditest.all_node_drivers[name]
        ret = node_driver_class()
        all_node_driver_singletons[name] = ret
    return ret


class TestRunConstellation:
    """
    The instance of a TestPlanConstellation associated with a particular test run.
    """
    def __init__(self, plan_constellation: TestPlanConstellation):
        self._plan_constellation = plan_constellation
        self._nodes : dict[str, Node] = {}
        self._appdata : dict[str, dict[str, str | None]] = {} # Record what apps and versions are running here. Preserved beyond teardown.


    def setup(self) -> None:
        """
        Set up the constellation of nodes needed for some tests.
        """
        if self._plan_constellation.name:
            trace('Setting up constellation:', self._plan_constellation.name)
        else:
            trace('Setting up constellation')

        # Two stages:
        # 1. check
        # 2. instantiate
        role_to_config_account_mgr : dict[str, tuple[NodeConfiguration,AccountManager | None]] = {}
        for plan_role_name, plan_node in self._plan_constellation.roles.items():
            if plan_node is None:
                raise ValueError('Unexpected null node')
            if plan_node.nodedriver is None:
                raise ValueError('Unexpected null nodedriver')

            node_driver : NodeDriver = nodedriver_singleton(plan_node.nodedriver)
            config_account_mgr = node_driver.create_configuration_account_manager(plan_role_name, plan_node) # may raise
            role_to_config_account_mgr[plan_role_name] = config_account_mgr

        wait_time = 0.0
        for plan_role_name, plan_node in self._plan_constellation.roles.items():
            if plan_node is None: # It's either repeat this here or do a cast to make the linter happy
                raise ValueError('Unexpected null node')
            if plan_node.nodedriver is None:
                raise ValueError('Unexpected null nodedriver')

            node_driver = nodedriver_singleton(plan_node.nodedriver)
            config_account_mgr = role_to_config_account_mgr[plan_role_name]
            config = config_account_mgr[0]
            account_mgr = config_account_mgr[1]
            node : Node = node_driver.provision_node(plan_role_name, config, account_mgr)
            self._nodes[plan_role_name] = node
            self._appdata[plan_role_name] = { # FIXME? Replace this with the NodeConfiguration object instead?
                'app' : config.app,
                'app_version' : config.app_version
            }
            wait_time = max(wait_time, config.start_delay)

        if wait_time:
            info(f'Sleeping for { wait_time } sec to give the Nodes some time to get ready.')
            time.sleep(wait_time) # Apparently some applications take some time
                                  # after deployment before they are ready to communicate.

        # set up CA and distribute it to all nodes if needed
        registry = registry_singleton()
        root_cert = registry.root_cert_for_trust_root()
        if root_cert:
            registry.memoize_system_trust_root()
            registry.add_to_system_trust_root(root_cert)
            for node in self._nodes.values():
                node.add_cert_to_trust_store(root_cert)


    def teardown(self) -> None:
        if self._plan_constellation.name:
            trace('Tearing down constellation:', self._plan_constellation.name)
        else:
            trace('Tearing down constellation')

        registry = registry_singleton()
        root_cert = registry.root_cert_for_trust_root()
        for plan_role_name in self._plan_constellation.roles:
            if plan_role_name in self._nodes: # setup may never have succeeded
                trace('Tearing down role', plan_role_name)
                node = self._nodes[plan_role_name]
                if root_cert:
                    try:
                        node.remove_cert_from_trust_store(root_cert)
                    except Exception as e:
                        warning(f'Problem removing temporary CA cert from trust store on {node}', e)

                try:
                    node.node_driver.unprovision_node(node)
                    del self._nodes[plan_role_name]

                except Exception as e:
                    warning(f'Problem unprovisioning node {node}', e)
        registry.reset_system_trust_root_if_needed()


    def get_node(self, role_name: str) -> Node | None:
        return self._nodes.get(role_name)


class HasStartEndResults(ABC):
    def __init__(self) -> None:
        self.started : datetime | None = None
        self.ended : datetime | None = None
        self.exception : Exception | None = None # If the item ended with a exception, here it is. None if no exception


class TestRunTest(HasStartEndResults):
    def __init__(self, run_session: 'TestRunSession', run_constellation: TestRunConstellation, plan_test_index: int):
        super().__init__()
        self.run_session = run_session
        self.run_constellation = run_constellation
        self.plan_test_index = plan_test_index


    @property
    def plan_testspec(self) -> TestPlanTestSpec:
        return self.run_session.plan_session.tests[self.plan_test_index]


    def outcome(self) -> Exception | None:
        """
        Returns the exception that stopped the test, or None if all passed.
        """
        ...


class TestRunFunction(TestRunTest):
    def __init__(self, run_session: 'TestRunSession', run_constellation: TestRunConstellation, test_from_test_function: feditest.TestFromTestFunction, plan_test_index: int):
        super().__init__(run_session, run_constellation, plan_test_index)
        self.test_from_test_function = test_from_test_function


    def __str__(self):
        return str(self.test_from_test_function)


    def str_in_session(self):
        return f'{ self.test_from_test_function } in { self.run_session }'


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        self.started = datetime.now(UTC)
        info(f'Started test { self.str_in_session() }')

        args = {}
        for local_role_name in self.test_from_test_function.needed_local_role_names():
            constellation_role_name = local_role_name
            if self.plan_testspec.rolemapping and local_role_name in self.plan_testspec.rolemapping:
                constellation_role_name = self.plan_testspec.rolemapping[local_role_name]
            args[local_role_name] = self.run_constellation.get_node(constellation_role_name) # type: ignore[union-attr]

        try:
            self.test_from_test_function.test_function(**args)

        except Exception as e:
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended test { self.str_in_session() } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended test { self.str_in_session() }')


class TestRunStepInClass(HasStartEndResults):
    def __init__(self, run_test: 'TestRunClass', test_step: feditest.TestStepInTestClass, plan_step_index: int):
        super().__init__()
        self.run_test = run_test
        self.test_step = test_step
        self.plan_step_index = plan_step_index


    def __str__(self):
        return str(self.test_step)


    def str_in_session(self):
        return f'{ self.test_step } in { self.run_test.run_session }'


    def run(self, test_instance: object, controller: feditest.testruncontroller.TestRunController) -> None:
        self.started = datetime.now(UTC)
        info(f'Started step { self.str_in_session() }')

        try:
            self.test_step.test_step_function(test_instance)

        except Exception as e:
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended step { self.str_in_session() } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended step { self.str_in_session() }')


class TestRunClass(TestRunTest):
    def __init__(self, run_session: 'TestRunSession', run_constellation: TestRunConstellation, test_from_test_class: feditest.TestFromTestClass, plan_test_index: int):
        super().__init__(run_session, run_constellation, plan_test_index)
        self.run_steps : list[TestRunStepInClass] = []
        self.test_from_test_class = test_from_test_class


    def __str__(self):
        return str(self.test_from_test_class)


    def str_in_session(self):
        return f'{ self.test_from_test_class } in { self.run_session }'


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        self.started = datetime.now(UTC)
        info(f'Started test { self.str_in_session() }')

        args = {}
        for local_role_name in self.plan_testspec.get_test().needed_local_role_names():
            constellation_role_name = local_role_name
            if self.plan_testspec.rolemapping and local_role_name in self.plan_testspec.rolemapping:
                constellation_role_name = self.plan_testspec.rolemapping[local_role_name]
            args[local_role_name] = self.run_constellation.get_node(constellation_role_name) # type: ignore[union-attr]

        try:
            test_instance = self.test_from_test_class.clazz(**args)

            plan_step_index = controller.determine_next_test_step_index()
            while plan_step_index>=0 and plan_step_index<len(self.test_from_test_class.steps):
                plan_step = self.test_from_test_class.steps[plan_step_index]
                run_step = TestRunStepInClass(self, plan_step, plan_step_index)
                self.run_steps.append(run_step)

                run_step.run(test_instance, controller)

                if run_step.exception:
                    break

                plan_step_index = controller.determine_next_test_step_index(plan_step_index)

        except feditest.testruncontroller.AbortTestException as e: # User input
            self.exception = e
            # we are done here
        except feditest.testruncontroller.AbortTestRunSessionException as e: # User input
            self.exception = e
            raise
        except feditest.testruncontroller.AbortTestRunException as e: # User input
            self.exception = e
            raise
        except Exception as e: # This should not happen
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended test { self.str_in_session() } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended test { self.str_in_session() }')


class TestRunSession(HasStartEndResults):
    def __init__(self, the_run: 'TestRun', plan_constellation_index: int):
        super().__init__()
        self.the_run = the_run
        self.plan_constellation_index = plan_constellation_index
        self.run_tests : list[TestRunTest] = []
        self.run_constellation : TestRunConstellation | None = None # keep around for transcript


    @property
    def plan_session(self) -> TestPlanSessionTemplate:
        return self.the_run.plan.session_template


    def __str__(self):
        return f'{ self.plan_session }'


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        """
        Run a TestSession.

        return: the number of tests run, or a negative number to signal that not all tests were run or completed
        """
        self.started = datetime.now(UTC)

        try:
            plan_test_index = controller.determine_next_test_index()
            while plan_test_index>=0 and plan_test_index<len(self.plan_session.tests):
                try:
                    test_spec = self.plan_session.tests[plan_test_index]

                    if test_spec.skip:
                        info('Skipping Test:', test_spec.skip)
                    else:
                        if not self.run_constellation:
                            # only allocate the constellation if we actually want to run a test
                            self.run_constellation = TestRunConstellation(self.the_run.plan.constellations[self.plan_constellation_index])
                            self.run_constellation.setup()

                        test = test_spec.get_test()
                        run_test : TestRunTest | None = None
                        if isinstance(test, feditest.TestFromTestFunction):
                            run_test = TestRunFunction(self, self.run_constellation, test, plan_test_index)
                        elif isinstance(test, feditest.TestFromTestClass):
                            run_test = TestRunClass(self, self.run_constellation, test, plan_test_index)
                        else:
                            fatal('What is this?', test)
                            return # does not actually return, but makes lint happy

                        self.run_tests.append(run_test) # constellation.setup() may raise, so don't add before that

                        run_test.run(controller)

                    plan_test_index = controller.determine_next_test_index(plan_test_index)

                except feditest.testruncontroller.AbortTestException as e:
                    self.exception = e
                    break

            if len(self.run_tests) == 0:
                fatal("No test results. Check for test errors. No transcript written.")

        except feditest.testruncontroller.AbortTestRunSessionException as e: # User input
            self.exception = e
            # we are done here
        except feditest.testruncontroller.AbortTestRunException as e: # User input
            self.exception = e
            raise
        except Exception as e: # This should not happen
            self.exception = e
        finally:
            if self.run_constellation:
                self.run_constellation.teardown()
                if self.run_constellation._nodes:
                    fatal( 'Still have nodes in the constellation', self.run_constellation._nodes )
            else:
                info(f'Skipping TestRunSession { self }: no tests')

            self.ended = datetime.now(UTC)
            if self.exception:
                if isinstance(self.exception, OSError):
                    error(f'Ended TestRunSession { self } with Exception: {self.exception}')
                else:
                    error(f'Ended TestRunSession { self } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended TestRunSession { self }')


class TestRun(HasStartEndResults):
    """
    Encapsulates the state of a test run while feditest is executing a TestPlan
    """
    def __init__(self, plan: TestPlan, record_who: bool = False):
        super().__init__()
        self.plan = plan
        self.id : str = 'feditest-run-' + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.platform : str = platform.platform()
        self.run_sessions : list[TestRunSession] = []
        self.username : str | None = None
        self.hostname : str | None = None
        if record_who:
            self.username = getpass.getuser()
            self.hostname = platform.node()


    def __str__(self):
        if self.plan.name:
            return f'{ self.id } ({ self.plan.name })'
        return self.id


    def run(self, controller: feditest.testruncontroller.TestRunController) -> None:
        """
        Run a TestPlan.
        """
        self.started = datetime.now(UTC)
        info(f'Started TestRun { self }')

        try:
            plan_constellation_index = controller.determine_next_constellation_index()
            while plan_constellation_index >=0 and plan_constellation_index<len(self.plan.constellations):
                run_session = TestRunSession(self, plan_constellation_index)
                self.run_sessions.append(run_session) # always append, even if we run the session plan session again

                run_session.run(controller)

                plan_constellation_index = controller.determine_next_constellation_index(plan_constellation_index)

            return

        except feditest.testruncontroller.AbortTestRunException as e: # User input
            self.exception = e
            # we are done here
        except Exception as e: # This should not happen
            self.exception = e
        finally:
            self.ended = datetime.now(UTC)
            if self.exception:
                error(f'Ended TestRun { self } with Exception:\n' + ''.join(traceback.format_exception(self.exception)))
            else:
                info(f'Ended TestRun { self }')


    def transcribe(self) -> TestRunTranscript:
        trans_sessions = []
        trans_test_metas = {}
        for run_session in self.run_sessions:
            nodes_transcript: dict[str, TestRunNodeTranscript] = {}
            run_constellation = cast(TestRunConstellation, run_session.run_constellation)
            for node_role, appdata in run_constellation._appdata.items():
                node = cast(TestPlanConstellationNode, run_constellation._plan_constellation.roles[node_role])
                nodes_transcript[node_role] = TestRunNodeTranscript(appdata, cast(str, node.nodedriver))
            trans_constellation = TestRunConstellationTranscript(nodes_transcript)
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
                test : Test = run_test.plan_testspec.get_test()
                if test.name not in trans_test_metas: # If we have it already, it's the same
                    if isinstance(test, TestFromTestClass):
                        meta_steps = []
                        for test_step in test.steps:
                            meta_steps.append(TestStepMetaTranscript(test_step.name, test_step.description))
                    else:
                        meta_steps = None
                    trans_test_metas[test.name] = TestMetaTranscript(test.name, test.needed_local_role_names(), meta_steps, test.description)

            trans_sessions.append(TestRunSessionTranscript(
                    run_session.plan_constellation_index,
                    cast(datetime, run_session.started),
                    cast(datetime, run_session.ended),
                    trans_constellation,
                    trans_tests,
                    TestRunResultTranscript.create_if_present(run_session.exception)))

        ret = TestRunTranscript(
                self.plan,
                self.id,
                cast(datetime, self.started),
                cast(datetime, self.ended),
                trans_sessions,
                trans_test_metas,
                TestRunResultTranscript.create_if_present(self.exception),
                self.platform,
                self.username,
                self.hostname)
        return ret
