"""
See annotated WebFinger specification, test 4.3
"""

from urllib.parse import parse_qs

from hamcrest import assert_that, equal_to, is_not, starts_with

from feditest import step
from feditest.protocols.web import WebServerLog, HttpRequestResponsePair
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@step
def only_returns_jrd_in_response_to_https(
        client: WebFingerClient,
        server: WebFingerServer
) -> None:
    test_id = server.obtain_account_identifier();

    correct_webfinger_uri = client.construct_webfinger_uri_for(test_id)
    http_webfinger_uri = correct_webfinger_uri.replace('https:', 'http:')

    assert_that(correct_webfinger_uri, starts_with('https://'))
    assert_that(http_webfinger_uri, starts_with('http://'))

    correct_webfinger_response = client.http_get(correct_webfinger_uri)
    assert_that(correct_webfinger_response.status_code, equal_to('200'))
    assert_that(correct_webfinger_response.headers['Content-Type'], equal_to('application/jrd+json'))

    http_webfinger_response = client.http_get(http_webfinger_uri)
    assert_that(http_webfinger_response.status_code, is_not(equal_to('200')))
    assert_that(http_webfinger_response.headers['Content-Type'], is_not(equal_to('application/jrd+json')))
