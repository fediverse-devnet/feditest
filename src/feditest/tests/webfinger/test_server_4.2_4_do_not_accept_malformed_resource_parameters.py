"""
"""

import urllib
import httpx

from feditest import fassert, register_test
from feditest.iut.webfinger import WebFingerClientIUT, WebFingerServerIUT

@register_test
def do_not_access_malformed_resource_parameters_not_percent_encoded(
        iut:    WebFingerServerIUT,
        driver: WebFingerClientIUT
) -> None:
    # We use the lower-level API from WebClientIUT because we can't make the WebFingerClientIUT do something invalid

    test_id : str = iut.obtain_account_identifier();
    domain_name : str = iut.get_domain_name();

    malformed_webfinger_uri : str = f"https://{domain_name}/.well-known/webfinger?resource={test_id}"

    result : httpx.Response = driver.http_get(malformed_webfinger_uri)
    fassert(result.status_code == 400, 'Not HTTP status 400')


@register_test
def do_not_access_malformed_resource_parameters_double_equals(
        iut:    WebFingerServerIUT,
        driver: WebFingerClientIUT
) -> None:
    # We use the lower-level API from WebClientIUT because we can't make the WebFingerClientIUT do something invalid

    test_id = iut.obtain_account_identifier();
    domain_name = iut.obtain_domain_name();

    malformed_webfinger_uri = f"https://{domain_name}/.well-known/webfinger?resource=={urllib.quote(resource_identifier)}"

    result : httpx.Response = driver.http_get(malformed_webfinger_uri)
    fassert(result.status_code == 400, 'Not HTTP status 400')
