"""
"""

from datetime import datetime
import httpx
import random
import string
from typing import Any, Callable, Iterable
from urllib.parse import urlparse, quote

from feditest import nodedriver
from feditest.protocols import NodeDriver
from feditest.protocols.web import WebClient, WebServerLog, HttpRequestResponsePair, ParsedUri
from feditest.protocols.webfinger import WebFingerClient, Jrd
from feditest.protocols.fediverse import FediverseNode
from feditest.reporting import info
from feditest.utils import account_id_validate


class Imp(WebFingerClient):

    # @override # from WebClient
    def http_get(self, uri: str) -> httpx.Response:
        # Do not follow redirects automatically, we need to know whether there are any
        print( f'XXX http_get of {uri}')
        return httpx.get(uri, follow_redirects=False)

    # @override # from WebFingerClient
    def perform_webfinger_query_for(self, resource_uri: str) -> Jrd:
        uri = self.construct_webfinger_uri(resource_uri)

        response: httpx.Response = None
        with httpx.Client(verify=False) as client:  # FIXME disable TLS cert verification for now
            info( f'Performing HTTP GET on {uri}')
            request = httpx.Request('GET', uri)
            for redirect_count in range(10, 0, -1):
                response = client.send(request)
                if response.is_redirect:
                    if redirect_count <= 0:
                        raise WebClient.TooManyRedirectsError(uri)
                    request = response.next_request

        if response and response.is_success :
            jrd = Jrd(response.content) # may raise
            jrd.validate() # may raise
            return jrd
        else:
            raise WebClient.HttpUnsuccessfulError(uri, response)

    def construct_webfinger_uri(self, resource_uri: str) -> str:
        """
        Helper method to construct the WebFinger URI from a resource URI
        """
        parsed_resource_uri = urlparse(resource_uri)
        match parsed_resource_uri.scheme:
            case 'acct':
                _, hostname = parsed_resource_uri.path.split('@', maxsplit=1) # 1: number of splits, not number of elements

            case 'http':
                hostname = parsed_resource_uri.netloc

            case 'https':
                hostname = parsed_resource_uri.netloc

            case _:
                raise WebFingerClient.UnsupportedUriSchemeError(uri)

        if not hostname:
            raise WebFingerClient.CannotDetermineWebfingerHost(resource_uri)

        uri = f"https://{hostname}/.well-known/webfinger?resource={quote(resource_uri)}"
        return uri

@nodedriver
class ImpInProcessDriver(NodeDriver):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    # Python 3.12 @override
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None ) -> Imp:
        if parameters:
            raise Exception('ImpInProcessDriver nodes do not take parameters')

        node = Imp(rolename, self);
        return node

    # Python 3.12 @override
    def _unprovision_node(self, node: Imp) -> None:
        pass
