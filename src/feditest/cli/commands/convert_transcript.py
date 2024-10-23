"""
Convert a TestRunTranscript to a different format
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

from feditest.reporting import warning
from feditest.testruntranscript import TestRunTranscript
from feditest.testruntranscriptserializer.json import JsonTestRunTranscriptSerializer
from feditest.testruntranscriptserializer.html import HtmlRunTranscriptSerializer
from feditest.testruntranscriptserializer.summary import SummaryTestRunTranscriptSerializer
from feditest.testruntranscriptserializer.tap import TapTestRunTranscriptSerializer
from feditest.utils import FEDITEST_VERSION

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """

    transcript = TestRunTranscript.load(args.in_file)
    if not transcript.is_compatible_type():
        warning(f'Transcript has unexpected type { transcript.type }: incompatibilities may occur.')

    if not transcript.has_compatible_version():
        warning(f'Transcript was created by FediTest { transcript.feditest_version }, you are running FediTest { FEDITEST_VERSION }: incompatibilities may occur.')

    if isinstance(args.html, str):
        HtmlRunTranscriptSerializer(args.template_path).write(transcript, args.html)
    elif args.html:
        warning('--html requires a filename: skipping')
    elif args.template_path:
        warning('--template-path only supported with --html. Ignoring.')

    if isinstance(args.tap, str) or args.tap:
        TapTestRunTranscriptSerializer().write(transcript, args.tap)

    if isinstance(args.json, str) or args.json:
        JsonTestRunTranscriptSerializer().write(transcript, args.json)

    if isinstance(args.summary, str) or args.summary:
        SummaryTestRunTranscriptSerializer().write(transcript, args.summary)

    return 0


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='Convert a transcript of a TestRun to a different format')
    parser.add_argument('--in', required=True, dest="in_file", help='JSON file containing the transcript')
    parser.add_argument('--tap', nargs="?", const=True, default=False,
                        help="Write results in TAP format to stdout, or to the provided file (if given).")
    html_group = parser.add_argument_group('html', 'HTML options')
    html_group.add_argument('--html',
                        help="Write results in HTML format to the provided file.")
    html_group.add_argument('--template-path', required=False,
                        help="When specifying --html, use this template path override (comma separated directory names)")
    parser.add_argument('--json', nargs="?", const=True, default=False,
                        help="Write results in JSON format to stdout, or to the provided file (if given).")
    parser.add_argument('--summary', nargs="?", const=True, default=False,
                        help="Write summary to stdout, or to the provided file (if given). This is the default if no other output option is given")

    return parser
