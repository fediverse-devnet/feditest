"""
List the available test sets
"""

from argparse import ArgumentParser, Namespace

def run(args: Namespace) -> None:
    """
    Run this command.
    """
    print( """activitypub
fediverse
webfinger""")

def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='List the available test sets' )
    parser.add_argument('--testdir', nargs='*', default='tests', help='Directory or directories where to find testsets and tests')
