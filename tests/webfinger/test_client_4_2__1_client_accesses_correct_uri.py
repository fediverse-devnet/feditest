"""
"""

from urllib.parse import parse_qs

from feditest import fassert, register_test
from feditest.protocols.web import WebServerLog, HttpRequestResponsePair
from feditest.protocols.webfinger import WebFingerClient, WebFingerServer

@register_test
def client_accesses_correct_uri(
        server: WebFingerServer,
        iut:    WebFingerClient
) -> None:
    test_id = server.obtain_account_identifier();

    log : WebServerLog = server.transaction( lambda :
        iut.perform_webfinger_query_on_resource(test_id)
        # ignore the result, we are not testing that
    )

    fassert(log.web_log_entries.size() == 1, 'Expecting one incoming request')

    entry : HttpRequestResponsePair = log.web_log_entries.get(0);
    fassert(entry.uri.scheme == 'https')
    fassert(entry.uri.netloc == server.domain_name())
    fassert(entry.uri.path == '/.well-known/webfinger')

    query : dict[str,list[str]] = parse_qs(entry.uri)
    fassert(len(query) == 1 )
    fassert('resource' in query )
    fassert(query['resource'] == test_id)
