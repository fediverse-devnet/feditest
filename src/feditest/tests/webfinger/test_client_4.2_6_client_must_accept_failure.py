"""
"""

from feditest import register_test, report_failure
from feditest.iut.webfinger import WebFingerClientIUT, WebFingerServerIUT, WebFingerUnknownResourceException

# We currently have no way of inserting an invalid certificate
# @register_test
# def client_must_accept_failure_invalid_certificate(
#         server: WebFingerServerIUT,
#         iut:    WebFingerClientIUT)
# -> None:
#


@register_test
def client_must_accept_failure_4xx(
        server: WebFingerServerIUT,
        iut:    WebFingerClientIUT
) -> None:
    test_id = server.obtain_non_existing_account_identifier();

    try:
        result = iut.perform_webfinger_query_on_resource(test_id)
        report_failure('Client obtained a response from webfinger query of non-existing account')

    except WebFingerUnknownResourceException as e:
         pass


# We currently have no way of inserting a server fault
# @register_test
# def client_must_accept_failure_5xx(
#         server: WebFingerServerIUT,
#         iut:    WebFingerClientIUT)
# -> None:
#
