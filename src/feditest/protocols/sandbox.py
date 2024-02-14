"""
"""

from datetime import datetime
from typing import List

from feditest.protocols import Node


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
        ...

    def start_logging(self):
        ...
    
    def get_and_clear_log(self) -> List[SandboxLogEvent]:
        ...


class SandboxMultClient(Node):
    """
    This is a "Client" Node in a to-be-tested toy protocol. It is only useful to illustrate how Feditest works.
    """
    def cause_mult(self, server: SandboxMultServer, a: int, b: int) -> int:
        ...
