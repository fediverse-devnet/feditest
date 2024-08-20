"""
Abstractions for the WebFinger protocol
"""

from typing import Any, Callable
from urllib.parse import quote, urlparse

from feditest.protocols import NodeDriver, NodeSpecificationInvalidError, NotImplementedByNodeError
from feditest.protocols.web import WebClient, WebServer
from feditest.protocols.webfinger.traffic import WebFingerQueryResponse
from feditest.testplan import TestPlanConstellationNode


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


class FallbackWebFingerServer(WebFingerServer):
    def __init__(self,
        rolename: str,
        parameters: dict[str,Any],
        node_driver: NodeDriver,
        test_plan_node: TestPlanConstellationNode
    ):
        super().__init__(rolename, parameters, node_driver)
        self._test_plan_node = test_plan_node


    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        account = self._test_plan_node.get_account_by_rolename(rolename)
        if not account:
            raise NodeSpecificationInvalidError(self.node_driver, 'accounts', f'No existing account for role {rolename} given in TestPlan')
        ret = account.uri
        if not ret:
            raise NodeSpecificationInvalidError(self.node_driver, 'accounts', f'No uri for pre-existing account of role {rolename} given in TestPlan')
        return ret


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        non_account = self._test_plan_node.get_non_existing_account_by_rolename(rolename)
        if not non_account:
            raise NodeSpecificationInvalidError(self.node_driver, 'non_existing_accounts', f'No existing account for role {rolename} given in TestPlan')
        ret = non_account.uri
        if not ret:
            raise NodeSpecificationInvalidError(self.node_driver, 'non_existing_accounts', f'No uri for pre-existing account of role {rolename} given in TestPlan')
        return ret


class WebFingerClient(WebClient):
    """
    A Node that acts as a WebFinger client.
    """
    def perform_webfinger_query(
        self,
        resource_uri: str,
        rels: list[str] | None = None,
        server: WebFingerServer | None = None
    ) -> WebFingerQueryResponse:
        """
        Make this Node perform a WebFinger query for the provided resource_uri.
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        rels is an optional list of 'rel' query parameters.
        server, if given, indicates the non-default server that is supposed to perform the query
        Return the result of the query. This should return WebFingerQueryResponse in as many cases
        as possible, but the WebFingerQueryResponse may indicate errors.
        """
        raise NotImplementedByNodeError(self, WebFingerClient.perform_webfinger_query)


    def construct_webfinger_uri_for(
        self,
        resource_uri: str,
        rels: list[str] | None = None,
        hostname: str | None = None
    ) -> str:
        """
        Helper method to construct the WebFinger URI from a resource URI, an optional list
        of rels to ask for, and (if given) a non-default hostname
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

        uri = f"https://{hostname}/.well-known/webfinger?resource={quote(resource_uri)}"
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
