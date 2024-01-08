"""
"""

from feditest import register_test
from feditest.iut.webfinger import WebfingerServerIUT
from feditest.webfinger import construct_webfinger_uri

@register_test
def do_not_access_malformed_resource_parameters_not_percent_encoded(iut: WebfingerServerIUT) -> None:
    test_id = iut.obtain_account_identifier();
    domain_name = iut.obtain_domain_name();

    webfinger_uri = f"https://{domain_name}/.well-known/webfinger?resource={resource_identifier}"

    # fixme
    results = fetch(webfinger_uri)
    assert(results.status, '400')

@register_test
def do_not_access_malformed_resource_parameters_extra_equals(iut: WebfingerServerIUT) -> None:
    test_id = iut.obtain_account_identifier();
    domain_name = iut.obtain_domain_name();

    webfinger_uri = f"https://{domain_name}/.well-known/webfinger?resource=={urllib.parse.quote(resource_identifier)}"

    # fixme
    results = fetch(webfinger_uri)
    assert(results.status, '400')

