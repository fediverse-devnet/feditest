"""
Main entry point for CLI invocation
"""

import sys
import traceback
from argparse import ArgumentParser
from feditest.reporting import fatal
from feditest.utils import find_commands

# FIXME imports -- need dynamic discovery
import feditest.iut
import feditest.iut.activitypub
import feditest.iut.fediverse
import feditest.iut.webfinger
import feditest.tests.activitypub.test_01_valid_actor_document
import feditest.tests.activitypub.test_02_follow
import feditest.tests.webfinger.test_01_valid_webfinger_document
import feditest.tests.webfinger.test_02_webfinger_account_does_not_exist


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

    if len(remaining)>0 :
        parser.print_help()
        sys.exit(0)

    if cmd_name in cmds:
        try :
            ret = cmds[cmd_name].run(args)
            sys.exit( ret )

        except Exception as e: # pylint: disable=broad-exception-caught
            if args.verbose > 1:
                traceback.print_exc( e )
            fatal( str(type(e)), '--', e )

    else:
        fatal('Sub-command not found:', cmd_name, '. Add --help for help.' )


if __name__ == '__main__':
    main()
