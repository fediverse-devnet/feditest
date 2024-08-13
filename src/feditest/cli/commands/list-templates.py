"""
List the available templates
"""

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

# We may define a way to make these discoverable in the future
TEMPLATES = [
    "test_matrix",
    "test_session",
]


def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> int:
    # TODO This should be a utility method that all commands can use
    if len(remaining):
        print(
            f"unrecognized option{'s' if len(remaining) > 1 else ''}: "
            f"{' '.join(remaining)}",
            file=sys.stderr,
        )
        parser.print_help()
        return 1

    print("\n".join(TEMPLATES))

    return 0


def add_sub_parser(parent_parser: _SubParsersAction, cmd_name: str) -> None:
    help = "List the available templates"
    parser = parent_parser.add_parser(cmd_name, help=help, description=help)

    return parser
