"""
A simple example test against a client and a server of the Sandbox protocol.
"""

from typing import List

from hamcrest import assert_that, equal_to

from feditest import step
from feditest.protocols.sandbox import SandboxLogEvent, SandboxMultClient, SandboxMultServer

@step
def test1_step1(
        client: SandboxMultClient,
        server: SandboxMultServer
) -> None:
    a : int = 2
    b : int = 7
    
    server.start_logging()
    
    c = client.cause_mult(server, a, b)
    
    assert_that(c, equal_to(14))

    log: List[SandboxLogEvent] = server.get_and_clear_log()
    
    assert_that(len(log), equal_to(1))
    assert_that(log[0].a, equal_to(a))
    assert_that(log[0].b, equal_to(b))
    assert_that(log[0].c, equal_to(c))
