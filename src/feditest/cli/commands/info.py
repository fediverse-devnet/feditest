"""
Provide information on a variety of objects
"""

from argparse import ArgumentParser, Namespace

def run(args: Namespace) -> None:
    """
    Run this command.
    """
    print( "Running info ..." )


def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Provide information on a variety of objects')
    parser.add_argument('--testdir', nargs='*', default='tests', help='Directory or directories where to find testsets and tests')
    parser.add_argument('--iutdriverdir', nargs='*', default='iutdrivers', help='Directory or directories where to find drivers for Instances-under-test')
    type_group = parser.add_mutually_exclusive_group(required=True)
    type_group.add_argument('--test',  help='Provide information about a test.')
    type_group.add_argument('--testset',  help='Provide information about a test set.')
    type_group.add_argument('--iutdriver',  help='Provide information about a driver for an instance-under-test.')

