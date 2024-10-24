"""
Provide information on a variety of objects
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction
from typing import Any

import feditest
import feditest.cli
from feditest.utils import format_name_value_string
from feditest.reporting import warning


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

    if args.test:
        return run_info_test(args.test)

    if args.nodedriver:
        return run_info_node_driver(args.nodedriver)

    parser.print_help()
    return 0


def run_info_test(name: str) -> int:
    """
    Provide information on a test
    """
    test = feditest.all_tests.get(name)
    if test:
        test_metadata = test.metadata()
        needed_role_names = test.needed_local_role_names()
        if needed_role_names:
            test_metadata['Needed roles:'] = sorted(needed_role_names)

        print(format_name_value_string(test_metadata), end='')
        return 0

    warning( 'Test not found:', name)
    return 1


def run_info_node_driver(name: str) -> int:
    """
    Provide information on a node driver
    """
    node_driver_class = feditest.all_node_drivers.get(name)
    if node_driver_class:
        node_driver_metadata : dict[str, Any] = {
            'Node driver name:' : node_driver_class.__qualname__,
            'Description:' : node_driver_class.__doc__,
        }
        pars = node_driver_class.test_plan_node_parameters()
        if pars:
            node_driver_metadata_pars = {}
            for par in pars:
                node_driver_metadata_pars[par.name] = par.description
            node_driver_metadata['Parameters:'] = node_driver_metadata_pars

        account_fields = node_driver_class.test_plan_node_account_fields()
        if account_fields:
            node_driver_metadata_fields = {}
            for field in account_fields:
                node_driver_metadata_fields[field.name] = field.description
            node_driver_metadata['Account fields:'] = node_driver_metadata_fields

        non_existing_account_fields = node_driver_class.test_plan_node_non_existing_account_fields()
        if non_existing_account_fields:
            node_driver_metadata_non_fields = {}
            for field in non_existing_account_fields:
                node_driver_metadata_non_fields[field.name] = field.description
            node_driver_metadata['Non-existing Account fields:'] = node_driver_metadata_non_fields

        print(format_name_value_string(node_driver_metadata), end='')
        return 0

    warning( 'Node driver not found:', name)
    return 1


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='Provide information on a variety of objects')
    parser.add_argument('--testsdir', action='append', default=['tests'], help='Directory or directories where to find tests')
    parser.add_argument('--nodedriversdir', action='append', help='Directory or directories where to find extra drivers for nodes that can be tested')
    type_group = parser.add_mutually_exclusive_group(required=True)
    type_group.add_argument('--test',  help='Provide information about a test.')
    type_group.add_argument('--nodedriver',  help='Provide information about a driver for a node to be tested.')

    return parser
