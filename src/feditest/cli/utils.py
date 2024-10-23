"""
Utility functions used by the CLI commands.
"""

from argparse import ArgumentError, Namespace
import re

from msgspec import ValidationError

import feditest
from feditest.tests import Test
from feditest.testplan import TestPlan, TestPlanConstellation, TestPlanConstellationNode, TestPlanSessionTemplate, TestPlanTestSpec

def create_plan_from_testplan(args: Namespace) -> TestPlan:
    if args.constellation:
        raise ArgumentError(None, '--testplan already defines --constellation. Do not provide both.')
    if args.session:
        raise ArgumentError(None, '--testplan already defines --session. Do not provide both.')
    if args.node:
        raise ArgumentError(None, '--testplan already defines --node via the contained constellation. Do not provide both.')
    if args.test:
        raise ArgumentError(None, '--testplan already defines --test via the contained session. Do not provide both.')
    plan = TestPlan.load(args.testplan)
    return plan


def create_plan_from_session_and_constellations(args: Namespace) -> TestPlan | None:
    session = create_session(args)
    constellations = create_constellations(args)

    plan = TestPlan(session, constellations, args.name)
    plan.simplify()
    return plan


def create_session(args: Namespace) -> TestPlanSessionTemplate:
    if args.session:
        session_template = create_session_from_files(args)
    else:
        session_template = create_session_template_from_tests(args)
    return session_template


def create_session_from_files(args: Namespace) -> TestPlanSessionTemplate:
    if args.filter_regex:
        raise ArgumentError(None, '--session already defines the tests, do not provide --filter-regex')
    if args.test:
        raise ArgumentError(None, '--session already defines --test. Do not provide both.')
    return TestPlanSessionTemplate.load(args.session)


def create_session_template_from_tests(args: Namespace) -> TestPlanSessionTemplate:
    test_plan_specs : list[TestPlanTestSpec]= []
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
        name = test.name
        test_plan_spec = TestPlanTestSpec(name)
        test_plan_specs.append(test_plan_spec)

    session = TestPlanSessionTemplate(test_plan_specs, args.name)
    return session


def create_constellations(args: Namespace) -> list[TestPlanConstellation]:
    if args.constellation:
        constellations = create_constellations_from_files(args)
    else:
        constellation = create_constellation_from_nodes(args)
        constellations = [ constellation ]
    return constellations


def create_constellations_from_files(args: Namespace) -> list[TestPlanConstellation]:
    if args.node:
        raise ArgumentError(None, '--constellation already defines --node. Do not provide both.')

    constellations = []
    for constellation_file in args.constellation:
        try:
            constellations.append(TestPlanConstellation.load(constellation_file))
        except ValidationError as e:
            raise ArgumentError(None, f'Constellation file { constellation_file }: { e }')
    return constellations


def create_constellation_from_nodes(args: Namespace) -> TestPlanConstellation:
    # Don't check for empty nodes: we need that for testing feditest
    roles : dict[str, TestPlanConstellationNode | None] = {}
    if args.node:
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
    return constellation
