"""
Classes that represent a running TestPlan and its its parts.
"""

# pylint: disable=broad-exception-raised,broad-exception-caught,protected-access

import getpass
import platform
import sys
import time
from abc import ABC
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from typing import IO, Any, List, Protocol, Type

import feditest
from feditest.protocols import Node, NodeDriver
from feditest.reporting import error, fatal, info, trace, warning
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


    def teardown(self):
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


class TestRunSession:
    """
    A TestRun consists of one or more TestRunSessions, each of which spins up a constallation, the runs
    some tests and then tears itself down again. Then the next TestRunSession can run.
    """
    def __init__(self, name: str, plan_session: TestPlanSession):
        self.name = name
        self.problems : List[TestProblem] = []
        self._plan_session = plan_session
        self.constellation : TestRunConstellation | None = None


    def run(self):
        if len(self._plan_session.tests ):
            info(f'Running session "{ self.name }"')

            try:
                self.constellation = TestRunConstellation(self._plan_session.constellation)
                self.constellation.setup()

                for test_spec in self._plan_session.tests:
                    if test_spec.disabled:
                        info(f'Skipping test "{ test_spec.name }" because: {test_spec.disabled}' )
                    else:
                        self._run_test_spec(test_spec)
            finally:
                self.constellation.teardown()

            if self.constellation._run_constellation:
                fatal( 'Still have nodes in the constellation', self.constellation._run_constellation )

            info(f'End running session: "{ self.name }"')

        else:
            info(f'Skipping session "{ self.name }": no tests defined')


    def _run_test_spec(self, test_spec: TestPlanTestSpec):
        info(f'Running test "{ test_spec.name }"')
        test : feditest.Test | None = feditest.all_tests.get(test_spec.name)

        if test:
            test.run(test_spec, self)
        else:
            error(f'Test not found: { test_spec.name }')


@dataclass
class TestProblem(ABC):
    """Information about test failure/problem."""
    test: TestPlanTestSpec
    exc: Exception


@dataclass
class TestFunctionProblem(TestProblem):
    """Information about test failure/problem of a test defined as a function."""


    def __str__(self):
        return f"{ self.test.name }: {self.exc}"


@dataclass
class TestClassTestStepProblem(TestProblem):
    """Information about test failure/problem."""
    test_step: 'feditest.TestStep'


    def __str__(self):
        return f"{ self.test.name } / { self.test_step.name }: {self.exc}"


@dataclass
class TestFunctionProblem(TestProblem):
    """Information about test failure/problem of a test defined as a function."""


    def __str__(self):
        return f"{ self.test.name }: {self.exc}"


@dataclass
class TestClassTestStepProblem(TestProblem):
    """Information about test failure/problem."""
    test_step: 'feditest.TestStep'


    def __str__(self):
        return f"{ self.test.name } / { self.test_step.name }: {self.exc}"


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
            print("FAILED")
        summary = TestSummary.for_run(plan, run_sessions)
        print(f"Test plan: {plan.name or 'N/A'}")
        if metadata:
            print(f"Test metadata: {plan.name or 'N/A'}")
            for key, value in metadata.items():
                print(f"    {key}: {value}")
        for run_session, plan_session in zip(run_sessions, plan.sessions):
            for test in plan_session.tests:
                if problem := _get_problem(run_session, test):
                    print(f"Test failure: {run_session.name}/{test.name}")
                    for line in str(problem.exc).strip().split("\n"):
                        print(f"    {line}")
        print(f"Test summary: total={ summary.total }, passed={ summary.passed }, failed={ summary.failed }, skipped={ summary.skipped }")


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
            print(f"# test plan: {plan.name or 'N/A'}")
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


def _get_problem(run_session, test: TestPlanTestSpec) -> TestProblem | None:
    return next((p for p in run_session.problems if p.test.name == test.name), None)


class TestRun:
    """
    Encapsulates the state of a test run while feditest is executing a TestPlan
    """
    def __init__(self, plan: TestPlan, result_writer: TestResultWriter | None = None):
        self._plan = plan
        self._result_writer = result_writer or DefaultTestResultWriter()
        self._runid : str = 'feditest-run-' + datetime.now(timezone.utc).strftime( "%Y-%m-%dT%H:%M:%S.%f")


    def run(self) -> int:
        if self._plan.name:
            info( f'Running test plan: "{ self._plan.name }" (id: "{ self._runid }")' )
        else:
            info( f'Running test plan (id: "{ self._runid }")' )

        run_sessions: list[TestRunSession] = []

        for i, plan_session in enumerate(self._plan.sessions):
            session_name = f'{self._plan.name}/{str(i)}' if self._plan.name else f'session_{ i }'
            run_session = TestRunSession(session_name, plan_session)
            run_session.run()
            run_sessions.append(run_session)

        metadata = {
            "timestamp": datetime.now(UTC),
            "platform": platform.platform(),
            "username": getpass.getuser(),
            "hostname": platform.node()
        }

        self._result_writer.write(self._plan, run_sessions, metadata=metadata)

        all_passed = all(not s.problems for s in run_sessions)
        return 0 if all_passed else 1
