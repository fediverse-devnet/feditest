"""
Run one or more tests
"""

from argparse import ArgumentParser, Namespace

from feditest.testplan import load

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> None:
    """
    Run this command.
    """
    plan = load(args.testplan)
    print( 'Running ' + repr(plan))

    return 1

def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Run one or more tests' )
    parser.add_argument('--testdir', nargs='*', default='tests', help='Directory or directories where to find testsets and tests')
    parser.add_argument('--appdriverdir', nargs='*', default='appdrivers', help='Directory or directories where to find drivers for applications that can be tested')
    parser.add_argument('--testplan', default='feditest-default.json', help='Name of the file that contains the test plan to run')
