"""
Create a template for a test session. This is very similar to list-tests, but the output is to be used
as input for generate-testplan.
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

import feditest
from feditest.cli.utils import create_session_template_from_tests


def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    feditest.load_default_tests()
    feditest.load_tests_from(args.testsdir)

    session_template = create_session_template_from_tests(args)

    if args.out:
        session_template.save(args.out)
    else:
        session_template.print()

    return 0


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    # general flags and options
    parser = parent_parser.add_parser(cmd_name, help='Create a template for a test session')
    parser.add_argument('--testsdir', action='append', default=['tests'], help='Directory or directories where to find tests')

    # session template options
    parser.add_argument('--name', default=None, required=False, help='Name of the created test session template')
    parser.add_argument('--filter-regex', default=None, help='Only include tests whose name matches this regular expression')
    parser.add_argument('--test', action='append', help='Include this/these named tests(s)')

    # output options
    parser.add_argument('--out', '-o', default=None, required=False, help='Name of the file for the created test session template')

    return parser
