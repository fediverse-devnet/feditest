"""
"""

import urllib
import httpx

from feditest import fassert, register_test
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@register_test
def do_not_access_malformed_resource_parameters_not_percent_encoded(
        iut:    WebFingerServer,
        driver: WebFingerClient
) -> None:
    # We use the lower-level API from WebClient because we can't make the WebFingerClient do something invalid

    test_id : str = iut.obtain_account_identifier();
    domain_name : str = iut.get_domain_name();

    malformed_webfinger_uri : str = f"https://{domain_name}/.well-known/webfinger?resource={test_id}"

    result : httpx.Response = driver.http_get(malformed_webfinger_uri)
    fassert(result.status_code == 400, 'Not HTTP status 400')


@register_test
def do_not_access_malformed_resource_parameters_double_equals(
        iut:    WebFingerServer,
        driver: WebFingerClient
) -> None:
    # We use the lower-level API from WebClient because we can't make the WebFingerClientI do something invalid

    test_id = iut.obtain_account_identifier();
    domain_name = iut.obtain_domain_name();

    malformed_webfinger_uri = f"https://{domain_name}/.well-known/webfinger?resource=={urllib.quote(test_id)}"

    result : httpx.Response = driver.http_get(malformed_webfinger_uri)
    fassert(result.status_code == 400, 'Not HTTP status 400')

