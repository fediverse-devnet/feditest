"""
Convert a TestRunTranscript to a different format
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

from feditest.reporting import warning
from feditest.testruntranscript import (
    JsonTestRunTranscriptSerializer,
    MultifileRunTranscriptSerializer,
    SummaryTestRunTranscriptSerializer,
    TapTestRunTranscriptSerializer,
    TestRunTranscript,
    TestRunTranscriptSerializer,
)
from feditest.utils import FEDITEST_VERSION

DEFAULT_TEMPLATE = 'default'

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """

    transcript = TestRunTranscript.load(args.in_file)
    if not transcript.has_compatible_version():
        warning(f'Transcript was created by FediTest { transcript.feditest_version }, you are running FediTest { FEDITEST_VERSION }: incompatibilities may occur.')

    serializer : TestRunTranscriptSerializer | None = None
    if isinstance(args.tap, str) or args.tap:
        serializer = TapTestRunTranscriptSerializer(transcript)
        serializer.write(args.tap)

    if isinstance(args.html, str) or args.html:
        multifile_serializer = MultifileRunTranscriptSerializer(args.html, args.template)
        multifile_serializer.write(transcript)

    if isinstance(args.json, str) or args.json:
        serializer = JsonTestRunTranscriptSerializer(transcript)
        serializer.write(args.json)

    if isinstance(args.summary, str) or args.summary:
        serializer = SummaryTestRunTranscriptSerializer(transcript)
        serializer.write(args.json)

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
    html_group.add_argument('--template', default=DEFAULT_TEMPLATE,
                        help=f"When specifying --html, use this template (defaults to '{ DEFAULT_TEMPLATE }').")
    parser.add_argument('--json', nargs="?", const=True, default=False,
                        help="Write results in JSON format to stdout, or to the provided file (if given).")
    parser.add_argument('--summary', nargs="?", const=True, default=False,
                        help="Write summary to stdout, or to the provided file (if given). This is the default if no other output option is given")
