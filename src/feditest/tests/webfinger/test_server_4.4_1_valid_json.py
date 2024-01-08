"""
"""

from feditest import register_test
from feditest.iut.webfinger import WebfingerServerIUT
from feditest.webfinger import construct_webfinger_uri

@register_test
def valid_json(iut: WebfingerServerIUT) -> None:
    test_id = iut.obtain_account_identifier();
    domain_name = iut.obtain_domain_name();

    webfinger_uri = construct_webfinger_uri(domain_name, test_id)

    # fixme
    results = fetch(webfinger_uri)
    json = parseJson(results)
    # no error
