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
    def __init__(self, rolename: str, hostname: str, node_driver: 'NodeDriver') -> None:
        """
        rolename: name of the role in the constellation
        hostname: the hostname of this Node
        node_driver: the NodeDriver that provisioned this Node
        """
        self._rolename = rolename
        self._hostname = hostname
        self._node_driver = node_driver


    def rolename(self):
        return self._rolename


    def hostname(self):
        return self._hostname


    def node_driver(self):
        return self._node_driver


class NodeDriver(ABC):
    """
    This is an abstract superclass for all objects that know how to instantiate Nodes of some kind.
    """
    def __init__(self, name: str) -> None:
        self._name : str = name


    @final
    def provision_node(self, rolename: str, hostname: str | None, parameters: dict[str,Any] | None = None) -> Node:
        """
        Instantiate a Node
        rolename: the name of this Node in the constellation
        hostname: the DNS hostname that was specified in the test plan, or None if none. The actual hostname is carried
                  by the returned Node
        """
        if rolename is None:
<<<<<<< Updated upstream
            raise Exception("rolename must be given")
        ret = self._provision_node(rolename, hostname, parameters)
=======
            raise NodeSpecificationInvalidError(self, 'rolename', 'rolename must be given')
        ret = self._provision_node(rolename, parameters)
>>>>>>> Stashed changes
        return ret


    @final
    def unprovision_node(self, node: Node) -> None:
        """
        Deactivate and delete a Node
        node: the Node
        """
        if node.node_driver() != self :
            raise Exception(f"Node does not belong to this NodeDriver: {node.node_driver()} vs {self}") # pylint: disable=broad-exception-raised
        self._unprovision_node(node)


    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        """
        The factory method for Node. Any subclass of NodeDriver should also
        override this and return a more specific subclass of IUT.
        """
        raise NotImplementedByDriverError(self, NodeDriver._provision_node)


    def _unprovision_node(self, node: Node) -> None:
        """
        Invoked when a Node gets unprovisioned, in case cleanup needs to be performed.
        This is here so subclasses of NodeDriver can override it.
        """
        # by default, do nothing
        pass # pylint: disable=unnecessary-pass


    def prompt_user(self, question: str, validation: Callable[[str],bool] | None = None) -> str:
        """
        If an NodeDriver does not natively implement support for a particular method,
        this method is invoked as a fallback. It prompts the user to enter information
        at the console.
        question: the text to be emitted to the user as a prompt
        validation: optional function that validates user input and returns True if valid
        return: the value entered by the user
        """
        while True:
            ret = input(f'TESTER ACTION REQUIRED: { question }')
            if validation is None or validation(ret):
                return ret
            print(f'INPUT ERROR: invalid input, try again. Was: "{ ret}"')

class NotImplementedByDriverError(RuntimeError):
    """
    This exception is raised when a Node cannot perform a certain operation because it
    has not been implemented in this subtype of Node.
    """
    def __init__(self, node: Node, method: Callable[...,Any], arg: Any = None ):
        super().__init__(f"Not implemented on node {node}: {method}" + (f" ({ arg })" if arg else ""))


class NodeSpecificationInsufficientError(RuntimeError):
    """
    This exception is raised when a NodeDriver cannot instantiate a Node because insufficient
    information (parameters) has been provided.
    """
    def __init__(self, node_driver: NodeDriver, details: str ):
        super().__init__(f"Node specification is insufficient for {node_driver}: {details}" )


class NodeSpecificationInvalidError(RuntimeError):
    """
    This exception is raised when a NodeDriver cannot instantiate a Node because invalid
    information (e.g. a syntax error in a parameter) has been provided.
    """
    def __init__(self, node_driver: NodeDriver, parameter: str, details: str ):
        super().__init__(f"Node specification is invalid for {node_driver}, parameter {parameter}: {details}" )
