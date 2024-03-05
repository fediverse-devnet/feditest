"""
Abstractions for the toy "Sandbox" protocol.
"""

from datetime import datetime
from typing import List

from feditest.protocols import Node, NotImplementedByDriverError


class SandboxLogEvent:
    def __init__(self, a: int, b: int, c: int):
        self.when = datetime.utcnow()
        self.a = a
        self.b = b
        self.c = c


class SandboxMultServer(Node):
    """
    This is a "Server" Node in a to-be-tested toy protocol. It is only useful to illustrate how Feditest works.
    """
    def mult(self, a: int, b: int) -> int:
        """
        The operation that's being tested
        """
        raise NotImplementedByDriverError(self, SandboxMultServer.mult)


    def start_logging(self):
        """
        Activate logging of mult() operations
        """
        raise NotImplementedByDriverError(self, SandboxMultServer.start_logging)


    def get_and_clear_log(self) -> List[SandboxLogEvent]:
        """
        Stop logging of mult() operations, return what has been logged so far
        and clear the log
        """
        raise NotImplementedByDriverError(self, SandboxMultServer.get_and_clear_log)


class SandboxMultClient(Node):
    """
    This is a "Client" Node in a to-be-tested toy protocol. It is only useful to illustrate how Feditest works.
    """
    def cause_mult(self, server: SandboxMultServer, a: int, b: int) -> int:
        """
        Enable FediTest to make the client perform the mult() operation on the server.
        """
        raise NotImplementedByDriverError(self, SandboxMultServer.cause_mult)
