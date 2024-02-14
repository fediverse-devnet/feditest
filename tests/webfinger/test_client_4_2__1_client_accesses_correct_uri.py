"""
See annotated WebFinger specification, test 4.2/1
"""

from urllib.parse import parse_qs

from hamcrest import assert_that, equal_to, has_key

from feditest import step
from feditest.protocols.web import WebServerLog, HttpRequestResponsePair
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@step
def client_accesses_correct_uri(
        server: WebFingerServer,
        client: WebFingerClient
) -> None:
    test_id = server.obtain_account_identifier();

    log : WebServerLog = server.transaction( lambda :
        client.perform_webfinger_query_on_resource(test_id)
        # ignore the result, we are not testing that
    )

    assert_that(log.web_log_entries.size(), equal_to(1), 'Expecting one incoming request')

    entry : HttpRequestResponsePair = log.web_log_entries.get(0);
    assert_that(entry.uri.scheme, equal_to('https'))
    assert_that(entry.uri.netloc, equal_to(server.domain_name()))
    assert_that(entry.uri.path, equal_to('/.well-known/webfinger'))

    query : dict[str,list[str]] = parse_qs(entry.uri)
    assert_that(len(query), equal_to(1))
    assert_that(query, has_key('resource'))
    assert_that(query['resource'], equal_to(test_id))
