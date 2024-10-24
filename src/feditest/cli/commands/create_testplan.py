"""
Create a test plan.
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction
import feditest
from feditest.cli.utils import create_plan_from_session_and_constellations
from feditest.reporting import fatal

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    feditest.load_default_tests()
    feditest.load_tests_from(args.testsdir)

    test_plan = create_plan_from_session_and_constellations(args)
    if test_plan:
        if args.out:
            test_plan.save(args.out)
        else:
            test_plan.print()
    else:
        fatal('Failed to create test plan from the provided arguments')

    return 0


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    # general flags and options
    parser = parent_parser.add_parser(cmd_name, help='Create a test plan by running all provided test sessions in all provided constellations')
    parser.add_argument('--testsdir', action='append', default=['tests'], help='Directory or directories where to find tests')

    # test plan options
    parser.add_argument('--name', default=None, required=False, help='Name of the generated test plan')
    parser.add_argument('--constellation', action='append', help='File(s) each containing a JSON fragment defining a constellation')
    parser.add_argument('--session', '--session-template', required=False, help='File containing a JSON fragment defining a test session')
    parser.add_argument('--node', action='append',
                        help="Use role=file to specify that the node definition in 'file' is supposed to be used for constellation role 'role'")
    parser.add_argument('--filter-regex', default=None, help='Only include tests whose name matches this regular expression')
    parser.add_argument('--test', action='append', help='Run this/these named tests(s)')

    # output options
    parser.add_argument('--out', '-o', default=None, required=False, help='Name of the file for the generated test plan')

    return parser
