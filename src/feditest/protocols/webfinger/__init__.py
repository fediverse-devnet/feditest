"""
Abstractions for the WebFinger protocol
"""

from feditest.nodedrivers import NotImplementedByNodeError
from feditest.protocols.web import WebClient, WebServer


class WebFingerClient(WebClient):
    """
    A Node that acts as a WebFinger client.
    """
    def perform_webfinger_query(self, resource_uri: str) -> None:
        """
        Make this Node perform a WebFinger query for the provided resource_uri.
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        This returns None as it is unreasonable to assume that a non-diag Node can implement
        this call otherwise. However, it may throw exceptions.
        It is used with a WebFingerDiagServer to determine whether this WebFingerClient performs
        valid WebFinger queries.
        """
        raise NotImplementedByNodeError(self, WebFingerClient.perform_webfinger_query)


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
        raise NotImplementedByNodeError(self, WebFingerServer.obtain_account_identifier)


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
        raise NotImplementedByNodeError(self, WebFingerServer.obtain_non_existing_account_identifier)


    def obtain_account_identifier_requiring_percent_encoding(self, rolename: str | None = None) -> str:
        """
        Smart factory method to return the identifier of an existing or newly created account on this
        Node that contains characters that require percent-encoding when provided as resource in a WebFinger
        query. Different rolenames produce different results; the same rolename produces the same result.

        If the Node does not ever issue such identifiers, raise NotImplementedByNodeException
        """
        raise NotImplementedByNodeError(self, WebFingerServer.obtain_account_identifier_requiring_percent_encoding)
