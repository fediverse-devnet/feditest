"""
"""

from datetime import UTC, date, datetime
from typing import Any, Callable, List, final

from feditest.protocols import Node, NodeDriver, NotImplementedByNodeError
from feditest.protocols.web.traffic import (
    HttpRequest,
    HttpRequestResponsePair,
    ParsedUri,
)


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


class WebServer(Node):
    """
    Abstract class used for Nodes that speak HTTP as server.
    """

    def __init__(self, rolename: str, parameters: dict[str,Any], node_driver: 'NodeDriver'):
        """
        WebServers need to know their hostnames.
        """
        super().__init__(rolename, parameters, node_driver)

        if not parameters.get("server-prefix") and not parameters.get('hostname'):
            raise Exception('Required: parameters["hostname"]')


    @final
    def transaction(self, code: Callable[[],None]) -> WebServerLog:
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
        raise NotImplementedByNodeError(self, WebServer._start_logging_http_requests)
        # This could be done manually, but returning the log cannot


    def _stop_logging_http_requests(self, collection_id: str) -> WebServerLog:
        """
        Corresponding "stop logging" method.
        collection_id: same identifier as returned by _start_logging_http_requests
        return: the collected HTTP requests
        see: _start_logging_http_requests
        """
        raise NotImplementedByNodeError(self, WebServer._stop_logging_http_requests)
        # This cannot be done manually


    def override_http_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):
        """
        Instruct the server to temporarily return the overridden_json_response when the client_operation is performed.
        """
        raise NotImplementedByNodeError(self, WebServer.override_http_response)


class WebClient(Node):
    """
    Abstract class used for Nodes that speak HTTP as client.
    """
    def http(self, request: HttpRequest, follow_redirects: bool = True, verify=False) -> HttpRequestResponsePair:
        """
        Make this WebClient perform an HTTP request.
        """
        raise NotImplementedByNodeError(self, WebClient.http, request.method)
        # Unlikely that there is a manual action the user could take, so no prompt here

    def http_get(self, uri: str, follow_redirects: bool = True, verify=False) -> HttpRequestResponsePair:
        """
        Make this WebClientperform an HTTP get on the provided uri.
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
            f'Too many redirects: { self._request.uri.get_uri() }'

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
            f'Unsuccessful HTTP request: { self._request.uri.get_uri() }'

    class WrongHttpStatusError(RuntimeError):
        """
        Raised when an HTTP status was obtained that was wrong for the situation.
        """
        def __init__(self, http_request_response_pair: HttpRequestResponsePair):
            self._http_request_response_pair = http_request_response_pair

        def __str__(self):
            return 'Wrong HTTP status code.' \
                   + f'\n -> { self._http_request_response_pair.response.http_status }'

    class WrongContentTypeError(RuntimeError):
        """
        Raised when payload of a content type was received that was wrong for the situation
        """
        def __init__(self, http_request_response_pair: HttpRequestResponsePair):
            self._http_request_response_pair = http_request_response_pair

        def __str__(self):
            return 'Wrong HTTP content type.' \
                   + f'\n -> "{ self._http_request_response_pair.response.content_type() }"'
