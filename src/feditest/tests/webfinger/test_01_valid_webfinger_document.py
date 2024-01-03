"""
"""

from feditest import register_test
from feditest.iut.webfinger import WebfingerIUT

@register_test
def test_01_valid_webfinger_document(iut: WebfingerIUT) -> None:
    testId = iut.obtainAccountIdentifier();
    rootUri = iut.obtainRootURI();

    webfingerUri = rootUri + ".well-known/webfinger?resource=acct%3a" + urllib.parse.quote(testId)

    # fixme
    results = fetch(webfingerUri)
    json = parseJson(results)
    checkEntries(json)