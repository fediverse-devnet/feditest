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

    @final
    def provision_node(self, rolename: str) -> Node:
        """
        Instantiate a Node
        nickname: the name of this instance in the constellation
        """
        if rolename is None:
            raise Exception("rolename must be given")
        ret = self._provision_node(rolename)
        return ret;

    @final
    def unprovision_node(self, instance: Node) -> None:
        """
        Deactivate a Node
        node: the Node
        """
        if instance.node_driver != self :
            raise Exception(f"Instance does not belong to this driver")
        self._unprovision_node(instance)

    def _provision_node(self, nickname: str) -> Node:
        """
        The factory method for Node. Any subclass of NodeDriver should also
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
        super().__init__(self, "Not implemented: " + str(method))
