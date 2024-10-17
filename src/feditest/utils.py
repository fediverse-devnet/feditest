"""
Utility functions
"""

from abc import ABC, abstractmethod
import glob
import importlib.util
import pkgutil
import re
import sys
import importlib.metadata
from types import ModuleType
from typing import Any, Callable, List, Optional, TypeVar
from urllib.parse import ParseResult, parse_qs, urlparse
from langcodes import Language

from feditest.reporting import warning

def _version(default_version="0.0.0"):
    try:
        return importlib.metadata.version("feditest")
    except importlib.metadata.PackageNotFoundError:
        return default_version

FEDITEST_VERSION = _version('feditest')

# From https://datatracker.ietf.org/doc/html/rfc7565#section-7, but simplified
ACCT_REGEX = re.compile(r"acct:([-a-zA-Z0-9\._~][-a-zA-Z0-9\._~!$&'\(\)\*\+,;=%]*)@([-a-zA-Z0-9\.:]+)")
SSH_REGEX = re.compile(r"ssh://([-a-z-A-Z0-9\._~!$&'\(\)\*\+,;=%:]+@)?([-a-zA-Z0-9\.:]+)(:[0-9]+)?")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$")

T = TypeVar("T")


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


    @property
    @abstractmethod
    def scheme(self) -> str:
        ...


    @property
    @abstractmethod
    def uri(self) -> str:
        ...


class ParsedNonAcctUri(ParsedUri):
    """
    ParsedUris that are "normal" URIs such as http URIs.
    """
    def __init__(self, scheme: str, netloc: str, path: str, params: str, query: str, fragment: str):
        self._scheme = scheme
        self._netloc = netloc
        self._path = path
        self._params = params
        self._query = query
        self._fragment = fragment
        self._query_params : dict[str,list[str]] | None = None


    # Python 3.12 @override
    @property
    def scheme(self) -> str:
        return self._scheme


    @property
    def netloc(self) -> str:
        return self._netloc


    @property
    def path(self) -> str:
        return self._path


    @property
    def params(self) -> str:
        return self._params


    @property
    def fragment(self) -> str:
        return self._fragment


    @property
    def query(self) -> str:
        return self._query


    # Python 3.12 @override
    @property
    def uri(self) -> str:
        ret = f'{ self._scheme }:'
        if self._netloc:
            ret += f'//{ self._netloc}'
        ret += self._path
        if self._params:
            ret += f';{ self._params}'
        if self._query:
            ret += f'?{ self._query }'
        if self._fragment:
            ret += f'#{ self._fragment }'
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


    # Python 3.12 @override
    def __repr__(self):
        return f'ParsedNonAcctUri({ self.uri })'


    def _parse_query_params(self):
        if self._query_params:
            return
        if self._query:
            self._query_params = parse_qs(self.query)
        else:
            self._query_params = {}


class ParsedAcctUri(ParsedUri):
    """
    ParsedUris that are acct: URIs
    """
    def __init__(self, user: str, host: str):
        self._user = user
        self._host = host


    # Python 3.12 @override
    @property
    def scheme(self) -> str:
        return 'acct'


    @property
    def user(self) -> str:
        return self._user


    @property
    def host(self) -> str:
        return self._host


    # Python 3.12 @override
    @property
    def uri(self) -> str:
        return f'acct:{ self.user }@{ self.host }'


    # Python 3.12 @override
    def __repr__(self):
        return f'ParsedAcctUri({ self.uri })'



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
                    try :
                        spec.loader.exec_module(module)
                    except BaseException as e:
                        warning(f'Attempt to lead module { module_name } failed. Skipping.', e)
        finally:
            sys.path = sys_path_before


def boolean_parse_validate(candidate: Any | None) -> bool | None:
    """
    Validate that the provided string represents a boolean.
    Return the boolean if valid, None otherwise
    """
    if candidate is None:
        return False
    if isinstance(candidate, bool):
        return candidate
    if isinstance(candidate,str):
        lower = candidate.lower()
    else:
        lower = str(candidate).lower()
    if lower in ("yes", "true", "y", "t", "1"):
        return True
    if lower in ("no", "false", "n", "f", "0"):
        return False
    return None


def acct_uri_parse_validate(candidate: str) -> ParsedUri | None:
    """
    Validate that the provided string is of the form 'acct:foo@bar.com'.
    return ParsedUri if valid, None otherwise
    """
    parsed = ParsedUri.parse(candidate)
    if isinstance(parsed,ParsedAcctUri):
        return parsed
    return None


def acct_uri_validate(candidate: str) -> str | None:
    parsed = acct_uri_parse_validate(candidate)
    if parsed:
        return parsed.uri
    return None


def acct_uri_list_validate(candidate: str) -> str | None:
    for uri in candidate.split():
        if not acct_uri_validate(uri):
            return None
    return candidate


def https_uri_parse_validate(candidate: str) -> ParsedUri | None:
    """
    Validate that the provided string is a valid HTTPS URI.
    return: ParsedUri if valid, None otherwise
    """
    parsed = ParsedUri.parse(candidate)
    if isinstance(parsed, ParsedNonAcctUri) and parsed.scheme == 'https' and len(parsed.netloc) > 0:
        return parsed
    return None


def https_uri_validate(candidate: str) -> str | None:
    parsed = https_uri_parse_validate(candidate)
    if parsed:
        return parsed.uri
    return None


def https_uri_list_validate(candidate: str) -> str | None:
    for uri in candidate.split():
        if not https_uri_validate(uri):
            return None
    return candidate


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
        return parsed.uri
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
        return parsed.uri
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
        return parsed.uri
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
        return parsed.uri
    return None


def ssh_uri_validate(candidate: str) -> str | None:
    """
    Form ssh://[user@]hostname[:port] per 'man ssh'
    """
    if SSH_REGEX.match(candidate):
        return candidate
    return None


def email_validate(candidate: str) -> str | None:
    if EMAIL_REGEX.match(candidate):
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


def appversion_validate(candidate: str) -> str | None:
    """
    Validate that the provided string is a valid application version.
    return: string if value, None otherwise
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


def find_first_in_array(array: List[T], condition: Callable[[T], bool]) -> T | None:
    """
    IMHO this should be a python built-in function. The next() workaround confuses me more than I like.
    """
    for t in array:
        if condition(t):
            return t
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


def prompt_user_parse_validate(question: str, parse_validate: Callable[[str],T | None]) -> T:
    """
    Prompt the user to enter a text string at the console. Parse/validate the entered
    String, and keep asking until validation passes. Return the parsed string.

    question: the text to be emitted to the user as a prompt
    parse_validate: function that attempts to parse and validate the provided user input.
    return: the value entered by the user (parsed)
    """
    while True:
        ret = input(f'TESTER ACTION REQUIRED: { question }')
        ret_parsed = parse_validate(ret)
        if ret_parsed is not None:
            return ret_parsed
        print(f'INPUT ERROR: invalid input, try again. Was: "{ ret }"')


def prompt_user(question: str) -> str:
    """
    Prompt the user to enter a text string at the console.

    question: the text to be emitted to the user as a prompt
    return: the value entered by the user
    """
    ret = input(f'TESTER ACTION REQUIRED: { question }')
    return ret
