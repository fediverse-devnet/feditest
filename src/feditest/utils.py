"""
Utility functions
"""

from ast import Module
import glob
import importlib
import pkgutil
import re
import sys
from urllib.parse import urlparse
from langcodes import Language


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
    for d in dirs:
        while d.endswith('/') :
            d = d[:-1]

        try:
            sys.path.append(d) # needed to automatially pull in dependencies
            for f in glob.glob(d + '/**/*.py', recursive=True):
                module_name = f[ len(d)+1 : -3 ].replace('/', '.' ) # remove d from the front, and the extension from the back
                if module_name.endswith('__init__'):
                    if skip_init_files:
                        continue
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
    match = re.match(r"acct:[-a-z0-9\.]+@[-a-z0-9\.]+", candidate) # FIXME: should tighten this regex
    return bool(match)


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
    # FIXME: check that urlparse faithfully implements the relevant RFCs
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
    if parsed.scheme == 'acct':
        # Don't like this parser
        # FIXME: regex likely does not match the relevant RFCs
        return len(parsed.netloc) == 0 and re.match(r"[-a-zA-Z0-9\.]+@[-a-zA-Z0-9\.]+", parsed.path) and len(parsed.params) == 0 and len(parsed.query) == 0 and len(parsed.fragment) == 0
    return False


def uri_validate(candidate: str) -> bool:
    """
    Validate that the provided string is a valid URI.
    return: True if valid
    """
    parsed = urlparse(candidate)
    return (len(parsed.scheme) > 0
            and len(parsed.netloc) > 0)


def rfc5646_language_tag_validate(candidate: str) -> bool:
    """
    Validate a language tag according to RFC 5646, see https://www.rfc-editor.org/rfc/rfc5646.html
    return: True if valid
    """
    return Language.get(candidate).is_valid() # FIXME needs checking that this library actually does what it says it does


def hostname_validate(candidate: str) -> bool:
    """
    Validate that the provided string is a valid hostname.
    return: True if valid
    """
    # from https://stackoverflow.com/questions/2532053/validate-a-hostname-string but we don't want trailing periods
    if len(candidate) > 255:
        return False
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in candidate.split("."))


def format_name_value_string(data: dict[str,str]) -> str:
    """
    Format name-value pairs to a string similar to how an HTML definition list would
    do it.
    data: the name-value pairs
    return: formatted string
    """
    line_width = 120 # FIXME?
    col1_width = len(max(data, key=len)) + 1
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
