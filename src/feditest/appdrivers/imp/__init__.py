"""
"""

from datetime import datetime
import httpx
import random
import string
from typing import Any, Callable, Iterable
from urllib.parse import urlparse, quote

from feditest import appdriver
from feditest.protocols import NodeDriver
from feditest.protocols.web import WebClient, WebServerLog, HttpRequestResponsePair, ParsedUri
from feditest.protocols.webfinger import WebFingerClient, Jrd
from feditest.protocols.fediverse import FediverseNode
from feditest.reporting import info
from feditest.utils import account_id_validate
from .httpserver import ImpHttpServer, ImpHttpsServer, Website


class Imp(FediverseNode, WebFingerClient,Website):
    def __init__(self, nickname: str, hostname: str, node_driver: 'ImpInProcessDriver') -> None:
        super(FediverseNode, self).__init__(nickname, hostname, node_driver)
        
        self._hosted_accounts : dict[str,str]= {}
        self._serverlog = WebServerLog()

    # @override # from WebClient
    def http_get(self, uri: str) -> httpx.Response:
        # Do not follow redirects automatically, we need to know whether there are any
        print( f'XXX http_get of {uri}')
        return httpx.get(uri, follow_redirects=False)

    # @override # from WebServer
    def _start_logging_http_requests(self) -> str:
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # @override # from WebServer
    def _stop_logging_http_requests(self, collection_id: str) -> WebServerLog:
        return self._serverlog().entries_since(str)

    # @override # from WebFingerClient
    def perform_webfinger_query_on_resource(self, resource_uri: str) -> Jrd:
        uri = self.construct_webfinger_uri(resource_uri)

        response: httpx.Response = None
        with httpx.Client() as client:
            info( f'Performing HTTP GET on {uri}')
            request = httpx.Request('GET', uri)
            for redirect_count in range(10, 0, -1):
                response = client.send(request)
                if response.is_redirect:
                    if redirect_count <= 0:
                        raise WebClient.TooManyRedirectsError(uri)
                    request = response.next_request

        if response and response.is_success :
            jrd = Jrd(response.content)
            jrd.validate() # may raise
            return jrd
        else:
            raise WebClient.HttpUnsuccessfulError(uri, response)

    def construct_webfinger_uri(self, resource_uri: str) -> str:
        """
        Helper method to construct the WebFinger URI from a resource URI
        """
        parsed_resource_uri = urlparse(resource_uri)
        match parsed_resource_uri.scheme:
            case 'acct':
                _, hostname = parsed_resource_uri.path.split('@', maxsplit=1) # 1: number of splits, not number of elements

            case 'http':
                hostname = parsed_resource_uri.netloc

            case 'https':
                hostname = parsed_resource_uri.netloc

            case _:
                raise WebFingerClient.UnsupportedUriSchemeError(uri)

        if not hostname:
            raise WebFingerClient.CannotDetermineWebfingerHost(resource_uri)

        uri = f"https://{hostname}/.well-known/webfinger?resource={quote(resource_uri)}"
        return uri

    # @override # from WebFingerServer
    def obtain_account_identifier(self) -> str:
        # Simply create a new one
        ret = self.obtain_non_existing_account_identifier();
        self._hosted_accounts[ret] = ret
        return ret

    # @override # from WebFingerServer
    def obtain_non_existing_account_identifier(self) ->str:
        while True :
            ret = 'acct:' + ''.join(random.choice(string.ascii_lowercase) for i in range(8)) + '@' + self._hostname
            if not ret in self._hosted_accounts:
                return ret
            # Very unlikely

    # @override # from ActivityPubNode
    def obtain_actor_document_uri(self) -> str:
        ...

    # @override # from ActivityPubNode
    def create_actor_document_uri(self) -> str:
        ...

    # invoked by the HttpServer
    def wsgi(self, env: dict[str,str], start_fn: Callable) -> Iterable[bytes]:
        when_started = datetime.utcnow()
        uri = ParsedUri(env['wsgi.url_scheme'], env['HTTP_HOST'], env['PATH_INFO'], '', env['QUERY_STRING'], '')

        ret = None
        response_status = None
        response_header = None

        def wrapped(status: str, header: dict[str,str]) :
            # We shall call this a hack
            nonlocal response_status
            nonlocal response_header

            response_status = status
            response_header = header
            start_fn(status, header)
            
        match uri.scheme:        
            case 'http':
                ret = self._serve_http(uri, env, wrapped)
            case 'https':
                ret = self._serve_https(uri, env, wrapped)
            case _:
                wrapped( '400 Bad Request', [('Content-Type', 'text/plain')])
                ret = [b"400 Bad Request\nUnkown URL scheme '" + env['wsgi.url_scheme'] + "'!\n"]
        
        if not ret:
            wrapped( '404 Not found', [('Content-Type', 'text/plain')])
            ret = [b'404 Not found\n']
            
        when_completed = datetime.utcnow()
        self._serverlog.append(HttpRequestResponsePair(when_started, when_completed, uri, response_status, response_header))
        return ret

    def _serve_http(self, uri: ParsedUri, env: dict[str,str], start_fn: Callable) -> Iterable[bytes]:
        start_fn( '400 Bad Request', [('Content-Type', 'text/plain')])
        return [b'400 Bad Request\nImp does not serve HTTP; use HTTPS']

    def _serve_https(self, uri: ParsedUri, env: dict[str,str], start_fn: Callable) -> Iterable[bytes]:
        if uri.path == '/.well-known/webfinger':
            return self._serve_webfinger(self, uri, env, start_fn )

        return None # FIXME

    def _serve_webfinger(self, uri: ParsedUri, env: dict[str,str], start_fn: Callable) -> Iterable[bytes]:
        if uri.has_param('resource'):
            resources = uri.param_mult('resource')
            match len(resources):
                case 1:
                    if resources[0] in self._hosted_accounts:
                        start_fn('200 OK', [('Content-Type', 'application/jrd+json'), ('Access-Control-Allow-Origin', '*' )])
                        return [ str.encode(self._construct_jrd_for(self._hosted_accounts[resources[0]])) ]
                    else:
                        return self._emit_error('400 Bad Request', 'More than one resource provided.', start_fn)
                case _:
                    return self._emit_error('400 Bad Request', 'More than one resource provided.', start_fn)
        else:
            return self._emit_error('400 Bad Request', 'No resource provided.', start_fn)


    def _emit_error(self, status: str, msg: str, start_fn: Callable) -> Iterable[bytes]:
        start_fn(status, [('Content-Type', 'text/plain')])
        return [ str.encode(f'{status}\n{msg}\n') ]


    def _construct_jrd_for(self, account:str) -> str:
        # FIXME
        return """
     {
       "subject" : "http://blog.example.com/article/id/314",
       "aliases" :
       [
         "http://blog.example.com/cool_new_thing",
         "http://blog.example.com/steve/article/7"
       ],
       "properties" :
       {
         "http://blgx.example.net/ns/version" : "1.3",
         "http://blgx.example.net/ns/ext" : null
       },
       "links" :
       [
         {
           "rel" : "copyright",
           "href" : "http://www.example.com/copyright"
         },
         {
           "rel" : "author",
           "href" : "http://blog.example.com/author/steve",
           "titles" :
           {
             "en-us" : "The Magical World of Steve",
             "fr" : "Le Monde Magique de Steve"
           },
           "properties" :
           {
             "http://example.com/role" : "editor"
           }
         }

       ]
     }
     """


imp_httpd : ImpHttpServer = None
imp_httpsd : ImpHttpsServer = None

@appdriver
class ImpInProcessDriver(NodeDriver):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    # Python 3.12 @override
    def _provision_node(self, nickname: str, hostname: str) -> Imp:
        global imp_httpd
        global imp_httpsd

        node =  Imp(nickname, hostname, self);
        if imp_httpd is None:
            imp_httpd = ImpHttpServer()
            imp_httpd.start()
        if imp_httpsd is None:
            imp_httpsd = ImpHttpsServer()
            imp_httpsd.start()
        imp_httpsd.install_site(node)
        return node

    # Python 3.12 @override
    def _unprovision_node(self, node: Imp) -> None:
        global imp_httpd
        global imp_httpsd

        if imp_httpd:
            imp_httpd.remove_app(node)
        if imp_httpsd:
            imp_httpsd.remove_app(node)

