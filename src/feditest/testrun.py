"""
"""

from datetime import datetime, timezone
import time
from typing import Any, List, Type

from feditest import all_node_drivers, all_tests, Test
from feditest.protocols import Node, NodeDriver
from feditest.reporting import info, error, fatal
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSession, TestPlanTestSpec


class TestRunConstellation:
    def __init__(self, plan_constellation: TestPlanConstellation ):
        self.plan_constellation = plan_constellation
        self.run_constellation : dict[str, Node] = {}

    def setup(self):
        global all_node_drivers
        
        info('Setting up constellation:', self.plan_constellation.name)

        for plan_role in self.plan_constellation.roles:
            plan_role_name = plan_role.name
            node_driver_class : Type[Any] = all_node_drivers[plan_role.nodedriver]

            info('Setting up role', plan_role_name, f'(node driver: {plan_role.nodedriver})')

            node_driver : NodeDriver = node_driver_class(plan_role_name)
            node : Node = node_driver.provision_node(plan_role_name, plan_role.hostname, plan_role.parameters)
            self.run_constellation[plan_role_name] = node

    def teardown(self):
        info('Tearing down constellation:', self.plan_constellation.name)

        for plan_role in reversed(self.plan_constellation.roles):
            plan_role_name = plan_role.name
            
            if plan_role_name in self.run_constellation: # setup may never have succeeded
                info('Tearing down role', plan_role_name)
                node = self.run_constellation[plan_role_name]
                driver = node.node_driver
                driver.unprovision_node(node)        
                del self.run_constellation[plan_role_name]


class TestRunSession:
    def __init__(self, name: str, plan_session: TestPlanSession):
        self.name = name
        self.plan_session = plan_session
        self.constellation = None
        self.problems : List[Exception] = []

    def run(self):
        if len(self.plan_session.tests ):
            info('Running session:', self.name)
            
            try :
                self.constellation = TestRunConstellation(self.plan_session.constellation)
                self.constellation.setup()

                time.sleep(10) # FIXME?

                for test_spec in self.plan_session.tests:
                    if test_spec.disabled:
                        info('Skipping TestSpec', test_spec.disabled, "reason:", test_spec.disabled)
                    else:
                        self.run_test_spec(test_spec)
            except Exception as e:
                error('FAILED test run session:', e)
                self.problems.append(e)
            finally:        
                self.constellation.teardown()

            if self.constellation.run_constellation:
                fatal( 'Still have nodes in the constellation', self.constellation.run_constellation )

            info('End running session:', self.name)

        else:
            info('Skipping session:', self.name, ': no tests defined')

    def run_test_spec(self, test_spec: TestPlanTestSpec):
        global all_tests

        info('Running test', test_spec.name)
        test : Test = all_tests.get(test_spec.name)

        for test_step in test.steps:
            info('Running step', test_step.name )

            plan_roles = self.constellation.plan_constellation.roles
            run_constellation = self.constellation.run_constellation

            match len(plan_roles):
                case 1:
                    test_step.function(run_constellation[plan_roles[0].name])
                case 2:
                    test_step.function(run_constellation[plan_roles[0].name], run_constellation[plan_roles[1].name])
                case 3:
                    test_step.function(run_constellation[plan_roles[0].name], run_constellation[plan_roles[1].name], run_constellation[plan_roles[2].name])
                case 4:
                    test_step.function(run_constellation[plan_roles[0].name], run_constellation[plan_roles[1].name], run_constellation[plan_roles[2].name], run_constellation[plan_roles[3].name])
                case _:
                    error( 'Constellation size not supported yet:', len(plan_roles))
                


class TestRun:
    """
    Encapsulates the state of a test run while feditest is executing a TestPlan
    """
    def __init__(self, plan: TestPlan):
        self.plan = plan
        self.runid : str = 'feditest-run-' + datetime.now(timezone.utc).strftime( "%Y-%m-%dT%H:%M:%S.%f")

    def run(self):
        info( f'RUNNING test plan: {self.plan.name} (id: {self.runid})' )

        all_passed : bool = True
        for i in range(0, len(self.plan.sessions)):
            plan_session = self.plan.sessions[i]
            run_session = TestRunSession(plan_session.name if plan_session.name else f'{self.plan.name}/{str(i)}', plan_session)

            run_session.run()
            if len(run_session.problems):
                all_passed = False

        if not all_passed:
            info('FAILED')
