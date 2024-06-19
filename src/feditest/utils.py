"""
Utility functions
"""

from abc import ABC, abstractmethod
import glob
import importlib.util
import pkgutil
import re
import sys
from importlib.metadata import version
from types import ModuleType
from typing import List, Optional
from urllib.parse import ParseResult, parse_qs, urlparse
from langcodes import Language

FEDITEST_VERSION = version('feditest')

# From https://datatracker.ietf.org/doc/html/rfc7565#section-7, but simplified
ACCT_REGEX = re.compile(r"acct:([-a-zA-Z0-9\._~][-a-zA-Z0-9\._~!$&'\(\)\*\+,;=%]*)@([-a-zA-Z0-9\.:]+)")


class ParsedUri(ABC):
    """
    An abstract data type for URIs. We want it to provide methods for accessing parameters,
    and so we don't use ParseResult. Also failed attempting to inherit from it.
    Because the structure is so different, we have subtypes.
    """
    @staticmethod
    def parse(url: str, scheme='', allow_fragments=True) -> Optional['ParsedUri']:
        """
        The equivalent of urlparse(str)
        """
        parsed : ParseResult = urlparse(url, scheme, allow_fragments)
        if parsed.scheme == 'acct':
            if match := ACCT_REGEX.match(url):
                return ParsedAcctUri(match[1], match[2])
        if not len(parsed.scheme):
            return None
        if not len(parsed.netloc):
            if parsed.scheme != 'data':
                return None
        return ParsedNonAcctUri(parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)


    @abstractmethod
    def get_uri(self) -> str:
        ...


class ParsedNonAcctUri(ParsedUri):
    """
    ParsedUris that are "normal" URIs such as http URIs.
    """
    def __init__(self, scheme: str, netloc: str, path: str, params: str, query: str, fragment: str):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.params = params
        self.query = query
        self.fragment = fragment
        self._query_params : dict[str,list[str]] | None = None


    def get_uri(self) -> str:
        ret = f'{ self.scheme }:'
        if self.netloc:
            ret += f'//{ self.netloc}'
        ret += self.path
        if self.params:
            ret += f';{ self.params}'
        if self.query:
            ret += f'?{ self.query }'
        if self.fragment:
            ret += f'#{ self.fragment }'
        return ret


    def has_query_param(self, name: str) -> bool:
        self._parse_query_params()
        if self._query_params:
            return name in self._query_params
        return False


    def query_param_single(self, name: str) -> str | None:
        self._parse_query_params()
        if self._query_params:
            found = self._query_params.get(name)
            if found:
                match len(found):
                    case 1:
                        return found[0]
                    case _:
                        raise RuntimeError(f'Query has {len(found)} values for query parameter {name}')
        return None


    def query_param_mult(self, name: str) -> List[str] | None:
        self._parse_query_params()
        if self._query_params:
            return self._query_params.get(name)
        return None


    def __repr__(self):
        return f'ParsedNonAcctUri({ self.get_uri() })'


    def _parse_query_params(self):
        if self._query_params:
            return
        if self.query:
            self._query_params = parse_qs(self.query)
        else:
            self._query_params = {}


class ParsedAcctUri(ParsedUri):
    """
    ParsedUris that are acct: URIs
    """
    def __init__(self, user: str, host: str):
        self.user = user
        self.host = host


    def get_uri(self) -> str:
        return f'acct:{ self.user }@{ self.host }'


    def __repr__(self):
        return f'ParsedAcctUri({ self.get_uri() })'



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


def account_id_parse_validate(candidate: str) -> ParsedUri | None:
    """
    Validate that the provided string is of the form 'acct:foo@bar.com'.
    return ParsedUri if valid, None otherwise
    """
    parsed = ParsedUri.parse(candidate)
    if isinstance(parsed,ParsedAcctUri):
        return parsed
    return None


def account_id_validate(candidate: str) -> str | None:
    parsed = account_id_parse_validate(candidate)
    if parsed:
        return parsed.get_uri()
    return None


def http_https_uri_parse_validate(candidate: str) -> ParsedUri | None:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI.
    return: ParsedUri if valid, None otherwise
    """
    parsed = ParsedUri.parse(candidate)
    if isinstance(parsed, ParsedNonAcctUri) and parsed.scheme in ['http', 'https'] and len(parsed.netloc) > 0:
        return parsed
    return None


def http_https_uri_validate(candidate: str) -> str | None:
    parsed = http_https_uri_parse_validate(candidate)
    if parsed:
        return parsed.get_uri()
    return None


def http_https_root_uri_parse_validate(candidate: str) -> ParsedUri | None:
    """
    Validate that the provided string is a valid HTTP or HTTPS URI without a path, query or
    fragment component
    return: ParsedUri if valid, None otherwise
    """
    parsed = ParsedUri.parse(candidate)
    if (isinstance(parsed, ParsedNonAcctUri) and parsed.scheme in ['http', 'https']
            and len(parsed.netloc) > 0
            and (len(parsed.path) == 0 or parsed.path == '/')
            and len(parsed.params) == 0
            and len(parsed.query) == 0
            and len(parsed.fragment) == 0):
        return parsed
    return None


def http_https_root_uri_validate(candidate: str) -> str | None:
    parsed = http_https_root_uri_parse_validate(candidate)
    if parsed:
        return parsed.get_uri()
    return None


def http_https_acct_uri_parse_validate(candidate: str) -> ParsedUri | None:
    """
    Validate that the provided string is a valid HTTP, HTTPS or ACCT URI.
    return: ParsedUri if valid, None otherwise
    """
    parsed = ParsedUri.parse(candidate)
    if isinstance(parsed,ParsedNonAcctUri):
        if parsed.scheme in ['http', 'https'] and len(parsed.netloc) > 0:
            return parsed

    elif isinstance(parsed,ParsedAcctUri):
        if parsed.user and parsed.host:
            return parsed
    return None


def http_https_acct_uri_validate(candidate: str) -> str | None:
    parsed = http_https_acct_uri_parse_validate(candidate)
    if parsed:
        return parsed.get_uri()
    return None


def uri_parse_validate(candidate: str) -> ParsedUri | None:
    """
    Validate that the provided string is a valid URI.
    return: string if valid, None otherwise
    """
    parsed = ParsedUri.parse(candidate)
    return parsed


def uri_validate(candidate: str) -> str | None:
    parsed = uri_parse_validate(candidate)
    if parsed:
        return parsed.get_uri()
    return None


def rfc5646_language_tag_parse_validate(candidate: str) -> str | None:
    """
    Validate a language tag according to RFC 5646, see https://www.rfc-editor.org/rfc/rfc5646.html
    return: string if valid, None otherwise
    """
    if Language.get(candidate).is_valid(): # FIXME needs checking that this library actually does what it says it does
        return candidate
    return None


def hostname_validate(candidate: str) -> str | None:
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


def appname_validate(candidate: str) -> str | None:
    """
    Validate that the provided string is a valid application name.
    return: string if valid, None otherwise
    """
    return candidate if len(candidate) > 0 else None


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
