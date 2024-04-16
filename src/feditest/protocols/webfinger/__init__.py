"""
Abstractions for the WebFinger protocol
"""

from urllib.parse import quote, urlparse

from feditest.protocols import NotImplementedByDriverError
from feditest.protocols.web import WebClient, WebServer
from feditest.protocols.web.traffic import HttpRequestResponsePair
from feditest.utils import account_id_validate
from feditest.protocols.webfinger.traffic import WebFingerQueryResponse


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
            return self.node_driver().prompt_user(
                    f'Please enter the URI of an existing or new account for role "{nickname}" at Node "{self._rolename}" (e.g. "acct:testuser@example.local" ): ',
                    self.parameter('existing-account-uri'),
                    account_id_validate )

        return self.node_driver().prompt_user(
                f'Please enter the URI of an existing or new account at Node "{self._rolename}" (e.g. "acct:testuser@example.local" ): ',
                self.parameter('existing-account-uri'),
                account_id_validate )


    def obtain_non_existing_account_identifier(self, nickname: str = None ) ->str:
        """
        Return the identifier of an account that does not exist on this Node, but that
        nevertheless follows the rules for identifiers of this Node.
        The identifier is of the form ``acct:foo@bar.com``.
        nickname: refer to this account by this nickname; used to disambiguate multiple accounts on the same server
        return: the identifier
        """
        if nickname:
            return self.node_driver().prompt_user(
                f'Please enter the URI of an non-existing account for role "{nickname}" at Node "{self._rolename}" (e.g. "acct:does-not-exist@example.local" ): ',
                self.parameter('nonexisting-account-uri'),
                account_id_validate )

        return self.node_driver().prompt_user(
            f'Please enter the URI of an non-existing account at Node "{self._rolename}" (e.g. "acct:does-not-exist@example.local" ): ',
            self.parameter('nonexisting-account-uri'),
            account_id_validate )


class WebFingerClient(WebClient):
    """
    A Node that acts as a WebFinger client.
    """
    def perform_webfinger_query(self, resource_uri: str, rels: list[str] | None = None) -> WebFingerQueryResponse:
        """
        Make this Node perform a WebFinger query for the provided resource_uri.
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        rels is an optional list of 'rel' query parameters
        Return the result of the query
        """
        raise NotImplementedByDriverError(self, WebFingerClient.perform_webfinger_query)


    def construct_webfinger_uri_for(self, resource_uri: str, rels: list[str] | None = None) -> str:
        """
        Helper method to construct the WebFinger URI from a resource URI, and an optional list
        of rels to ask for
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
                raise WebFingerClient.UnsupportedUriSchemeError(resource_uri)

        if not hostname:
            raise WebFingerClient.CannotDetermineWebfingerHostError(resource_uri)

        uri = f"https://{hostname}/.well-known/webfinger?resource={quote(resource_uri)}"
        if rels:
            uri += '&rel=' + '&rel='.join(quote(rel) for rel in rels)

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


    class WebfingerQueryFailedError(RuntimeError):
        """
        Raised when no JRD could be obtained (e.g. got 404)
        """
        def __init__(self, resource_uri: str, http_request_response_pair: HttpRequestResponsePair | None):
            self.resource_uri = resource_uri
            self.http_request_response_pair = http_request_response_pair
