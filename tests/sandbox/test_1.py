"""
"""

from typing import List

from feditest import step, fassert
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
    
    fassert(c==14)

    log: List[SandboxLogEvent] = server.get_and_clear_log()
    
    fassert(len(log)==1)
    fassert(log[0].a==a)
    fassert(log[0].b==b)
    fassert(log[0].c==c)
