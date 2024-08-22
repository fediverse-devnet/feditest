"""
Define interfaces to interact with the nodes in the constellation being tested
"""

from abc import ABC
from collections.abc import Callable
from typing import Any, final

from feditest.testplan import TestPlanConstellationNode
from feditest.reporting import warning, trace


class Account(ABC):
    """
    The notion of an existing account on a Node. As different Nodes have different ideas about
    what they know about an Account, this is an entirey abstract base class here.
    """
    def __init__(self, role: str | None):
        self.role = role


class NonExistingAccount(ABC):
    """
    The notion of a non-existing account on a Node. As different Nodes have different ideas about
    what they know about an Account, this is an entirey abstract base class here.
    """
    def __init__(self, role: str | None):
        self.role = role


class NodeConfiguration(ABC):
    """
    Collects all information about a Node so that the Node can be instantiated.
    This is an abstract concept; specific Node subclasses will have their own subclasses.
    On this level, just a few properties have been defined that are commonly used.

    (Maybe this could be a @dataclass: not sure how exactly that works with ABC and subclasses
    so I rather not try)
    """
    def __init__(self,
        node_driver: 'NodeDriver',
        app: str,
        app_version: str | None = None,
        hostname: str | None = None,
        known_accounts: list[Account] | None = None,
        known_non_existing_accounts: list[NonExistingAccount] | None = None,
        start_delay: float = 0.0
    ):
        self._node_driver = node_driver
        self._app = app
        self._app_version = app_version
        self._hostname = hostname
        self._known_accounts = known_accounts
        self._known_non_existing_accounts = known_non_existing_accounts
        self._start_delay = start_delay


    @property
    def node_driver(self) -> 'NodeDriver':
        return self._node_driver


    @property
    def app(self) -> str:
        return self._app


    @property
    def app_version(self) -> str | None:
        return self._app_version


    @property
    def hostname(self) -> str | None:
        return self._hostname


    @property
    def known_accounts(self) -> list[Account]:
        return self._known_accounts if self._known_accounts is not None else []


    @property
    def known_non_existing_accounts(self) -> list[NonExistingAccount]:
        return self._known_non_existing_accounts if self._known_non_existing_accounts is not None else []


    @property
    def start_delay(self) -> float:
        return self._start_delay


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
    def __init__(self, rolename: str, config: NodeConfiguration):
        """
        rolename: name of the role in the constellation
        config: the previous created configuration object for this Node
        """
        if not rolename:
            raise Exception('Required: rolename')
        if not config: # not trusting the linter
            raise Exception('Required: config')

        self._rolename = rolename
        self._config = config


    @property
    def rolename(self):
        return self._rolename


    @property
    def config(self):
        return self._config


    @property
    def hostname(self):
        return self._config.hostname


    @property
    def node_driver(self):
        return self._config.node_driver


    def add_cert_to_trust_store(self, root_cert: str) -> None:
        self.prompt_user(f'Please add this temporary certificate to the trust root of node { self } and hit return when done:\n' + root_cert)


    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        self.prompt_user(f'Please remove this previously-added temporary certificate from the trust store of node { self } and hit return when done:\n' + root_cert)


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
        return self.node_driver.prompt_user(question, value_if_known, parse_validate)


class NodeDriver(ABC):
    """
    This is an abstract superclass for all objects that know how to instantiate Nodes of some kind.
    Any one subclass of NodeDriver is only instantiated once as a singleton
    """
    def create_configuration(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> NodeConfiguration:
        """
        Read the node data provided in test_plan_node and create a NodeConfiguration object
        from it. This will throw exceptions if the Node is misconfigured.

        Override in subclasses.
        """
        return NodeConfiguration(
            self,
            test_plan_node.parameter_or_raise('app'),
            test_plan_node.parameter('app_version'),
            test_plan_node.parameter('hostname')
        )


    @final
    def provision_node(self, rolename: str, config: NodeConfiguration) -> Node:
        """
        Instantiate a Node
        rolename: the name of this Node in the constellation
        config: the NodeConfiguration created with create_configuration
        """
        trace(f'Provisioning node for role { rolename } with NodeDriver { self.__class__.__name__} and configuration { config }')
        ret = self._provision_node(rolename, config)
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


    def _provision_node(self, rolename: str, config: NodeConfiguration) -> Node:
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
        return self.__class__.__name__


class SkipTestException(Exception):
    """
    Indicates that the test wanted to be skipped. It can be thrown if the test recognizes
    the circumstances in which it should be run are not currently present.
    Modeled after https://github.com/hamcrest/PyHamcrest/blob/main/src/hamcrest/core/assert_that.py
    """
    def __init__(self, msg: str) :
        """
        Provide reasoning why this test was skipped.
        """
        super().__init__(msg)


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


class NodeOutOfAccountsException(RuntimeError):
    """
    A test wanted to obtain an (or obtain another) account on this Node, but no account was
    known, no account could be automatically provisioned, or all known or provisionable
    accounts were returned already.
    """
    def __init__(self, node: NodeDriver, rolename: str ):
        super().__init__(f"Out of accounts on Node { node }, account role { rolename }" )


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


class TimeoutException(RuntimeError):
    """
    A result has not arrived within the expected time period.
    """
    def __init__(self, msg: str, timeout: int):
        super().__init__(f'{ msg } (timeout: { timeout })')
