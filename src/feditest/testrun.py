"""
"""

from datetime import datetime, timezone
from typing import Any, Type

from feditest import all_app_drivers
from feditest.protocols import Node, NodeDriver
from feditest.reporting import info, fatal
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSession



class TestRunConstellation:
    def __init__(self, plan_constellation: TestPlanConstellation ):
        self.plan_constellation = plan_constellation
        self.run_constellation : dict[str, Node] | None = None

    def setup(self):
        info('Setting up constellation:', self.plan_constellation.name)
        
        for plan_role_name in self.plan_constellation.roles:
            app_driver_name : str = self.plan_constellation.roles[plan_role_name].appdriver
            app_driver_class : Type[Any] = all_app_drivers[app_driver_name]
            info('Setting up role', plan_role_name, f'(app driver: {app_driver_class})')
            app_driver : NodeDriver = app_driver_class()
            node : Node = app_driver.provision_node(plan_role_name)
            info('Node is', node)
            self.run_constellation[plan_role_name] = node

    def teardown(self):
        info('Tearing down constellation:', self.plan_constellation.name)

        for plan_role_name in self.plan_constellation.roles:
            app_driver = self.plan_constellation.roles[plan_role_name].appdriver
            info('Tearing down role', plan_role_name, f'(app driver: {app_driver})')
            
            node = self.run_constallation[plan_role_name]
            driver = node.node_driver
            driver.unprovision_node(node)


class TestRunSession:
    def __init__(self, name: str, plan_session: TestPlanSession):
        self.name = name
        self.plan_session = plan_session
        self.constellation = None

    def run(self):
        if len(self.plan_session.tests ):
            info('Running session:', self.name)
            
            self.constellation = TestRunConstellation(self.plan_session.constellation)
            self.constellation.setup()

            for testSpec in self.plan_session.tests:
                info('Running TestSpec', testSpec.name, '(disabled)' if testSpec.disabled else '' )
                
            self.constellation.teardown()

            if self.constellation.run_constellation:
                fatal( 'Still have nodes in the constellation', self.constellation.run_constellation )

            info('End running session:', self.name)

        else:
            info('Skipping session:', self.name, ': no tests defined')


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
