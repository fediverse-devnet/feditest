"""
"""

from datetime import datetime, timezone
from typing import Any, Type

from feditest import all_app_drivers, all_tests, Test
from feditest.protocols import Node, NodeDriver
from feditest.reporting import info, error, fatal
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSession, TestPlanTestSpec


class TestRunConstellation:
    def __init__(self, plan_constellation: TestPlanConstellation ):
        self.plan_constellation = plan_constellation
        self.run_constellation : dict[str, Node] = {}

    def setup(self):
        global all_app_drivers
        
        info('Setting up constellation:', self.plan_constellation.name)
        
        for plan_role in self.plan_constellation.roles:
            plan_role_name = plan_role.name
            app_driver_class : Type[Any] = all_app_drivers[plan_role.appdriver]
            info('Setting up role', plan_role_name, f'(app driver: {plan_role.appdriver})')

            app_driver : NodeDriver = app_driver_class(plan_role_name)
            node : Node = app_driver.provision_node(plan_role_name)
            info('Node is', node)
            self.run_constellation[plan_role_name] = node

    def teardown(self):
        info('Tearing down constellation:', self.plan_constellation.name)

        for plan_role in reversed(self.plan_constellation.roles):
            plan_role_name = plan_role.name
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

    def run(self):
        if len(self.plan_session.tests ):
            info('Running session:', self.name)
            
            try :
                self.constellation = TestRunConstellation(self.plan_session.constellation)
                self.constellation.setup()

                for test_spec in self.plan_session.tests:
                    if test_spec.disabled:
                        info('Skipping TestSpec', test_spec.disabled, "reason:", test_spec.disabled)
                    else:
                        self.run_test_spec(test_spec)

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

            match test_step.test.constellation_size:
                case 1:
                    test_step.function(run_constellation[plan_roles[0].name])
                case 2:
                    test_step.function(run_constellation[plan_roles[0].name], run_constellation[plan_roles[1].name])
                case _:
                    error( 'Not supported yet')
                


class TestRun:
    """
    Encapsulates the state of a test run while feditest is executing a TestPlan
    """
    def __init__(self, plan: TestPlan):
        self.plan = plan
        self.runid = datetime.now(timezone.utc).strftime( "%Y-%m-%dT%H:%M:%S.%f")

    def run(self):
        info( f'RUNNING test plan: {self.plan.name} (id: {self.runid})' )

        for i in range(0, len(self.plan.sessions)):
            plan_session = self.plan.sessions[i]
            run_session = TestRunSession(plan_session.name if plan_session.name else f'{self.plan.name}/{str(i)}', plan_session)

            run_session.run()
