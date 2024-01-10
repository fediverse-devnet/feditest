"""
"""

from datetime import date, datetime, timezone
import httpx
from typing import Callable, List
from urllib import ParseResult as ParsedUri

from feditest.iut import IUT, IUTDriver, NotImplementedByIUTError
from feditest.utils import http_https_root_uri_validate

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


class WebServerIUT(IUT):
    def __init__(self, nickname: str, iut_driver: 'WebServerIUTDriver') -> None:
        super().__init__(nickname, iut_driver)

    def get_root_uri(self) -> str:
        """
        Return the fully-qualified top-level URI at which this WebIUT serves HTTP or HTTPS.
        The identifier is of the form ``http[s]://example.com/``. It does contain scheme
        and resolvable hostname, but does not contain path, fragment, or query elements.
        return: the URI
        """
        return self._iut_driver.prompt_user(
            'Please enter the WebIUT\' root URI (e.g. "https://example.local/" )',
            http_https_root_uri_validate )
        
        
    def get_domain_name(self) -> str:
        """
        Return a resolvable DNS hostname that resolves to this WebServerIUT.
        """
        raise NotImplementedByIUTError(WebServerIUT.get_domain_name)
    
    
    def transaction(self, code: Callable[[],None]) -> WebServerLog:
        """
        While this method runs, the server records incoming HTTP requests, and
        returns them when this method returns. During the method call, execute
        the provided code.
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
        Override this to instruct the IUT to start logging HTTP requests.
        return: an identifier for the log
        see: _stop_logging_http_requests
        """
        raise NotImplementedByIUTError(WebServerIUT._start_logging_http_requests)
    
    
    def _stop_logging_http_requests(self, collection_id: str) -> WebServerLog:
        """
        Corresponding "stop logging" method.
        collection_id: same identifier as returned by _start_logging_http_requests
        return: the collected HTTP requests
        see: _start_logging_http_requests
        """
        raise NotImplementedByIUTError(WebServerIUT._stop_logging_http_requests)


class WebServerIUTDriver(IUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> WebServerIUT:
        return WebServerIUT(nickname, self);


class WebClientIUT(IUT):
    def __init__(self, nickname: str, iut_driver: 'WebClientIUTDriver') -> None:
        super().__init__(nickname, iut_driver)

    def http_get(self, uri: str) -> httpx.Response:
        """
        Make this WebClientIUT perform an HTTP get on the provided uri.
        """
        raise NotImplementedByIUTError(WebClientIUT._http_get)


class WebClientIUTDriver(IUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> WebClientIUT:
        return WebClientIUT(nickname, self);
