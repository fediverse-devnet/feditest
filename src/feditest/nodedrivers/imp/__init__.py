"""
An in-process Node implementation for now.
"""

from typing import Any
import httpx
from multidict import MultiDict

from feditest import nodedriver
from feditest.protocols import Node, NodeDriver, NodeSpecificationInvalidError
from feditest.protocols.web import ParsedUri, WebClient
from feditest.protocols.web.traffic import HttpRequest, HttpRequestResponsePair, HttpResponse
from feditest.protocols.webfinger import WebFingerClient
from feditest.protocols.webfinger.traffic import ClaimedJrd, WebFingerQueryResponse
from feditest.reporting import trace


class Imp(WebFingerClient):
    """
    Our placeholder test client. Its future is to ~~tbd~~ be factored out of here.
    """
    # use superclass constructor

    # @override # from WebClient
    def http(self, request: HttpRequest) -> HttpRequestResponsePair:
        trace( f'Performing HTTP { request.method } on { request.uri.get_uri() }')

        httpx_response = None
        # Do not follow redirects automatically, we need to know whether there are any
        with httpx.Client(verify=False, follow_redirects=False) as httpx_client:  # FIXME disable TLS cert verification for now
            httpx_request = httpx.Request(request.method, request.uri.get_uri()) # FIXME more arguments
            httpx_response = httpx_client.send(httpx_request)

        if httpx_response:
            response_headers : MultiDict = MultiDict()
            for key, value in httpx_response.headers.items():
                response_headers.add(key.lower(), value)
            return HttpRequestResponsePair(request, request, HttpResponse(httpx_response.status_code, response_headers, httpx_response.read()))
        raise WebClient.HttpUnsuccessfulError(request)


    # @override # from WebFingerClient
    def perform_webfinger_query(self, resource_uri: str, rels: list[str] | None = None) -> WebFingerQueryResponse:
        uri = self.construct_webfinger_uri_for(resource_uri, rels)

        first_request = HttpRequest(ParsedUri.parse(uri))
        current_request = first_request
        pair : HttpRequestResponsePair | None = None
        for redirect_count in range(10, 0, -1):
            pair = self.http(current_request)
            if pair.response and pair.response.is_redirect():
                if redirect_count <= 0:
                    raise WebClient.TooManyRedirectsError(current_request)
                current_request = HttpRequest(ParsedUri.parse(pair.response.location()))
            break

        # I guess we always have a non-null responses here, but mypy complains without the if
        if pair:
            ret_pair = HttpRequestResponsePair(first_request, current_request, pair.response)
            if ret_pair.response is not None:
                if ret_pair.response.http_status == 200:
                    if ret_pair.response.content_type() == 'application/jrd+json' or ret_pair.response.content_type().startswith('application/jrd+json;'):
                        if ret_pair.response.payload is not None:
                            json_string = ret_pair.response.payload.decode(
                                encoding=ret_pair.response.payload_charset() or "utf8" )
                            jrd = ClaimedJrd(json_string)
                            jrd.validate()
                            return WebFingerQueryResponse(pair, jrd)
                        raise WebFingerClient.WebfingerQueryFailedError(uri, ret_pair, "No payload")
                    raise WebFingerClient.WebfingerQueryFailedError(uri, ret_pair, f"Invalid content type: { ret_pair.response.content_type() }")
                raise WebFingerClient.WebfingerQueryFailedError(uri, ret_pair, f"Invalid HTTP status: { ret_pair.response.http_status }")

        raise WebFingerClient.WebfingerQueryFailedError(uri, ret_pair)


@nodedriver
class ImpInProcessNodeDriver(NodeDriver):
    """
    Knows how to instantiate an Imp.
    """
    # use superclass constructor

    # Python 3.12 @override
    def _provision_node(self, rolename: str, parameters: dict[str,Any] ) -> Imp:
        if parameters:
            raise NodeSpecificationInvalidError(self, 'any', 'No parameters can be specified')

        node = Imp(rolename, parameters, self)
        return node


    # Python 3.12 @override
    def _unprovision_node(self, node: Node) -> None:
        pass
