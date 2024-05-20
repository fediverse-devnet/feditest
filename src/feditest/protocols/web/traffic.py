"""
Abstract data types that capture what is exchanged over HTTP.
"""

from datetime import UTC, date, datetime
from dataclasses import dataclass
from multidict import MultiDict

from feditest.utils import ParsedUri


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
