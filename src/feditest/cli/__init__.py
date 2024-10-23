"""
Main entry point for CLI invocation
"""

from argparse import ArgumentError, ArgumentParser, Action
import importlib
import sys
import traceback
from types import ModuleType

from feditest.reporting import fatal, set_reporting_level, warning
from feditest.utils import find_submodules
import feditest.cli.commands

def main() -> None:
    """
    Main entry point for CLI invocation.
    """

    # Discover and install sub-commands
    cmds = find_commands()

    parser = ArgumentParser(description='FediTest: test federated protocols')
    parser.add_argument('-v', '--verbose', action='count', default=0,
            help='Display extra output. May be repeated for even more output' )
    cmd_parsers : Action = parser.add_subparsers(dest='command', required=True)
    cmd_sub_parsers : dict[str,ArgumentParser] = {}

    for cmd_name, cmd in cmds.items():
        cmd_sub_parsers[cmd_name] = cmd.add_sub_parser(cmd_parsers, cmd_name)

    args,remaining = parser.parse_known_args(sys.argv[1:])
    cmd_name = args.command

    set_reporting_level(args.verbose)

    if sys.version_info.major != 3 or sys.version_info.minor != 11:
        warning(f"feditest currently requires Python 3.11. You are using { sys.version }"
                + " and may get unpredictable results. We'll get to other versions in the future.")

    if cmd_name in cmds:
        try :
            ret = cmds[cmd_name].run(cmd_sub_parsers[cmd_name], args, remaining)
            sys.exit( ret )

        except ArgumentError as e:
            fatal(e.message)
        except Exception as e: # pylint: disable=broad-exception-caught
            if args.verbose > 1:
                traceback.print_exception( e )
            fatal( str(type(e)), '--', e )

    else:
        fatal('Sub-command not found:', cmd_name, '. Add --help for help.' )


def find_commands() -> dict[str,ModuleType]:
    """
    Find available commands.
    """
    cmd_names = find_submodules(feditest.cli.commands)

    cmds = {}
    for cmd_name in cmd_names:
        mod = importlib.import_module('feditest.cli.commands.' + cmd_name)
        cmds[cmd_name.replace('_', '-')] = mod

    return cmds


if __name__ == '__main__':
    main()
