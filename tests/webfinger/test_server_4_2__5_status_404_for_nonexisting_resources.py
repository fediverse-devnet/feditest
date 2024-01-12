"""
"""

from feditest import fassert, step, report_failure
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@step
def status_404_for_nonexisting_resources(
        iut:    WebFingerServer,
        driver: WebFingerClient
) -> None:
    test_id = iut.obtain_non_existing_account_identifier();

    try:
        test_result = driver.perform_webfinger_query_on_resource(test_id)

        report_failure('No exception when performing WebFinger query on non-existing resource')

    except WebFingerClient.UnknownResourceException as e:
        fassert(e.http_response.http_status, 404)
