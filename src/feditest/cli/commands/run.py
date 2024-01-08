"""
Run one or more tests
"""

from argparse import ArgumentParser, Namespace

import feditest

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> None:
    """
    Run this command.
    """

    return 1

def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Run one or more tests' )
    parser.add_argument('--testdir', nargs='*', default='tests', help='Directory or directories where to find testsets and tests')
    parser.add_argument('--iutdriverdir', nargs='*', default='iutdrivers', help='Directory or directories where to find drivers for Instances-under-test')

    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument('--save-test-plan-only', help='Do not run any tests. Only construct a test plan and save it to the specified file' )
    mode_group.add_argument('--run-test-plan', help='Read the test plan from the specified file')