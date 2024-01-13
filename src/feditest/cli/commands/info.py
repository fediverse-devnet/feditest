"""
Provide information on a variety of objects
"""

from argparse import ArgumentParser, Namespace

import feditest
import feditest.cli
from feditest.utils import format_name_value_string
from feditest.reporting import warning


def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> None:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help();
        return 0

    feditest.load_tests_from(args.testsdir)
    if args.appdriversdir:
        feditest.load_app_drivers_from(args.appdriversdir)
    else:
        feditest.load_app_drivers_from(feditest.cli.default_app_drivers_dir) 
    
    if args.test:
        return run_info_test(args.test)

    if args.testset:
        return run_info_testset(args.testset)

    if args.appdriver:
        return run_info_app_driver(args.appdriver)


def run_info_test(name: str) -> None:
    test = feditest.all_tests.get(name)
    if test:
        test_metadata = {
            'Test name:' : test.name,
            'Description:' : test.description,
            'Constellation size:' : str(test.constellation_size)
        }
        if test.test_set:
            test_metadata['Test set:'] = test.test_set.name

        print(format_name_value_string(test_metadata), end='')
        return 0

    else:
        warning( 'Test not found:', name)
        return 1


def run_info_testset(name: str) -> None:
    test_set = feditest.all_test_sets.get(name)
    if test_set:
        test_set_metadata = {
            'Test set name:' : test_set.name,
            'Description:' : test_set.description
        }

        print(format_name_value_string(test_set_metadata), end='')
        return 0

    else:
        warning( 'Test set not found:', name)
        return 1


def run_info_app_driver(name: str) -> None:
    test = feditest.all_app_drivers.get(name)
    if test:
        test_metadata = {
            'App driver name:' : test.name,
            'Description:' : test.description
        }

        print(format_name_value_string(test_metadata), end='')
        return 0

    else:
        warning( 'App driver not found:', name)
        return 1


def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Provide information on a variety of objects')
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find testsets and tests')
    parser.add_argument('--appdriversdir', action='append', help='Directory or directories where to find drivers for applications that can be tested')
        # Can't set a default value, because action='append' adds to the default value, instead of replacing it
    type_group = parser.add_mutually_exclusive_group(required=True)
    type_group.add_argument('--test',  help='Provide information about a test.')
    type_group.add_argument('--testset',  help='Provide information about a test set.')
    type_group.add_argument('--appdriver',  help='Provide information about a driver for an application to be tested.')
