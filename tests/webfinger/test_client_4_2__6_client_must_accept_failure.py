"""
"""

from feditest import step, report_failure
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

# We currently have no way of inserting an invalid certificate
# @step
# def client_must_accept_failure_invalid_certificate(
#         server: WebFingerServer,
#         iut:    WebFingerClient)
# -> None:
#


@step
def client_must_accept_failure_4xx(
        server: WebFingerServer,
        iut:    WebFingerClient
) -> None:
    test_id = server.obtain_non_existing_account_identifier();

    try:
        result = iut.perform_webfinger_query_on_resource(test_id)
        report_failure('Client obtained a response from webfinger query of non-existing account')

    except WebFingerClient.UnknownResourceException as e:
         pass


# We currently have no way of inserting a server fault
# @step
# def client_must_accept_failure_5xx(
#         server: WebFingerServer,
#         iut:    WebFingerClient)
# -> None:
#
