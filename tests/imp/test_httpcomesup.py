"""
"""

import httpx
from feditest import step, report_failure
from feditest.protocols.web import WebServer

@step
def frontpage(
        iut: WebServer
) -> None:
    hostname = iut.get_hostname()
    response = httpx.get(f'http://{hostname}/', follow_redirects=False)

    print( f"XXX got {response}")
