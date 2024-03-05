"""
"""

from typing import Any, List

from feditest import nodedriver
from feditest.protocols import Node, NodeDriver
from feditest.protocols.sandbox import SandboxLogEvent, SandboxMultClient, SandboxMultServer


class SandboxMultClient_ImplementationA(SandboxMultClient):
    """
    A client implementation in the Sandbox protocol that can be tested. It's trivially simple.
    """
    def cause_mult(self, server: SandboxMultServer, a: int, b: int) -> int:
        c = server.mult(a, b)
        return c


@nodedriver
class SandboxMultClientDriver_ImplementationA(NodeDriver):
    """
    Driver for the client implementation, so the client can be provisioned and unprovisioned for
    test sessions.
    """
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        return SandboxMultClient_ImplementationA(rolename, self)


class SandboxMultServer_Implementation1(SandboxMultServer):
    """
    First server implementation in the Sandbox protocol with some test instrumentation.
    This server implementation simply calculates a*b.
    """
    def __init__(self, rolename: str, node_driver: 'SandboxMultServer_Implementation1'):
        super().__init__(rolename, node_driver)
        self._log : List[SandboxLogEvent] | None = None


    def mult(self, a: int, b: int) -> int:
        c = a*b # << here's the key 'mult' functionality
        if self._log is not None:
            self._log.append(SandboxLogEvent(a, b, c))
        return c


    def start_logging(self):
        self._log = []


    def get_and_clear_log(self):
        ret = self._log
        self._log = None
        return ret


@nodedriver
class SandboxMultServerDriver_Implementation1(NodeDriver):
    """
    Driver for the first server implementation, so this server implementation can be provisioned and unprovisioned for
    test sessions.
    """
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        return SandboxMultServer_Implementation1(rolename, self)


class SandboxMultServer_Implementation2(SandboxMultServer):
    """
    Second server implementation in the Sandbox protocol with some test instrumentation.
    This server calculates a*b through a for loop
    """
    def __init__(self, rolename: str, node_driver: 'SandboxMultServer_Implementation1'):
        super().__init__(rolename, node_driver)
        self._log : List[SandboxLogEvent] | None = None


    def mult(self, a: int, b: int) -> int:
        c = 0
        for i in range(0, a): # << here's the key 'mult' functionality
            c += b
        if self._log is not None:
            self._log.append(SandboxLogEvent(a, b, c))
        return c


    def start_logging(self):
        self._log = []


    def get_and_clear_log(self):
        ret = self._log
        self._log = None
        return ret


@nodedriver
class SandboxMultServerDriver_Implementation2(NodeDriver):
    """
    Driver for the second server implementation, so this server implementation can be provisioned and unprovisioned for
    test sessions.
    """
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        return SandboxMultServer_Implementation2(rolename, self)


class SandboxMultServer_Implementation3_Faulty(SandboxMultServer):
    """
    Third (faulty) server implementation in the Sandbox protocol with some test instrumentation.
    This server always returns 17.
    """
    def __init__(self, rolename: str, node_driver: 'SandboxMultServer_Implementation1'):
        super().__init__(rolename, node_driver)
        self._log : List[SandboxLogEvent] | None = None


    def mult(self, a: int, b: int) -> int:
        c = 17 # << always returns 17
        if self._log is not None:
            self._log.append(SandboxLogEvent(a, b, c))
        return c


    def start_logging(self):
        self._log = []


    def get_and_clear_log(self):
        ret = self._log
        self._log = None
        return ret


@nodedriver
class SandboxMultServerDriver_Implementation3_Faulty(NodeDriver):
    """
    Driver for the third (faulty) server implementation, so this server implementation can be provisioned and unprovisioned for
    test sessions.
    """
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        return SandboxMultServer_Implementation3_Faulty(rolename, self)
