"""
Core module.
"""

from ast import Module
from collections.abc import Callable
import glob
import importlib.util
from inspect import signature, getmodule
from pkgutil import resolve_name
import sys
from types import FunctionType
from typing import Any

from feditest.protocols import Node
from feditest.reporting import fatal, warning

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

def load_tests_from(dirs: list[str]) -> None:
    sys_path_before = sys.path
    for dir in dirs:
        while dir.endswith('/') :
            dir = dir[:-1]
            
        sys.path.append(dir) # needed to automatially pull in dependencies
        for f in glob.glob(dir + '/**/*.py', recursive=True):
            module_name = f[ len(dir)+1 : -3 ].replace('/', '.' ) # remove dir from the front, and the extension from the back
            if module_name.endswith('__init__'):
                continue
            if not module_name:
                module_name = 'default'
            spec = importlib.util.spec_from_file_location(module_name, f)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        sys.path = sys_path_before


def step(to_register: Callable[..., None]) -> None:
    """
    Used as decorator, like this:
    
    @test
    def test_something() : ...
    """

    if not isinstance(to_register,FunctionType):
        fatal('Cannot register a non-function test')

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

    print( f"XXX registering test_name {test_name}, step_name {step_name} with test_set {test_set.name}")

    if test_name in all_tests.tests:
        test = all_tests.tests[test_name]
        if test.constellation_size != len(step_signature.parameters):
            warning(f'Test step has different signature, constellation size {test.constellation_size} vs {len(step_signature.parameters)}, skipping' )
    else:
        test = Test(test_name, test_description, test_set, len(step_signature.parameters))
        all_tests.tests[test.name] = test
        if test_set:
            test_set.tests[test.name] = test

    step = TestStep(test_name, test_description, test, to_register)
    test.steps.append(step)


class FeditestFailure(RuntimeError):
    """
    Raised when a test failed.
    """
    def FeditestFailure(self, msg: str | Exception):
        super.__init__(msg)


def report_failure(msg: str | Exception) -> None:
    """
    Report a test failure
    msg: the error message
    """
    raise FeditestFailure(msg)


def fassert(condition: bool, msg: str = "Assertion failure" ):
    """
    Our version of assert.
    """
    if not condition:
        raise FeditestFailure(msg)

