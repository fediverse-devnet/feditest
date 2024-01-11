"""
"""

from feditest import register_test, report_failure
from feditest.protocols import NotImplementedByDriverError
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@register_test
def valid_json(
        iut:    WebFingerServer,
        driver: WebFingerClient
) -> None:
    test_id = iut.obtain_account_identifier();

    try :
        test_result = driver.perform_webfinger_query_of_resource(test_id)

    except NotImplementedByDriverError:
        raise # not a failure

    except Exception as e:
        report_failure(e)
