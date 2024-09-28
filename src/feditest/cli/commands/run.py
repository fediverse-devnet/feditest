"""
Run one or more tests
"""

from argparse import ArgumentError, ArgumentParser, Namespace, _SubParsersAction
import re
from typing import Any

from msgspec import ValidationError

import feditest
from feditest.registry import Registry, set_registry_singleton
from feditest.reporting import warning
from feditest.tests import Test
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSession, TestPlanTestSpec
from feditest.testrun import TestRun
from feditest.testruncontroller import AutomaticTestRunController, InteractiveTestRunController, TestRunController
from feditest.testruntranscript import (
    JsonTestRunTranscriptSerializer,
    MultifileRunTranscriptSerializer,
    SummaryTestRunTranscriptSerializer,
    TapTestRunTranscriptSerializer,
    TestRunTranscriptSerializer,
)
from feditest.utils import FEDITEST_VERSION, hostname_validate


DEFAULT_TEMPLATE = 'default'

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    feditest.load_default_tests()
    feditest.load_tests_from(args.testsdir)

    feditest.load_default_node_drivers()
    if args.nodedriversdir:
        feditest.load_node_drivers_from(args.nodedriversdir)

    if args.domain:
        set_registry_singleton(Registry.create(args.domain)) # overwrite

    # Determine testplan. While we are at it, check consistency of arguments.
    if args.testplan:
        plan = _create_plan_from_testplan(args)
    else:
        session_templates = _create_session_templates(args)
        constellations = _create_constellations(args)

        sessions = []
        for session_template in session_templates:
            for constellation in constellations:
                session = session_template.instantiate_with_constellation(constellation, constellation.name)
                sessions.append(session)
        if sessions:
            plan = TestPlan(sessions, None)
            plan.simplify()
        else: # neither sessions nor testplan specified
            plan = TestPlan.load("feditest-default.json")

    if not plan.is_compatible_type():
        warning(f'Test plan has unexpected type { plan.type }: incompatibilities may occur.')
    if not plan.has_compatible_version():
        warning(f'Test plan was created by FediTest { plan.feditest_version }, you are running FediTest { FEDITEST_VERSION }: incompatibilities may occur.')
    plan.check_can_be_executed()

    test_run = TestRun(plan, args.who)
    if args.interactive :
        warning('--interactive: implementation is incomplete')
        controller : TestRunController = InteractiveTestRunController(test_run)
    else:
        controller = AutomaticTestRunController(test_run)
    test_run.run(controller)

    transcript : feditest.testruntranscript.TestRunTranscript = test_run.transcribe()

    summary_serializer = SummaryTestRunTranscriptSerializer(transcript)
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
    # general flags and options
    parser = parent_parser.add_parser(cmd_name, help='Run one or more tests' )
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find tests')
    parser.add_argument('--nodedriversdir', action='append', help='Directory or directories where to find extra drivers for nodes that can be tested')
    parser.add_argument('--domain', type=hostname_validate, help='Local-only DNS domain for the DNS hostnames that are auto-generated for nodes')
    parser.add_argument('--interactive', action="store_true",
                        help="Run the tests interactively")
    parser.add_argument('--who', action='store_true',
                        help="Record who ran the test plan on what host.")

    # test plan options. We do not use argparse groups, as the situation is more complicated than argparse seems to support
    parser.add_argument('--testplan', help='Name of the file that contains the test plan to run')
    parser.add_argument('--constellation', nargs='+', help='File(s) each containing a JSON fragment defining a constellation')
    parser.add_argument('--session', '--session-template', nargs='+', help='File(s) each containing a JSON fragment defining a test session')
    parser.add_argument('--node', action='append',
                        help="Use role=file to specify that the node definition in 'file' is supposed to be used for constellation role 'role'")
    parser.add_argument('--filter-regex', default=None, help='Only include tests whose name matches this regular expression')
    parser.add_argument('--test', nargs='+', help='Run this/these named tests(s)')

    # output options
    parser.add_argument('--tap', nargs="?", const=True, default=False,
                        help="Write results in TAP format to stdout, or to the provided file (if given).")
    html_group = parser.add_argument_group('html', 'HTML options')
    html_group.add_argument('--html',
                        help="Write results in HTML format to the provided file.")
    html_group.add_argument('--template', default=DEFAULT_TEMPLATE,
                        help=f"When specifying --html, use this template (defaults to '{ DEFAULT_TEMPLATE }').")
    parser.add_argument('--json', '--testresult', nargs="?", const=True, default=False,
                        help="Write results in JSON format to stdout, or to the provided file (if given).")
    parser.add_argument('--summary', nargs="?", const=True, default=False,
                        help="Write summary to stdout, or to the provided file (if given). This is the default if no other output option is given")

    return parser


def _create_plan_from_testplan(args: Namespace) -> TestPlan:
    if args.constellation:
        raise ArgumentError(None, '--testplan already defines --constellation. Do not provide both.')
    if args.session:
        raise ArgumentError(None, '--testplan already defines --session-template. Do not provide both.')
    if args.node:
        raise ArgumentError(None, '--testplan already defines --node via the contained constellation. Do not provide both.')
    if args.test:
        raise ArgumentError(None, '--testplan already defines --test via the contained session. Do not provide both.')
    plan = TestPlan.load(args.testplan)
    return plan


def _create_session_templates(args: Namespace) -> list[TestPlanSession]:
    if args.session:
        if args.filter_regex:
            raise ArgumentError(None, '--session already defines the tests, do not provide --filter-regex')
        if args.test:
            raise ArgumentError(None, '--session already defines --test. Do not provide both.')
        session_templates = []
        for session_file in args.session:
            session_templates.append(TestPlanSession.load(session_file))
        return session_templates

    test_plan_specs : list[TestPlanTestSpec]= []
    constellation_role_names : dict[str,Any] = {}
    constellation_roles: dict[str,TestPlanConstellationNode | None] = {}
    tests : list[Test]= []

    if args.test:
        if args.filter_regex:
            raise ArgumentError(None, '--filter-regex already defines --test. Do not provide both.')
        for name in args.test:
            test = feditest.all_tests.get(name)
            if test is None:
                raise ArgumentError(None, f'Cannot find test: "{ name }".')
            tests.append(test)

    elif args.filter_regex:
        pattern = re.compile(args.filter_regex)
        for name in sorted(feditest.all_tests.keys()):
            if pattern.match(name):
                test = feditest.all_tests.get(name)
                if test is None: # make linter happy
                    continue
                if test.builtin:
                    continue
                tests.append(test)

    else:
        for name in sorted(feditest.all_tests.keys()):
            test = feditest.all_tests.get(name)
            if test is None: # make linter happy
                continue
            if test.builtin:
                continue
            tests.append(test)

    for test in tests:
        test_plan_spec = TestPlanTestSpec(name)
        test_plan_specs.append(test_plan_spec)

        for role_name in test.needed_local_role_names():
            constellation_role_names[role_name] = 1
            if not test_plan_spec.rolemapping:
                test_plan_spec.rolemapping = {}
            test_plan_spec.rolemapping[role_name] = role_name

    for constellation_role_name in constellation_role_names:
        constellation_roles[constellation_role_name] = None

    session = TestPlanSession(TestPlanConstellation(constellation_roles), test_plan_specs)
    return [ session ]


def _create_constellations(args: Namespace) -> list[TestPlanConstellation]:
    if args.constellation:
        if args.node:
            raise ArgumentError(None, '--constellation already defines --node. Do not provide both.')

        constellations = []
        for constellation_file in args.constellation:
            try:
                constellations.append(TestPlanConstellation.load(constellation_file))
            except ValidationError as e:
                raise ArgumentError(None, f'Constellation file { constellation_file }: { e }')
        return constellations

    # Don't check for empty nodes: we need that for testing feditest
    roles : dict[str, TestPlanConstellationNode | None] = {}
    for nodepair in args.node:
        rolename, nodefile = nodepair.split('=', 1)
        if not rolename:
            raise ArgumentError(None, f'Rolename component of --node must not be empty: "{ nodepair }".')
        if rolename in roles:
            raise ArgumentError(None, f'Role is already taken: "{ rolename }".')
        if not nodefile:
            raise ArgumentError(None, f'Filename component must not be empty: "{ nodepair }".')
        node = TestPlanConstellationNode.load(nodefile)
        roles[rolename] = node

    constellation = TestPlanConstellation(roles)
    return [ constellation ]
