"""
Run one or more tests
"""

from argparse import ArgumentParser, Namespace

def run(args: Namespace) -> None:
    """
    Run this command.
    """
    print( "Running run ..." )


def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Run one or more tests' )
    parser.add_argument('--testdir', nargs='*', default='tests', help='Directory or directories where to find testsets and tests')
    parser.add_argument('--iutdriverdir', nargs='*', default='iutdrivers', help='Directory or directories where to find drivers for Instances-under-test')
    parser.add_argument('--save-run-config-only', help='Do not run the test. Only save the run configuration to the specified file' )
    parser.add_argument('--run-config', help='Read the run configuration from the specified file')