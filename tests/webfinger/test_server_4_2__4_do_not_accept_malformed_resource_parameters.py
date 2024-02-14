"""
See annotated WebFinger specification, test 4.2/4
"""

import urllib
import httpx

from hamcrest import assert_that, equal_to

from feditest import step
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@step
def do_not_access_malformed_resource_parameters_not_percent_encoded(
        server: WebFingerServer,
        client: WebFingerClient
) -> None:
    # We use the lower-level API from WebClient because we can't make the WebFingerClient do something invalid

    test_id : str = server.obtain_account_identifier();
    domain_name : str = server.get_domain_name();

    malformed_webfinger_uri : str = f"https://{domain_name}/.well-known/webfinger?resource={test_id}"

    result : httpx.Response = client.http_get(malformed_webfinger_uri)
    assert_that(result.status_code, equal_to(400), 'Not HTTP status 400')


@step
def do_not_access_malformed_resource_parameters_double_equals(
        server: WebFingerServer,
        client: WebFingerClient
) -> None:
    # We use the lower-level API from WebClient because we can't make the WebFingerClient do something invalid

    test_id = server.obtain_account_identifier();
    domain_name = server.obtain_domain_name();

    malformed_webfinger_uri = f"https://{domain_name}/.well-known/webfinger?resource=={urllib.quote(test_id)}"

    result : httpx.Response = client.http_get(malformed_webfinger_uri)
    assert_that(result.status_code, equal_to(400), 'Not HTTP status 400')

