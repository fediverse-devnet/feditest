"""
Run one or more tests
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

import feditest
from feditest.cli import default_node_drivers_dir
from feditest.testplan import TestPlan
from feditest.testrun import HtmlTestResultWriter, TapTestResultWriter, TestRun


def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    feditest.load_tests_from(args.testsdir)
    if args.nodedriversdir:
        feditest.load_node_drivers_from(args.nodedriversdir)
    else:
        feditest.load_node_drivers_from(default_node_drivers_dir)

    plan = TestPlan.load(args.testplan)
    plan.check_can_be_executed()

    result_writer: object | None = None
    if isinstance(args.tap, str):
        with open(args.tap, "w", encoding="utf8") as out:
            result_writer = TapTestResultWriter(out)
            test_run = TestRun(plan, result_writer)
            return test_run.run()
    elif args.tap:
        if args.template:
            parser.print_help()
            return 0
        result_writer = TapTestResultWriter()
        test_run = TestRun(plan, result_writer)
        return test_run.run()
    elif isinstance(args.html, str):
        # TODO refactor to eliminate duplicate logic
        with open(args.html, "w", encoding="utf8") as out:
            result_writer = HtmlTestResultWriter(args.template, out)
            test_run = TestRun(plan, result_writer)
            return test_run.run()
    elif args.html:
        result_writer = HtmlTestResultWriter(args.template)
        test_run = TestRun(plan, result_writer)
        return test_run.run()
    else:
        test_run = TestRun(plan)
        return test_run.run()


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='Run one or more tests' )
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find tests')
    parser.add_argument('--testplan', default='feditest-default.json', help='Name of the file that contains the test plan to run')
    parser.add_argument('--nodedriversdir', action='append', help='Directory or directories where to find drivers for nodes that can be tested')
        # Can't set a default value, because action='append' adds to the default value, instead of replacing it
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument('--tap', nargs="?", const=True, default=False,
                        help="Use TAP test result format. Can also provide an optional filename for results. Default is standard out.")
    format_group.add_argument('--html', nargs="?", const=True, default=False,
                        help="Use HTML test result format. Can also provide an optional filename for results. Default is standard out.")
    parser.add_argument('--template', default='report-standalone.jinja2',
                        help="When specifying --html, use this HTML template (jinja2 format).")
    # I'm failing to create a group below the mutually_exclusive group that puts --html and --template together
