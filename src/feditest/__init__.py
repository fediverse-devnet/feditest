"""
Core module.
"""

from abc import ABC
from collections.abc import Callable
from inspect import signature
from types import FunctionType
from typing import Any

from feditest.iut import IUT


class Test(ABC):
    def __init__(self, name: str, function: Callable[[Any], None]) -> None:
        self._name: str = name
        self._function: Callable[Any, None] = function


class Constallation1Test(Test):
    def __init__(self, name: str, function: Callable[[IUT], None]) -> None:
        super.__init__(str, function)


class Constallation2Test(Test):
    def __init__(self, name: str, function: Callable[[IUT, IUT], None]) -> None:
        super.__init__(str, function)


class TestSet:
    def __init__(self) -> None:
        self._constellation1Tests: dict[str,Constallation1Test] = {}
        self._constellation2Tests: dict[str,Constallation2Test] = {}

    def register_test(self, to_register: Callable[[Any], None], name: str) -> None:
        if not isinstance(to_register,FunctionType):
            fatal('Cannot register a non-function test')

        if not name:
            name = to_register.__qualname__

        sig = signature(to_register)

        match len(sig.parameters):
            case 1:
                self._constellation1Tests[name] = to_register
            case 2:
                self._constellation2Tests[name] = to_register

    def allTests(self):
        return { **self._constellation1Tests, **self._constellation2Tests }


allTests = TestSet()

def register_test(to_register: Callable[[Any], None], name: str = None) -> None:
    allTests.register_test(to_register, name)


