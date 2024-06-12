"""
Core module.
"""

from collections.abc import Callable
from enum import Enum
from inspect import getmembers, getmodule, isfunction
from types import FunctionType
from typing import Any,  Type, TypeVar, cast

from hamcrest.core.matcher import Matcher
from hamcrest.core.string_description import StringDescription

from feditest.reporting import fatal, warning
from feditest.tests import (
    Test,
    TestFromTestClass,
    TestFromTestFunction,
    TestStepInTestClass,
)
from feditest.utils import load_python_from

T = TypeVar("T")

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
            test = TestFromTestFunction(
                    name,
                    value.__doc__.strip() if value.__doc__ else None,
                    value)

        elif isinstance(value, type):
            test = TestFromTestClass(
                name,
                value.__doc__.strip() if value.__doc__ else None,
                value)

            # inspect.getmembers lists members alphabetically, while our @step annotations
            # list them in sequence. So we need to process @steps rather than getmembers()
            to_delete = []
            for step_name in _registered_as_test_step:
                for _, candidate_step_function in getmembers(value,isfunction):
                    candidate_step_name = _full_name_of_function(candidate_step_function)
                    if step_name == candidate_step_name:
                        test_step = TestStepInTestClass(
                                candidate_step_name,
                                candidate_step_function.__doc__.strip() if candidate_step_function.__doc__ else None,
                                test,
                                candidate_step_function)
                        test.steps.append(test_step)
                        to_delete.append(step_name)
            for d in to_delete:
                del _registered_as_test_step[d]

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


class SpecLevel(Enum):
    MUST = 1
    SHOULD = 2
    IMPLIED = 3
    UNSPECIFIED = 4


    def formatted_name(self):
        return self.name.capitalize()


class InteropLevel(Enum):
    PROBLEM = 1
    DEGRADED = 2
    UNAFFECTED = 3
    UNKNOWN = 4


    def formatted_name(self):
        return self.name.capitalize()


class AssertionFailure(Exception):
    """
    Indicates a failure in the system under test.
    """
    def __init__(self, spec_level: SpecLevel, interop_level: InteropLevel, msg: Any):
        self.spec_level = spec_level
        self.interop_level = interop_level
        self.msg = msg


    def __str__(self):
        return str(self.msg)


def _assert_match(
    actual: T,
    matcher: Matcher[T],
    reason: str,
    spec_level: SpecLevel,
    interop_level: InteropLevel
) -> None:
    if not matcher.matches(actual):
        description = StringDescription()
        if reason:
            description.append_text(reason).append_text("\n")
        description.append_text("Expected: ").append_description_of(
            matcher
        ).append_text("\n     but: ")
        matcher.describe_mismatch(actual, description)
        description.append_text("\n")
        raise AssertionFailure(spec_level, interop_level, description)


def _assert_bool(
    assertion: bool,
    reason: str,
    spec_level: SpecLevel,
    interop_level: InteropLevel
) -> None:
    if not assertion:
        if not reason:
            reason = "Test failed."
        raise AssertionFailure(spec_level, interop_level, reason)


def assert_that(
    actual_or_assertion: T,
    matcher=None,
    reason="",
    spec_level: SpecLevel | None = None,
    interop_level: InteropLevel | None = None
) -> None:
    """
    Modeled after https://github.com/hamcrest/PyHamcrest/blob/main/src/hamcrest/core/assert_that.py
    """
    # set the defaults here, so we don't have to replicate them in functions that invoke this function, like in the activitypub Node
    if spec_level is None:
        spec_level = SpecLevel.MUST
    if interop_level is None:
        interop_level = InteropLevel.UNKNOWN

    if isinstance(matcher, Matcher):
        _assert_match(actual=actual_or_assertion, matcher=matcher, reason=reason, spec_level=spec_level, interop_level=interop_level)
    else:
        if isinstance(actual_or_assertion, Matcher):
            warning("arg1 should be boolean, but was {}".format(type(actual_or_assertion)))
        _assert_bool(assertion=cast(bool, actual_or_assertion), reason=cast(str, matcher), spec_level=spec_level, interop_level=interop_level)


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
