"""
"""

from datetime import datetime
import httpx
import random
import string
from typing import Any
from urllib.parse import urlparse, quote

from feditest import appdriver
from feditest.protocols import NodeDriver
from feditest.protocols.web import WebClient, WebServerLog
from feditest.protocols.webfinger import WebFingerClient, Jrd
from feditest.protocols.fediverse import FediverseNode

class Imp(FediverseNode, WebFingerClient):
    def __init__(self, nickname: str, node_driver: 'ImpInProcessDriver') -> None:
        super().__init__(self, nickname, node_driver)
        
        self._hosted_accounts : dict[str,str]= ()

    # @override # from WebClient
    def http_get(self, uri: str) -> httpx.Response:
        # Do not follow redirects automatically, we need to know whether there are any
        return httpx.get(uri, follow_redirects=False)

    # @override # from WebServer
    def _start_logging_http_requests(self) -> str:
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # @override # from WebServer
    def _stop_logging_http_requests(self, collection_id: str) -> WebServerLog:
        ...

    # @override # from WebFingerClient
    def perform_webfinger_query_on_resource(self, resource_uri: str) -> Jrd:
        uri = self.construct_webfinger_uri(resource_uri)

        request = httpx.Request('GET', uri)
        response: httpx.Response = None
        for redirect_count in range(10, 0, -1):
            response = self.http_get(request)
            if response.is_redirect:
                if redirect_count <= 0:
                    raise WebClient.TooManyRedirectsError(uri)
                request = response.next_request

        if response.is_success :
            jrd = Jrd(response.content)
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
                _, hostname = parsed_resource_uri.netloc.split('@', maxsplit=1) # 1: number of splits, not number of elements

            case 'http':
                hostname = parsed_resource_uri.netloc

            case 'https':
                hostname = parsed_resource_uri.netloc

            case _:
                raise WebFingerClient.UnsupportedUriSchemeError(uri)

        if not hostname:
            raise WebFingerClient.CannotDetermineWebfingerHost(resource_uri)

        uri = f"https://{hostname}/.well-known/webfinger?resource={quote(resource_uri)}"

    # @override # from WebFingerServer
    def obtain_account_identifier(self) -> str:
        # Simply create a new one
        ret = self.obtain_non_existing_account_identifier();
        self._hosted_accounts[ret] = ret
        return ret

    # @override # from WebFingerServer
    def obtain_non_existing_account_identifier(self) ->str:
        while True :
            ret = ''.join(random.choice(string.ascii_lowercase) for i in range(8)) + '@' + self._hostname
            if not ret in self._hosted_accounts:
                return ret
            # Very unlikely

    # @override # from ActivityPubNode
    def obtain_actor_document_uri(self) -> str:
        ...

    # @override # from ActivityPubNode
    def create_actor_document_uri(self) -> str:
        ...


@appdriver
class ImpInProcessDriver(NodeDriver):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    # Python 3.12 @override
    def _provision_node(self, nickname: str) -> Imp:
        return Imp(nickname, self);

    # Python 3.12 @override
    def _unprovision_node(self, instance: Imp) -> None:
        pass # no op so far




