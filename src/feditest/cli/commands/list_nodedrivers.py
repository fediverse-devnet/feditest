"""
List the available drivers for nodes that can be tested
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

import feditest
import feditest.cli

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    if args.nodedriversdir:
        feditest.load_node_drivers_from(args.nodedriversdir)
    feditest.load_default_node_drivers()

    for name in sorted(feditest.all_node_drivers.keys()):
        print(name)

    return 0


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='List the available drivers for nodes that can be tested')
    parser.add_argument('--nodedriversdir', action='append', help='Directory or directories where to find extra drivers for nodes that can be tested')

    return parser
