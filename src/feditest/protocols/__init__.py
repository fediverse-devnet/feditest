"""
Define interfaces to interact with the nodes in the constellation being tested
"""

from abc import ABC
from collections.abc import Callable
from typing import Any, final

from feditest import SkipTestException
from feditest.reporting import warning


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
    def __init__(self, rolename: str, parameters: dict[str,Any], node_driver: 'NodeDriver'):
        """
        rolename: name of the role in the constellation
        parameters: parameters for this Node. Always provided, even if empty
        node_driver: the NodeDriver that provisioned this Node
        """
        self._rolename = rolename
        self._parameters = parameters
        self._node_driver = node_driver


    @property
    def rolename(self):
        return self._rolename


    @property
    def hostname(self):
        return self._parameters.get('hostname')


    @property
    def node_driver(self):
        return self._node_driver


    @property
    def app_name(self):
        ...


    @property
    def app_version(self):
        return None # by default we don't know


    def parameter(self, name:str) -> str | None:
        return self._parameters.get(name)


    def __str__(self) -> str:
        return f'"{ type(self).__name__}" in constellation role "{self.rolename}"'


    def prompt_user(self, question: str, value_if_known: Any | None = None, parse_validate: Callable[[str],Any] | None = None) -> Any | None:
        """
        If an Node does not natively implement support for a particular method,
        this method is invoked as a fallback. It prompts the user to enter information
        at the console.

        question: the text to be emitted to the user as a prompt
        value_if_known: if given, that value can be used instead of asking the user
        parse_validate: optional function that attempts to parse and validate the provided user input.
        If the value is valid, it parses the value and returns the parsed version. If not valid, it returns None.
        return: the value entered by the user, parsed, or None
        """
        return self._node_driver.prompt_user(question, value_if_known, parse_validate)


class NodeDriver(ABC):
    """
    This is an abstract superclass for all objects that know how to instantiate Nodes of some kind.
    """
    def __init__(self, name: str):
        self.name : str = name


    @final
    def provision_node(self, rolename: str, parameters: dict[str,Any]) -> Node:
        """
        Instantiate a Node
        rolename: the name of this Node in the constellation
        parameters: parameters for this Node
        """
        if rolename is None:
            raise NodeSpecificationInvalidError(self, 'rolename', 'rolename must be given')
        ret = self._provision_node(rolename, parameters)
        return ret


    @final
    def unprovision_node(self, node: Node) -> None:
        """
        Deactivate and delete a Node
        node: the Node
        """
        if node.node_driver != self :
            raise Exception(f"Node does not belong to this NodeDriver: { node.node_driver } vs { self }") # pylint: disable=broad-exception-raised
        self._unprovision_node(node)


    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> Node:
        """
        The factory method for Node. Any subclass of NodeDriver should also
        override this and return a more specific subclass of IUT.
        """
        raise NotImplementedByNodeDriverError(self, NodeDriver._provision_node)


    def _unprovision_node(self, node: Node) -> None:
        """
        Invoked when a Node gets unprovisioned, in case cleanup needs to be performed.
        This is here so subclasses of NodeDriver can override it.
        """
        # by default, do nothing
        pass # pylint: disable=unnecessary-pass


    def prompt_user(self, question: str, value_if_known: Any | None = None, parse_validate: Callable[[str],Any] | None = None) -> Any | None:
        """
        If an NodeDriver does not natively implement support for a particular method,
        this method is invoked as a fallback. It prompts the user to enter information
        at the console.

        This is implemented on NodeDriver rather than Node, so we can also ask
        provisioning-related questions.

        question: the text to be emitted to the user as a prompt
        value_if_known: if given, that value can be used instead of asking the user
        parse_validate: optional function that attempts to parse and validate the provided user input.
        If the value is valid, it parses the value and returns the parsed version. If not valid, it returns None.
        return: the value entered by the user, parsed, or None
        """
        if value_if_known:
            if parse_validate is None:
                return value_if_known
            ret_parsed = parse_validate(value_if_known)
            if ret_parsed is not None:
                return ret_parsed
            warning(f'Preconfigured value "{ value_if_known }" is invalid, ignoring.')

        while True:
            ret = input(f'TESTER ACTION REQUIRED: { question }')
            if parse_validate is None:
                return ret
            ret_parsed = parse_validate(ret)
            if ret_parsed is not None:
                return ret_parsed
            print(f'INPUT ERROR: invalid input, try again. Was: "{ ret }"')


    def __str__(self) -> str:
        return f'"{ self.name }"'


class NotImplementedByNodeOrDriverError(SkipTestException):
    pass


class NotImplementedByNodeError(NotImplementedByNodeOrDriverError):
    """
    This exception is raised when a Node cannot perform a certain operation because it
    has not been implemented in this subtype of Node.
    """
    def __init__(self, node: Node, method: Callable[...,Any], arg: Any = None ):
        super().__init__(f"Not implemented by node {node}: {method.__name__}" + (f" ({ arg })" if arg else ""))


class NotImplementedByNodeDriverError(NotImplementedByNodeOrDriverError):
    """
    This exception is raised when a Node cannot perform a certain operation because it
    has not been implemented in this subtype of Node.
    """
    def __init__(self, node_driver: NodeDriver, method: Callable[...,Any], arg: Any = None ):
        super().__init__(f"Not implemented by node driver {node_driver}: {method.__name__}" + (f" ({ arg })" if arg else ""))


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
