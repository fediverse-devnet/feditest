"""
"""

from datetime import date, datetime, timezone
import httpx
from typing import Callable, List, final
from urllib.parse import ParseResult as ParsedUri

from feditest.protocols import Node, NodeDriver, NotImplementedByDriverError

class HttpRequestResponsePair:
    """
    A single logged HTTP request and response
    """
    def __init__(
            self,
            when: date,
            uri: ParsedUri,
            status: int ):
        """
        Create a single log event.
        when: time when request was made
        uri: the ParseResult from parsing the request URI
        status: the returned HTTP status, such as 404
        """
        self.when = when
        self.uri = uri
        self.status = status


class WebServerLog:
    """
    A list of logged HTTP requests to a web server.
    """
    def __init__(self):
        self.time_started : date = datetime.now(timezone.utc)
        self.web_log_entries : List[HttpRequestResponsePair] = ()

    
    def append(self, to_add: HttpRequestResponsePair) -> None:
        self.web_log_entries.append(to_add)


class WebServer(Node):
    """
    Abstract class used for Nodes that speak HTTP as server.
    """
    def __init__(self, nickname: str, hostname: str, node_driver: 'NodeDriver') -> None:
        super().__init__(nickname, node_driver)
        
        self._hostname = hostname

    def get_hostname(self) -> str:
        """
        Return a resolvable DNS hostname that resolves to this WebServerNode.
        """
        return self._hostname
    
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

        finally:
            return self._stop_logging_http_requests(collection_id)


    def _start_logging_http_requests(self) -> str:
        """
        Override this to instruct the WebServer to start logging HTTP requests.
        return: an identifier for the log
        see: _stop_logging_http_requests
        """
        raise NotImplementedByDriverError(WebServer._start_logging_http_requests)
    
    
    def _stop_logging_http_requests(self, collection_id: str) -> WebServerLog:
        """
        Corresponding "stop logging" method.
        collection_id: same identifier as returned by _start_logging_http_requests
        return: the collected HTTP requests
        see: _start_logging_http_requests
        """
        raise NotImplementedByDriverError(WebServer._stop_logging_http_requests)


class WebClient(Node):
    def __init__(self, nickname: str, iut_driver: 'NodeDriver') -> None:
        super().__init__(nickname, iut_driver)

    def http_get(self, uri: str) -> httpx.Response:
        """
        Make this WebClientIUT perform an HTTP get on the provided uri.
        """
        raise NotImplementedByDriverError(WebClient._http_get)

    class TooManyRedirectsError(RuntimeError):
        """
        Can be thrown to indicate that the WebClient has lost patience with the redirects of the server
        it is talking to.
        """
        def __init__(self, uri: str):
            """
            uri: the original URI before the first redirect
            """
            self.uri = uri
            
    class HttpUnsuccessfulError(RuntimeError):
        """
        Thrown to indicate an unsuccessful HTTP request.
        """
        def __init__(self, uri: str, response: httpx.Response):
            """
            uri: the original URI
            response: the failed response
            """
            self.uri = uri
            self.response = response
