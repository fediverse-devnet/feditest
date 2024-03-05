"""
Abstractions for the WebFinger protocol
"""

import httpx
from typing import Any

from feditest.protocols import NodeDriver
from feditest.protocols.web import WebClient, WebServer


class WebFingerServer(WebServer):
    """
    A Node that acts as a WebFinger server.
    """
    def obtain_account_identifier(self, nickname: str = None) -> str:
        """
        Return the identifier of an existing or newly created account on this
        Node that a client is supposed to be able to perform WebFinger resolution on.
        The identifier is of the form ``acct:foo@bar.com``.
        nickname: refer to this account by this nickname; used to disambiguate multiple accounts on the same server
        return: the identifier
        """
        if nickname:
            return self.node_driver.prompt_user(
                    f'Please enter the URI of an existing or new account for {nickname} at node {self._rolename} (e.g. "acct:testuser@example.local" )',
                    account_id_validate )
        else:
            return self.node_driver.prompt_user(
                    f'Please enter the URI of an existing or new account at node {self._rolename} (e.g. "acct:testuser@example.local" )',
                    account_id_validate )


    def obtain_non_existing_account_identifier(self, nickname: str = None ) ->str:
        """
        Return the identifier of an account that does not exist on this Node, but that
        nevertheless follows the rules for identifiers of this Node.
        The identifier is of the form ``foo@bar.com``.
        nickname: refer to this account by this nickname; used to disambiguate multiple accounts on the same server
        return: the identifier
        """
        if nickname:
            return self.node_driver.prompt_user(
                f'Please enter the URI of an non-existing account for {nickname} at node {self._rolename} (e.g. "acct:does-not-exist@example.local" )',
                account_id_validate )
        else:
            return self.node_driver.prompt_user(
                f'Please enter the URI of an non-existing account at node {self._rolename} (e.g. "acct:does-not-exist@example.local" )',
                account_id_validate )


class WebFingerClient(WebClient):
    """
    A Node that acts as a WebFinger client.
    """
    def perform_webfinger_query_for(self, resource_uri: str) -> dict[str,Any]:
        """
        Make this Node perform a WebFinger query for the provided resource_uri.
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        Return a dict that is the parsed form of the JRD or throws an exception
        """
        return self.node_driver.prompt_user(
            f'Please take an action at node {self._rolename} that makes it perform a WebFinger query on URI {resource_uri}' )


    class UnknownResourceException(RuntimeError):
        """
        Raised when a WebFinger query results in a 404 because the resource cannot be
        found by the server.
        resource_uri: URI of the resource
        http_response: the underlying Response object
        """
        def __init__(self, resource_uri: str, http_response: httpx.Response):
            self._resource_uri = resource_uri
            self._http_response = http_response


    class UnsupportedUriSchemeError(RuntimeError):
        def __init__(self, resource_uri: str):
            self._resource_uri = resource_uri


    class InvalidUriError(RuntimeError):
        def __init__(self, resource_uri: str):
            self._resource_uri = resource_uri


    class CannotDetermineWebfingerHost(RuntimeError):
        def __init__(self, resource_uri: str):
            self._resource_uri = resource_uri
