"""
An in-process Node implementation for now.
"""

import httpx
from multidict import MultiDict

from feditest.nodedrivers import AccountManager, Node, NodeConfiguration, NodeDriver, HOSTNAME_PAR
from feditest.protocols.web.diag import (
    HttpRequest,
    HttpRequestResponsePair,
    HttpResponse,
    WebDiagClient
)
from feditest.protocols.webfinger.abstract import AbstractWebFingerDiagClient
from feditest.reporting import trace
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeParameter
from feditest.utils import FEDITEST_VERSION

_HEADERS = {
    "User-Agent": f"feditest/{ FEDITEST_VERSION }",
    "Origin": "https://test.example" # to trigger CORS headers in response
}

class Imp(AbstractWebFingerDiagClient):
    """
    In-process diagnostic WebFinger client.
    """
    # Python 3.12 @override
    def http(self, request: HttpRequest, follow_redirects: bool = True, verify=False) -> HttpRequestResponsePair:
        trace( f'Performing HTTP { request.method } on { request.parsed_uri.uri }')

        httpx_response = None
        # Do not follow redirects automatically, we need to know whether there are any
        with httpx.Client(verify=verify, follow_redirects=follow_redirects) as httpx_client:
            httpx_request = httpx.Request(request.method, request.parsed_uri.uri, headers=_HEADERS) # FIXME more arguments
            httpx_response = httpx_client.send(httpx_request)

# FIXME: catch Tls exception and raise WebDiagClient.TlsError

        if httpx_response:
            response_headers : MultiDict = MultiDict()
            for key, value in httpx_response.headers.items():
                response_headers.add(key.lower(), value)
            ret = HttpRequestResponsePair(request, request, HttpResponse(httpx_response.status_code, response_headers, httpx_response.read()))
            trace( f'HTTP query returns { ret }')
            return ret
        raise WebDiagClient.HttpUnsuccessfulError(request)


    # Python 3.12 @override
    def add_cert_to_trust_store(self, root_cert: str) -> None:
        """
        On the Imp, we don't do this (for now?)
        """
        return


    # Python 3.12 @override
    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        return


class ImpInProcessNodeDriver(NodeDriver):
    """
    Knows how to instantiate an Imp.
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return []


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        return (
            NodeConfiguration(
                self,
                'Imp',
                FEDITEST_VERSION,
                test_plan_node.parameter(HOSTNAME_PAR)
            ),
            None
        )


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> Imp:
        return Imp(rolename, config, account_manager)


    # Python 3.12 @override
    def _unprovision_node(self, node: Node) -> None:
        pass
