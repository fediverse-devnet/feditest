"""
"""

from feditest import register_test
from feditest.iut.webfinger import WebfingerIUT

@register_test
def test_02_webfinger_account_does_not_exist(iut: WebfingerIUT) -> None:
    testId = iut.obtainNonExistingAccountIdentifier();
    rootUri = iut.obtainRootURI();

    webfingerUri = rootUri + ".well-known/webfinger?resource=acct%3a" + urllib.parse.quote(testId)

    # fixme
    results = fetch(webfingerUri)
    assert(results.status, '404')
