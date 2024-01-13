"""
List the available drivers for applications that can be tested
"""

from argparse import ArgumentParser, Namespace

import feditest
import feditest.cli

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> None:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help();
        return 0

    if args.appdriversdir:
        feditest.load_app_drivers_from(args.appdriversdir)
    else:
        feditest.load_app_drivers_from(feditest.cli.default_app_drivers_dir) 

    for name in sorted(feditest.all_app_drivers.keys()):
        print( name )

    return 0

def add_sub_parser( parent_parser: ArgumentParser, cmd_name: str ) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='List the available drivers for applications that can be tested' )
    parser.add_argument('--appdriversdir', action='append', help='Directory or directories where to find drivers for applications that can be tested')
        # Can't set a default value, because action='append' adds to the default value, instead of replacing it
