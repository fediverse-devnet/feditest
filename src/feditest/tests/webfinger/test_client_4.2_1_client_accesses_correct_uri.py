"""
"""

from feditest import register_test
from feditest.iut.webfinger import WebfingerClientIUT
from feditest.webfinger import construct_webfinger_uri

@register_test
def client_accesses_correct_uri(client: WebfingerClientIUT, server: WebfingerServerIUT) -> None:
    test_id = server.obtain_account_identifier();

    result = server.transaction( lambda :
        client.perform_webfinger_query_on_resource(test_id)
    )
    assert( result.server_requests.size() == 1, 'Expecting one incoming request')
    request = result.server_requests.get(0);
    assert( request.uri.scheme() == 'https' )
    assert( request.uri.netloc() == server.domain_name() )
    assert( request.uri.path == '/.well-known/webfinger' )
    assert( request.uri.args.size() == 1 )
    assert( request.uri.args.get_name( 0 ) == 'resource' )
    assert( request.uri.args.get_value( 0 ) == 'test_id' )
