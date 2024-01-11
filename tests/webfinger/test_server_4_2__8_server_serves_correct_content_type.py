"""
"""

from feditest import register_test, report_failure
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@register_test
def correct_content_type(
        iut:    WebFingerServer,
        driver: WebFingerClient
) -> None:
    test_id = iut.obtain_account_identifier();

    try:
        test_result = driver.perform_webfinger_query_on_resource(test_id)

    except Exception as e:
        report_failure(e)

