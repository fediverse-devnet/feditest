"""
"""

from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import ssl
from threading import Thread
from typing import Tuple

from feditest.reporting import info

class Website:
    def do_GET(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_HEAD(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_POST(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_PUT(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_DELETE(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_CONNECT(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_OPTIONS(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_TRACE(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def do_PATCH(self, handler: BaseHTTPRequestHandler) -> None:
        self.fallback(handler)

    def fallback(self, handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(404)
        handler.send_header('Content-Type', 'text/plain')
        handler.end_headers()
        handler.wfile.write( b'404 Not Found. Fallback website.')


class FallbackWebsite(Website):
    pass


class ImpHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        return self.server.get_website(self.server).do_GET(self)
        

class BaseImpHttpServer(Thread):
    """
    Embedded HTTP Server
    """
    def __init__(self, hostport: Tuple[str,int], fallback_site : Website | None = None):
        super().__init__()
        self._sites : dict[str,Website] = {}
        self._httpd = ThreadingHTTPServer(hostport, ImpHttpHandler) # different sites may call each other
        self._fallback_site = fallback_site if fallback_site else FallbackWebsite()

    def start(self):
        super().start()

    def stop(self):
        self._httpd.shutdown() # This blocks until the server is shut down


    def run(self):
        info('Starting Imp HttpServer')
        self._httpd.serve_forever(0.5) # check for shutdown every half second
        info('Stopping Imp HttpServer')
    

    def install_website(self, hostname: str, site: Website) -> None:
        self._sites[hostname] = site


    def remove_website(self, hostname: str) -> None:
        del self._sites[hostname]


    def get_website(self, hostname: str) -> Website:
        ret : Website | None = None
        if hostname in self._sites:
            ret = self._sites[hostname]
        else:
            ret = self._fallback_site


class ImpHttpServer(BaseImpHttpServer):
    def __init__(self, hostport: Tuple[str,int] = ('', 80)):
        super().__init__(hostport)


class ImpHttpsServer(BaseImpHttpServer):
    def __init__(self, certfile: str, keyfile: str = 'None', hostport: Tuple[str,int] = ('', 443)):
        super().__init__(hostport)
        
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile, keyfile)
        self._httpd.socket = ssl_context.wrap_socket(self._httpd.socket, server_side=True)

