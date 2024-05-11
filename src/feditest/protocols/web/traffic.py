"""
Abstract data types that capture what is exchanged over HTTP.
"""

from datetime import UTC, date, datetime
from dataclasses import dataclass
from typing import List
from urllib.parse import ParseResult, parse_qs, urlparse
from multidict import MultiDict

class ParsedUri:
    """
    An abstract data type for URIs. We want it to provide methods for accessing parameters,
    and so we don't use ParseResult. Also failed attempting to inherit from it.
    """
    def __init__(self, scheme: str, netloc: str, path: str, params: str, query: str, fragment: str):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.params = params
        self.query = query
        self.fragment = fragment
        self._query_params : dict[str,list[str]] | None = None


    @staticmethod
    def parse(url: str, scheme='', allow_fragments=True) -> 'ParsedUri':
        """
        The equivalent of urlparse(str)
        """
        parsed : ParseResult = urlparse(url, scheme, allow_fragments)
        return ParsedUri(parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)


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
        return f'ParsedUri({ self.get_uri() })'


    def _parse_query_params(self):
        if self._query_params:
            return
        if self.query:
            self._query_params = parse_qs(self.query)
        else:
            self._query_params = {}


@dataclass
class HttpRequest:
    """
    Captures an HTTP request.
    """
    uri: ParsedUri
    method: str = 'GET'
    accept_header : str | None = None
    payload : bytes | None = None
    content_type : str | None = None
    when_started: date = datetime.now(UTC)


@dataclass
class HttpResponse:
    """
    Captures the response of an HTTP request.
    """
    http_status : int
    response_headers: MultiDict # keys are lowercased
    payload : bytes | None = None
    when_completed: date | None = datetime.now(UTC)


    def content_type(self):
        return self.response_headers.get('content-type')


    def payload_charset(self):
        content_type = self.content_type()
        tag = 'charset='
        if content_type and content_type.find(tag) >= 0:
            return content_type[ content_type.find(tag)+len(tag) : ]
        return None


    def payload_as_string(self):
        if not self.payload:
            return None
        content_type = self.content_type()
        if content_type and content_type.startswith('text/'):
            return self.payload.decode(self.payload_charset())
        raise ValueError()


    def location(self):
        return self.response_headers.get('location')


    def is_redirect(self):
        return self.http_status in [301, 302, 303, 307, 308]




@dataclass
class HttpRequestResponsePair:
    request: HttpRequest # the original request, in case of redirects
    final_request: HttpRequest # this is the request that actually produced this response, in case of redirects
    response: HttpResponse | None # the response, if one was obtained
