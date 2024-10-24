"""
Abstractions for the toy "Sandbox" protocol.
"""

from datetime import datetime, UTC
from typing import List

from feditest.nodedrivers import Node, NotImplementedByNodeError

class SandboxLogEvent:
    """
    The structure of the data inserted into the log.
    """
    def __init__(self, a: float, b: float, c: float):
        self.when = datetime.now(UTC)
        self.a = a
        self.b = b
        self.c = c


class SandboxMultServer(Node):
    """
    This is a "Server" Node in a to-be-tested toy protocol. It is only useful to illustrate how Feditest works.
    """
    def mult(self, a: float, b: float) -> float:
        """
        The operation that's being tested
        """
        raise NotImplementedByNodeError(self, SandboxMultServer.mult)


    def start_logging(self):
        """
        Activate logging of mult() operations
        """
        raise NotImplementedByNodeError(self, SandboxMultServer.start_logging)


    def get_and_clear_log(self) -> List[SandboxLogEvent]:
        """
        Stop logging of mult() operations, return what has been logged so far
        and clear the log
        """
        raise NotImplementedByNodeError(self, SandboxMultServer.get_and_clear_log)


class SandboxMultClient(Node):
    """
    This is a "Client" Node in a to-be-tested toy protocol. It is only useful to illustrate how Feditest works.
    """
    def cause_mult(self, server: SandboxMultServer, a: float, b: float) -> float:
        """
        Enable FediTest to make the client perform the mult() operation on the server.
        """
        raise NotImplementedByNodeError(self, SandboxMultClient.cause_mult)
