"""
Utility functions
"""

from ast import Module
import importlib
import pkgutil
from urllib.parse import urlparse
import feditest.cli.commands


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

def find_submodules(package: Module) -> list[str]:
    """
    Find all submodules in the named package

    package: the package
    return: array of module names
    """
    ret = []
    for _, modname, _ in pkgutil.iter_modules(package.__path__):
        ret.append(modname)
    return ret


def http_https_uri_validate(uri: str) -> bool:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI.
    return: True if valid
    """
    parsed = urlparse(uri)
    return (parsed.scheme in ['http', 'https']
            and len( parsed.netloc) > 0 )

def http_https_root_uri_validate(uri: str) -> bool:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI without a path, query or
    fragment component
    return: True if valid
    """
    parsed = urlparse(uri)
    return (parsed.scheme in ['http', 'https']
            and len( parsed.netloc) > 0
            and ( len(parsed.path) == 0 or parsed.path == '/' )
            and len( parsed.params ) == 0
            and len( parsed.query ) == 0
            and len( parsed.fragment ) == 0 )
