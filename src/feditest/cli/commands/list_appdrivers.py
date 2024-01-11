"""
List the available drivers for applications that can be tested
"""

from argparse import ArgumentParser, Namespace

def run(parser: ArgumentParser, args: Namespace, remaining: list[str]) -> None:
    """
    Run this command.
    """
    print( "Running list-appdrivers ... (FIXME)" )
    print("""manual
mastodon-4.2.2/vbox-provisiononly
mastodon-4.2.2/docker-all
wordpress+activitypub-6.4.2/nspawn-ubos-partial""")

def add_sub_parser( parent_parser: ArgumentParser, cmd_name: str ) -> None:
    """
    Enable this command to add its own command-line options
    parent_parser: the parent argparse parser
    cmd_name: name of this command
    """
    parser = parent_parser.add_parser( cmd_name, help='List the available drivers for applications that can be tested' )
    parser.add_argument('--appdriverdir', nargs='*', default='appdrivers', help='Directory or directories where to find drivers for applications that can be tested')
