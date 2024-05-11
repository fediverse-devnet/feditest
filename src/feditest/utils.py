"""
Utility functions
"""

import glob
import importlib.util
import pkgutil
import re
import sys
from types import ModuleType
from urllib.parse import urlparse
from langcodes import Language


# From https://datatracker.ietf.org/doc/html/rfc7565#section-7, but simplified
ACCT_REGEX = re.compile("acct:([-a-z0-9\._~][-a-z0-9\._~!$&'\(\)\*\+,;=%]*)@([-a-z0-9\.:]+)")


def find_submodules(package: ModuleType) -> list[str]:
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
                if spec is not None and spec.loader is not None:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
        finally:
            sys.path = sys_path_before


def account_id_parse_validate(candidate: str) -> tuple[str,str] | None:
    """
    Validate that the provided string is of the form 'acct:foo@bar.com'.
    return tuple of user, host if valid, None otherwise
    """
    match = ACCT_REGEX.match(candidate)
    if match:
        return (match.group(1) or "", match.group(2) or "")
    return None


def http_https_uri_parse_validate(candidate: str) -> str | None:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI.
    return: string if valid, None otherwise
    """
    parsed = urlparse(candidate)
    if parsed.scheme in ['http', 'https'] and len(parsed.netloc) > 0:
        return candidate
    return None


def http_https_root_uri_parse_validate(candidate: str) -> str | None:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI without a path, query or
    fragment component
    return: string if valid, None otherwise
    """
    parsed = urlparse(candidate)
    # FIXME: check that urlparse faithfully implements the relevant RFCs
    if (parsed.scheme in ['http', 'https']
            and len(parsed.netloc) > 0
            and (len(parsed.path) == 0 or parsed.path == '/')
            and len(parsed.params) == 0
            and len(parsed.query) == 0
            and len(parsed.fragment) == 0):
        return candidate
    return None


def http_https_acct_uri_parse_validate(candidate: str) -> str | None:
    """
    Validate that the provided string is a valid HTTP, HTTPS or ACCT URI.
    return: string if valid, None otherwise
    """
    parsed = urlparse(candidate)
    if parsed.scheme in ['http', 'https'] and len(parsed.netloc) > 0:
        return candidate
    if parsed.scheme == 'acct':
        # Don't like this parser
        if ACCT_REGEX.match(candidate):
            return candidate
    return None


def uri_parse_validate(candidate: str) -> str | None:
    """
    Validate that the provided string is a valid URI.
    return: string if valid, None otherwise
    """
    parsed = urlparse(candidate)
    if len(parsed.scheme) > 0 and len(parsed.netloc) > 0:
        return candidate
    return None


def rfc5646_language_tag_parse_validate(candidate: str) -> str | None:
    """
    Validate a language tag according to RFC 5646, see https://www.rfc-editor.org/rfc/rfc5646.html
    return: string if valid, None otherwise
    """
    if Language.get(candidate).is_valid(): # FIXME needs checking that this library actually does what it says it does
        return candidate
    return None


def hostname_parse_validate(candidate: str) -> str | None:
    """
    Validate that the provided string is a valid hostname.
    return: string if valid, None otherwise
    """
    # from https://stackoverflow.com/questions/2532053/validate-a-hostname-string but we don't want trailing periods
    if len(candidate) > 255:
        return None
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    if all(allowed.match(x) for x in candidate.split(".")):
        return candidate
    return None


def boolean_response_parse_validate(candidate:str) -> bool | None:
    """
    The provided string was entered by the user as a response a boolean question.
    return a True or False if the provided string can be interpreted as answering the boolean question, None otherwise
    """
    candidate = candidate.strip().lower()
    if not candidate:
        # just hit CR, we take this as True
        return True
    if candidate.startswith('y'):
        return True
    if candidate.startswith('t'):
        return True
    if candidate.startswith('n'):
        return False
    if candidate.startswith('f'):
        return False
    return None


def format_name_value_string(data: dict[str,str | None]) -> str:
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
        if not value:
            line += '<no value>\n'
        elif isinstance(value, str):
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
            line += ' ' + str(value)
            ret += line
            ret += '\n'

    return ret
