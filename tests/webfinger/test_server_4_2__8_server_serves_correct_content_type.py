"""
See annotated WebFinger specification, test 4.2/8
"""

from hamcrest import assert_that, raises

from feditest import step
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

import time

@step
def correct_content_type(
        iut:    WebFingerServer,
        driver: WebFingerClient
) -> None:
    test_id = iut.obtain_account_identifier();

    try:
        test_result = driver.perform_webfinger_query_on_resource(test_id)

    except Exception as e:
        assert_that('correct_content_type', raises(e))

