"""
"""

from feditest import register_test
from feditest.iut.webfinger import WebfingerServerIUT
from feditest.webfinger import construct_webfinger_uri

@register_test
def status_404_for_nonexisting_resources(iut: WebfingerServerIUT) -> None:
    test_id = iut.obtain_non_existing_account_identifier();
    domain_name = iut.obtain_domain_name();

    webfinger_uri = construct_webfinger_uri(domain_name, test_id)

    # fixme
    results = fetch(webfinger_uri)
    assert(results.status, '404')

