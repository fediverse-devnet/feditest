"""
Combine node definitions into a constellation.
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction

from feditest.testplan import TestPlanConstellation, TestPlanConstellationNode
from feditest.reporting import fatal


def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """

    roles : dict[str,TestPlanConstellationNode | None] = {}

    if remaining:
        parser.print_help() # Would be nice to print help for this sub-command but I can't figure out how to do it
        return 0

    for nodepair in args.node:
        rolename, nodefile = nodepair.split('=', 1)
        if not rolename:
            fatal('Rolename component must not be empty:', nodepair)
        if rolename in roles:
            fatal('Role is already taken:', rolename)
        if not nodefile:
            fatal('Filename component must not be empty:', nodepair)
        node = TestPlanConstellationNode.load(nodefile)
        roles[rolename] = node

    constellation = TestPlanConstellation(roles)

    if args.name:
        constellation.name = args.name

    if args.out:
        constellation.save(args.out)
    else:
        constellation.print()

    return 0


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='Combine node definitions into a constellation')
    parser.add_argument('--name', default=None, required=False, help='Name of the generated constellation')
    parser.add_argument('--node', action='append', required=True,
                        help="Use role=file to specify that the node definition in 'file' is supposed to be used for constellation role 'role'")
    parser.add_argument('--out', '-o', default=None, required=False, help='Name of the file for the generated constellation')
