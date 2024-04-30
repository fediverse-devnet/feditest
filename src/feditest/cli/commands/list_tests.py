"""
List the available tests
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction
import re

import feditest

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    pattern = re.compile(args.filter_regex) if args.filter_regex else None

    feditest.load_tests_from(args.testsdir)
<<<<<<< HEAD
    for name in sorted(feditest.all_tests.all().keys()):
=======
    for name in sorted(feditest.all_tests.keys()):
>>>>>>> cc174835d7893d31fb9ed08b1e70b8befed7aa9e
        if pattern is None or pattern.match(name):
            print(name)

    return 0

def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='List the available tests')
    parser.add_argument('--filter-regex', default=None, help='Only list tests whose name matches this regular expression')
<<<<<<< HEAD
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find testsets and tests')
=======
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find tests')
>>>>>>> cc174835d7893d31fb9ed08b1e70b8befed7aa9e
