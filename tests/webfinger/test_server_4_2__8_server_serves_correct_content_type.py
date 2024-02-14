"""
See annotated WebFinger specification, test 4.2/8
"""

from hamcrest import assert_that, raises

from feditest import step
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

import time

@step
def correct_content_type(
        server: WebFingerServer,
        client: WebFingerClient
) -> None:
    test_id = server.obtain_account_identifier();

    try:
        test_result = client.perform_webfinger_query_for(test_id)

    except Exception as e:
        assert_that('correct_content_type', raises(e))

