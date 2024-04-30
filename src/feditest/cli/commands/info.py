"""
Provide information on a variety of objects
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

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

    feditest.load_tests_from(args.testsdir)
    if args.nodedriversdir:
        feditest.load_node_drivers_from(args.nodedriversdir)
    else:
        feditest.load_node_drivers_from(feditest.cli.default_node_drivers_dir)

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
        print(format_name_value_string(test.metadata()), end='')
        return 0

    warning( 'Test not found:', name)
    return 1


def run_info_node_driver(name: str) -> int:
    """
    Provide information on a node driver
    """
    node_driver_class = feditest.all_node_drivers.get(name)
    if node_driver_class:
        node_driver_metadata = {
            'Node driver name:' : node_driver_class.__qualname__,
            'Description:' : node_driver_class.__doc__
        }

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
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find tests')
    parser.add_argument('--nodedriversdir', action='append', help='Directory or directories where to find drivers for nodes that can be tested')
        # Can't set a default value, because action='append' adds to the default value, instead of replacing it
    type_group = parser.add_mutually_exclusive_group(required=True)
    type_group.add_argument('--test',  help='Provide information about a test.')
    type_group.add_argument('--nodedriver',  help='Provide information about a driver for a node to be tested.')
