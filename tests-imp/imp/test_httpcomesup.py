"""
"""

import httpx
from feditest import step
from feditest.protocols.web import WebServer
from hamcrest import assert_that, equal_to

@step
def frontpage(
        server: WebServer
) -> None:
    hostname = server.get_hostname()
    response = httpx.get(f'http://{hostname}/', follow_redirects=False)

    assert_that(response.status_code, equal_to(200))
