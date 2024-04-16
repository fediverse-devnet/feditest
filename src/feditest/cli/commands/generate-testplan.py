"""
Generate a test plan
"""

from argparse import ArgumentParser, Namespace
import json
import feditest

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    """
    Run this command.
    """
    if len(remaining):
        parser.print_help()
        return 0

    if args.constellation:
        with open(args.constellation, 'r', encoding='utf-8') as f:
            constellation_json = json.load(f)
    else:
        constellation_json = {
            'name' : 'unnamed',
            'roles' : [
                {
                    'name' : 'REPLACE',
                    'nodedriver' : 'REPLACE'
                }
            ]
        }

    feditest.load_tests_from(args.testsdir)

    tests_json = []
    for name in sorted(feditest.all_tests.all().keys()):
        tests_json.append( { 'name' : name } )

    testplan_json = {
        'name' : 'unnamed',
        'sessions' : [
            {
                'constellation' : constellation_json,
                'tests' : tests_json
            }
        ]
    }
    if args.out:
        with open(args.out, 'w', encoding="utf8") as w:
            json.dump(testplan_json, w, indent=4)
    else:
       print(json.dumps(testplan_json, indent=4))

    return 0


def add_sub_parser(parent_parser: ArgumentParser, cmd_name: str) -> None:
    """
    Add command-line options for this sub-command
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser(cmd_name, help='Generate a test plan' )
    parser.add_argument('--constellation', default=None, required=False, help='Name of a file containing a JSON fragment to use for the constellation')
    parser.add_argument('--out', default=None, required=False, help='Name of the file for the generated test plan')
    parser.add_argument('--testsdir', nargs='*', default=['tests'], help='Directory or directories where to find testsets and tests')
