"""
List the available tests
"""

from argparse import ArgumentParser, Namespace
import feditest

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    feditest.load_tests_from(args.testsdir)
    for name in sorted(feditest.all_tests.all().keys()):
        print(name)

    return 0

def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='List the available tests' )
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find testsets and tests')
