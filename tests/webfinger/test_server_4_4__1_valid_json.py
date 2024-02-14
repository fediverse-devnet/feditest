"""
See annotated WebFinger specification, test 4.4/1
"""

from hamcrest import assert_that, raises

from feditest import step
from feditest.protocols import NotImplementedByDriverError
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@step
def valid_json(
        client: WebFingerClient,
        server: WebFingerServer
) -> None:

    test_id = server.obtain_account_identifier();

    test_result = client.perform_webfinger_query_for(test_id)