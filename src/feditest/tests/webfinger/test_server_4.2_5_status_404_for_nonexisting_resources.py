"""
"""

from feditest import fassert, register_test, report_failure
from feditest.iut.webfinger import WebFingerClientIUT, WebFingerServerIUT, WebFingerUnknownResourceException

@register_test
def status_404_for_nonexisting_resources(
        iut:    WebFingerServerIUT,
        driver: WebFingerClientIUT
) -> None:
    test_id = iut.obtain_non_existing_account_identifier();

    try:
        test_result = driver.perform_webfinger_query_on_resource(test_id)

        report_failure('No exception when performing WebFinger query on non-existing resource')

    except WebFingerUnknownResourceException as e:
        fassert(e.http_response.http_status, 404)
