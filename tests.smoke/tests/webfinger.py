from feditest import InteropLevel, SpecLevel, assert_that, test
from feditest.protocols.webfinger import WebFingerServer
from feditest.protocols.webfinger.diag import WebFingerDiagClient
from feditest.protocols.webfinger.utils import wf_error
from hamcrest import not_none


@test
def fetch(
        client: WebFingerDiagClient,
        server: WebFingerServer
) -> None:
    """
    Perform a normal, simple query on an existing account.
    This is not a WebFinger conformance test, it's too lenient for this.
    This is a smoke test that tests FediTest can perform these kinds of tests.
    """
    test_id = server.obtain_account_identifier()

    webfinger_response = client.diag_perform_webfinger_query(test_id)

    assert_that(
            webfinger_response.jrd,
            not_none(),
            wf_error(webfinger_response),
            spec_level=SpecLevel.MUST,
            interop_level=InteropLevel.PROBLEM)
