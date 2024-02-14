"""
Run one or more tests
"""

from argparse import ArgumentParser, Namespace

import feditest
from feditest.testplan import TestPlan
from feditest.testrun import TestRun

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> None:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help();
        return 0

    feditest.load_tests_from(args.testsdir)
    if args.nodedriversdir:
        feditest.load_node_drivers_from(args.nodedriversdir)
    else:
        feditest.load_node_drivers_from(feditest.cli.default_node_drivers_dir) 

    plan = TestPlan.load(args.testplan)
    plan.check_can_be_executed();

    run = TestRun(plan)
    run.run()
    

def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Run one or more tests' )
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find testsets and tests')
    parser.add_argument('--testplan', default='feditest-default.json', help='Name of the file that contains the test plan to run')
    parser.add_argument('--nodedriversdir', action='append', help='Directory or directories where to find drivers for nodes that can be tested')
        # Can't set a default value, because action='append' adds to the default value, instead of replacing it
