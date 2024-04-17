"""
Classes that represent a running TestPlan and its its parts.
"""

# pylint: disable=protected-access

import os
import sys
import time
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import IO, Any, List, Protocol, Type

from feditest import Test, all_node_drivers, all_tests
from feditest.protocols import Node, NodeDriver
from feditest.reporting import error, fatal, info
from feditest.testplan import (
    TestPlan,
    TestPlanConstellation,
    TestPlanSession,
    TestPlanTestSpec,
)


class TestRunConstellation:
    """
    The instance of a TestPlanConstellation associated with a particular test run.
    """
    def __init__(self, plan_constellation: TestPlanConstellation ):
        self._plan_constellation = plan_constellation
        self._run_constellation : dict[str, Node] = {}

    def setup(self):
        """
        Set up the constellation of nodes needed for some tests.
        """

        info('Setting up constellation:', self._plan_constellation.name)

        for plan_role in self._plan_constellation.roles:
            plan_role_name = plan_role.name
            node_driver_class : Type[Any] = all_node_drivers[plan_role.nodedriver]

            info('Setting up role', plan_role_name, f'(node driver: {plan_role.nodedriver})')

            node_driver : NodeDriver = node_driver_class(plan_role_name)
            node : Node = node_driver.provision_node(plan_role_name, plan_role.hostname, plan_role.parameters)
            if node:
                self._run_constellation[plan_role_name] = node
            else:
                raise Exception(f'NodeDriver {node_driver} returned null Node from provision_node()')

        if not os.environ.get("UNIT_TESTING"):
            info('Sleeping for 10sec to give the Nodes some time to get ready.')
            time.sleep(10) # This is a fudge factor because apparently some applications take some time
                           # after deployment before they are ready to communicate.
                           # FIXME? This should potentially be in the NodeDrivers

    def teardown(self):
        info('Tearing down constellation:', self._plan_constellation.name)

        for plan_role in reversed(self._plan_constellation.roles):
            plan_role_name = plan_role.name

            if plan_role_name in self._run_constellation: # setup may never have succeeded
                info('Tearing down role', plan_role_name)
                node = self._run_constellation[plan_role_name]
                driver = node.node_driver()
                driver.unprovision_node(node)
                del self._run_constellation[plan_role_name]


class TestRunSession:
    """
    A TestRun consists of one or more TestRunSessions, each of which spins up a constallation, the runs
    some tests and then tears itself down again. Then the next TestRunSession can run.
    """
    def __init__(self, name: str, plan_session: TestPlanSession):
        self.name = name
        self.problems : List[Exception] = []
        self._plan_session = plan_session
        self._constellation = None

    def run(self):
        if len(self._plan_session.tests ):
            info('Running session:', self.name)

            try:
                self._constellation = TestRunConstellation(self._plan_session.constellation)
                self._constellation.setup()

                for test_spec in self._plan_session.tests:
                    if test_spec.disabled:
                        info('Skipping TestSpec', test_spec.disabled, "reason:", test_spec.disabled)
                    else:
                        try:
                            self._run_test_spec(test_spec)
                        except Exception as e:
                            error('FAILED test:', e)
                            self.problems.append(TestProblem(test_spec, e))
            finally:
                self._constellation.teardown()

            if self._constellation._run_constellation:
                fatal( 'Still have nodes in the constellation', self._constellation._run_constellation )

            info('End running session:', self.name)

        else:
            info('Skipping session:', self.name, ': no tests defined')


    def _run_test_spec(self, test_spec: TestPlanTestSpec):
        info('Running test', test_spec.name)
        test : Test = all_tests.get(test_spec.name)

        for test_step in test.steps:
            info('Running step', test_step.name )

            plan_roles = self._constellation._plan_constellation.roles
            run_constellation = self._constellation._run_constellation

            # FIXME: we should map the plan_roles to the names of the @test function parameters
            match len(plan_roles):
                case 1:
                    test_step.function(run_constellation[plan_roles[0].name])
                case 2:
                    test_step.function(run_constellation[plan_roles[0].name],
                                       run_constellation[plan_roles[1].name])
                case 3:
                    test_step.function(run_constellation[plan_roles[0].name],
                                       run_constellation[plan_roles[1].name],
                                       run_constellation[plan_roles[2].name])
                case 4:
                    test_step.function(run_constellation[plan_roles[0].name],
                                       run_constellation[plan_roles[1].name],
                                       run_constellation[plan_roles[2].name],
                                       run_constellation[plan_roles[3].name])
                case _:
                    error( 'Constellation size not supported yet:', len(plan_roles))

@dataclass
class TestProblem:
    """Information about test failure/problem."""
    test: TestPlanTestSpec
    exc: Exception


class TestResultWriter(Protocol):
    """An object that writes test results in some format."""
    def write(self, plan: TestPlan, 
              run_sessions: list[TestRunSession], 
              metadata: dict[str, Any]|None = None):
        """Write test results."""
        ...

@dataclass
class TestSummary:
    total: int
    passed: int
    failed: int
    skipped: int

    @staticmethod
    def for_run(plan: TestPlan, run_sessions: list[TestRunSession]) -> "TestSummary":
        count = 0
        passed = 0
        failed = 0
        skipped = 0
        for run_session, plan_session in zip(run_sessions, plan.sessions):
            for test in plan_session.tests:
                count += 1
                if _get_problem(run_session, test):
                    failed += 1
                elif test.disabled:
                    skipped += 1
                else:
                    passed += 1
        return TestSummary(count, passed, failed, skipped)


class DefaultTestResultWriter:
    def write(
        self,
        plan: TestPlan,
        run_sessions: list[TestRunSession],
        metadata: dict[str, Any] | None = None,
    ):
        if any(s.problems for s in run_sessions):
            info("FAILED")
        summary = TestSummary.for_run(plan, run_sessions)
        info(
            "Test summary: total=%d, passed=%d, failed=%d, skipped=%d"
            % (
                summary.total,
                summary.passed,
                summary.failed,
                summary.skipped,
            )
        )


class TapTestResultWriter:
    def __init__(self, out: IO = sys.stdout):
        self.out = out

    def write(
        self,
        plan: TestPlan,
        run_sessions: list[TestRunSession],
        metadata: dict[str, Any] | None = None,
    ):
        with redirect_stdout(self.out):
            print("TAP version 14")
            print(f"# test plan: {plan.name}")
            if metadata:
                for key, value in metadata.items():
                    print(f"# {key}: {value}")
            # date, etc.
            test_id = 0
            for run_session, plan_session in zip(run_sessions, plan.sessions):
                print(f"# session: {run_session.name}")
                print(f"# constellation: {plan_session.constellation.name}")
                print(f"#   name: {plan_session.constellation.name}")
                print("#   roles:")
                for role in plan_session.constellation.roles:
                    print(f"#     - name: {role.name}")
                    print(f"#       driver: {role.nodedriver}")
                for test in plan_session.tests:
                    test_id += 1
                    if problem := _get_problem(run_session, test):
                        print(f"not ok {test_id} - {test.name}")
                        print("  ---")
                        print("  problem: |")
                        for line in str(problem.exc).strip().split("\n"):
                            print(f"    {line}")
                        print("  ...")
                    else:
                        directives = f" # SKIP {test.disabled}" if test.disabled else ""
                        print(f"ok {test_id} - {test.name}{directives}")
            print(f"1..{test_id}")
            summary = TestSummary.for_run(plan, run_sessions)
            print("# test run summary:")
            print(f"#   total: {summary.total}")
            print(f"#   passed: {summary.passed}")
            print(f"#   failed: {summary.failed}")
            print(f"#   skipped: {summary.skipped}")


def _get_problem(run_session, test: TestPlanTestSpec) -> TestProblem:
    return next((p for p in run_session.problems if p.test.name == test.name), None)


class TestRun:
    """
    Encapsulates the state of a test run while feditest is executing a TestPlan
    """
    def __init__(self, plan: TestPlan, result_writer: TestResultWriter):
        self._plan = plan
        self._result_writer = result_writer
        self._runid : str = 'feditest-run-' + datetime.now(timezone.utc).strftime( "%Y-%m-%dT%H:%M:%S.%f")

    def run(self):
        info( f'RUNNING test plan: {self._plan.name} (id: {self._runid})' )

        run_sessions: list[TestRunSession] = []

        for i in range(0, len(self._plan.sessions)): # pylint: disable=consider-using-enumerate
            plan_session = self._plan.sessions[i]
            run_session = TestRunSession(plan_session.name if plan_session.name else f'{self._plan.name}/{str(i)}', plan_session)
            run_session.run()
            run_sessions.append(run_session)

        self._result_writer.write(self._plan, run_sessions)

        all_passed = all(not s.problems for s in run_sessions)
        return 0 if all_passed else 1
