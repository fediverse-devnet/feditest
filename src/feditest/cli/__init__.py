"""
Main entry point for CLI invocation
"""

from argparse import ArgumentParser
from ast import Module
import importlib
import sys
import traceback

from feditest.reporting import fatal, set_reporting_level
from feditest.utils import find_submodules

# FIXME imports -- need dynamic discovery
import feditest.protocols
import feditest.protocols.activitypub
import feditest.protocols.fediverse
import feditest.protocols.webfinger
import feditest.tests.fediverse.test_follow
import feditest.cli.commands

def main():
    """
    Main entry point for CLI invocation.
    """

    # Discover and install sub-commands

    cmds = find_commands()

    parser = ArgumentParser(description='FediTest: test federated protocols')
    parser.add_argument('-v', '--verbose', action='count', default=0,
            help='Display extra output. May be repeated for even more output' )
    cmd_parsers = parser.add_subparsers(dest='command', required=True)

    for cmd_name, cmd in cmds.items():
        cmd.add_sub_parser(cmd_parsers, cmd_name)

    args,remaining = parser.parse_known_args(sys.argv[1:])
    cmd_name = args.command

    set_reporting_level(args.verbose)

    if cmd_name in cmds:
        try :
            ret = cmds[cmd_name].run(parser, args, remaining)
            sys.exit( ret )

        except Exception as e: # pylint: disable=broad-exception-caught
            print( f"XXX Exception is {type(e)}")
            if args.verbose > 1:
                traceback.print_exception( e )
            fatal( str(type(e)), '--', e )

    else:
        fatal('Sub-command not found:', cmd_name, '. Add --help for help.' )


def find_commands() -> dict[str,Module]:
    """
    Find available commands.
    """
    cmd_names = find_submodules( feditest.cli.commands )

    cmds = {}
    for cmd_name in cmd_names:
        mod = importlib.import_module('feditest.cli.commands.' + cmd_name)
        cmds[cmd_name.replace('_', '-')] = mod

    return cmds



if __name__ == '__main__':
    main()
