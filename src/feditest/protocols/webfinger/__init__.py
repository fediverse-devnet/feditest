"""
Abstractions for the WebFinger protocol
"""

from typing import Any, Callable
from urllib.parse import quote, urlparse

from feditest.protocols import NotImplementedByNodeError
from feditest.protocols.web import WebClient, WebServer
from feditest.protocols.webfinger.traffic import WebFingerQueryResponse
from feditest.utils import http_https_acct_uri_validate


class WebFingerServer(WebServer):
    """
    A Node that acts as a WebFinger server.

    The implementation code in this class is here entirely for fallback purposes. Given this,
    we are not trying to manage the collection behind the smart factory methods.
    """
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        """
        Smart factory method to return the identifier to an account on this Node that
        a client is supposed to be able to perform WebFinger resolution on. Different
        rolenames produce different results; the same rolename produces the same result.
        The identifier is of the form ``acct:foo@bar.com``.
        rolename: refer to this account by this rolename; used to disambiguate multiple
           accounts on the same server by how they are used in tests
        return: the identifier
        """
        if rolename:
            ret = self.prompt_user(
                    f'Please enter the URI of an existing or new account for role "{rolename}" at Node "{self._rolename}" (e.g. "acct:testuser@example.local" ): ',
                    self.parameter('existing-account-uri'),
                    http_https_acct_uri_validate)
        else:
            ret = self.prompt_user(
                    f'Please enter the URI of an existing or new account at Node "{self._rolename}" (e.g. "acct:testuser@example.local" ): ',
                    self.parameter('existing-account-uri'),
                    http_https_acct_uri_validate)
        assert ret
        self.set_parameter('existing-account-uri', ret)
        return ret


    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        """
        Smart factory method to return the identifier of an account that does not exist on this Node,
        but that nevertheless follows the rules for identifiers of this Node. Different rolenames
        produce different results; the same rolename produces the same result.
        The identifier is of the form ``acct:foo@bar.com``.
        rolename: refer to this account by this rolename; used to disambiguate multiple
           accounts on the same server by how they are used in tests
        return: the identifier
        """
        if rolename:
            ret = self.prompt_user(
                    f'Please enter the URI of an non-existing account for role "{rolename}" at Node "{self._rolename}" (e.g. "acct:does-not-exist@example.local" ): ',
                    self.parameter('nonexisting-account-uri'),
                    http_https_acct_uri_validate)
        else:
            ret = self.prompt_user(
                    f'Please enter the URI of an non-existing account at Node "{self._rolename}" (e.g. "acct:does-not-exist@example.local" ): ',
                    self.parameter('nonexisting-account-uri'),
                    http_https_acct_uri_validate)
        assert ret
        self.set_parameter('nonexisting-account-uri', ret)
        return ret


    def obtain_account_identifier_requiring_percent_encoding(self, nickname: str | None = None) -> str:
        """
        Smart factory method to return the identifier of an existing or newly created account on this
        Node that contains characters that require percent-encoding when provided as resource in a WebFinger
        query. Different rolenames produce different results; the same rolename produces the same result.

        If the Node does not ever issue such identifiers, raise NotImplementedByNodeException
        """
        raise NotImplementedByNodeError(self, WebFingerServer.obtain_account_identifier_requiring_percent_encoding)


    def override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):
        """
        Instruct the server to temporarily return the overridden_json_response when the client_operation is performed.
        """
        raise NotImplementedByNodeError(self, WebFingerServer.override_webfinger_response)


class WebFingerClient(WebClient):
    """
    A Node that acts as a WebFinger client.
    """
    def perform_webfinger_query(
        self,
        server: WebFingerServer,
        resource_uri: str,
        rels: list[str] | None = None,
        scheme: str = 'https'
    ) -> WebFingerQueryResponse:
        """
        Make this Node perform a WebFinger query for the provided resource_uri on the provided server
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        rels is an optional list of 'rel' query parameters. The scheme can be overridden to 'http'
        for development scenarios
        Return the result of the query. This should returns WebFingerQueryResponse in as many cases
        as possible, but the WebFingerQueryResponse may indicate errors.
        """
        raise NotImplementedByNodeError(self, WebFingerClient.perform_webfinger_query)


    def construct_webfinger_uri_for(
        self,
        resource_uri: str,
        rels: list[str] | None = None,
        hostname: str | None = None,
        scheme: str = 'https'
    ) -> str:
        """
        Helper method to construct the WebFinger URI from a resource URI, and an optional list
        of rels to ask for
        """
        if not hostname:
            parsed_resource_uri = urlparse(resource_uri)
            match parsed_resource_uri.scheme:
                case "acct":
                    _, hostname = parsed_resource_uri.path.split(
                        "@", maxsplit=1
                    )  # 1: number of splits, not number of elements

                case 'http':
                    hostname = parsed_resource_uri.netloc

                case 'https':
                    hostname = parsed_resource_uri.netloc

                case _:
                    raise WebFingerClient.UnsupportedUriSchemeError(resource_uri)

        if not hostname:
            raise WebFingerClient.CannotDetermineWebfingerHostError(resource_uri)

        uri = f"{scheme}://{hostname}/.well-known/webfinger?resource={quote(resource_uri)}"
        if rels:
            for rel in rels:
                uri += f"&rel={ quote(rel) }"

        return uri


    class UnsupportedUriSchemeError(RuntimeError):
        """
        Raised when a WebFinger resource uses a scheme other than http, https, acct
        """
        def __init__(self, resource_uri: str):
            self.resource_uri = resource_uri


    class CannotDetermineWebfingerHostError(RuntimeError):
        """
        Raised when the WebFinger host could not be determined.
        """
        def __init__(self, resource_uri: str):
            self.resource_uri = resource_uri
