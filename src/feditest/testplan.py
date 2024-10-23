"""
Classes that represent a TestPlan and its parts.
"""

from abc import ABC
from dataclasses import dataclass
import json
from typing import Any, Callable, Final

import msgspec

import feditest
from feditest.utils import hostname_validate, FEDITEST_VERSION


class InvalidAccountSpecificationException(Exception):
    """
    Thrown if an account specification given in a TestPlan does not have sufficient information
    to be used as an Account for a Node instantiated by this NodeDriver.
    """
    def __init__(self, account_info_from_testplan: dict[str, str | None], msg: str, context_msg: str = ''):
        super().__init__(f'{ context_msg }Invalid account specification: { msg }')


class InvalidNonExistingAccountSpecificationException(Exception):
    """
    Thrown if a non-existing account specification given in a TestPlan does not have sufficient information
    to be used as an NonExistingAccount for a Node instantiated by this NodeDriver.
    """
    def __init__(self, non_existing_account_info_from_testplan: dict[str, str | None], msg: str, context_msg: str = ''):
        super().__init__(f'{ context_msg }Invalid non-existing account specification: { msg }')


@dataclass
class TestPlanNodeParameter:
    """
    Captures everything that's there to know about a parameter in a Node specification in a test plan.
    This centralizes error checking functionality and makes emitting helpful output simpler.
    """
    name: str
    description: str
    validate: Callable[[str],Any] | None = None
    default: str | None = None


@dataclass
class TestPlanNodeAccountOrNonExistingAccountField(ABC):
    name: str
    description: str
    validate: Callable[[str],Any] | None = None
    validate_error_msg: str = 'Value invalid.'


    def get_validate_from(self, account_info_in_testplan: dict[str, str | None], context_msg: str = '') -> str | None:
        """
        Get the value of this field from account_info_in_testplan.
        If there is no value, return None.
        If there is a value, and it does not pass validation, raise an exception.
        """
        if account_info_in_testplan is None or self.name not in account_info_in_testplan or not account_info_in_testplan[self.name]:
            return None
        ret = account_info_in_testplan[self.name]
        if ret and self.validate and not self.validate(ret):
            raise InvalidAccountSpecificationException(account_info_in_testplan, f'Field { self.name }: { self.validate_error_msg } Is: "{ ret }".', context_msg)
        return ret


    def get_validate_from_or_raise(self, account_info_in_testplan: dict[str, str | None], context_msg: str = '') -> str:
        ret = self.get_validate_from(account_info_in_testplan, context_msg)
        if ret is None:
            raise InvalidAccountSpecificationException(account_info_in_testplan, f'Missing field value for: { self.name }.', context_msg)
        return ret


@dataclass
class TestPlanNodeAccountField(TestPlanNodeAccountOrNonExistingAccountField):
    """
    Captures everything that's there to know about a field providing information about a pre-existing
    Account on a Node specification in a test plan.
    This centralizes error checking functionality and makes emitting helpful output simpler.
    """
    pass


@dataclass
class TestPlanNodeNonExistingAccountField(TestPlanNodeAccountOrNonExistingAccountField):
    """
    Captures everything that's there to know about a field providing information about a non-existing
    Account on a Node specification in a test plan.
    This centralizes error checking functionality and makes emitting helpful output simpler.
    """
    pass


class TestPlanError(RuntimeError):
    """
    This exception is raised when a TestPlan is defined incorrectly or incompletely.
    """
    def __init__(self, details: str):
        super().__init__(f"TestPlan defined insufficiently: {details}" )


class TestPlanNodeParameterRequiredError(TestPlanError):
    """
    A required parameter was missing.
    """
    def __init__(self, par: TestPlanNodeParameter, more_details : str = ''):
        super().__init__(f'Required parameter missing: "{ par.name }"{ more_details}.')


class TestPlanNodeParameterMalformedError(TestPlanError):
    """
    A required parameter was given but malformed.
    """
    def __init__(self, par: TestPlanNodeParameter, more_details : str = ''):
        super().__init__(f'Required parameter malformed: "{ par.name }"{ more_details}.')


ROLE_KEY: Final[str] = 'role' # This applies to the TestPlanConstellationNode, but needs to be out here
                              # so it won't be JSON serialized

class TestPlanConstellationNode(msgspec.Struct):
    """
    A Node in a TestPlanConstellation.

    The accounts field collects the active accounts that are known to pre-exist on the
    Node, and can be used for testing. The non_existing_accounts collects information
    on accounts that are known not to exist. (This is useful to test what happens if
    a message is directed to a non-existing account, for example.)

    The accounts and non_existing_accounts fields are free-form hashes on this level,
    with only one pre-defined (but optional) key: 'role'. The 'role' field indicates
    which account role this account should be used with, if any.

    This is a free-form hash because different subclasses of Node want different
    fields, and only they can decide what is and isn't valid for them. This
    checking is initiated by the TestRun before the Nodes are provisioned. The
    TestRun delegates it to the NodeDrivers that will instantiate the Nodes.
    """
    nodedriver: str | None = None # if we allow this to be None, we can do better error reporting
    parameters: dict[str, Any | None] | None = None
    accounts: list[dict[str, str | None]] | None = None
    non_existing_accounts: list[dict[str, str | None]] | None = None


    @staticmethod
    def load(filename: str) -> 'TestPlanConstellationNode':
        """
        Read a file, and instantiate a TestPlanConstellationNode from what we find.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            testplanconstellationnode_json = json.load(f)

        return msgspec.convert(testplanconstellationnode_json, type=TestPlanConstellationNode)


    def parameter(self, par: TestPlanNodeParameter, defaults: dict[str, str | None] | None = None) -> Any | None:
        ret = None
        if self.parameters:
            ret = self.parameters.get(par.name)
        if ret is None and defaults:
            ret = defaults.get(par.name)
        if ret is None:
            ret = par.default
        if ret is not None:
            if par.validate and par.validate(ret) is None:
                raise TestPlanNodeParameterMalformedError(par)
            return ret
        return None


    def parameter_or_raise(self, par: TestPlanNodeParameter, defaults: dict[str, str | None] | None = None) -> Any:
        ret = self.parameter(par, defaults)
        if ret is None:
            raise TestPlanNodeParameterRequiredError(par)
        return ret


    def get_account_by_rolename(self, rolename: str | None) -> dict[str, str | None] | None:
        """
        Convenience method to centralize search in one place.
        """
        if not self.accounts:
            return None
        for account in self.accounts:
            if 'role' in account and rolename == account['role']:
                return account
        return None


    def get_non_existing_account_by_rolename(self, rolename: str | None) -> dict[str, str | None] | None:
        """
        Convenience method to centralize search in one place.
        """
        if not self.non_existing_accounts:
            return None
        for non_account in self.non_existing_accounts:
            if 'role' in non_account and rolename == non_account['role']:
                return non_account
        return None


    def check_can_be_executed(self, context_msg: str = "") -> None:
        if not self.nodedriver:
            raise TestPlanError(context_msg + 'No NodeDriver')
        if self.nodedriver not in feditest.all_node_drivers:
            raise TestPlanError(context_msg + f'Cannot find NodeDriver "{ self.nodedriver }".')

        # self.accounts and self.non_existing_accounts cannot be checked here;
        # this can only be done later once the NodeDriver has been instantiated

        # also check well-known parameters
        if self.parameters:
            hostname = self.parameters.get('hostname')
            if hostname:
                if isinstance(hostname, str):
                    if hostname_validate(hostname) is None:
                        raise TestPlanError(context_msg + f'Invalid hostname: "{ hostname }".')
                else:
                    raise TestPlanError(context_msg + 'Invalid hostname: not a string')


class TestPlanConstellation(msgspec.Struct):
    roles : dict[str,TestPlanConstellationNode | None] # can be None if used as template
    name: str | None = None


    @staticmethod
    def load(filename: str) -> 'TestPlanConstellation':
        """
        Read a file, and instantiate a TestPlanConstellation from what we find.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            testplanconstellation_json = json.load(f)

        return msgspec.convert(testplanconstellation_json, type=TestPlanConstellation)


    def __str__(self):
        if self.name:
            return self.name
        # construct something that makes sense to the user
        return ", ".join( [ f'{ role }: { node.nodedriver if node else "" }' for role, node in self.roles.items() ] )


    def is_template(self):
        """
        Returns true if the roles in the constellation have not all been bound to NodeDrivers.
        """
        for node in self.roles.values():
            if node is None:
                return True
        return False


    def check_can_be_executed(self, context_msg: str = "") -> None:
        for role_name, node in self.roles.items():
            role_context_msg = context_msg + f"Role {role_name}: "
            if node is None:
                raise TestPlanError(context_msg + f'No node assigned to role {role_name}.')
            node.check_can_be_executed(role_context_msg)


    def check_defines_all_role_names(self, want_role_names: set[str], context_msg: str = ""):
        for want_role_name in want_role_names:
            if want_role_name not in self.roles:
                raise TestPlanError(context_msg + f'Constellation does not define role "{ want_role_name }".')


    def as_json(self) -> bytes:
        ret = msgspec.json.encode(self)
        ret = msgspec.json.format(ret, indent=4)
        return ret


    def save(self, filename: str) -> None:
        with open(filename, 'wb') as f:
            f.write(self.as_json())


    def print(self) -> None:
        print(self.as_json().decode('utf-8'))


class TestPlanTestSpec(msgspec.Struct):
    name: str
    rolemapping: dict[str,str] | None = None # maps from the Test's role names to the constellation's role names
    skip: str | None = None # if a string is given, it's a reason message why this test spec should be skipped


    def __str__(self):
        return self.name


    def get_test(self, context_msg : str = "" ) -> 'feditest.Test':
        ret = feditest.all_tests.get(self.name)
        if ret is None:
            raise TestPlanError(context_msg + f'Cannot find test "{ self.name }".')
        return ret


    def needed_constellation_role_names(self, context_msg : str = "" ) -> set[str]:
        """
        Return the names of the constellation roles needed after translation from whatever the test itself
        might call them locally.
        """
        ret = self.get_test().needed_local_role_names()
        if self.rolemapping:
            ret = ret.copy() # keep unchanged the ones not mapped
            for key, value in self.rolemapping.items():
                if key in ret:
                    ret.remove(key) # remove first
                    ret.add(value)
                else:
                    raise TestPlanError(context_msg + f'Cannot find role "{ key }" in test')
        return ret


    def check_can_be_executed(self, constellation: TestPlanConstellation, context_msg: str = "") -> None:
        test_context_msg = context_msg + f'Test "{ self.name }": '
        needed_constellation_role_names = self.needed_constellation_role_names(context_msg) # may raise
        constellation.check_defines_all_role_names(needed_constellation_role_names, test_context_msg )


    def simplify(self) -> None:
        """
        If possible, simplify this test specification
        """
        if self.rolemapping:
            new_rolemapping : dict[str,str] | None = None
            for name, value in self.rolemapping.items():
                if name != value:
                    if new_rolemapping is None:
                        new_rolemapping = {}
                    new_rolemapping[name] = value
            if new_rolemapping is None:
                self.rolemapping = None
            elif len(new_rolemapping) < len(self.rolemapping):
                self.rolemapping = new_rolemapping


class TestPlanSessionTemplate(msgspec.Struct):
    """
    A TestPlanSessionTemplate defines a list of tests that will be executed in the context of
    a particular TestPlanConstellation. The session template and the constellation together make the session.
    """
    tests : list[TestPlanTestSpec]
    name: str | None = None


    @staticmethod
    def load(filename: str) -> 'TestPlanSessionTemplate':
        """
        Read a file, and instantiate a TestPlanSession from what we find.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            testplansession_json = json.load(f)

        return msgspec.convert(testplansession_json, type=TestPlanSessionTemplate)


    def __str__(self):
        return self.name if self.name else 'Unnamed'


    def check_can_be_executed(self, constellation: TestPlanConstellation, context_msg: str = "") -> None:
        if not self.tests:
            raise TestPlanError(context_msg + 'No tests have been defined.')

        for index, test_spec in enumerate(self.tests):
            test_spec.check_can_be_executed(constellation, context_msg + f'Test (index {index}): ')


    def needed_constellation_role_names(self) -> set[str]:
        ret = set()
        for test in self.tests:
            ret |= test.needed_constellation_role_names()
        return ret


    def simplify(self) -> None:
        """
        If possible, simplify this test plan session.
        """
        for test in self.tests:
            test.simplify()


    def as_json(self) -> bytes:
        ret = msgspec.json.encode(self)
        ret = msgspec.json.format(ret, indent=4)
        return ret


    def save(self, filename: str) -> None:
        with open(filename, 'wb') as f:
            f.write(self.as_json())


    def print(self) -> None:
        print(self.as_json().decode('utf-8'))


class TestPlan(msgspec.Struct):
    """
    A TestPlan runs the same TestPlanSession with one or more TestPlanConstellations.
    """
    session_template : TestPlanSessionTemplate
    constellations : list[TestPlanConstellation]
    name: str | None = None
    type: str = 'feditest-testplan'
    feditest_version: str = FEDITEST_VERSION


    def simplify(self) -> None:
        """
        If possible, simplify this test plan.
        """
        self.session_template.simplify()


    @staticmethod
    def load(filename: str) -> 'TestPlan':
        """
        Read a file, and instantiate a TestPlan from what we find.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            testplan_json = json.load(f)

        return msgspec.convert(testplan_json, type=TestPlan)


    def __str__(self):
        return self.name if self.name else 'Unnamed'


    def is_compatible_type(self):
        return self.type is None or self.type == 'feditest-testplan'


    def has_compatible_version(self):
        if not self.feditest_version:
            return True
        return self.feditest_version == FEDITEST_VERSION


    def as_json(self) -> bytes:
        ret = msgspec.json.encode(self)
        ret = msgspec.json.format(ret, indent=4)
        return ret


    def save(self, filename: str) -> None:
        with open(filename, 'wb') as f:
            f.write(self.as_json())


    def print(self) -> None:
        print(self.as_json().decode('utf-8'))


    def check_can_be_executed(self, context_msg: str = "") -> None:
        """
        Check that this TestPlan is ready for execution. If not, raise a TestPlanEerror that explains the problem.
        """
        for constellation in self.constellations:
            constellation.check_can_be_executed(context_msg + f'Constellation { constellation }: ')
            self.session_template.check_can_be_executed(constellation, context_msg + f'TestPlanSession with Constellation { constellation }: ')
