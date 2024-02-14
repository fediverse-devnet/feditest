"""
Core module.
"""

from ast import Module
from collections.abc import Callable
from inspect import signature, getmodule
from pkgutil import resolve_name
from types import FunctionType
from typing import Any, Type

from feditest.protocols import Node
from feditest.reporting import fatal, warning
from feditest.utils import load_python_from


class TestStep:
    """
    A step in a test. TestSteps for the same Test are all declared with @step in the same source file,
    and will be executed in sequence unless specified otherwise.
    """
    def __init__(self, name: str, description: str, test: 'Test', function: Callable[..., None]) -> None:
        self.name: str = name
        self.description: str = description
        self.function: Callable[..., None] = function
        self.test = test

        
class Test:
    """
    Captures the notion of a Test, such as "see whether a follower is told about a new post".
    """
    def __init__(self, name: str, description: str, test_set: 'TestSet', constellation_size: int ) -> None:
        self.name: str = name
        self.description: str = description
        self.constellation_size = constellation_size
        self.test_set = test_set
        self.steps = []


class TestSet:
    """
    A set of tests that can be treated as a unit.
    """
    def __init__(self, name: str, description: str, package: Module) -> None:
        self.name = name
        self.description = description
        self.package = package
        self.tests: dict[str,Test] = {}

    def get(self, name: str) -> Test | None:
        if name in self.tests:
            return self.tests[name]
        else:
            return None

    def all(self) -> dict[str,Test]:
        return self.tests


# Tests are contained in their respective TestSets, and in addition also in the all_tests TestSet
all_tests = TestSet('all-tests', 'Collects all available tests', None)
all_test_sets: dict[str,TestSet] = {}

_loading_tests = False


def load_tests_from(dirs: list[str]) -> None:
    global _loading_tests
    
    _loading_tests = True
    load_python_from(dirs, True)
    _loading_tests = False


def step(to_register: Callable[..., None]) -> None:
    """
    Used as decorator of test functions, like this:
    
    @step
    def test_something() : ...
    """
    global _loading_tests
    global all_tests
    global all_test_sets

    if not _loading_tests:
        fatal('Do not define tests outside of testsdir')

    if not isinstance(to_register,FunctionType):
        fatal('Cannot register a non-function test:', to_register.__name__)

    module = getmodule(to_register)
    parent_module_name = '.'.join( module.__name__.split('.')[0:-1])
    if parent_module_name :
        if parent_module_name in all_test_sets:
            test_set = all_test_sets[parent_module_name]
        else:
            parent_module = resolve_name(parent_module_name)
            test_set = TestSet(parent_module_name, parent_module.__doc__, parent_module)
            all_test_sets[parent_module_name] = test_set
    else:
        test_set = None

    test_name = to_register.__module__
    test_description = module.__doc__
    step_name = f"{test_name}::{to_register.__qualname__}" # The same convention as pytest's I believe, but applied for steps
    step_description = to_register.__doc__
    step_signature = signature(to_register)

    if test_name in all_tests.tests:
        test = all_tests.tests[test_name]
        if test.constellation_size != len(step_signature.parameters):
            warning(f'Test step has different signature, constellation size {test.constellation_size} vs {len(step_signature.parameters)}, skipping' )
    else:
        test = Test(test_name, test_description, test_set, len(step_signature.parameters))
        all_tests.tests[test.name] = test
        if test_set:
            test_set.tests[test.name] = test

    step = TestStep(step_name, step_description, test, to_register)
    test.steps.append(step)


_loading_node_drivers = False

def load_node_drivers_from(dirs: list[str]) -> None:
    global _loading_node_drivers
    
    _loading_node_drivers = True
    load_python_from(dirs, False)
    _loading_node_drivers = False
    

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
    full_name = f'{module.__name__}.{to_register.__qualname__}'

    if full_name in all_node_drivers:
        fatal('Cannot re-register NodeDriver', full_name )
    all_node_drivers[full_name] = to_register
