"""
WebClient and WebServer, augmented with diagnostic functionality, that may be implemented by diagnostic Nodes.
"""

from datetime import UTC, date, datetime
from dataclasses import dataclass
from multidict import MultiDict
from typing import Any, Callable, List, final

from . import WebClient, WebServer
from feditest.nodedrivers import NotImplementedByNodeError
from feditest.utils import ParsedUri


@dataclass
class HttpRequest:
    """
    Captures an HTTP request.
    """
    parsed_uri: ParsedUri
    method: str = 'GET'
    accept_header : str | None = None
    payload : bytes | None = None
    content_type : str | None = None
    when_started: datetime = datetime.now(UTC) # Always need one so we can compare in the WebServerLog


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


class WebServerLog:
    """
    A list of logged HTTP requests to a web server.
    """
    def __init__(self, time_started: date = datetime.now(UTC), entries: List[HttpRequestResponsePair] | None = None ):
        self._time_started : date = time_started
        self._web_log_entries : List[HttpRequestResponsePair] = entries or []


    def append(self, to_add: HttpRequestResponsePair) -> None:
        self._web_log_entries.append(to_add)


    def entries(self):
        return self._web_log_entries


    def entries_since(self, cutoff: date) ->  'WebServerLog':
        ret : List[HttpRequestResponsePair] = []
        for entry in self._web_log_entries:
            if entry.request.when_started >= cutoff :
                ret.append(entry)
        return WebServerLog(cutoff, ret)


class WebDiagClient(WebClient):
    """
    Abstract class used for diagnostic Nodes that speak HTTP as client.
    """
    def http(self, request: HttpRequest, follow_redirects: bool = True, verify=False) -> HttpRequestResponsePair:
        """
        Make this WebClient perform an HTTP request.
        """
        raise NotImplementedByNodeError(self, WebDiagClient.http, request.method)
        # Unlikely that there is a manual action the user could take, so no prompt here


    def http_get(self, uri: str, follow_redirects: bool = True, verify=False) -> HttpRequestResponsePair:
        """
        Convenience function that makes it easier to invoke making this WebClient perform an HTTP GET request.
        """
        parsed = ParsedUri.parse(uri)
        if not parsed:
            raise ValueError('Invalid URI:', uri)
        return self.http(
            HttpRequest(parsed, "GET"),
            follow_redirects=follow_redirects,
            verify=verify,
        )


    class TooManyRedirectsError(RuntimeError):
        """
        Can be thrown to indicate that the WebClient has lost patience with the redirects of the server
        it is talking to.
        """
        def __init__(self, request: HttpRequest):
            """
            request: the original request before the first redirect
            """
            self._request = request


        def __str__(self):
            f'Too many redirects: { self._request.uri.uri }'


    class HttpUnsuccessfulError(RuntimeError):
        """
        Thrown to indicate an unsuccessful HTTP request because DNS could not be resolved, the request
        timed out etc.
        """
        def __init__(self, request: HttpRequest):
            """
            request: the request
            """
            self._request = request


        def __str__(self):
            f'Unsuccessful HTTP request: { self._request.uri.uri }'


    class TlsError(RuntimeError):
        """
        Raised when the provided TLS certificate was invalid.
        """
        def __init__(self, http_request_response_pair: HttpRequestResponsePair):
            self._http_request_response_pair = http_request_response_pair


        def __str__(self):
            return 'Invalid TLS certificate.' \
                   + f'\n -> "{ self._http_request_response_pair.response.payload_as_string() }"'


class WebDiagServer(WebServer):
    """
    Abstract class used for Nodes that speak HTTP as server.
    """
    @final
    def diag_http_transaction(self, code: Callable[[],None]) -> WebServerLog:
        """
        While this method runs, the server records incoming HTTP requests, and
        returns them as the return value of this method. In the method call,
        execute the provided code (usually to make the client do something
        that results in the hits to the WebServer
        code: the code to run
        return: the collected HTTP requests
        """
        collection_id : str = self._start_logging_http_requests()
        try:
            code()
            return self._stop_logging_http_requests(collection_id)

        finally:
            self._stop_logging_http_requests(collection_id)


    def _start_logging_http_requests(self) -> str:
        """
        Override this to instruct the WebServer to start logging HTTP requests.
        return: an identifier for the log
        see: _stop_logging_http_requests
        """
        raise NotImplementedByNodeError(self, WebDiagServer._start_logging_http_requests)
        # This could be done manually, but returning the log cannot


    def _stop_logging_http_requests(self, collection_id: str) -> WebServerLog:
        """
        Corresponding "stop logging" method.
        collection_id: same identifier as returned by _start_logging_http_requests
        return: the collected HTTP requests
        see: _start_logging_http_requests
        """
        raise NotImplementedByNodeError(self, WebDiagServer._stop_logging_http_requests)
        # This cannot be done manually


    @final
    def diag_override_http_response(self, code: Callable[[],Any], request: HttpRequest, overridden_response: HttpResponse) -> None:
        """
        Instruct the server to temporarily return the overridden_response when the
        specified request is made during execution of `code`.
        """
        self._start_override_http_response(request, overridden_response)
        try:
            code()
        finally:
            self._stop_override_http_response(request)


    def _start_override_http_response(self, request: HttpRequest, overridden_response: HttpResponse) -> None:
        """
        Override this to instruct the WebServer to return an alternate response when
        the provided request is made.
        """
        raise NotImplementedByNodeError(self, WebDiagServer._start_override_http_response)


    def _stop_override_http_response(self, request: HttpRequest) -> None:
        """
        Corresponding "stop override" method.
        """
        raise NotImplementedByNodeError(self, WebDiagServer._stop_override_http_response)
