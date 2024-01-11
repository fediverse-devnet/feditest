"""
Define interfaces to interact with the nodes in the constellation being tested
"""

from abc import ABC
from collections.abc import Callable
from typing import Any, final

class Node(ABC):
    """
    A Node is the interface through which FediTest talks to an application instance.
    Node itself is an abstract superclass.
    
    There are (also abstract) sub-classes that provide methods specific to specific
    protocols to be tested. Each such protocol has a sub-class for each role in the
    protocol. For example, client-server protocols have two different subclasses of
    Node, one for the client, and one for the server.

    Any application that wishes to benefit from automated test execution with FediTest
    needs to define for itself a subclass of each protocol-specific subclass of Node
    so FediTest can control and observe what it needs to when attempting to
    participate with the respective protocol.
    """
    def __init__(self, nickname: str, node_driver: 'NodeDriver') -> None:
        self.nickname   = nickname
        self.node_driver = node_driver


class NodeDriver(ABC):
    """
    This is an abstract superclass for all objects that know how to instantiate Nodes of some kind.
    """
    def __init__(self, name: str) -> None:
        self._name : str = name
        self.known_nodes : dict[str, Node] = ()

    @final
    def provision_node(self, hostname: str, nickname: str) -> Node:
        """
        Instantiate a Node
        hostname: DNS name
        nickname: the nickname of this instance
        """
        if hostname is None:
            raise Exception("hostname must be given")
        if nickname is None:
            nickname = hostname
        if nickname in self.known_nodes:
            raise Exception(f"Nickname { nickname } provisioned already")
        ret = self._provision_node(hostname, nickname)
        self.known_nodes[nickname] = ret
        return ret;

    @final
    def unprovision_node(self, instance: Node) -> None:
        """
        Deactivate a Node
        node: the Node
        """
        if not instance.nickname in self.known_nodes :
            raise Exception(f"Nickname { instance.nickname } not known")
        if self.known_nodes[instance.nickname] != instance :
            raise Exception(f"Instance does not belong to this driver")
        self._unprovision_node(instance)
        del self.known_nodes[instance.nickname]

    def _provision_node(self, hostname: str, nickname: str) -> Node:
        """
        The factory method for Node. Any subclass of IUTDriver should also
        override this and return a more specific subclass of IUT.
        """
        raise NotImplementedByDriverError(NodeDriver._provision_node)

    def _unprovision_node(self, instance: Node) -> None:
        """
        Invoked when a Node gets unprovisioned, in case cleanup needs to be performed.
        This is here so subclasses of NodeDriver can override it.
        """
        raise NotImplementedByDriverError(NodeDriver._unprovision_node)

    def prompt_user(self, question: str, validation: Callable[[str],bool]=None) -> str:
        """
        If an NodeDriver does not natively implement support for a particular method,
        this method is invoked as a fallback. It prompts the user to enter information
        at the console.
        question: the text to be emitted to the user as a prompt
        validation: optional function that validates user input and returns True if valid
        return: the value entered by the user
        """
        while True:
            ret = input(question)
            if validation is None or validation(ret):
                return ret
        

class NotImplementedByDriverError(RuntimeError):
    """
    This exception is raised when a Node cannot perform a certain operation because it
    has not been implemented in this subtype of Node.
    """
    def __init__(self, method: Callable[...,Any] ):
        super.__init__("Not implemented: " + str(method))
