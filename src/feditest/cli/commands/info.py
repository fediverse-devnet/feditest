"""
Provide information on a variety of objects
"""

from argparse import ArgumentParser, Namespace

import feditest
from feditest.utils import format_name_value_string

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> None:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help();
        return 0

    if args.test:
        return run_info_test(args.test)

    if args.testset:
        return run_info_testset(args.testset)

    if args.iutdriver:
        return run_info_iut_driver(args.iotdriver)


def run_info_test(name: str) -> None:
    test = feditest.all_tests.get(name)
    if test:
        test_metadata = {
            'Name:' : test.name(),
            'Description:' : test.description(),
            'IUTs:' : str(test.n_iuts())
        }
        if test.test_set():
            test_metadata['Test set:'] = test.test_set().name()

        print(format_name_value_string(test_metadata), end='')
        return 0

    else:
        warning( 'Test not found:', name)
        return 1

def run_info_testset(name: str) -> None:
    test_set = feditest.all_test_sets.get(name)
    if test_set:
        test_set_metadata = {
            'Name:' : test_set.name(),
            'Description:' : test_set.description()
        }

        print(format_name_value_string(test_set_metadata), end='')
        return 0

    else:
        warning( 'Testset not found:', name)
        return 1


def run_info_iut_driver(name: str) -> None:
    raise Exception("FIXME")


def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Provide information on a variety of objects')
    parser.add_argument('--testdir', nargs='*', default='tests', help='Directory or directories where to find testsets and tests')
    parser.add_argument('--iutdriverdir', nargs='*', default='iutdrivers', help='Directory or directories where to find drivers for Instances-under-test')
    type_group = parser.add_mutually_exclusive_group(required=True)
    type_group.add_argument('--test',  help='Provide information about a test.')
    type_group.add_argument('--testset',  help='Provide information about a test set.')
    type_group.add_argument('--iutdriver',  help='Provide information about a driver for an instance-under-test.')

