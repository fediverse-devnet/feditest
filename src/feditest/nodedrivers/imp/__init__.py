"""
An in-process Node implementation for now.
"""

from typing import Any, cast

import httpx
from multidict import MultiDict

from feditest import nodedriver
from feditest.protocols import Node, NodeDriver
from feditest.protocols.web import ParsedUri, WebClient
from feditest.protocols.web.traffic import (
    HttpRequest,
    HttpRequestResponsePair,
    HttpResponse,
)
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer
from feditest.protocols.webfinger.traffic import ClaimedJrd, WebFingerQueryResponse
from feditest.reporting import trace
from feditest.utils import FEDITEST_VERSION

_HEADERS = {
    "User-Agent": f"feditest/{ FEDITEST_VERSION }",
    "Origin": "test.example" # to trigger CORS headers in response
}

class Imp(WebFingerClient):
    """
    Our placeholder test client. Its future is to ~~tbd~~ be factored out of here.
    """
    # use superclass constructor

    @property
    def app_version(self):
        return FEDITEST_VERSION

    # @override # from WebClient
    def http(self, request: HttpRequest, follow_redirects: bool = True, verify=False) -> HttpRequestResponsePair:
        trace( f'Performing HTTP { request.method } on { request.uri.get_uri() }')

        httpx_response = None
        # Do not follow redirects automatically, we need to know whether there are any
        with httpx.Client(verify=verify, follow_redirects=follow_redirects) as httpx_client:  # FIXME disable TLS cert verification for now
            httpx_request = httpx.Request(request.method, request.uri.get_uri(), headers=_HEADERS) # FIXME more arguments
            httpx_response = httpx_client.send(httpx_request)

        if httpx_response:
            response_headers : MultiDict = MultiDict()
            for key, value in httpx_response.headers.items():
                response_headers.add(key.lower(), value)
            ret = HttpRequestResponsePair(request, request, HttpResponse(httpx_response.status_code, response_headers, httpx_response.read()))
            trace( f'HTTP query returns { ret }')
            return ret
        raise WebClient.HttpUnsuccessfulError(request)

    # @override # from WebFingerClient
    def perform_webfinger_query(
        self,
        server: WebFingerServer,
        resource_uri: str|None = None,
        rels: list[str] | None = None,
    ) -> WebFingerQueryResponse:
        if resource_uri is None:
            resource_uri = server.parameter("existing-account-uri")
        if server_prefix := server.parameter("server-prefix"):
            query_url = self.construct_webfinger_query_for(server_prefix, resource_uri, rels)
        else:
            query_url = self.construct_webfinger_uri_for(resource_uri, rels, server.parameter("hostname"))
        parsed_uri = ParsedUri.parse(query_url)
        if not parsed_uri:
            raise ValueError('Not a valid URI:', query_url) # can't avoid this
        first_request = HttpRequest(parsed_uri)
        current_request = first_request
        pair : HttpRequestResponsePair | None = None
        for redirect_count in range(10, 0, -1):
            pair = self.http(current_request)
            if pair.response and pair.response.is_redirect():
                if redirect_count <= 0:
                    return WebFingerQueryResponse(pair, None, WebClient.TooManyRedirectsError(current_request))
                parsed_location_uri = ParsedUri.parse(pair.response.location())
                if not parsed_location_uri:
                    return WebFingerQueryResponse(pair, None, ValueError('Location header is not a valid URI:', query_url, '(from', resource_uri, ')'))
                current_request = HttpRequest(parsed_location_uri)
            break

        # I guess we always have a non-null responses here, but mypy complains without the cast
        pair = cast(HttpRequestResponsePair, pair)
        ret_pair = HttpRequestResponsePair(first_request, current_request, pair.response)
        if ret_pair.response is None:
            raise RuntimeError('Unexpected None HTTP response')

        excs : list[Exception] = []
        if ret_pair.response.http_status != 200:
            excs.append(WebClient.WrongHttpStatusError(ret_pair))

        content_type = ret_pair.response.content_type()
        if (content_type is None or (content_type != "application/jrd+json"
            and not content_type.startswith( "application/jrd+json;" ))
        ):
            excs.append(WebClient.WrongContentTypeError(ret_pair))

        jrd : ClaimedJrd | None = None

        if ret_pair.response.payload is None:
            raise RuntimeError('Unexpected None payload in HTTP response')

        try:
            json_string = ret_pair.response.payload.decode(encoding=ret_pair.response.payload_charset() or "utf8")

            jrd = ClaimedJrd(json_string) # May throw JSONDecodeError
            jrd.validate() # May throw JrdError
        except ExceptionGroup as exc:
            excs += exc.exceptions
        except Exception as exc:
            excs.append(exc)

        if len(excs) > 1:
            return WebFingerQueryResponse(ret_pair, jrd, ExceptionGroup('WebFinger errors', excs))
        elif len(excs) == 1:
            return WebFingerQueryResponse(ret_pair, jrd, excs[0])
        else:
            return WebFingerQueryResponse(ret_pair, jrd, None)


@nodedriver
class ImpInProcessNodeDriver(NodeDriver):
    """
    Knows how to instantiate an Imp.
    """
    # use superclass constructor

    # Python 3.12 @override
    def _provision_node(self, rolename: str, parameters: dict[str,Any] ) -> Imp:
        parameters['app'] = 'Imp'
        node = Imp(rolename, parameters, self)
        return node


    # Python 3.12 @override
    def _unprovision_node(self, node: Node) -> None:
        pass
