"""
Core module.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from inspect import getfullargspec, getmembers, getmodule, isfunction
import traceback
from types import FunctionType
from typing import Any, Type

from feditest.protocols import NotImplementedByNodeOrDriverError
from feditest.testplan import TestPlanTestSpec
from feditest.testrun import TestRunSession, TestClassTestStepProblem, TestFunctionProblem
from feditest.reporting import fatal, error, info, trace
from feditest.utils import load_python_from


class Test(ABC):
    """
    Captures the notion of a Test, such as "see whether a follower is told about a new post".
    """
    def __init__(self, name: str, description: str | None ) -> None:
        self.name: str = name
        self.description: str | None = description

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        ...


    @abstractmethod
    def needed_local_role_names(self) -> set[str]:
        """
        Determines the local names of the constellation roles this test needs. These may be mapped to
        constellation roles in the test definition.
        """
        ...

    @abstractmethod
    def run(self, test_spec: TestPlanTestSpec, session: TestRunSession):
        """
        Run this test in the provided constellation.
        """
        ...


class TestFromTestFunction(Test):
    """
    A test that is defined as a single function.
    """
    def __init__(self, name: str, description: str | None, test_function: Callable[..., None]) -> None:
        super().__init__(name, description)

        self.test_function = test_function


    def metadata(self) -> dict[str, Any]:
        return {
            'Test name:' : self.name,
            'Description:' : self.description
        }


    def needed_local_role_names(self) -> set[str]:
        ret = {}
        function_spec = getfullargspec(self.test_function)
        for arg in function_spec.args:
            ret[arg] = 1
        return set(ret)


    def run(self, test_spec: TestPlanTestSpec, session: TestRunSession):
        """
        Run this test in the provided constellation.
        """
        trace(f'Running test { test_spec }, function "{ self.name }"')

        constellation = session.constellation
        if constellation is None: # cannot really happen
            raise ValueError('Null constellation')

        args = {}
        for local_role_name in self.needed_local_role_names():
            constellation_role_name = local_role_name
            if test_spec.rolemapping and local_role_name in test_spec.rolemapping:
                constellation_role_name = test_spec.rolemapping[local_role_name]
            args[local_role_name] = constellation.get_node(constellation_role_name)

        try:
            self.test_function(**args)

        except AssertionError as e:
            problem = TestFunctionProblem(test_spec, e)
            error('FAILED test assertion:', problem, "\n".join(traceback.format_exception(problem.exc)))
            session.problems.append(problem)

        except NotImplementedByNodeOrDriverError as e:
            info(f'Skipping test "{ test_spec.name }" because: { e }' )

        except Exception as e:
            problem = TestFunctionProblem(test_spec, e)
            error('FAILED test (other reason):', problem, "\n".join(traceback.format_exception(problem.exc)))
            session.problems.append(problem)


class TestStep:
    """
    A step in a TestByTestClass. TestSteps for the same Test are all declared with @step in the same class,
    and will be executed in sequence unless specified otherwise.
    """
    def __init__(self, name: str, description: str | None, test: 'TestFromTestClass', test_step_function: Callable[[Any],None]) -> None:
        self.name: str = name
        self.description: str | None = description
        self.test = test
        self.test_step_function: Callable[[Any], None] = test_step_function


class TestFromTestClass(Test):
    def __init__(self, name: str, description: str | None, clazz: type) -> None:
        super().__init__(name, description)

        self.clazz = clazz
        self.steps : list[TestStep] = []


    def metadata(self) -> dict[str, Any]:
        return {
            'Test name:' : self.name,
            'Description:' : self.description,
            'Steps:' : len(self.steps)
        }

    def needed_local_role_names(self) -> set[str]:
        """
        Determines the names of the constellation roles this test step needs.
        It determines that by creating the union of the parameter names of all the TestSteps in the Test
        """
        ret = {}
        function_spec = getfullargspec(self.clazz.__init__) # type: ignore [misc]
        for arg in function_spec.args[1:]: # first is self
            ret[arg] = 1
        return set(ret)


    def run(self, test_spec: TestPlanTestSpec, session: TestRunSession):
        trace(f'Running test { test_spec }, instantiating class "{ self.name }"')

        constellation = session.constellation
        if constellation is None: # cannot really happen
            raise ValueError('Null constellation')

        args = {}
        for local_role_name in self.needed_local_role_names():
            constellation_role_name = local_role_name
            if test_spec.rolemapping and local_role_name in test_spec.rolemapping:
                constellation_role_name = test_spec.rolemapping[local_role_name]
            args[local_role_name] = constellation.get_node(constellation_role_name)

        test_instance = self.clazz(**args)

        for test_step in self.steps:
            trace(f'Running test { test_spec }, step "{ test_step.name }"')

            try:
                test_step.test_step_function(test_instance) # what an object-oriented language this is

            except AssertionError as e:
                problem = TestClassTestStepProblem(test_spec, e, test_step)
                error('FAILED test assertion:', problem, "\n".join(traceback.format_exception(problem.exc)))
                session.problems.append(problem)
                break # no point about the remaining steps in the test

            except NotImplementedByNodeOrDriverError as e:
                info(f'Skipping test "{ test_spec.name }", step { test_step.name } because: { e }' )

            except Exception as e:
                problem = TestClassTestStepProblem(test_spec, e, test_step)
                error('FAILED test (other reason):', problem, "\n".join(traceback.format_exception(problem.exc)))
                session.problems.append(problem)
                break # no point about the remaining steps in the test



# Tests are contained in all_tests and run from there
all_tests : dict[str,Test] = {}

# Used to collect supposed tested during annotation processing, destructively processed, ignored afterwards
_registered_as_test : dict[str,Any] = {}
_registered_as_test_step : dict[str,Any] = {}

_loading_tests = False


def _full_name_of_function( f: Callable[..., None]) -> str:
    """
    Centralize how test functions and test step functions are named.
    This is the same convention as pytest's I believe
    """
    return f"{f.__module__}::{f.__qualname__}"


def load_tests_from(dirs: list[str]) -> None:
    """
    Load all tests found in the provided directories
    """
    global all_tests
    global _loading_tests
    global _registered_as_test
    global _registered_as_test_step

    # Pass 1: let them all register without any error checking
    _loading_tests = True
    load_python_from(dirs, True)
    _loading_tests = False

    # Pass 2: make sense of what was being registered, error checking and connect them together
    for name, value in _registered_as_test.items():
        test : Test | None
        if isinstance(value, FunctionType):
            test = TestFromTestFunction(name, value.__doc__, value)

        elif isinstance(value, type):
            test = TestFromTestClass(name, value.__doc__, value)
            for _, candidate_step_function in getmembers(value,isfunction):
                candidate_step_name = _full_name_of_function(candidate_step_function)
                if candidate_step_name in _registered_as_test_step:
                    test_step = TestStep(candidate_step_name, candidate_step_function.__doc__, test, candidate_step_function)
                    test.steps.append(test_step)
                    del _registered_as_test_step[candidate_step_name]
                # else ignore, some other function

        else:
            fatal('Cannot register a test that is neither a function nor a class', name)

        if test:
            all_tests[name] = test

    if _registered_as_test_step:
        fatal('Marked as @step, but not a member function of a class marked as @test\n    '
              + '\n    '.join( _registered_as_test_step.keys() ))


def test(to_register: type[Any]) -> type[Any]:
    """
    Use as a decorator to register a supposed test. Use either on a function (running of which constitutes the entire test)
    or on a class (where the tests consists of running __init__ and then all the contained functions maked with @step).

    @test
    def test_something() :
        ...

    @test
    class ArithmeticsTest:
        @step
        def test_step_1() :
            ...
    """
    global _loading_tests
    global _registered_as_test

    if not _loading_tests:
        fatal('Do not define tests outside of testsdir')

    name = _full_name_of_function(to_register)
    if name in _registered_as_test:
        fatal(f'Test with this name registered already: {name}')

    _registered_as_test[name] = to_register
    return to_register


def step(to_register: Callable[..., None]) -> Callable[..., None]:
    """
    Used as decorator to register a step in a test. Use on a non-static function defined in a class
    that has been decorated with @test.
    """
    global _loading_tests
    global _registered_as_test_step

    if not _loading_tests:
        fatal('Do not define test steps outside of testsdir')

    name = _full_name_of_function(to_register)
    if name in _registered_as_test_step:
        fatal(f'Test step with this name registered already: {name}')

    _registered_as_test_step[name] = to_register
    return to_register


_loading_node_drivers = False

def load_node_drivers_from(dirs: list[str]) -> None:
    """
    Load all node drivers found in the provided directories
    """
    global _loading_node_drivers

    _loading_node_drivers = True
    load_python_from(dirs, False)
    _loading_node_drivers = False


# Holds all node drivers
all_node_drivers : dict[str,Type[Any]]= {}

def nodedriver(to_register: Type[Any]):
    """
    Used as decorator of NodeDriver classes, like this:

    @nodedriver
    class XYZDriver : ...
    """
    global _loading_node_drivers
    global all_node_drivers

    if not _loading_node_drivers:
        fatal('Do not define NodeDrivers outside of nodedriversdir')

    if not isinstance(to_register,type):
        fatal('Cannot register a non-Class NodeDriver:', to_register.__name__)

    module = getmodule(to_register)
    if module is not None:
        full_name = f'{module.__name__}.{to_register.__qualname__}'

        if full_name in all_node_drivers:
            fatal('Cannot re-register NodeDriver', full_name )
        all_node_drivers[full_name] = to_register
