"""
Utility functions
"""

from ast import Module
import pkgutil
import re
from urllib.parse import urlparse


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


def account_id_validate(candidate: str) -> bool:
    """
    Validate that the provided string is of the form 'acct:foo@bar.com'.
    return True if valid
    """
    match = re.match("acct:[^\s]+@[^\s]+", candidate)
    if match:
        return True
    else:
        return False
    

def uri_validate(candidate: str) -> bool:
    """
    Validate that the provided string is a valid URI.
    return: True if valid
    """
    parsed = urlparse(candidate)
    return len(parsed.scheme) > 0 and len(parsed.netloc) > 0


def http_https_uri_validate(candidate: str) -> bool:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI.
    return: True if valid
    """
    parsed = urlparse(candidate)
    return (parsed.scheme in ['http', 'https']
            and len(parsed.netloc) > 0)


def http_https_root_uri_validate(uri: str) -> bool:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI without a path, query or
    fragment component
    return: True if valid
    """
    parsed = urlparse(uri)
    return (parsed.scheme in ['http', 'https']
            and len(parsed.netloc) > 0
            and (len(parsed.path) == 0 or parsed.path == '/')
            and len(parsed.params) == 0
            and len(parsed.query) == 0
            and len(parsed.fragment) == 0 )


def format_name_value_string(data: dict[str,str]) -> str:
    """
    Format name-value pairs to a string similar to how an HTML definition list would
    do it.
    data: the name-value pairs
    return: formatted string
    """

    line_width = 120 # FIXME?
    col1_width = len(max(data, key=len)) + 1
    col2_width = line_width - col1_width
    ret = ''
    line = ''
    for key, value in data.items():
        line = ("{:<" + str(col1_width) + "}").format(key)
        if value:
            for word in value.split():
                if len(line)+1+len(word) <= line_width:
                    line += ' '
                else:
                    ret += line
                    ret += '\n'
                    line = (col1_width+1)*' '
                line += word
            if len(line) > col1_width+1:
                ret += line
                ret += '\n'
        else:
            line += '<no value>\n'

    return ret
