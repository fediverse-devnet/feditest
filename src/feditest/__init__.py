"""
Core module.
"""

from abc import ABC, abstractmethod
from ast import Module
from collections.abc import Callable
from inspect import signature, getmodule
from pkgutil import resolve_name
from types import FunctionType
from typing import Any

from feditest.iut import IUT

class Test(ABC):
    """
    Captures the notion of a Test, such as "see whether a follower is told about a new post".
    Different Tests may require different numbers of IUTs, and those different constallations
    are represented as subclasses.
    """
    def __init__(self, name: str, description: str, test_set: 'TestSet', function: Callable[[Any], None]) -> None:
        self._name: str = name
        self._description: str = description
        self._function: Callable[Any, None] = function
        if test_set:
            self._test_set = test_set
            test_set.add_test(self)

    def name(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    def test_set(self) -> 'TestSet':
        return self._test_set

    @abstractmethod
    def n_iuts(self) -> int:
        ...


class Constallation1Test(Test):
    """
    Any test that is performed against a single IUT
    """
    def __init__(self, name: str, description: str, test_set: 'TestSet', function: Callable[[IUT], None]) -> None:
        super().__init__(name, description, test_set, function)

    def n_iuts(self) -> int:
        return 1


class Constallation2Test(Test):
    """
    Any test that is performed two IUTs. They may be either of the same type
    (e.g. Mastodon against Mastodon) or of different types.
    """
    def __init__(self, name: str, description: str, test_set: 'TestSet', function: Callable[[IUT, IUT], None]) -> None:
        super().__init__(name, description, test_set, function)

    def n_iuts(self) -> int:
        return 2


class TestSet:
    """
    A set of tests that can be treated as a unit.
    """
    def __init__(self, name: str, description: str, package: Module) -> None:
        self._name = name
        self._description = description
        self._package = package
        self._tests: dict[str,Test] = {}

    def name(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    def add_test(self, to_add: Test) -> None:
        self._tests[to_add.name()] = to_add

    def get(self, name: str) -> Test | None:
        if name in self._tests:
            return self._tests[name]
        else:
            return Non

    def allTests(self):
        return self._tests


class TestPlan:
    """
    A series of steps that can be run to perform one or more tests
    """
    pass


# Tests are contained in their respective TestSets, and in addition also in the all_tests TestSet
all_tests = TestSet('all-tests', 'Collects all availalbe tests', None)
all_test_sets: dict[str,TestSet] = {}

def register_test(to_register: Callable[[Any], None], name: str | None = None, description: str | None = None) -> None:

    if not isinstance(to_register,FunctionType):
        fatal('Cannot register a non-function test')

    module = getmodule(to_register)
    if module :
        package_name = '.'.join( module.__name__.split('.')[0:-1])
        if package_name in all_test_sets:
            test_set = all_test_sets[package_name]
        else:
            package = resolve_name(package_name)
            test_set = TestSet(package_name, package.__doc__, package)
            all_test_sets[package_name] = test_set
    else :
        test_set = None

    if not name:
        name = f"{to_register.__module__}::{to_register.__qualname__}"
        # This is the same convention as pytest's I believe
    if not description:
        description = to_register.__doc__

    sig = signature(to_register)

    match len(sig.parameters):
        case 1:
            test = Constallation1Test(name, description, test_set, to_register)
        case 2:
            test = Constallation2Test(name, description, test_set, to_register)
        case _:
            fatal("FIXME: not implemented")

    all_tests.add_test(test)
    if test_set:
        test_set.add_test(test)
