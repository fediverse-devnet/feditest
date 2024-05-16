"""
Run one or more tests
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

import feditest
from feditest.cli import default_node_drivers_dir
from feditest.testplan import TestPlan
from feditest.testruntranscript import HtmlTestRunTranscriptSerializer, JsonTestRunTranscriptSerializer, SummaryTestRunTranscriptSerializer, TapTestRunTranscriptSerializer, TestRunTranscriptSerializer
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController, InteractiveTestRunController
import feditest.testruntranscript

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

    test_run = TestRun(plan)
    controller = InteractiveTestRunController(test_run) if args.interactive else AutomaticTestRunController(test_run)
    test_run.run(controller)

    transcript : feditest.testruntranscript.TestRunTranscript = test_run.transcribe()

    summary_serializer = SummaryTestRunTranscriptSerializer(transcript)
    serializer : TestRunTranscriptSerializer | None = None
    if isinstance(args.tap, str) or args.tap:
        serializer = TapTestRunTranscriptSerializer(transcript)
        serializer.write(args.tap)

    if isinstance(args.html, str) or args.html:
        serializer = HtmlTestRunTranscriptSerializer(transcript, args.template)
        serializer.write(args.html)

    if isinstance(args.json, str) or args.json:
        serializer = JsonTestRunTranscriptSerializer(transcript)
        serializer.write(args.json)

    if isinstance(args.summary, str) or args.summary or serializer is None:
        summary_serializer.write(args.summary)

    if transcript.build_summary().n_failed > 0:
        print('FAILED.')
        return 1
    return 0


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
    parser.add_argument('--interactive', action="store_true",
                        help="Run the tests interactively")
    parser.add_argument('--tap', nargs="?", const=True, default=False,
                        help="Write results in TAP format to stdout, or to the provided file (if given).")
    html_group = parser.add_argument_group('html', 'HTML options')
    html_group.add_argument('--html', nargs="?", const=True, default=False,
                        help="Write results in HTML format to stdout, or to the provided file (if given).")
    html_group.add_argument('--template',
                        help="When specifying --html, use this HTML template (jinja2 format).")
    parser.add_argument('--json', nargs="?", const=True, default=False,
                        help="Write results in JSON format to stdout, or to the provided file (if given).")
    parser.add_argument('--summary', nargs="?", const=True, default=False,
                        help="Write summary to stdout, or to the provided file (if given). This is the default if no other output option is given")
