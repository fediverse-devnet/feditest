"""
Utility functions
"""

import glob
import importlib
import pkgutil
import re
import sys
from ast import Module
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


def load_python_from(dirs: list[str], skip_init_files: bool) -> None:
    """
    Helper to load the Python files found in the provided directories, and any subdirectory
    """
    sys_path_before = sys.path
    for dir in dirs:
        while dir.endswith('/') :
            dir = dir[:-1]

        try:
            sys.path.append(dir) # needed to automatially pull in dependencies
            for f in glob.glob(dir + '/**/*.py', recursive=True):
                module_name = f[ len(dir)+1 : -3 ].replace('/', '.' ) # remove dir from the front, and the extension from the back
                if module_name.endswith('__init__'):
                    if skip_init_files:
                        continue
                    else:
                        module_name = module_name[:-9] # remote .__init__
                if not module_name:
                    module_name = 'default'
                spec = importlib.util.spec_from_file_location(module_name, f)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
        finally:
            sys.path = sys_path_before


def account_id_validate(candidate: str) -> bool:
    """
    Validate that the provided string is of the form 'acct:foo@bar.com'.
    return True if valid
    """
    match = re.match("acct:[-a-z0-9\.]+@[-a-z0-9\.]+", candidate) # FIXME: should tighten this regex
    if match:
        return True
    else:
        return False


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
            and len(parsed.fragment) == 0)


def http_https_acct_uri_validate(candidate: str) -> bool:
    """
    Validate that the provided string is a valid HTTP, HTTPS or ACCT URI.
    return: True if valid
    """
    parsed = urlparse(candidate)
    if parsed.scheme in ['http', 'https']:
        return len(parsed.netloc) > 0
    elif parsed.scheme == 'acct':
        # Don't like this parser
        return len(parsed.netloc) == 0 and re.match("[-a-z0-9\.]+@[-a-z0-9\.]+", parsed.path) and len(parsed.params) == 0 and len(parsed.query) == 0
    else:
        return False


def format_name_value_string(data: dict[str,str]) -> str:
    """
    Format name-value pairs to a string similar to how an HTML definition list would
    do it.
    data: the name-value pairs
    return: formatted string
    """

    line_width = 120 # FIXME?
    col1_width = len(max(data, key=len)) + 1
    # col2_width = line_width - col1_width
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
