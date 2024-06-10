"""
Generate a test plan
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction
import feditest
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanSession


def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    feditest.load_tests_from(args.testsdir)

    constellations = []
    for constellation_file in args.constellation:
        constellations.append(TestPlanConstellation.load(constellation_file))

    session_templates = []
    for session_file in args.session:
        session_templates.append(TestPlanSession.load(session_file))

    test_plan = TestPlan([], args.name)
    for session_template in session_templates:
        for constellation in constellations:
            session = session_template.instantiate_with_constellation(constellation, constellation.name)
            test_plan.sessions.append(session)

    test_plan.simplify()
    if args.out:
        test_plan.save(args.out)
    else:
        test_plan.print()

    return 0


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='Generate a test plan by running all provided test sessions in all provided constellations')
    parser.add_argument('--name', default=None, required=False, help='Name of the generated test plan')
    parser.add_argument('--constellation', required=True, nargs='+', help='File(s) each containing a JSON fragment defining a constellation')
    parser.add_argument('--session', '--session-template', required=True, nargs='+', help='File(s) each containing a JSON fragment defining a test session')
    parser.add_argument('--out', '-o', default=None, required=False, help='Name of the file for the generated test plan')
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find testsets and tests')
