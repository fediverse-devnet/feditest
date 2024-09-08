"""
Define interfaces to interact with the nodes in the constellation being tested
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, cast, final

from feditest.testplan import TestPlanConstellationNode, TestPlanNodeParameter
from feditest.reporting import warning, trace
from feditest.utils import hostname_validate, appname_validate, appversion_validate


APP_PAR = TestPlanNodeParameter(
    'app',
    """Name of the app""",
    validate = lambda x: len(x)
)
APP_VERSION_PAR = TestPlanNodeParameter(
    'app_version',
    """Version of the app"""
)
HOSTNAME_PAR = TestPlanNodeParameter(
    'hostname',
    """DNS hostname of where the app is running.""",
    validate=hostname_validate
)


class Account(ABC):
    """
    The notion of an existing account on a Node. As different Nodes have different ideas about
    what they know about an Account, this is an entirey abstract base class here.
    """
    def __init__(self, role: str | None):
        self.role = role
        self.node : 'Node' | None = None


    def set_node(self, node: 'Node'):
        """
        Set the Node at which this is an Account. This is invoked exactly once after the Node
        has been instantiated (the Account is instantiated earlier).
        """
        if self.node:
            raise ValueError(f'Node already set {self}')
        self.node = node


class NonExistingAccount(ABC):
    """
    The notion of a non-existing account on a Node. As different Nodes have different ideas about
    what they know about an Account, this is an entirey abstract base class here.
    """
    def __init__(self, role: str | None):
        self.role = role
        self.node : 'Node' | None = None


    def set_node(self, node: 'Node'):
        """
        Set the Node at which this is a NonExistingAccount. This is invoked exactly once after the Node
        has been instantiated (the NonExistingAccount is instantiated earlier).
        """
        if self.node:
            raise ValueError(f'Node already set {self}')
        self.node = node


class InvalidAccountSpecificationException(Exception):
    """
    Thrown if an account specification given in a TestPlan does not have sufficient information
    to be used as an Account for a Node instantiated by this NodeDriver.
    """
    def __init__(self, account_info_from_testplan: dict[str, str | None], node_driver: 'NodeDriver', msg: str):
        super().__init__(f'Invalid account specification for NodeDriver { node_driver }: { msg }')


class InvalidNonExistingAccountSpecificationException(Exception):
    """
    Thrown if a non-existing account specification given in a TestPlan does not have sufficient information
    to be used as an NonExistingAccount for a Node instantiated by this NodeDriver.
    """
    def __init__(self, non_existing_account_info_from_testplan: dict[str, str | None], node_driver: 'NodeDriver', msg: str):
        super().__init__(f'Invalid non-existing account specification for NodeDriver { node_driver }: { msg }')


class OutOfAccountsException(Exception):
    """
    Thrown if another Account was requested, but no additional Account was known or could be
    provisionined.
    """
    ...


class OutOfNonExistingAccountsException(Exception):
    """
    Thrown if another NonExistingAccount was requested, but no additional NonExistingAccount
    was known or could be provisionined.
    """
    ...


class AccountManager(ABC):
    """
    Manages accounts on a Node. It can be implemented in a variety of ways, including
    being a facade for the Node's API, or returning only Accounts pre-allocated in the
    TestPlan, or dynamically provisioning accounts etc.
    """
    @abstractmethod
    def set_node(self, node: 'Node'):
        """
        Set the Node to which this AccountManager belongs. This is invoked exactly once after the Node
        has been instantiated (the AccountManager is instantiated earlier).
        """
        ...


    @abstractmethod
    def obtain_account_by_role(self, role: str | None = None) -> Account:
        """
        If this method is invoked with the same role twice, it returns
        the same Account. May raise OutOfAccountsException.
        """
        ...


    @abstractmethod
    def obtain_non_existing_account_by_role(self, role: str | None = None) -> NonExistingAccount:
        """
        If this method is invoked with the same role twice, it returns
        the same NonExistingAccount. May raise OutOfNonExistingAccountsException.
        """
        ...


class AbstractAccountManager(AccountManager):
    """
    An AccountManager implementation that is initialized from lists of inital accounts and non-accounts
    in a NodeConfiguration, and then dynamically allocates those Accounts and
    NonExistingAccounts to the requested roles.
    It has an empty method to dynamically provision new Accounts, which can be implemented
    by subclasses.
    As the name (but not the code) says, it is intended to be abstract. We love Python.
    """
    def __init__(self, initial_accounts: list[Account], initial_non_existing_accounts: list[NonExistingAccount]):
        """
        Provide the accounts and non-existing-accounts that are known to exist/not exist
        when the Node is provisioned.
        """
        self._accounts_allocated_to_role : dict[str | None, Account] = { account.role : account for account in initial_accounts if account.role }
        self._accounts_not_allocated_to_role : list[Account] = [ account for account in initial_accounts if not account.role ]

        self._non_existing_accounts_allocated_to_role : dict[str | None, NonExistingAccount] = { non_account.role : non_account for non_account in initial_non_existing_accounts if non_account.role }
        self._non_existing_accounts_not_allocated_to_role : list[NonExistingAccount ]= [ non_account for non_account in initial_non_existing_accounts if not non_account.role ]

        self._node : Node | None = None # the Node this AccountManager belongs to. Set once the Node has been instantiated


    # Python 3.12 @override
    def set_node(self, node: 'Node') -> None:
        if self._node:
            raise ValueError('Have Node already')
        self._node = node

        for account in self._accounts_allocated_to_role.values():
            account.set_node(self._node)
        for account in self._accounts_not_allocated_to_role:
            account.set_node(self._node)
        for non_existing_account in self._non_existing_accounts_allocated_to_role.values():
            non_existing_account.set_node(self._node)
        for non_existing_account in self._non_existing_accounts_not_allocated_to_role:
            non_existing_account.set_node(self._node)


    # Python 3.12 @override
    def obtain_account_by_role(self, role: str | None = None) -> Account:
        ret = self._accounts_allocated_to_role.get(role)
        if not ret:
            if self._accounts_not_allocated_to_role:
                ret = self._accounts_not_allocated_to_role.pop()
                self._accounts_allocated_to_role[role] = ret
            else:
                ret = self._provision_account_for_role(role)
                if ret:
                    if ret.node is None: # the Node may already have assigned it
                        ret.set_node(cast(Node, self._node)) # by now it is not None
                    self._accounts_allocated_to_role[role] = ret
        if ret:
            return ret
        raise OutOfAccountsException()


    # Python 3.12 @override
    def obtain_non_existing_account_by_role(self, role: str | None = None) -> NonExistingAccount:
        ret = self._non_existing_accounts_allocated_to_role.get(role)
        if not ret:
            if self._non_existing_accounts_not_allocated_to_role:
                ret = self._non_existing_accounts_not_allocated_to_role.pop()
                self._non_existing_accounts_allocated_to_role[role] = ret
            else:
                ret = self._provision_non_existing_account_for_role(role)
                if ret:
                    if ret.node is None: # the Node may already have assigned it
                        ret.set_node(cast(Node, self._node)) # by now it is not None
                    self._non_existing_accounts_allocated_to_role[role] = ret
        if ret:
            return ret
        raise OutOfNonExistingAccountsException()


    @abstractmethod
    def _provision_account_for_role(self, role: str | None = None) -> Account | None:
        """
        This can be overridden by subclasses to dynamically provision a new Account.
        By default, we ask our Node.
        """
        ...


    @abstractmethod
    def _provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        """
        This can be overridden by subclasses to dynamically provision a new NonExistingAccount.
        By default, we ask our Node.
        """
        ...


class DefaultAccountManager(AbstractAccountManager):
    """
    An AccountManager that asks the Node to provision accounts.
    """
    def _provision_account_for_role(self, role: str | None = None) -> Account | None:
        node = cast(Node, self._node)
        return node.provision_account_for_role(role)


    def _provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        node = cast(Node, self._node)
        return node.provision_non_existing_account_for_role(role)


class StaticAccountManager(AbstractAccountManager):
    """
    An AccountManager that only uses the static informatation about Accounts and NonExistingAccounts
    that was provided in the TestPlan.
    """
    def _provision_account_for_role(self, role: str | None = None) -> Account | None:
        return None


    def _provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        return None


class NodeConfiguration:
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
        start_delay: float = 0.0
    ):
        if app and not appname_validate(app):
            raise NodeSpecificationInvalidError(node_driver, 'app', app)
        if app_version and not appversion_validate(app_version):
            raise NodeSpecificationInvalidError(node_driver, 'app_version', app_version)
        if hostname and not hostname_validate(hostname):
            raise NodeSpecificationInvalidError(node_driver, 'hostname', hostname)

        self._node_driver = node_driver
        self._app = app
        self._app_version = app_version
        self._hostname = hostname
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
    def __init__(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None = None):
        """
        rolename: name of the role in the constellation
        config: the previously created configuration object for this Node
        account_manager: use this AccountManager
        """
        if not rolename:
            raise Exception('Required: rolename')
        if not config: # not trusting the linter
            raise Exception('Required: config')

        self._rolename = rolename
        self._config = config
        if account_manager:
            self._account_manager = account_manager
            self._account_manager.set_node(self)


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


    @property
    def account_manager(self) -> AccountManager | None:
        return self._account_manager


    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        """
        We need a new Account on this Node, for the given role. Provision that account,
        or return None if not possible. By default, we ask the user.
        """
        return None


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        """
        We need a new NonExistingAccount on this Node, for the given role. Return information about that
        non-existing account, or return None if not possible. By default, we ask the user.
        """
        return None


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
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        """
        Return the TestPlanNodeParameters understood by this NodeDriver. This is used by
        feditest info --nodedriver to help the user figure out what parameters to specify
        and what their names are.
        """
        return [ APP_PAR, APP_VERSION_PAR, HOSTNAME_PAR ]


    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        """
        Read the node data provided in test_plan_node and create a NodeConfiguration object
        from it. This will throw exceptions if the Node is misconfigured.

        May be overridden in subclasses.
        """
        return (
            NodeConfiguration(
                self,
                test_plan_node.parameter_or_raise(APP_PAR),
                test_plan_node.parameter(APP_VERSION_PAR),
                test_plan_node.parameter(HOSTNAME_PAR)
            ),
            None
        )


    @final
    def provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None = None) -> Node:
        """
        Instantiate a Node
        rolename: the name of this Node in the constellation
        config: the NodeConfiguration created with create_configuration
        """
        trace(f'Provisioning node for role { rolename } with NodeDriver { self.__class__.__name__} and configuration { config }')
        ret = self._provision_node(rolename, config, account_manager)
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


    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> Node:
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
